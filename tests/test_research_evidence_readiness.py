from dataclasses import replace

import pytest

from engine.research_evidence_readiness import (
    EvidenceCapability, EvidenceRequirement, ResearchClaim, assess_readiness,
)


def capability(evidence_id="price", role="feature", **changes):
    value = EvidenceCapability(
        evidence_id=evidence_id, role=role, presence="PRESENT", linked=True,
        scope_checked=True, required_coverage_checked=True, required_coverage_passed=True,
        availability_checked=True,
        verification="VERIFIED", source_ref="artifact:certified-input-v1",
        known_at="2026-09-01T00:00:00+09:00", scope_ref="development:2018-2022",
        runtime_binding="snapshot:abc", coverage_contract_ref="coverage:baseline-v1",
        coverage_evidence_ref="artifact:scoped-coverage-receipt-v1",
    )
    return replace(value, **changes)


def claim(claim_id="prediction", evidence_id="price", role="feature", policy=None):
    return ResearchClaim(claim_id, (EvidenceRequirement(
        evidence_id, role, "coverage:baseline-v1", allow_assumed_policy_ref=policy,
    ),))


def check(claims=None, capabilities=None, **changes):
    args = dict(scope_ref="development:2018-2022", runtime_binding="snapshot:abc",
                as_of="2026-09-02T00:00:00+09:00")
    args.update(changes)
    return assess_readiness(
        [claim()] if claims is None else claims,
        [capability()] if capabilities is None else capabilities,
        **args,
    )


def requirement(result):
    return result["claims"][0]["requirements"][0]


def test_ready_is_only_a_supplied_metadata_check():
    result = check()
    assert result["status"] == "READY"
    assert result["assessment"] == "SUPPLIED_METADATA_CONTRACT_ONLY"
    assert result["source_or_coverage_reverified"] is False
    assert result["research_executed"] is False
    assert result["economic_verdict"] == "NOT_ASSESSED"


def test_missing_mechanism_does_not_block_predictive_claim():
    result = check(claims=[claim(), claim("cash_mechanism", "cash_outcome", "outcome")])
    assert result["status"] == "PARTIAL" and result["ready_claims"] == 1
    assert [row["status"] for row in result["claims"]] == ["READY", "NOT_TESTABLE"]
    assert result["claims"][1]["requirements"][0]["status"] == "MISSING"
    assert "REJECT" not in str(result)


@pytest.mark.parametrize("presence,status,reason", [
    ("MISSING", "MISSING", "EVIDENCE_MISSING"),
    ("UNKNOWN", "UNVERIFIED", "EVIDENCE_UNKNOWN"),
    ("ERROR", "UNVERIFIED", "EVIDENCE_ERROR"),
])
def test_unknown_missing_and_error_never_ready(presence, status, reason):
    result = check(capabilities=[capability(presence=presence)])
    assert result["status"] == "NOT_READY"
    assert requirement(result)["status"] == status
    assert reason in requirement(result)["reasons"]


def test_stored_but_not_linked_is_not_sufficient():
    result = check(capabilities=[capability(linked=False)])
    assert requirement(result)["status"] == "PRESENT_NOT_CONNECTED"
    assert result["claims"][0]["status"] == "NOT_TESTABLE"


@pytest.mark.parametrize("field,value,reason", [
    ("scope_checked", False, "SCOPE_NOT_CHECKED"),
    ("scope_checked", 1, "SCOPE_NOT_CHECKED"),
    ("required_coverage_checked", False, "REQUIRED_COVERAGE_NOT_CHECKED"),
    ("required_coverage_passed", False, "COVERAGE_REQUIREMENT_NOT_MET"),
    ("coverage_evidence_ref", None, "COVERAGE_EVIDENCE_MISSING"),
    ("availability_checked", False, "AVAILABILITY_NOT_CHECKED"),
    ("source_ref", None, "SOURCE_REFERENCE_MISSING"),
    ("source_ref", " ", "SOURCE_REFERENCE_MISSING"),
    ("runtime_binding", None, "RUNTIME_BINDING_MISSING"),
    ("scope_ref", None, "SCOPE_BINDING_MISSING"),
    ("coverage_contract_ref", None, "COVERAGE_CONTRACT_MISSING"),
    ("known_at", None, "KNOWN_AT_MISSING_OR_INVALID"),
    ("known_at", "2026-09-01", "KNOWN_AT_MISSING_OR_INVALID"),
    ("known_at", "not-a-date", "KNOWN_AT_MISSING_OR_INVALID"),
    ("verification", "UNKNOWN", "VERIFICATION_NOT_ACCEPTED"),
])
def test_missing_attestations_and_provenance_fail_closed(field, value, reason):
    result = check(capabilities=[capability(**{field: value})])
    assert result["status"] == "NOT_READY"
    assert reason in requirement(result)["reasons"]


