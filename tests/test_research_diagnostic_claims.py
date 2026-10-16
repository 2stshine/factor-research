"""Synthetic diagnostic-claim contract; no frozen scores, files, or data access."""
from decimal import Decimal

import pytest

from engine.research_diagnostic_claims import classify_economic_claims


UNAVAILABLE = "ECONOMIC_OUTCOME_UNAVAILABLE"
MECHANISM = "MECHANISM_UNIDENTIFIED"


def entry(status="COMPUTED", *, eid="e1", diagnostic="economic_link", **response):
    return {"evidence_id": eid, "diagnostic_id": diagnostic,
            "response": {"diagnostic_id": diagnostic, "status": status,
                         "metrics": {"signal_to_economic_change_ic": {"mean": 0.25}}, **response}}


def test_absent_economic_diagnostic_is_untested_and_never_causal():
    result = classify_economic_claims([entry(diagnostic="coverage")])
    assert result["economic_status"] == "UNTESTED"
    assert result["causal_identification"] == "NOT_IDENTIFIED"
    assert result["runtime_connected"] is False
    assert result["historical_scores_modified"] is False
    assert result["evidence_authenticated"] is False
    assert result["measurement_validity_reverified"] is False
    assert isinstance(result["contract_version"], str) and result["contract_version"]
    assert result["claims_valid"] is True


def test_unavailable_finding_requires_the_exact_economic_citation():
    evidence = [entry("NOT_COMPUTED", missing_datasets=["economic_outcomes"]),
                entry(eid="other", diagnostic="coverage")]
    accepted = classify_economic_claims(evidence, findings=[UNAVAILABLE], evidence_ids=["e1"])
    assert accepted["economic_status"] == "DATA_UNAVAILABLE"
    assert accepted["accepted_findings"] and accepted["rejected_findings"] == []
    assert accepted["claims_valid"] is True
    for citations in ([], ["other"]):
        rejected = classify_economic_claims(evidence, findings=[UNAVAILABLE], evidence_ids=citations)
        assert rejected["accepted_findings"] == [] and rejected["rejected_findings"]
        assert rejected["claims_valid"] is False


@pytest.mark.parametrize("evidence,citations", [([], []), ([entry()], ["e1"]),
    ([entry("EXECUTION_FAILED", missing_datasets=["economic_outcomes"])], ["e1"])])
def test_no_data_gap_credit_from_absence_association_or_execution_failure(evidence, citations):
    result = classify_economic_claims(evidence, findings=[UNAVAILABLE], evidence_ids=citations)
    assert result["accepted_findings"] == [] and result["rejected_findings"]
    assert result["claims_valid"] is False


def test_mechanism_code_is_only_a_neutral_limitation():
    result = classify_economic_claims([], findings=[MECHANISM])
    assert result["accepted_findings"] == result["rejected_findings"] == []
    assert result["neutral_limitations"] and result["claims_valid"] is True
    assert result["economic_status"] == "UNTESTED"
    assert result["causal_identification"] == "NOT_IDENTIFIED"


@pytest.mark.parametrize("metrics,status", [
    ({"signal_to_economic_change_ic": {"mean": Decimal("-0.125")}}, "ASSOCIATION_ASSESSED"),
    ({"economic_change_to_return_ic": {"mean": 0}}, "ASSOCIATION_ASSESSED"),
    ({"signal_to_economic_change_ic": {"mean": 0.4}, "n_months": 12,
      "outcome_availability_lag_months": 6}, "ASSOCIATION_ASSESSED"),
    ({}, "UNRESOLVED"), ({"value": "0.4", "valid": True}, "UNRESOLVED"),
    ([1, 2], "UNRESOLVED"), (0.4, "UNRESOLVED"),
    ({"signal_to_economic_change_ic": {"mean": float("nan")}}, "UNRESOLVED"),
    ({"economic_change_to_return_ic": {"mean": Decimal("Infinity")}}, "UNRESOLVED"),
    ({"signal_to_economic_change_ic": {"mean": 0.4},
      "economic_change_to_return_ic": {"mean": None}}, "UNRESOLVED"),
])
def test_only_finite_named_estimates_assess_association(metrics, status):
    result = classify_economic_claims([entry(metrics=metrics)])
    assert result["economic_status"] == status
    assert result["causal_identification"] == "NOT_IDENTIFIED"


@pytest.mark.parametrize("metrics", [
    {"n_months": 12}, {"outcome_availability_lag_months": 6}, {"summary_count": 1},
    {"n_months": 12, "outcome_availability_lag_months": 6},
    {"signal_to_economic_change_ic": {"n_months": 12}},
    {"signal_to_economic_change_ic": {"mean": "0.25"}},
    {"signal_to_economic_change_ic": {"mean": True}},
    {"signal_to_economic_change_ic": 0.25},
    {"other_summary": {"mean": 0.25}},
    {"nested": {"signal_to_economic_change_ic": {"mean": 0.25}}},
])
def test_counts_lags_or_unrecognized_summaries_do_not_establish_association(metrics):
    result = classify_economic_claims([entry(metrics=metrics)])
    assert result["economic_status"] == "UNRESOLVED"


@pytest.mark.parametrize("status", ["NOT_COMPUTED", "EXECUTION_FAILED"])
def test_status_cannot_be_promoted_by_numeric_metrics_without_missing_data(status):
    assert classify_economic_claims([entry(status, missing_datasets=[])])["economic_status"] == "UNRESOLVED"


def test_computed_metrics_with_missing_datasets_remain_unresolved():
    result = classify_economic_claims([entry(missing_datasets=["economic_outcomes"])])
    assert result["economic_status"] == "UNRESOLVED"


@pytest.mark.parametrize("missing", [None, "economic_outcomes", [""], [1], ["x", "x"]])
def test_malformed_missing_datasets_are_invalid_even_for_other_diagnostics(missing):
    with pytest.raises(ValueError):
        classify_economic_claims([entry(diagnostic="coverage", missing_datasets=missing)])


@pytest.mark.parametrize("evidence", [
    [entry(eid="")], [entry(diagnostic=" ")], [entry(), entry(diagnostic="coverage")],
    [entry(), entry(eid="e2")], [entry("AVAILABLE")],
    [entry(), entry("INVALID", eid="other", diagnostic="coverage")],
    [{"evidence_id": "e1", "diagnostic_id": "economic_link", "response":
      {"diagnostic_id": "coverage", "status": "COMPUTED", "metrics": {"n": 1}}}],
])
def test_invalid_or_ambiguous_evidence_is_rejected_even_outside_economic_link(evidence):
    with pytest.raises(ValueError):
        classify_economic_claims(evidence)


@pytest.mark.parametrize("findings,citations", [(["UNKNOWN"], []),
    ([MECHANISM, MECHANISM], []), ([], ["unknown"]), ([], ["e1", "e1"])])
def test_unknown_or_duplicate_claim_inputs_are_rejected(findings, citations):
    with pytest.raises(ValueError):
        classify_economic_claims([entry()], findings=findings, evidence_ids=citations)


def test_response_diagnostic_id_is_optional():
    evidence = entry()
    del evidence["response"]["diagnostic_id"]
    assert classify_economic_claims([evidence])["economic_status"] == "ASSOCIATION_ASSESSED"
