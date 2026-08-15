from __future__ import annotations

import pytest

from engine import research_policy
from engine.factors import Factor


def _candidate(index: int, domain: str | None, category: str) -> Factor:
    return Factor(
        name=f"domain_candidate_{index}",
        family=f"domain_family_{index}",
        category=category,
        exploration_domain=domain,
        hypothesis=f"result-blind mechanism {index}",
        predicted_sign=1,
        params={"candidate": index},
        needs=(f"domain_input_{index}",),
        compute=lambda frame: frame["market_cap"],
    )


def test_factor_rejects_unknown_exploration_domain():
    with pytest.raises(ValueError, match="exploration_domain"):
        _candidate(0, "accounting_other", "quality")


def test_existing_definition_hash_is_unchanged_when_domain_is_omitted():
    legacy = Factor(
        name="legacy_identity",
        category="other",
        hypothesis="legacy",
        predicted_sign=1,
        compute=lambda frame: frame["market_cap"],
    )
    explicit = Factor(
        name="legacy_identity",
        category="other",
        exploration_domain="value",
        hypothesis="legacy",
        predicted_sign=1,
        compute=lambda frame: frame["market_cap"],
    )

    assert legacy.definition_hash != explicit.definition_hash


def test_ten_candidate_batch_accepts_five_configured_domains():
    domains = (
        "value", "value",
        "profitability_quality", "profitability_quality",
        "investment_capital_allocation", "investment_capital_allocation",
        "momentum_trend_reversal", "momentum_trend_reversal",
        "liquidity_trading", "liquidity_trading",
    )
    categories = (
        "value", "value", "quality", "quality", "earnings",
        "other", "momentum", "momentum", "size", "other",
    )
    artifact = research_policy.candidate_batch_policy([
        _candidate(index, domain, categories[index])
        for index, domain in enumerate(domains)
    ])

    assert artifact["status"] == "PASS"
    assert artifact["exploration_domain_count"] == 5
    assert artifact["exploration_domains"] == sorted(set(domains))


def test_ten_candidate_batch_rejects_missing_narrow_and_crowded_domains():
    domains = (
        None,
        "value", "value", "value",
        "profitability_quality", "profitability_quality",
        "low_risk", "low_risk",
        "liquidity_trading", "liquidity_trading",
    )
    categories = (
        "value", "value", "quality", "quality", "earnings",
        "other", "momentum", "momentum", "size", "other",
    )
    artifact = research_policy.candidate_batch_policy([
        _candidate(index, domain, categories[index])
        for index, domain in enumerate(domains)
    ])
    rules = {row["rule"] for row in artifact["violations"]}

    assert artifact["status"] == "FAIL"
    assert "explicit_exploration_domain_required" in rules
    assert "minimum_exploration_domain_diversity" in rules
    assert "maximum_candidates_per_exploration_domain" in rules


def test_five_candidate_batch_requires_three_explicit_domains():
    factors = [
        _candidate(index, domain, category)
        for index, (domain, category) in enumerate((
            ("value", "value"),
            ("value", "value"),
            ("profitability_quality", "quality"),
            ("low_risk", "other"),
            ("low_risk", "other"),
        ))
    ]
    assert research_policy.candidate_batch_policy(factors)["status"] == "PASS"

