"""Point-in-time financial features materialized from certified Silver rows.

Silver stores every filing revision in long form.  We replay those revisions by
``available_date`` instead of using ``fundamental_current``; the latter is a
current-state view and would leak later restatements into historical months.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from engine import silver


FUNDAMENTAL_METHODOLOGY_VERSION = "dart-pit-contiguous-fiscal-quarters-v2"


def source_sha256() -> str:
    """Bind a rebuilt panel to the complete implementation, not just a label."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


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


def is_contiguous_fiscal_quarters(
    records: list[tuple[pd.Timestamp, str, float]],
) -> bool:
    """Recognize consecutive declared quarters under one consistent calendar.

    Calendar-month schedules advance three months from the first endpoint
    (preserving month-end for month-end schedules).  Weekly schedules use a
    common weekday and 13-week quarters, with at most one 14-week quarter in
    the inspected, at-most-one-year chain.  This admits 52/53-week reporting
    without an arbitrary day tolerance or assuming a December year end.

    This is a structural check, not certification of a fiscal calendar.  The
    source has no period_start/calendar_id: a calendar change indistinguishable
    from one of these schedules cannot be diagnosed from these fields alone.
    Missing values/dates, duplicate endpoints, label discontinuities and
    unrecognized schedules fail closed.  Callers must not drop such barriers.
    """
    if not 2 <= len(records) <= 5:
        return False
    order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    dates = tuple(pd.Timestamp(row[0]) for row in records)
    labels = tuple(order.get(row[1]) for row in records)
    if (
        any(pd.isna(date) for date in dates)
        or any(label is None for label in labels)
        or any(not np.isfinite(row[2]) for row in records)
    ):
        return False
    return _quarter_structure_is_contiguous(dates, labels)


@lru_cache(maxsize=8192)
def _quarter_structure_is_contiguous(
    dates: tuple[pd.Timestamp, ...], labels: tuple[int, ...],
) -> bool:
    """Cache only immutable endpoint structure; never cache financial values.

    Revision replay repeats these calendar checks for many metrics and event
    dates.  Finite-value checks remain outside the cache so a newly missing
    value cannot reuse an earlier successful TTM decision.
    """
    if (
        any(right <= left for left, right in zip(dates, dates[1:]))
        or any(right != left % 4 + 1 for left, right in zip(labels, labels[1:]))
    ):
        return False

    if all(date.is_month_end for date in dates):
        calendar = all(
            date == dates[0] + pd.offsets.MonthEnd(3 * position)
            for position, date in enumerate(dates)
        )
    else:
        calendar = all(
            date == dates[0] + pd.DateOffset(months=3 * position)
            for position, date in enumerate(dates)
        )
    if calendar:
        return True

    gaps = [(right - left).days for left, right in zip(dates, dates[1:])]
    return (
        len({date.dayofweek for date in dates}) == 1
        and all(gap in {13 * 7, 14 * 7} for gap in gaps)
        and gaps.count(14 * 7) <= 1
    )


def _standalone_flow(state: dict, metric: str) -> list[tuple[pd.Timestamp, str, float]]:
    records = [
        (period_end, fiscal_period, float(row["value"]) if pd.notna(row["value"]) else np.nan)
        for (period_end, fiscal_period, met), row in state.items()
        if met == metric
    ]
    records.sort(key=lambda x: (x[0], x[1]))
    by_period: dict[pd.Timestamp, tuple[str, float]] = {}
    for period_end, fiscal_period, value in records:
        if fiscal_period == "FY":
            continue
        # Different fiscal labels for one endpoint are not a priority choice.
        # Preserve a NaN barrier so a later rolling window cannot skip it.
        if period_end in by_period or fiscal_period not in {"Q1", "Q2", "Q3", "Q4"}:
            by_period[period_end] = ("INVALID", np.nan)
        else:
            by_period[period_end] = (fiscal_period, value)
    fiscal_years = [(pe, value) for pe, fp, value in records if fp == "FY"]

    previous_fy: pd.Timestamp | None = None
    for fy_end, fy_value in fiscal_years:
        explicit = by_period.get(fy_end)
        if explicit is not None and explicit[0] == "Q4":
            # An explicit standalone Q4 is not overwritten by an FY residual.
            previous_fy = fy_end
            continue
        prior = [
            (pe, fp, value)
            for pe, (fp, value) in sorted(by_period.items()) if pe < fy_end
        ][-3:]
        chain = [*prior, (fy_end, "Q4", fy_value)]
        valid = (
            explicit is None
            and [row[1] for row in prior] == ["Q1", "Q2", "Q3"]
            and is_contiguous_fiscal_quarters(chain)
        )
        if valid and previous_fy is not None:
            # Do not infer a normal annual interval across an observed changed
            # FY boundary (or an unobserved intervening FY).  Its value is not
            # used: only the endpoint establishes the same fiscal-year chain.
            valid = is_contiguous_fiscal_quarters(
                [(previous_fy, "Q4", 0.0), *chain]
            )
        if valid:
            by_period[fy_end] = ("Q4", fy_value - sum(row[2] for row in prior))
        else:
            # A known latest FY with unprovable Q4 must invalidate current TTM,
            # rather than silently returning the last four older observations.
            by_period[fy_end] = ("INVALID", np.nan)
        previous_fy = fy_end

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
            and is_contiguous_fiscal_quarters(recent)
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
    # A dated missing/retracted value is an observation, not permission to
    # skip a fiscal period or keep an older revision of that same flow value.
    d = d.dropna(subset=["period_end", "available_date"])
    # This version changes the flow/TTM contract only.  Preserve the existing
    # stock policy (ignore missing stock rows) rather than changing balance-
    # sheet revision fallback as an incidental consequence of flow barriers.
    d = d[d["value"].notna() | d["metric"].isin(FLOW)]
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