@pytest.mark.parametrize("field,value,reason", [
    ("role", "outcome", "ROLE_MISMATCH"),
    ("scope_ref", "sealed-oos", "SCOPE_BINDING_MISMATCH"),
    ("runtime_binding", "snapshot:other", "RUNTIME_BINDING_MISMATCH"),
    ("coverage_contract_ref", "aggregate-row-count", "COVERAGE_CONTRACT_MISMATCH"),
    ("known_at", "2026-09-03T00:00:00+09:00", "EVIDENCE_NOT_YET_KNOWN"),
])
def test_out_of_scope_bindings(field, value, reason):
    result = check(capabilities=[capability(**{field: value})])
    assert requirement(result)["status"] == "OUT_OF_SCOPE"
    assert reason in requirement(result)["reasons"]


@pytest.mark.parametrize("role", ["diagnostic", "regime"])
def test_assumed_diagnostic_requires_exact_opt_in_and_provenance(role):
    claims = [claim(role=role, policy="policy:macro-diagnostic-v1")]
    caps = [capability(role=role, verification="PIT_ASSUMED",
                       assumption_policy_ref="policy:macro-diagnostic-v1")]
    result = check(claims, caps)
    assert result["status"] == "READY"
    assert requirement(result)["verification"] == "PIT_ASSUMED"
    assert requirement(result)["assumption_policy_ref"] == "policy:macro-diagnostic-v1"


@pytest.mark.parametrize("role", ["feature", "outcome", "execution"])
def test_diagnostic_policy_cannot_be_reused_for_features_outcomes_or_execution(role):
    result = check(
        [claim(role=role, policy="policy:macro-diagnostic-v1")],
        [capability(role=role, verification="PIT_ASSUMED",
                    assumption_policy_ref="policy:macro-diagnostic-v1")],
    )
    assert result["status"] == "NOT_READY"
    assert "ASSUMPTION_FORBIDDEN_FOR_ROLE" in requirement(result)["reasons"]


def test_assumption_without_requirement_opt_in_is_blocked():
    result = check([claim(role="diagnostic")], [capability(
        role="diagnostic", verification="PIT_ASSUMED", assumption_policy_ref="policy:v1",
    )])
    assert "ASSUMPTION_NOT_ALLOWED_BY_REQUIREMENT" in requirement(result)["reasons"]


@pytest.mark.parametrize("policy,reason", [
    (None, "ASSUMPTION_PROVENANCE_MISSING"),
    ("policy:other", "ASSUMPTION_POLICY_MISMATCH"),
])
def test_assumption_provenance_cannot_be_missing_or_changed(policy, reason):
    result = check([claim(role="diagnostic", policy="policy:v1")], [capability(
        role="diagnostic", verification="PIT_ASSUMED", assumption_policy_ref=policy,
    )])
    assert result["status"] == "NOT_READY"
    assert reason in requirement(result)["reasons"]


def test_equivalent_timezone_instants_are_accepted():
    result = check(capabilities=[capability(known_at="2026-09-01T15:00:00Z")])
    assert result["status"] == "READY"


def test_empty_claims_do_not_vacuously_pass():
    assert check(claims=[], capabilities=[])["status"] == "NOT_READY"
    with pytest.raises(ValueError, match="at least one"):
        check(claims=[ResearchClaim("empty", ())])


def test_duplicate_ids_are_rejected():
    with pytest.raises(ValueError, match="Capability IDs"):
        check(capabilities=[capability(), capability()])
    with pytest.raises(ValueError, match="Claim IDs"):
        check(claims=[claim(), claim()])
    item = claim()
    with pytest.raises(ValueError, match="Requirement IDs"):
        check(claims=[replace(item, requirements=item.requirements * 2)])


def test_invalid_contracts_fail_closed():
    with pytest.raises(ValueError, match="timezone-aware"):
        check(as_of="2026-09-02")
    with pytest.raises(ValueError, match="Nonempty"):
        check(runtime_binding="")
    with pytest.raises(ValueError, match="Unknown evidence role"):
        check(claims=[claim(role="any")])
    with pytest.raises(ValueError, match="Unknown presence"):
        check(capabilities=[capability(presence="probably-present")])
    with pytest.raises(ValueError, match="coverage contract"):
        check(claims=[ResearchClaim("prediction", (EvidenceRequirement("price", "feature", ""),))])


def test_row_counts_or_performance_metrics_are_not_valid_capability_inputs():
    for arbitrary in ({"record_count": 1_000_000}, {"ic": .1}, {"return": .5}):
        with pytest.raises(ValueError, match="arbitrary metrics"):
            check(capabilities=[arbitrary])
    with pytest.raises(TypeError):
        EvidenceCapability("price", "feature", record_count=1_000_000)


def test_all_reasons_are_preserved_and_inputs_are_unchanged():
    value = capability(linked=False, source_ref=None, required_coverage_checked=False)
    before = repr(value)
    result = check(capabilities=[value])
    assert {"NOT_LINKED", "SOURCE_REFERENCE_MISSING", "REQUIRED_COVERAGE_NOT_CHECKED"}.issubset(
        requirement(result)["reasons"])
    assert repr(value) == before
