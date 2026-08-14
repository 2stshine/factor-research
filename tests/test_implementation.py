from __future__ import annotations

import pandas as pd
import pytest

from engine import implementation
from engine.factors import Factor


STRATEGY_SHA256 = "c" * 64


def _factor() -> Factor:
    return Factor(
        name="parity_factor",
        family="parity_factor",
        category="other",
        hypothesis="낮은 원값이 높은 미래수익을 예측한다.",
        predicted_sign=-1,
        compute=lambda frame: frame["raw"],
        needs=("raw",),
    )


def _spec(factor: Factor) -> dict:
    return {
        "sql": "pipeline/gold/factors/parity_factor.sql",
        "predicted_sign": factor.predicted_sign,
        "research_definition_hash": factor.definition_hash,
        "value_contract": "raw_value_direction_adjusted_rank_v1",
    }


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    python = pd.DataFrame({
        "asset_id": [1, 2, 3],
        "as_of_date": pd.to_datetime(["2023-05-31"] * 3),
        "value": [1.0, 1.0, 2.0],
    })
    sql = python.copy()
    sql["rank"] = [1, 1, 3]
    return python, sql


def test_query_only_contract_rejects_dml_and_requires_closed_month_range():
    implementation.validate_query_only_sql(
        "SELECT asset_id, trade_date AS as_of_date, market_cap AS value, 1 AS rank "
        "FROM public.price_daily "
        "WHERE month BETWEEN %(start_month)s AND %(end_month)s"
    )
    implementation.validate_query_only_sql(
        "SELECT r.asset_id, r.applied_trade_date AS as_of_date, "
        "r.adjusted_cash_amount AS value, 1 AS rank "
        "FROM public.price_return_contract c "
        "JOIN public.dividend_event_resolution r ON r.quality_run_id = c.quality_run_id "
        "WHERE r.applied_trade_date BETWEEN %(start_month)s AND %(end_month)s"
    )
    with pytest.raises(ValueError, match="SELECT 또는 WITH|변경 명령"):
        implementation.validate_query_only_sql(
            "INSERT INTO x SELECT * FROM y WHERE m BETWEEN %(start_month)s AND %(end_month)s"
        )
    with pytest.raises(ValueError, match="필수 parameter"):
        implementation.validate_query_only_sql("SELECT * FROM x")
    with pytest.raises(ValueError, match="Silver relation"):
        implementation.validate_query_only_sql(
            "SELECT * FROM gold.factor_value "
            "WHERE month BETWEEN %(start_month)s AND %(end_month)s"
        )
    with pytest.raises(ValueError, match="Silver relation"):
        implementation.validate_query_only_sql(
            "SELECT * FROM public.fundamental_current "
            "WHERE month BETWEEN %(start_month)s AND %(end_month)s"
        )


@pytest.mark.parametrize("label", ["total_return_close", "return_close"])
def test_gold_feature_sql_cannot_read_ex_post_label_fields(label):
    sql = (
        f"SELECT asset_id, trade_date AS as_of_date, {label} AS value, "
        "1 AS rank FROM public.price_daily "
        "WHERE trade_date BETWEEN %(start_month)s AND %(end_month)s"
    )
    with pytest.raises(ValueError, match="forward label 전용"):
        implementation.validate_feature_sql(sql)

    implementation.validate_feature_sql(
        "SELECT asset_id, trade_date AS as_of_date, adj_close AS value, "
        "1 AS rank FROM public.factor_price_feature_daily "
        "WHERE trade_date BETWEEN %(start_month)s AND %(end_month)s"
    )

    with pytest.raises(ValueError, match="인증 feature view"):
        implementation.validate_feature_sql(
            "SELECT asset_id, trade_date AS as_of_date, adj_close AS value, "
            "1 AS rank FROM public.price_daily "
            "WHERE trade_date BETWEEN %(start_month)s AND %(end_month)s"
        )


def test_gold_feature_sql_cannot_hide_label_field_in_json_key_literal():
    sql = (
        "SELECT p.asset_id, p.trade_date AS as_of_date, "
        "(to_jsonb(p)->>'total_return_close')::numeric AS value, 1 AS rank "
        "FROM public.price_daily p "
        "WHERE p.trade_date BETWEEN %(start_month)s AND %(end_month)s"
    )

    with pytest.raises(ValueError, match="동적 필드 접근"):
        implementation.validate_feature_sql(sql)


@pytest.mark.parametrize(
    "dynamic_value",
    [
        "to_jsonb(p)->>('total_' || 'return_' || 'close')",
        "to_jsonb(p)->>concat('total','_ret','urn_cl','ose')",
        "row_to_json(p)->>chr(116)",
    ],
)
def test_gold_feature_sql_rejects_fragmented_dynamic_field_access(dynamic_value):
    sql = (
        "SELECT p.asset_id, p.trade_date AS as_of_date, "
        f"({dynamic_value})::numeric AS value, 1 AS rank "
        "FROM public.price_daily p "
        "WHERE p.trade_date BETWEEN %(start_month)s AND %(end_month)s"
    )

    with pytest.raises(ValueError, match="동적 필드 접근"):
        implementation.validate_feature_sql(sql)


def test_gold_feature_sql_cannot_serialize_whole_price_row_to_recover_label():
    sql = (
        "SELECT p.asset_id, p.trade_date AS as_of_date, "
        "split_part(p::text, ',', 7)::numeric AS value, 1 AS rank "
        "FROM public.price_daily p "
        "WHERE p.trade_date BETWEEN %(start_month)s AND %(end_month)s"
    )

    with pytest.raises(ValueError, match="인증 feature view"):
        implementation.validate_feature_sql(sql)


