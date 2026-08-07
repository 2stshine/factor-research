from __future__ import annotations

import pandas as pd
import pytest

from engine import implementation
from engine.factors import Factor


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
    )

    assert evidence["status"] == "PASS"
    assert evidence["counts"]["rank_mismatches"] == 0
    assert evidence["counts"]["expected_signal_months"] == 1


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda frame: frame.assign(value=[1.0, 1.0, 2.1]), "raw_values_close"),
        (lambda frame: frame.assign(rank=[1, 2, 3]), "direction_adjusted_ranks_exact"),
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
    )

    assert evidence["status"] == "FAIL"
    assert reason in evidence["failure_reasons"]


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
        )


def test_pre_parity_exception_is_preserved_as_deterministic_failure_evidence():
    factor = _factor()
    first = implementation.failure_evidence(
        factor,
        discovery_signal_start="2018-03",
        discovery_signal_end="2023-05",
        discovery_snapshot_digest="b" * 64,
        stage="sql_execute",
        error=RuntimeError("relation unavailable"),
    )
    second = implementation.failure_evidence(
        factor,
        discovery_signal_start="2018-03",
        discovery_signal_end="2023-05",
        discovery_snapshot_digest="b" * 64,
        stage="sql_execute",
        error=RuntimeError("relation unavailable"),
    )

    assert first == second
    assert first["status"] == "FAIL"
    assert first["failure_reasons"] == ["sql_execute_error"]
    assert len(first["evidence_digest"]) == 64
