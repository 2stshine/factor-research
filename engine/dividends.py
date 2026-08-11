"""Point-in-time trailing cash dividends from the certified Silver rebuild.

The total-return rebuild can apply a dividend on its historical ex-date even
when the issuer announces the final cash amount later.  A research signal must
not inherit that hindsight.  An event therefore enters a month-end signal only
after both its applied trade date and the day after its announcement, and it
expires once its applied trade date is outside the trailing 12-month window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import silver


DIVIDEND_CASH_TTM = "dividend_cash_ttm"
DIVIDEND_EVENT_COUNT_TTM = "dividend_event_count_ttm"
FEATURE_VERSION = "certified_canonical_applied_dividend_ttm_v1"
PIT_FEATURES = frozenset({DIVIDEND_CASH_TTM, DIVIDEND_EVENT_COUNT_TTM})
PIT_AVAILABILITY_META_KEY = "dividend_pit_availability_contract"


def pit_availability_contract() -> dict:
    """Exact evidence required for point-in-time dividend feature exposure."""
    return {
        "contract": silver.DIVIDEND_PIT_AVAILABILITY_CONTRACT,
        "canonical_resolution_only": True,
        "known_at_field": "announcement_date",
        "known_at_lag_days": 1,
    }


def _verify_pit_availability_contract(history: pd.DataFrame) -> None:
    expected = pit_availability_contract()
    actual = history.attrs.get("pit_availability_contract")
    if actual != expected:
        raise RuntimeError(
            "Silver 배당 이력의 latest terminal announcement PIT 계약이 "
            f"없거나 다릅니다: {actual!r}"
        )


def _certified_coverage(history: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    contract = history.attrs.get("return_contract")
    if not isinstance(contract, dict):
        raise RuntimeError("Silver 배당 이력에 총수익 계약 메타데이터가 없습니다")
    if (
        contract.get("status") != "CERTIFIED"
        or contract.get("methodology_version") != silver.TOTAL_RETURN_METHOD
    ):
        raise RuntimeError(
            "Silver 배당 이력의 총수익 계약이 인증 기준과 다릅니다: "
            f"{contract}"
        )
    evidence = silver.verify_total_return_validation_evidence(
        contract.get("validation_evidence"),
    )
    if str(contract.get("quality_run_id")) != str(evidence["quality_run_id"]):
        raise RuntimeError(
            "Silver 배당 이력 계약 run과 validation evidence run이 다릅니다"
        )
    start = pd.to_datetime(contract.get("coverage_start"), errors="coerce")
    end = pd.to_datetime(contract.get("coverage_end"), errors="coerce")
    if pd.isna(start) or pd.isna(end) or start > end:
        raise RuntimeError(
            "Silver 배당 이력의 인증 coverage_start/coverage_end가 잘못되었습니다"
        )
    if (
        start.date().isoformat() != evidence["coverage_start"]
        or end.date().isoformat() != evidence["coverage_end"]
    ):
        raise RuntimeError(
            "Silver 배당 이력 coverage와 validation evidence가 다릅니다"
        )
    return pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()


def attach(monthly: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Attach PIT trailing-12-month adjusted cash DPS to month-end rows.

    The window is ``(month_end - 12 months, month_end]`` on
    ``applied_trade_date``.  Within certified coverage, a stock with no known
    applied event receives explicit ``0.0`` and ``0``; rows outside coverage
    remain missing so they cannot be mistaken for non-dividend payers.
    """
    required_monthly = {"asset_id", "trade_date"}
    missing_monthly = required_monthly - set(monthly.columns)
    if missing_monthly:
        raise ValueError(
            "월말 패널의 배당 필수 컬럼 누락: "
            f"{sorted(missing_monthly)}"
        )

    coverage_start, coverage_end = _certified_coverage(history)
    _verify_pit_availability_contract(history)
    output = monthly.copy()
    asset_ids = pd.to_numeric(output["asset_id"], errors="coerce")
    as_of = pd.to_datetime(output["trade_date"], errors="coerce").dt.normalize()
    if asset_ids.isna().any() or as_of.isna().any():
        raise ValueError("월말 패널의 asset_id/trade_date는 비어 있을 수 없습니다")
    asset_ids = asset_ids.astype("int64")

    within_coverage = as_of.between(
        coverage_start, coverage_end, inclusive="both",
    ).to_numpy()
    cash = np.full(len(output), np.nan, dtype=float)
    counts = np.full(len(output), np.nan, dtype=float)
    cash[within_coverage] = 0.0
    counts[within_coverage] = 0.0

    if history.empty:
        output[DIVIDEND_CASH_TTM] = cash
        output[DIVIDEND_EVENT_COUNT_TTM] = pd.array(counts, dtype="Int64")
        return output

    required_history = {
        "asset_id",
        "source",
        "action_key",
        "resolution_version",
        "announcement_date",
        "applied_trade_date",
        "adjusted_cash_amount",
        "quality_run_id",
    }
    missing_history = required_history - set(history.columns)
    if missing_history:
        raise ValueError(
            "Silver 배당 이력 필수 컬럼 누락: "
            f"{sorted(missing_history)}"
        )

    events = history.copy()
    events["asset_id"] = pd.to_numeric(
        events["asset_id"], errors="coerce",
    )
    events["announcement_date"] = pd.to_datetime(
        events["announcement_date"], errors="coerce",
    ).dt.normalize()
    events["applied_trade_date"] = pd.to_datetime(
        events["applied_trade_date"], errors="coerce",
    ).dt.normalize()
    events["adjusted_cash_amount"] = pd.to_numeric(
        events["adjusted_cash_amount"], errors="coerce",
    )
    invalid = (
        events["asset_id"].isna()
        | events["announcement_date"].isna()
        | events["applied_trade_date"].isna()
        | events["adjusted_cash_amount"].isna()
        | ~np.isfinite(events["adjusted_cash_amount"])
        | events["adjusted_cash_amount"].le(0)
    )
    if invalid.any():
        raise RuntimeError(
            "인증된 Silver 배당 이력에 PIT 계산 불가능한 행이 있습니다: "
            f"{int(invalid.sum())}행"
        )
    events["asset_id"] = events["asset_id"].astype("int64")
    event_key = ["asset_id", "source", "action_key", "resolution_version"]
    if events.duplicated(event_key).any():
        raise RuntimeError("인증된 Silver 배당 resolution 키가 중복되었습니다")

    # ``announcement_date`` belongs to the latest terminal POSITIVE receipt
    # selected by the canonical resolution. One calendar day after that filing
    # is a deliberately conservative PIT availability rule. The applied-date
    # condition separately prevents an announced future dividend from entering
    # the trailing realized cash sum.
    events["known_date"] = (
        events["announcement_date"] + pd.Timedelta(days=1)
    )
    events_by_asset = {
        int(asset_id): group
        for asset_id, group in events.groupby("asset_id", sort=False)
    }
    asset_array = asset_ids.to_numpy()
    as_of_array = as_of.to_numpy(dtype="datetime64[ns]")

    for asset_id in np.unique(asset_array[within_coverage]):
        event_rows = events_by_asset.get(int(asset_id))
        if event_rows is None:
            continue
        positions = np.flatnonzero(within_coverage & (asset_array == asset_id))
        month_dates = pd.DatetimeIndex(as_of.iloc[positions])
        lower_bounds = (
            month_dates - pd.DateOffset(months=12)
        ).to_numpy(dtype="datetime64[ns]")
        month_values = month_dates.to_numpy(dtype="datetime64[ns]")
        applied = event_rows["applied_trade_date"].to_numpy(
            dtype="datetime64[ns]",
        )
        known = event_rows["known_date"].to_numpy(dtype="datetime64[ns]")
        amounts = event_rows["adjusted_cash_amount"].to_numpy(dtype=float)
        eligible = (
            (applied[None, :] > lower_bounds[:, None])
            & (applied[None, :] <= month_values[:, None])
            & (known[None, :] <= month_values[:, None])
        )
        cash[positions] = eligible @ amounts
        counts[positions] = eligible.sum(axis=1)

    output[DIVIDEND_CASH_TTM] = cash
    output[DIVIDEND_EVENT_COUNT_TTM] = pd.array(counts, dtype="Int64")
    return output
