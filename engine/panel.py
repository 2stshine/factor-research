"""Certified Silver price panel and the immutable research universe."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from engine import silver


MIN_LISTING_DAYS = 250
# Research does not know the user's AUM or order size, so an arbitrary KRW
# capacity cutoff would redefine the evidence.  Keep only a basic "traded"
# contract here; capacity is assessed later as order size / ADV20.
INVESTABLE_ADV = 0.0
SUPPORTED_MARKETS = ("KOSPI", "KOSDAQ")
INACTIVE_DAYS = 45


@dataclass
class Panel:
    """Month-end PIT panel shared by factor computation and every gate."""

    monthly: pd.DataFrame
    dead: pd.Series  # inactive/delisted asset_id -> last observed trading date
    meta: dict = field(default_factory=dict)

    @property
    def universe(self) -> pd.Series:
        d = self.monthly
        return (
            d["in_universe"]
            & d["market_cap"].notna()
            & (d["market_cap"] > 0)
            & d["return_close"].notna()
            & (d["return_close"] > 0)
        )

    @property
    def investable(self) -> pd.Series:
        return self.universe & (self.monthly["adv20"] > INVESTABLE_ADV)


def snapshot_digest(panel: Panel) -> str:
    """Hash the exact non-factor panel, terminal set, and boundary metadata."""
    columns = sorted(
        column for column in panel.monthly.columns
        if not str(column).startswith("f_")
    )
    order = [
        column for column in ("asset_id", "ym", "trade_date")
        if column in panel.monthly.columns
    ]
    frame = panel.monthly[columns]
    if order:
        frame = frame.sort_values(order, kind="mergesort")
    frame = frame.reset_index(drop=True)
    schema = [(str(column), str(frame[column].dtype)) for column in columns]
    metadata = {str(key): str(value) for key, value in sorted(panel.meta.items())}
    dead = sorted(
        (str(asset_id), str(pd.Timestamp(last_seen)))
        for asset_id, last_seen in panel.dead.items()
    )
    digest = hashlib.sha256()
    digest.update(json.dumps(
        {"schema": schema, "meta": metadata, "dead": dead},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8"))
    digest.update(pd.util.hash_pandas_object(
        frame, index=False, categorize=True,
    ).values.tobytes())
    return digest.hexdigest()


def _numeric(d: pd.DataFrame, columns: tuple[str, ...]) -> None:
    for column in columns:
        d[column] = pd.to_numeric(d[column], errors="coerce")


def from_silver_frame(prices: pd.DataFrame, *, verbose: bool = True) -> Panel:
    """Normalize the result of ``PRICE_SNAPSHOT_SQL`` into the engine contract."""
    if prices.empty:
        raise RuntimeError("인증된 KRX Silver price_daily 행이 없습니다")

    return_contract = prices.attrs.get("return_contract")
    if not isinstance(return_contract, dict):
        raise RuntimeError(
            "Silver total_return_close의 배당 포함 방법론 계약이 없습니다"
        )
    if (
        return_contract.get("status") != "CERTIFIED"
        or return_contract.get("methodology_version")
        != silver.TOTAL_RETURN_METHOD
    ):
        raise RuntimeError(
            "Silver total_return_close 방법론 계약이 인증 기준과 다릅니다: "
            f"{return_contract}"
        )

    required = {
        "asset_id", "Code", "Name", "instrument_type", "trade_date",
        "adj_close", "total_return_close", "trading_value", "market_cap",
        "shares", "market", "adv20", "age_days", "first_seen",
        "dataset_start", "quality_run_id", "amihud_illiquidity_1m",
        "amihud_observations_1m", "daily_volatility_252d",
        "daily_return_observations_252d", "max_daily_return_1m",
        "max_daily_return_observations_1m", "price_high_252d",
        "price_high_observations_252d",
    }
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Silver 가격 스냅샷 필수 컬럼 누락: {sorted(missing)}")

    d = prices.copy()
    d["asset_id"] = pd.to_numeric(d["asset_id"], errors="raise").astype("int64")
    d["Code"] = d["Code"].astype(str)
    for column in ("trade_date", "first_seen", "dataset_start", "listed_from", "listed_to"):
        if column in d:
            d[column] = pd.to_datetime(d[column], errors="coerce")
    _numeric(
        d,
        ("close", "adj_close", "total_return_close", "trading_value",
         "market_cap", "shares", "adv20", "age_days",
         "amihud_illiquidity_1m", "amihud_observations_1m",
         "daily_volatility_252d", "daily_return_observations_252d",
         "max_daily_return_1m", "max_daily_return_observations_1m",
         "price_high_252d", "price_high_observations_252d"),
    )
    bad_total_return = d["total_return_close"].isna() | (d["total_return_close"] <= 0)
    if bad_total_return.any():
        raise RuntimeError(
            "Silver total_return_close가 비었거나 0 이하입니다: "
            f"{int(bad_total_return.sum()):,}행. 총수익 적재를 완료한 뒤 build 하세요."
        )

    d["return_close"] = d["total_return_close"]
    d["amount"] = d["trading_value"]
    d["Market"] = d["market"]
    d["ym"] = d["trade_date"].dt.to_period("M")

    name = d["Name"].fillna("").astype(str)
    d["ok_market"] = d["market"].isin(SUPPORTED_MARKETS)
    d["ok_common"] = d["instrument_type"].eq("common_stock")
    d["is_spac"] = name.str.contains("스팩|SPAC", case=False, regex=True)
    # KRX asset classification currently distinguishes preferred/common only.
    # Keep the explicit name guard until Silver promotes REIT to instrument_type.
    d["is_reit"] = d["instrument_type"].eq("reit") | name.str.contains("리츠")
    d["seasoned"] = d["first_seen"].eq(d["dataset_start"])
    d["ok_age"] = (d["age_days"] >= MIN_LISTING_DAYS) | d["seasoned"]
    d["in_universe"] = (
        d["ok_market"] & d["ok_common"] & ~d["is_spac"]
        & ~d["is_reit"] & d["ok_age"]
    )
    d["is_distress"] = False  # Silver has no PIT distress classification yet.

    d = d.sort_values(["asset_id", "ym"]).reset_index(drop=True)
    if d.duplicated(["asset_id", "ym"]).any():
        raise RuntimeError("Silver 월말 스냅샷 키(asset_id, ym)가 중복되었습니다")

    last_day = d["trade_date"].max()
    last_seen = d.groupby("asset_id")["trade_date"].max()
    dead = last_seen[last_seen < last_day - pd.Timedelta(days=INACTIVE_DAYS)]
    meta = {
        "source": "RDS public Silver",
        "last_day": last_day,
        "n_dead": len(dead),
        "n_stocks": d["asset_id"].nunique(),
        "quality_run_ids": sorted(d["quality_run_id"].dropna().astype(str).unique()),
        "return_field": "total_return_close",
        "return_methodology": return_contract["methodology_version"],
        "return_contract_status": return_contract["status"],
        "return_contract_run_id": return_contract.get("quality_run_id"),
    }
    if verbose:
        snap = d[d["ym"] == d["ym"].max()]
        print(
            f"[panel] Silver {len(d):,}행 / {d['ym'].nunique()}개월 / "
            f"최종 유니버스 {int(snap['in_universe'].sum()):,}종목 / "
            f"비활성·상폐 {len(dead):,}종목"
        )
    return Panel(monthly=d, dead=dead, meta=meta)


def build(conn, *, verbose: bool = True) -> Panel:
    """Load a certified, immutable month-end snapshot from RDS Silver."""
    if verbose:
        print("[panel] RDS Silver 월말 가격 로딩...", flush=True)
    return from_silver_frame(silver.load_price_snapshot(conn), verbose=verbose)


def forward_returns(panel: Panel, terminal: float = -0.50) -> pd.Series:
    """One-month total return with an explicit terminal return for inactive assets."""
    d = panel.monthly.sort_values(["asset_id", "ym"])
    next_close = d.groupby("asset_id")["return_close"].shift(-1)
    next_ym = d.groupby("asset_id")["ym"].shift(-1)
    consecutive = next_ym.eq(d["ym"] + 1)
    fwd = (next_close / d["return_close"] - 1).where(consecutive)

    last_ym = d["ym"].max()
    last_for_asset = d["ym"].eq(d.groupby("asset_id")["ym"].transform("max"))
    is_terminal = (
        last_for_asset
        & d["asset_id"].isin(panel.dead.index)
        & d["ym"].ne(last_ym)
    )
    return pd.Series(np.where(is_terminal, terminal, fwd), index=d.index).reindex(
        panel.monthly.index
    )
