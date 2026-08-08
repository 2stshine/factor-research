"""Point-in-time financial features materialized from certified Silver rows.

Silver stores every filing revision in long form.  We replay those revisions by
``available_date`` instead of using ``fundamental_current``; the latter is a
current-state view and would leak later restatements into historical months.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from engine import silver


FLOW = frozenset({
    "revenue", "operating_income", "pretax_income", "net_income",
    "comprehensive_income",
})
STOCK = frozenset({
    "total_assets", "current_assets", "noncurrent_assets",
    "total_liabilities", "current_liabilities", "noncurrent_liabilities",
    "total_equity", "capital_stock", "retained_earnings",
})
ALL_METRICS = FLOW | STOCK
PIT_FEATURES = (
    STOCK
    | FLOW
    | frozenset(f"{metric}_ttm" for metric in FLOW)
    | frozenset({"net_income_yoy_change", "sue_score"})
)


def _priority(row: Mapping) -> tuple:
    """Consolidated statements dominate separate statements, then latest filing."""
    return (
        1 if row["fs_type"] == "CFS" else 0,
        pd.Timestamp(row["available_date"]),
        str(row["revision_key"]),
    )


def _standalone_flow(state: dict, metric: str) -> list[tuple[pd.Timestamp, str, float]]:
    records = [
        (period_end, fiscal_period, float(row["value"]))
        for (period_end, fiscal_period, met), row in state.items()
        if met == metric and pd.notna(row["value"])
    ]
    records.sort(key=lambda x: x[0])
    direct = {(pe, fp): value for pe, fp, value in records if fp in {"Q1", "Q2", "Q3", "Q4"}}
    fiscal_years = [(pe, value) for pe, fp, value in records if fp == "FY"]

    previous_fy: pd.Timestamp | None = None
    for fy_end, fy_value in fiscal_years:
        if (fy_end, "Q4") in direct:
            previous_fy = fy_end
            continue
        lower = previous_fy if previous_fy is not None else fy_end - pd.Timedelta(days=370)
        quarters: dict[str, tuple[pd.Timestamp, float]] = {}
        for pe, fp, value in records:
            if fp in {"Q1", "Q2", "Q3"} and lower < pe < fy_end:
                prior = quarters.get(fp)
                if prior is None or pe > prior[0]:
                    quarters[fp] = (pe, value)
        if set(quarters) == {"Q1", "Q2", "Q3"}:
            direct[(fy_end, "Q4")] = fy_value - sum(v for _, v in quarters.values())
        previous_fy = fy_end

    # One standalone observation per period.  Explicit Q4 wins over a derived one.
    by_period: dict[pd.Timestamp, tuple[str, float]] = {}
    order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    for (period_end, fiscal_period), value in direct.items():
        prior = by_period.get(period_end)
        if prior is None or order[fiscal_period] >= order[prior[0]]:
            by_period[period_end] = (fiscal_period, value)
    return [(pe, fp, value) for pe, (fp, value) in sorted(by_period.items())]


def _snapshot(state: dict, asset_id: int, available_date: pd.Timestamp) -> dict:
    out: dict[str, object] = {"asset_id": asset_id, "available_date": available_date}
    # Balance-sheet metrics occasionally can be represented by more than one
    # fiscal-period label on the same period end.  Make that tie deterministic
    # and identical to the Gold SQL contract instead of depending on input row
    # order from the database.
    stock_period_order = {"Q1": 1, "Q2": 2, "Q3": 3, "FY": 4, "Q4": 5}
    for metric in STOCK:
        known = [
            (period_end, fiscal_period, row)
            for (period_end, fiscal_period, met), row in state.items()
            if met == metric and pd.notna(row["value"])
        ]
        latest = max(
            known,
            key=lambda item: (item[0], stock_period_order.get(item[1], 0)),
        ) if known else None
        out[metric] = float(latest[2]["value"]) if latest is not None else np.nan

    flow_series: dict[str, list[tuple[pd.Timestamp, str, float]]] = {}
    for metric in FLOW:
        series = _standalone_flow(state, metric)
        flow_series[metric] = series
        out[metric] = series[-1][2] if series else np.nan
        recent = series[-4:]
        complete_year = (
            len(recent) == 4
            and (recent[-1][0] - recent[0][0]).days <= 370
        )
        out[f"{metric}_ttm"] = sum(x[2] for x in recent) if complete_year else np.nan

    ni = flow_series.get("net_income", [])
    changes = [
        ni[i][2] - ni[i - 4][2]
        for i in range(4, len(ni))
        if ni[i][1] == ni[i - 4][1]
        and 330 <= (ni[i][0] - ni[i - 4][0]).days <= 400
    ]
    latest_change = changes[-1] if changes else np.nan
    recent_changes = changes[-8:]
    scale = np.std(recent_changes, ddof=1) if len(recent_changes) >= 4 else np.nan
    out["net_income_yoy_change"] = latest_change
    out["sue_score"] = (
        latest_change / scale
        if pd.notna(latest_change) and pd.notna(scale) and scale > 0
        else np.nan
    )
    return out


def materialize_pit(rows: pd.DataFrame, *, verbose: bool = True) -> pd.DataFrame:
    """Replay filing revisions and emit a wide feature snapshot at each event date."""
    if rows.empty:
        columns = ["asset_id", "available_date", *sorted(STOCK)]
        columns += [x for metric in sorted(FLOW) for x in (metric, f"{metric}_ttm")]
        columns += ["net_income_yoy_change", "sue_score"]
        return pd.DataFrame(columns=columns)

    required = {
        "asset_id", "period_end", "fiscal_period", "fs_type", "available_date",
        "metric", "value", "revision_key",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"Silver 재무 필수 컬럼 누락: {sorted(missing)}")

    d = rows[rows["metric"].isin(ALL_METRICS)].copy()
    d["asset_id"] = pd.to_numeric(d["asset_id"], errors="raise").astype("int64")
    d["period_end"] = pd.to_datetime(d["period_end"], errors="coerce")
    d["available_date"] = pd.to_datetime(d["available_date"], errors="coerce")
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    d = d.dropna(subset=["period_end", "available_date", "value"])
    d = d.sort_values(["asset_id", "available_date", "revision_key", "metric"])

    snapshots: list[dict] = []
    for asset_id, asset_rows in d.groupby("asset_id", sort=False):
        state: dict[tuple[pd.Timestamp, str, str], dict] = {}
        for available_date, event in asset_rows.groupby("available_date", sort=True):
            changed = False
            for row in event.to_dict("records"):
                key = (pd.Timestamp(row["period_end"]), str(row["fiscal_period"]), str(row["metric"]))
                prior = state.get(key)
                if prior is None or _priority(row) > _priority(prior):
                    state[key] = row
                    changed = True
            if changed:
                snapshots.append(_snapshot(state, int(asset_id), pd.Timestamp(available_date)))

    out = pd.DataFrame(snapshots).sort_values(["available_date", "asset_id"]).reset_index(drop=True)
    if verbose:
        print(
            f"[fund] Silver PIT {len(out):,}스냅샷 / "
            f"{out['asset_id'].nunique():,}종목 / revision replay"
        )
    return out


def build(conn, *, verbose: bool = True) -> pd.DataFrame:
    if verbose:
        print("[fund] RDS Silver 재무 revision 로딩...", flush=True)
    rows = silver.load_fundamentals(conn, sorted(ALL_METRICS))
    return materialize_pit(rows, verbose=verbose)


def attach(monthly: pd.DataFrame, fund: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Attach only the latest financial snapshot known by each month end."""
    left = monthly.copy()
    left["me_date"] = pd.to_datetime(left["trade_date"]).astype("datetime64[ns]")
    left = left.sort_values(["me_date", "asset_id"])
    have = [column for column in cols if column in fund.columns]
    missing = sorted(set(cols) - set(have))
    if missing:
        raise ValueError(f"Silver 재무에서 만들 수 없는 팩터 입력: {missing}")
    if fund.empty:
        for column in have:
            left[column] = np.nan
        return left

    right = fund[["asset_id", "available_date", *have]].copy()
    right["available_date"] = pd.to_datetime(right["available_date"]).astype("datetime64[ns]")
    right = right.sort_values(["available_date", "asset_id"])
    return pd.merge_asof(
        left,
        right,
        left_on="me_date",
        right_on="available_date",
        by="asset_id",
        direction="backward",
        allow_exact_matches=True,
    )
