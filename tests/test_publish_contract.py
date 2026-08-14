from __future__ import annotations

import pytest

from engine import silver
from engine.factors import Factor
from engine.gate import Result, Verdict
from engine.publish import ImplementationRef, VALUE_CONTRACT_ID, build_row
from factors.candidate_loader import load_candidates
from engine import factors as factor_registry
from scripts.run import _implementation_ref


def _factor(*, predicted_sign: int) -> Factor:
    def compute(frame):
        return frame["raw_input"]

    return Factor(
        name="contract_test",
        category="other",
        hypothesis="원값과 투자 방향을 분리한다.",
        predicted_sign=predicted_sign,
        compute=compute,
        needs=("raw_input",),
    )


def _implementation(factor: Factor) -> ImplementationRef:
    return ImplementationRef(
        uri="repo://factor-research/implementations/gold/factors/contract_test.sql",
        sha256="a" * 64,
        research_definition_hash=factor.definition_hash,
    )


@pytest.mark.parametrize(
    ("predicted_sign", "raw_value_order"),
    [(1, "descending"), (-1, "ascending")],
)
def test_build_row_binds_sql_implementation_and_value_contract(
    predicted_sign: int,
    raw_value_order: str,
):
    factor = _factor(predicted_sign=predicted_sign)
    implementation = _implementation(factor)
    result = Result(
        factor=factor.name,
        definition_hash=factor.definition_hash,
        verdict=Verdict.PROVISIONAL,
    )

    row = build_row(factor, result, implementation=implementation)

    assert row["implementation_uri"] == implementation.uri
    assert row["implementation_hash"] == implementation.sha256
    assert row["config"]["research_definition_hash"] == factor.definition_hash
    assert row["config"]["value_contract"] == {
        "id": VALUE_CONTRACT_ID,
        "value": "raw",
        "predicted_sign": predicted_sign,
        "score": "value*predicted_sign",
        "rank": "score_descending",
        "raw_value_order": raw_value_order,
        "as_of_date": "asset_last_valid_trading_day_in_signal_month",
        "rank_partition": "signal_month_full_implementation_universe",
    }


def test_build_row_rejects_mismatched_research_definition():
    factor = _factor(predicted_sign=1)
    result = Result(
        factor=factor.name,
        definition_hash=factor.definition_hash,
        verdict=Verdict.PROVISIONAL,
    )
    implementation = ImplementationRef(
        uri="repo://factor-research/implementations/gold/factors/contract_test.sql",
        sha256="b" * 64,
        research_definition_hash="different-definition",
    )

    with pytest.raises(ValueError, match="research_definition_hash"):
        build_row(factor, result, implementation=implementation)


def test_gold_trial_history_prefers_research_hash_with_legacy_fallback():
    normalized = " ".join(silver.GOLD_TRIAL_HISTORY_SQL.lower().split())

    expression = (
        "coalesce( nullif(btrim(config->>'research_definition_hash'), ''), "
        "implementation_hash )"
    )
    assert f"select {expression} as definition_hash" in normalized
    assert f"where {expression} is not null" in normalized


@pytest.mark.parametrize(
    "factor_name",
    [
        "amihud_illiquidity_1m",
        "max_daily_return_1m",
        "net_equity_issuance_price_adjusted_12m",
        "operating_income_to_liabilities",
        "paid_in_capital_ratio",
        "realized_volatility_252d",
        "trading_turnover_20d",
    ],
)
def test_research_candidate_binds_to_local_gold_sql(
    factor_name: str, monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TEAMALPHA_DATA_DIR", "/definitely/not/used")
    load_candidates(factor_registry.REGISTRY)
    factor = factor_registry.REGISTRY[factor_name]

    implementation = _implementation_ref(factor)

    assert implementation.uri.endswith(
        f"implementations/gold/factors/{factor_name}.sql"
    )
    assert implementation.uri.startswith("repo://factor-research/")
    assert len(implementation.sha256) == 64
    assert implementation.research_definition_hash == factor.definition_hash


def test_uncertified_direct_dividend_candidates_have_no_gold_binding():
    from factors.candidate_loader import DISABLED_RESEARCH_SPECS

    load_candidates(factor_registry.REGISTRY)

    for name in ("dividend_event_frequency_ttm", "dividend_yield_ttm"):
        assert name not in factor_registry.REGISTRY
        assert "historical-vintage/known_at" in (
            DISABLED_RESEARCH_SPECS[name]["disabled_reason"]
        )