def test_negative_sign_and_tie_rank_parity_passes():
    factor = _factor()
    python, sql = _frames()
    evidence = implementation.compare_parity(
        factor,
        python,
        sql,
        implementation_uri="repo://TeamAlpha-data/pipeline/gold/factors/parity_factor.sql",
        implementation_sha256="a" * 64,
        manifest_spec=_spec(factor),
        discovery_signal_start="2023-05",
        discovery_signal_end="2023-05",
        discovery_snapshot_digest="b" * 64,
        strategy_sha256=STRATEGY_SHA256,
    )

    assert evidence["status"] == "PASS"
    assert evidence["counts"]["rank_mismatches"] == 0
    assert evidence["counts"]["expected_signal_months"] == 1


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda frame: frame.assign(value=[1.0, 1.0, 2.1]), "raw_values_close"),
        (lambda frame: frame.assign(rank=[1, 2, 3]), "direction_adjusted_ranks_consistent"),
        (lambda frame: frame.iloc[:-1], "keys_exact"),
    ],
)
def test_parity_mismatches_are_auditable_failures(mutation, reason):
    factor = _factor()
    python, sql = _frames()
    evidence = implementation.compare_parity(
        factor,
        python,
        mutation(sql),
        implementation_uri="repo://TeamAlpha-data/pipeline/gold/factors/parity_factor.sql",
        implementation_sha256="a" * 64,
        manifest_spec=_spec(factor),
        discovery_signal_start="2023-05",
        discovery_signal_end="2023-05",
        discovery_snapshot_digest="b" * 64,
        strategy_sha256=STRATEGY_SHA256,
    )

    assert evidence["status"] == "FAIL"
    assert reason in evidence["failure_reasons"]


def test_rank_contract_allows_only_tolerance_equivalent_reordering():
    factor = _factor()
    python = pd.DataFrame({
        "asset_id": [1, 2, 3],
        "as_of_date": pd.to_datetime(["2023-05-31"] * 3),
        "value": [1.0, 1.0 + 1e-7, 2.0],
    })
    sql = python.copy()
    sql["rank"] = [2, 1, 3]
    spec = _spec(factor)
    spec["allow_tolerance_equivalent_ranks"] = True

    tolerated = implementation.compare_parity(
        factor, python, sql,
        implementation_uri="repo://TeamAlpha-data/pipeline/gold/factors/parity_factor.sql",
        implementation_sha256="a" * 64, manifest_spec=spec,
        discovery_signal_start="2023-05", discovery_signal_end="2023-05",
        discovery_snapshot_digest="b" * 64,
        strategy_sha256=STRATEGY_SHA256, atol=1e-6,
        allow_tolerance_equivalent_ranks=True,
    )
    material = implementation.compare_parity(
        factor, python, sql,
        implementation_uri="repo://TeamAlpha-data/pipeline/gold/factors/parity_factor.sql",
        implementation_sha256="a" * 64, manifest_spec=spec,
        discovery_signal_start="2023-05", discovery_signal_end="2023-05",
        discovery_snapshot_digest="b" * 64,
        strategy_sha256=STRATEGY_SHA256, atol=1e-10,
        allow_tolerance_equivalent_ranks=True,
    )

    assert tolerated["status"] == "PASS"
    assert tolerated["counts"]["rank_mismatches"] == 2
    assert tolerated["counts"]["tolerance_equivalent_rank_mismatches"] == 2
    assert tolerated["counts"]["material_rank_mismatches"] == 0
    assert material["status"] == "FAIL"
    assert "direction_adjusted_ranks_consistent" in material["failure_reasons"]


def test_manifest_definition_hash_must_bind_python_definition():
    factor = _factor()
    python, sql = _frames()
    spec = _spec(factor)
    spec["research_definition_hash"] = "different"

    with pytest.raises(ValueError, match="research_definition_hash"):
        implementation.compare_parity(
            factor,
            python,
            sql,
            implementation_uri="repo://TeamAlpha-data/pipeline/gold/factors/parity_factor.sql",
            implementation_sha256="a" * 64,
            manifest_spec=spec,
            discovery_signal_start="2023-05",
            discovery_signal_end="2023-05",
            discovery_snapshot_digest="b" * 64,
            strategy_sha256=STRATEGY_SHA256,
        )


def test_pre_parity_exception_is_preserved_as_deterministic_failure_evidence():
    factor = _factor()
    first = implementation.failure_evidence(
        factor,
        discovery_signal_start="2018-03",
        discovery_signal_end="2023-05",
        discovery_snapshot_digest="b" * 64,
        strategy_sha256=STRATEGY_SHA256,
        stage="sql_execute",
        error=RuntimeError("relation unavailable"),
    )
    second = implementation.failure_evidence(
        factor,
        discovery_signal_start="2018-03",
        discovery_signal_end="2023-05",
        discovery_snapshot_digest="b" * 64,
        strategy_sha256=STRATEGY_SHA256,
        stage="sql_execute",
        error=RuntimeError("relation unavailable"),
    )

    assert first == second
    assert first["status"] == "FAIL"
    assert first["failure_reasons"] == ["sql_execute_error"]
    assert len(first["evidence_digest"]) == 64
