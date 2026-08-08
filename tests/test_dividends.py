from __future__ import annotations

import pandas as pd
import pytest

from engine import dividends, silver


HISTORY_COLUMNS = [
    "asset_id",
    "source",
    "action_key",
    "resolution_version",
    "announcement_date",
    "applied_trade_date",
    "adjusted_cash_amount",
    "quality_run_id",
]


def _history(
    rows: list[dict] | None = None,
    *,
    coverage_start: str = "2024-01-02",
    coverage_end: str = "2026-12-31",
) -> pd.DataFrame:
    frame = pd.DataFrame(rows or [], columns=HISTORY_COLUMNS)
    frame.attrs["return_contract"] = {
        "status": "CERTIFIED",
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "quality_run_id": "return-run",
    }
    return frame


def _event(
    *,
    announcement_date: str,
    applied_trade_date: str,
    amount: float = 100.0,
    action_key: str = "event-1",
) -> dict:
    return {
        "asset_id": 1,
        "source": "DART_DISCLOSURE",
        "action_key": action_key,
        "resolution_version": "krx_dividend_resolution_v1",
        "announcement_date": announcement_date,
        "applied_trade_date": applied_trade_date,
        "adjusted_cash_amount": amount,
        "quality_run_id": "return-run",
    }


def _monthly(*dates: str, asset_id: int = 1) -> pd.DataFrame:
    return pd.DataFrame({
        "asset_id": [asset_id] * len(dates),
        "trade_date": pd.to_datetime(list(dates)),
    })


def test_late_announcement_is_not_visible_until_the_following_day():
    history = _history([_event(
        announcement_date="2024-01-31",
        applied_trade_date="2024-01-15",
        amount=250.0,
    )])
    result = dividends.attach(
        _monthly("2024-01-31", "2024-02-29"), history,
    )

    assert result["dividend_cash_ttm"].tolist() == [0.0, 250.0]
    assert result["dividend_event_count_ttm"].tolist() == [0, 1]


def test_announced_future_dividend_waits_for_applied_trade_date():
    history = _history([_event(
        announcement_date="2024-01-15",
        applied_trade_date="2024-02-15",
    )])
    result = dividends.attach(
        _monthly("2024-01-31", "2024-02-29"), history,
    )

    assert result["dividend_cash_ttm"].tolist() == [0.0, 100.0]
    assert result["dividend_event_count_ttm"].tolist() == [0, 1]


def test_event_expires_at_the_open_lower_bound_of_the_12_month_window():
    history = _history([_event(
        announcement_date="2024-01-01",
        applied_trade_date="2024-01-31",
        amount=75.0,
    )])
    result = dividends.attach(
        _monthly("2025-01-30", "2025-01-31"), history,
    )

    assert result["dividend_cash_ttm"].tolist() == [75.0, 0.0]
    assert result["dividend_event_count_ttm"].tolist() == [1, 0]


def test_zero_event_month_is_zero_but_precoverage_row_is_missing():
    result = dividends.attach(
        _monthly("2023-12-29", "2024-01-31"), _history(),
    )

    assert pd.isna(result.loc[0, "dividend_cash_ttm"])
    assert pd.isna(result.loc[0, "dividend_event_count_ttm"])
    assert result.loc[1, "dividend_cash_ttm"] == 0.0
    assert result.loc[1, "dividend_event_count_ttm"] == 0


def test_dividend_sql_filters_to_current_canonical_applied_resolution():
    sql = " ".join(silver.DIVIDEND_HISTORY_SQL.lower().split())

    assert "r.quality_run_id = c.quality_run_id" in sql
    assert "r.resolution_version = c.resolution_version" in sql
    assert "ca.quality_run_id = c.action_snapshot_run_id" in sql
    assert "r.is_canonical is true" in sql
    assert "r.excluded_reason is null" in sql
    assert "r.applied_trade_date is not null" in sql
    assert "r.adjusted_cash_amount > 0" in sql
    assert "ca.announcement_date is not null" in sql
    assert "ca.action_scope = 'issuer'" in sql
    assert "resolution_q.status = 'certified'" in sql
    assert "action_q.status = 'certified'" in sql


def test_loader_preserves_certified_coverage_for_zero_dividend_months(monkeypatch):
    contract = pd.DataFrame([{
        "source": "KRX",
        "asset_type": "stock",
        "field_name": "total_return_close",
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "dividend_treatment": "gross_cash_dividend_reinvested_on_ex_date",
        "status": "CERTIFIED",
        "coverage_start": pd.Timestamp("2024-01-02"),
        "coverage_end": pd.Timestamp("2026-12-31"),
        "quality_run_id": "return-run",
        "metadata": {
            "resolution_version": "krx_dividend_resolution_v1",
            "action_snapshot_run_id": "action-run",
        },
        "certified_at": pd.Timestamp("2026-08-08"),
    }])
    loaded = pd.DataFrame(columns=HISTORY_COLUMNS)
    calls: list[str] = []

    def fake_read_frame(conn, sql, params=None, *, chunk_size=50_000):
        calls.append(sql)
        return contract.copy() if len(calls) == 1 else loaded.copy()

    monkeypatch.setattr(silver, "read_frame", fake_read_frame)
    result = silver.load_dividend_history(object())

    assert calls == [silver.TOTAL_RETURN_CONTRACT_SQL, silver.DIVIDEND_HISTORY_SQL]
    assert result.attrs["return_contract"]["status"] == "CERTIFIED"
    assert result.attrs["return_contract"]["coverage_start"] == "2024-01-02 00:00:00"


def test_loader_rejects_contract_without_dividend_lineage(monkeypatch):
    contract = pd.DataFrame([{
        "source": "KRX",
        "asset_type": "stock",
        "field_name": "total_return_close",
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "dividend_treatment": "gross_cash_dividend_reinvested_on_ex_date",
        "status": "CERTIFIED",
        "coverage_start": pd.Timestamp("2024-01-02"),
        "coverage_end": pd.Timestamp("2026-12-31"),
        "quality_run_id": "return-run",
        "metadata": {},
        "certified_at": pd.Timestamp("2026-08-08"),
    }])

    monkeypatch.setattr(
        silver, "read_frame", lambda conn, sql, params=None, **kwargs: contract,
    )

    with pytest.raises(RuntimeError, match="총수익 계약에 묶여"):
        silver.load_dividend_history(object())


def test_attach_rejects_an_uncertified_history_contract():
    history = _history()
    history.attrs["return_contract"]["status"] = "BUILDING"

    with pytest.raises(RuntimeError, match="인증 기준"):
        dividends.attach(_monthly("2024-01-31"), history)
