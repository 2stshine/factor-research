"""Contracts for daily-derived features in the Silver month-end snapshot."""
from __future__ import annotations

import re

import pandas as pd
import pytest

from engine import silver
from engine.panel import from_silver_frame, verify_return_roles


DAILY_FEATURES = {
    "amihud_illiquidity_1m": "1.25e-12",
    "amihud_observations_1m": "20",
    "daily_volatility_252d": "0.018",
    "daily_return_observations_252d": "252",
    "max_daily_return_1m": "0.071",
    "max_daily_return_observations_1m": "20",
    "price_high_252d": "12345.0",
    "price_high_observations_252d": "252",
}


def _return_evidence(run_id: str = "q") -> dict:
    evidence = {
        "validation_status": "VERIFIED",
        "contract_release": silver.TOTAL_RETURN_CONTRACT_RELEASE,
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "dividend_treatment": silver.TOTAL_RETURN_DIVIDEND_TREATMENT,
        "quality_run_id": run_id,
        "coverage_start": "2026-07-31",
        "coverage_end": "2026-07-31",
        "certified_scope_start": "2015-01-01",
        "certified_markets": ["KOSPI", "KOSDAQ"],
        "price_row_count": 1,
        "asset_count": 1,
        "action_snapshot_run_id": "action-run",
        "action_snapshot_schema_version": (
            silver.TOTAL_RETURN_ACTION_SNAPSHOT_SCHEMA
        ),
        "action_snapshot_manifest_sha256": "a" * 64,
        "action_snapshot_body_digest": "b" * 64,
        "pit_scope_contract": silver.TOTAL_RETURN_PIT_SCOPE_CONTRACT,
        "pit_input_action_count": 1,
        "pit_included_action_count": 1,
        "pit_excluded_action_count": 0,
        "source_receipt_row_count": 1,
        "source_receipt_row_digest": "d" * 64,
        "terminal_economic_receipt_count": 1,
        "terminal_economic_receipt_digest": "e" * 64,
        "published_action_count": 1,
        "published_action_row_digest": "f" * 64,
        "published_action_scope_contract": (
            "issuer_cash_ex_plus_manifest_scale_support_v1"
        ),
        "included_cash_action_parity_count": 1,
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
        "cash_action_count": 1,
        "canonical_event_count": 1,
        "applied_event_count": 1,
        "excluded_event_count": 0,
        "cash_scale_resolution_contract": (
            silver.TOTAL_RETURN_CASH_SCALE_RESOLUTION_CONTRACT
        ),
        "cash_scale_resolution_row_count": 1,
        "cash_scale_resolution_row_digest": "4" * 64,
        "cash_scale_stable_event_count": 1,
        "cash_scale_changed_event_count": 0,
        "cash_scale_evidence_match_count": 0,
        "cash_scale_adjusted_cash_parity_count": 1,
        "cash_scale_first_listing_exclusion_count": 0,
        "cash_scale_explicit_exclusion_count": 0,
        "cash_scale_adj_close_decimal_places": 4,
        "cash_scale_cash_in_adj_close": False,
        "asset_identity_contract": silver.TOTAL_RETURN_ASSET_IDENTITY_CONTRACT,
        "asset_identity_digest": "c" * 64,
    }
    evidence["evidence_sha256"] = silver.total_return_evidence_sha256(evidence)
    return evidence


def _normalized_sql() -> str:
    return re.sub(r"\s+", " ", silver.PRICE_SNAPSHOT_SQL.lower()).strip()


def _snapshot_row() -> pd.DataFrame:
    row = {
        "asset_id": 1,
        "Code": "005930",
        "Name": "삼성전자",
        "instrument_type": "common_stock",
        "listed_from": None,
        "listed_to": None,
        "trade_date": "2026-07-31",
        "close": "10000",
        "adj_close": "9900",
        "total_return_close": "10300",
        "trading_value": "5000000000",
        "market_cap": "100000000000",
        "shares": "10000000",
        "market": "KOSPI",
        "adv20": "4000000000",
        "age_days": "300",
        "first_seen": "2025-01-02",
        "dataset_start": "2015-01-02",
        "quality_run_id": "q",
        "total_return_quality_run_id": "q",
        **DAILY_FEATURES,
    }
    frame = pd.DataFrame([row])
    frame.attrs["return_contract"] = {
        "status": "CERTIFIED",
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "quality_run_id": "q",
        "validation_evidence": _return_evidence(),
    }
    frame.attrs["return_roles"] = silver.return_role_contract()
    return frame


def test_daily_feature_sql_uses_adj_close_and_never_total_return_for_features():
    sql = _normalized_sql()

    assert "p.total_return_quality_run_id" in sql
    assert "trade_date >= date '2015-01-01'" in sql
    assert "then adj_close end as certified_feature_price" in sql
    assert "lag(certified_feature_price) over" in sql
    assert "certified_feature_price / lag(" in sql
    assert "avg(abs(daily_price_return) / trading_value) filter" in sql
    assert "trading_value > 0" in sql
    assert "stddev_samp(daily_price_return) over" in sql
    assert "max(daily_price_return) over" in sql
    assert "max(certified_feature_price) over" in sql
    assert "count(certified_feature_price) over" in sql
    assert "when p.trade_date >= date '2015-01-01' then p.trading_value" in sql
    feature_sql = sql.split("), monthly as (", 1)[0]
    assert "certified_total_return_close" not in feature_sql
    assert "daily_total_return" not in feature_sql


def test_daily_feature_sql_is_trailing_or_same_calendar_month_only():
    sql = _normalized_sql()

    assert sql.count("rows between 251 preceding and current row") == 4
    assert "following" not in sql
    assert sql.count(
        "partition by asset_id, date_trunc('month', trade_date)"
    ) >= 5
    assert "where month_rank = 1" in sql


def test_panel_requires_and_normalizes_daily_feature_contract():
    panel = from_silver_frame(_snapshot_row(), verbose=False)

    for column, raw_value in DAILY_FEATURES.items():
        assert column in panel.monthly
        assert panel.monthly.loc[0, column] == pytest.approx(float(raw_value))

    missing = _snapshot_row().drop(columns=["price_high_252d"])
    with pytest.raises(ValueError, match="price_high_252d"):
        from_silver_frame(missing, verbose=False)


def test_panel_keeps_total_return_and_split_adjusted_price_semantics_distinct():
    panel = from_silver_frame(_snapshot_row(), verbose=False)
    row = panel.monthly.iloc[0]

    assert row["total_return_close"] == pytest.approx(10300.0)
    assert row["adj_close"] == pytest.approx(9900.0)
    assert "return_close" not in panel.monthly
    assert row["price_high_252d"] == pytest.approx(12345.0)


def test_panel_fails_closed_when_feature_label_role_contract_is_missing_or_changed():
    missing = _snapshot_row()
    missing.attrs.pop("return_roles")
    with pytest.raises(RuntimeError, match="feature/label 역할 계약"):
        from_silver_frame(missing, verbose=False)

    exposed = _snapshot_row()
    exposed.attrs["return_roles"] = {
        **silver.return_role_contract(),
        "label_candidate_access": True,
    }
    with pytest.raises(RuntimeError, match="feature/label 역할 계약"):
        from_silver_frame(exposed, verbose=False)

    panel = from_silver_frame(_snapshot_row(), verbose=False)
    panel.monthly["return_close"] = panel.monthly["total_return_close"]
    with pytest.raises(RuntimeError, match="구형 return_close"):
        verify_return_roles(panel)
