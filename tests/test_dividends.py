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


def _validation_evidence(
    *, coverage_start: str, coverage_end: str, applied_event_count: int,
) -> dict:
    certified_applied_event_count = max(applied_event_count, 1)
    evidence = {
        "validation_status": "VERIFIED",
        "contract_release": silver.TOTAL_RETURN_CONTRACT_RELEASE,
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "dividend_treatment": silver.TOTAL_RETURN_DIVIDEND_TREATMENT,
        "quality_run_id": "return-run",
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "certified_scope_start": "2015-01-01",
        "certified_markets": ["KOSPI", "KOSDAQ"],
        "price_row_count": 10,
        "asset_count": 1,
        "action_snapshot_run_id": "action-run",
        "action_snapshot_schema_version": (
            silver.TOTAL_RETURN_ACTION_SNAPSHOT_SCHEMA
        ),
        "action_snapshot_manifest_sha256": "a" * 64,
        "action_snapshot_body_digest": "b" * 64,
        "pit_scope_contract": silver.TOTAL_RETURN_PIT_SCOPE_CONTRACT,
        "pit_input_action_count": max(applied_event_count, 1),
        "pit_included_action_count": max(applied_event_count, 1),
        "pit_excluded_action_count": 0,
        "source_receipt_row_count": max(applied_event_count, 1),
        "source_receipt_row_digest": "d" * 64,
        "terminal_economic_receipt_count": max(applied_event_count, 1),
        "terminal_economic_receipt_digest": "e" * 64,
        "published_action_count": max(applied_event_count, 1),
        "published_action_row_digest": "f" * 64,
        "published_action_scope_contract": (
            "issuer_cash_ex_plus_manifest_scale_support_v1"
        ),
        "included_cash_action_parity_count": max(applied_event_count, 1),
        "included_cash_action_parity_digest": "1" * 64,
        "cash_scale_source_contract": (
            silver.TOTAL_RETURN_CASH_SCALE_SOURCE_CONTRACT
        ),
        "cash_scale_source_evidence_count": 0,
        "cash_scale_source_evidence_digest": "3" * 64,
        "cash_scale_source_manifest_sha256": "5" * 64,
        "cash_scale_source_manifest_digest": "6" * 64,
        "cash_scale_support_action_count": 0,
        "cash_scale_support_action_digest": "7" * 64,
        "cash_scale_support_manifest_digest": "8" * 64,
        "cash_scale_support_semantic_group_count": 0,
        "disclosure_observation_contract": (
            silver.TOTAL_RETURN_DISCLOSURE_OBSERVATION_CONTRACT
        ),
        "disclosure_mutable_conflict_digest": "2" * 64,
        "research_role": dict(silver.TOTAL_RETURN_RESEARCH_ROLE),
        "resolution_version": silver.TOTAL_RETURN_RESOLUTION_VERSION,
        "cash_action_count": certified_applied_event_count,
        "canonical_event_count": certified_applied_event_count,
        "applied_event_count": certified_applied_event_count,
        "excluded_event_count": 0,
        "cash_scale_resolution_contract": (
            silver.TOTAL_RETURN_CASH_SCALE_RESOLUTION_CONTRACT
        ),
        "cash_scale_resolution_row_count": certified_applied_event_count,
        "cash_scale_resolution_row_digest": "4" * 64,
        "cash_scale_stable_event_count": certified_applied_event_count,
        "cash_scale_changed_event_count": 0,
        "cash_scale_evidence_match_count": 0,
        "cash_scale_adjusted_cash_parity_count": certified_applied_event_count,
        "cash_scale_first_listing_exclusion_count": 0,
        "cash_scale_explicit_exclusion_count": 0,
        "cash_scale_adj_close_decimal_places": 4,
        "cash_scale_cash_in_adj_close": False,
        "asset_identity_contract": silver.TOTAL_RETURN_ASSET_IDENTITY_CONTRACT,
        "asset_identity_digest": "c" * 64,
    }
    evidence["evidence_sha256"] = silver.total_return_evidence_sha256(evidence)
    return evidence


def _history(
    rows: list[dict] | None = None,
    *,
    coverage_start: str = "2024-01-02",
    coverage_end: str = "2026-12-31",
) -> pd.DataFrame:
    frame = pd.DataFrame(rows or [], columns=HISTORY_COLUMNS)
    evidence = _validation_evidence(
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        applied_event_count=len(frame),
    )
    frame.attrs["return_contract"] = {
        "status": "CERTIFIED",
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "quality_run_id": "return-run",
        "validation_evidence": evidence,
    }
    frame.attrs["pit_availability_contract"] = {
        "contract": silver.DIVIDEND_PIT_AVAILABILITY_CONTRACT,
        "canonical_resolution_only": True,
        "known_at_field": "announcement_date",
        "known_at_lag_days": 1,
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
        "resolution_version": silver.TOTAL_RETURN_RESOLUTION_VERSION,
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


def test_latest_terminal_announcement_is_not_visible_until_following_day():
    history = _history([_event(
        # The economic event applied earlier, but this is the canonical latest
        # terminal POSITIVE receipt date; an earlier receipt must not expose it.
        announcement_date="2024-02-10",
        applied_trade_date="2024-01-15",
        amount=250.0,
    )])
    result = dividends.attach(
        _monthly("2024-01-31", "2024-02-10", "2024-02-29"), history,
    )

    assert result["dividend_cash_ttm"].tolist() == [0.0, 0.0, 250.0]
    assert result["dividend_event_count_ttm"].tolist() == [0, 0, 1]


def test_dividend_attach_rejects_missing_or_weakened_terminal_contract():
    history = _history([_event(
        announcement_date="2024-02-10",
        applied_trade_date="2024-01-15",
    )])
    history.attrs.pop("pit_availability_contract")
    with pytest.raises(RuntimeError, match="latest terminal announcement"):
        dividends.attach(_monthly("2024-02-29"), history)

    weakened = _history([_event(
        announcement_date="2024-02-10",
        applied_trade_date="2024-01-15",
    )])
    weakened.attrs["pit_availability_contract"]["known_at_lag_days"] = 0
    with pytest.raises(RuntimeError, match="latest terminal announcement"):
        dividends.attach(_monthly("2024-02-29"), weakened)


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
    assert "ca.action_key = r.action_key" in sql
    assert "ca.quality_run_id = c.action_snapshot_run_id" in sql
    assert "r.is_canonical is true" in sql
    assert "r.excluded_reason is null" in sql
    assert "r.applied_trade_date is not null" in sql
    assert "r.applied_trade_date between c.coverage_start and c.coverage_end" in sql
    assert "r.adjusted_cash_amount > 0" in sql
    assert "ca.announcement_date is not null" in sql
    assert "ca.action_scope = 'issuer'" in sql
    assert "resolution_q.status = 'certified'" in sql
    assert "action_q.status = 'certified'" in sql
    assert "a.instrument_type = 'common_stock'" in sql


def test_loader_refuses_to_self_certify_ex_post_dividends_as_pit_features():
    with pytest.raises(RuntimeError, match="historical-vintage/known_at"):
        silver.load_dividend_history(object())


def test_loader_propagates_contract_lineage_failure(monkeypatch):
    monkeypatch.setattr(
        silver, "_load_validated_total_return_contract",
        lambda conn: (_ for _ in ()).throw(
            RuntimeError("총수익 계약에 묶여 있지 않습니다")
        ),
    )

    with pytest.raises(RuntimeError, match="historical-vintage/known_at"):
        silver.load_dividend_history(object())


def test_loader_rejects_missing_applied_event_rows(monkeypatch):
    contract = {
        "status": "CERTIFIED",
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "coverage_start": pd.Timestamp("2024-01-02"),
        "coverage_end": pd.Timestamp("2026-12-31"),
        "quality_run_id": "return-run",
        "metadata": {},
    }
    evidence = _validation_evidence(
        coverage_start="2024-01-02",
        coverage_end="2026-12-31",
        applied_event_count=1,
    )
    monkeypatch.setattr(
        silver, "_load_validated_total_return_contract",
        lambda conn: (dict(contract), dict(evidence)),
    )
    monkeypatch.setattr(
        silver, "read_frame",
        lambda *_args, **_kwargs: pd.DataFrame(columns=HISTORY_COLUMNS),
    )

    with pytest.raises(RuntimeError, match="historical-vintage/known_at"):
        silver.load_dividend_history(object())


def test_loader_rejects_dividend_rows_from_another_return_run(monkeypatch):
    contract = {
        "status": "CERTIFIED",
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "coverage_start": pd.Timestamp("2024-01-02"),
        "coverage_end": pd.Timestamp("2026-12-31"),
        "quality_run_id": "return-run",
        "metadata": {},
    }
    evidence = _validation_evidence(
        coverage_start="2024-01-02",
        coverage_end="2026-12-31",
        applied_event_count=1,
    )
    loaded = pd.DataFrame([_event(
        announcement_date="2024-01-01",
        applied_trade_date="2024-01-02",
    )])
    loaded.loc[0, "quality_run_id"] = "stale-run"
    monkeypatch.setattr(
        silver, "_load_validated_total_return_contract",
        lambda conn: (dict(contract), dict(evidence)),
    )
    monkeypatch.setattr(
        silver, "read_frame", lambda *_args, **_kwargs: loaded.copy(),
    )

    with pytest.raises(RuntimeError, match="historical-vintage/known_at"):
        silver.load_dividend_history(object())


def test_attach_rejects_an_uncertified_history_contract():
    history = _history()
    history.attrs["return_contract"]["status"] = "BUILDING"

    with pytest.raises(RuntimeError, match="인증 기준"):
        dividends.attach(_monthly("2024-01-31"), history)
