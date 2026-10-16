from copy import deepcopy

import pytest

from engine import adaptive_research as original
from engine.research_comparison_lab import CATALOG, ComparisonLab
from engine.research_comparison_runtime import ComparisonSession, PROMPT, VERSION, make_contract


def setup_case(tmp_path, scenario="economic_supported", question="ECONOMIC", **budgets):
    lab = ComparisonLab(11, scenario, question)
    contract = make_contract(lab.public_case(), CATALOG, planner_kind="HOST_LLM", **budgets)
    session = ComparisonSession(tmp_path / "session.sqlite", contract)
    return lab, session


def test_action(test, refs=()):
    return {"kind": "TEST", "reason": "Distinguish rival explanations", "evidence_ids": list(refs),
            "payload": {"diagnostic_id": test, "rivals": [
                {"explanation": "First account", "expected_if_true": "First observation"},
                {"explanation": "Second account", "expected_if_true": "Second observation"}],
                "changes_mind_if": "Evidence contradicts the first account"}}


# Utility, not a pytest test case.
test_action.__test__ = False


def stop(conclusion, refs=(), findings=()):
    return {"kind": "STOP", "reason": "Primary question addressed", "evidence_ids": list(refs),
            "payload": {"conclusion": conclusion, "findings": list(findings),
                        "limitations": "Observational associations do not identify causality",
                        "mechanism_identified": False}}


def submit(session, lab, action, **kwargs):
    packet = session.request()
    return session.submit(action, request_id=f"a-{packet['state']['actions_used']}",
                          expected_revision=packet["state"]["revision"], execute=kwargs.get("execute", lab.run))


def observe(session, lab, *tests):
    for test in tests:
        assert submit(session, lab, test_action(test))["status"] == "OBSERVED"
    return [e["evidence_id"] for e in session.packet()["state"]["evidence"]]


def test_new_contract_and_prompt_no_global_changes(tmp_path):
    before = (original.VERSION, original.PROMPT, set(original.CONCLUSIONS), set(original.FINDINGS))
    lab, session = setup_case(tmp_path)
    packet = session.packet()
    assert packet["version"] == VERSION
    assert packet["prompt"] == PROMPT
    assert "ECONOMIC_LINK_SUPPORTED" in packet["allowed_conclusions"]
    assert "ECONOMIC_OUTCOME_UNAVAILABLE" in packet["allowed_findings"]
    assert packet["economic_claim_contract"]["runtime_connected"] is True
    assert before == (original.VERSION, original.PROMPT, original.CONCLUSIONS, original.FINDINGS)
    assert ComparisonSession(session.path).packet() == packet


def test_contract_tampering_and_legacy_reopening_rejected(tmp_path):
    lab = ComparisonLab(11, "clean", "PREDICTIVE")
    contract = make_contract(lab.public_case(), CATALOG, planner_kind="LEAN_FIXED_REFERENCE")
    assert contract["planner_kind"] == "LEAN_FIXED_REFERENCE"
    tampered = deepcopy(contract)
    tampered["prompt_sha256"] = "wrong"
    with pytest.raises(ValueError):
        ComparisonSession(tmp_path / "tampered.sqlite", tampered)
    legacy = original.make_contract(lab.public_case(), CATALOG, planner_kind="HOST_LLM")
    original.DiagnosticSession(tmp_path / "legacy.sqlite", legacy)
    with pytest.raises(ValueError):
        ComparisonSession(tmp_path / "legacy.sqlite")


@pytest.mark.parametrize("conclusion", ["ECONOMIC_LINK_SUPPORTED", "ECONOMIC_LINK_NOT_SUPPORTED"])
def test_economic_conclusion_requires_both_cited_reports(tmp_path, conclusion):
    lab, session = setup_case(tmp_path)
    refs = observe(session, lab, "input_audit")
    result = submit(session, lab, stop(conclusion, refs))
    assert result["status"] == "REJECTED"
    refs = observe(session, lab, "economic_link")
    result = submit(session, lab, stop(conclusion, refs[1:]))
    assert result["error_code"] == "ECONOMIC_CONCLUSION_REQUIRES_CITED_VALID_INPUT_AUDIT"
    assert submit(session, lab, stop(conclusion, refs))["status"] == "STOPPED"
    assert session.export()["economic_claim_contract"]["economic_status"] == "ASSOCIATION_ASSESSED"


def test_economic_invalid_input_cannot_support_path(tmp_path):
    lab, session = setup_case(tmp_path, "economic_lookahead")
    refs = observe(session, lab, "input_audit", "economic_link")
    assert submit(session, lab, stop("ECONOMIC_LINK_SUPPORTED", refs))["status"] == "REJECTED"
    assert submit(session, lab, stop("INPUT_INVALID", refs, ["LOOKAHEAD"]))["status"] == "STOPPED"


def test_missing_finding_requires_actual_cited_missing_report(tmp_path):
    lab, session = setup_case(tmp_path, "economic_missing")
    refs = observe(session, lab, "input_audit")
    action = stop("NEEDS_DATA", refs, ["ECONOMIC_OUTCOME_UNAVAILABLE"])
    assert submit(session, lab, action)["status"] == "REJECTED"
    all_refs = observe(session, lab, "economic_link")
    assert submit(session, lab, action)["status"] == "REJECTED"
    assert submit(session, lab, stop("NEEDS_DATA", all_refs, ["ECONOMIC_OUTCOME_UNAVAILABLE"]))["status"] == "STOPPED"


def test_untested_neutral_causal_limitation_does_not_require_data(tmp_path):
    lab, session = setup_case(tmp_path)
    refs = observe(session, lab, "input_audit")
    assert submit(session, lab, stop("NEEDS_DATA", refs))["status"] == "REJECTED"
    assert submit(session, lab, stop("INCONCLUSIVE", refs, ["MECHANISM_UNIDENTIFIED"]))["status"] == "STOPPED"
    assert session.export()["economic_claim_contract"]["economic_status"] == "UNTESTED"


def test_request_data_requires_exact_missing_dataset_and_citation(tmp_path):
    lab, session = setup_case(tmp_path, "economic_missing")
    action = {"kind": "REQUEST_DATA", "reason": "Distinguish unavailable from assessed path",
              "evidence_ids": [], "payload": {"dataset": "next_period_economic_change",
                  "distinguishes": "Supported from unsupported observational path", "expected_value": "Allow both correlations"}}
    assert submit(session, lab, action)["status"] == "REJECTED"
    refs = observe(session, lab, "input_audit", "economic_link")
    assert submit(session, lab, action)["status"] == "REJECTED"
    action["evidence_ids"] = refs
    action["payload"]["dataset"] = "unobserved_dataset"
    assert submit(session, lab, action)["status"] == "REJECTED"
    action["payload"]["dataset"] = "next_period_economic_change"
    assert submit(session, lab, action)["status"] == "DATA_REQUESTED_NOT_ACQUIRED"


def test_positive_prediction_requires_all_three_cited_reports(tmp_path):
    lab, session = setup_case(tmp_path, "clean", "PREDICTIVE")
    refs = observe(session, lab, "input_audit", "controls")
    assert submit(session, lab, stop("ASSOCIATION_REMAINS", refs))["status"] == "REJECTED"
    refs = observe(session, lab, "execution_cost")
    assert submit(session, lab, stop("ECONOMIC_LINK_SUPPORTED", refs))["status"] == "REJECTED"
    assert submit(session, lab, stop("ASSOCIATION_REMAINS", refs))["status"] == "STOPPED"


def test_causal_claim_is_rejected(tmp_path):
    lab, session = setup_case(tmp_path)
    refs = observe(session, lab, "input_audit", "economic_link")
    action = stop("ECONOMIC_LINK_SUPPORTED", refs)
    action["payload"]["mechanism_identified"] = True
    assert submit(session, lab, action)["error_code"] == "CAUSAL_IDENTIFICATION_NOT_SUPPORTED"


@pytest.mark.parametrize("change", ["legacy_status", "one_estimate", "no_ci", "metadata_only"])
def test_malformed_economic_report_never_supports_path(tmp_path, change):
    lab, session = setup_case(tmp_path)
    observe(session, lab, "input_audit")
    def execute(test):
        report = lab.run(test)
        if change == "legacy_status":
            report["status"] = "AVAILABLE"
        elif change == "one_estimate":
            report["metrics"].pop("economic_change_to_return_ic")
        elif change == "no_ci":
            report["metrics"]["economic_change_to_return_ic"]["ci95"] = None
        else:
            report["metrics"] = {"n_rows": 11520, "outcome_availability_lag_months": 2}
        return report
    result = submit(session, lab, test_action("economic_link"), execute=execute)
    assert result["status"] == ("EXECUTION_FAILED" if change == "legacy_status" else "OBSERVED")
    refs = [e["evidence_id"] for e in session.packet()["state"]["evidence"]]
    assert submit(session, lab, stop("ECONOMIC_LINK_SUPPORTED", refs))["status"] == "REJECTED"


def test_ledger_budget_idempotency_and_failure_reservation(tmp_path):
    lab, session = setup_case(tmp_path, max_cost_units=3)
    packet = session.request()
    action = test_action("economic_link")
    calls = []
    def failing(test):
        calls.append(test)
        raise RuntimeError("must not log backend secrets")
    result = session.submit(action, request_id="same", expected_revision=packet["state"]["revision"], execute=failing)
    assert result["status"] == "EXECUTION_FAILED"
    assert session.submit(action, request_id="same", expected_revision=packet["state"]["revision"], execute=failing) == result
    assert calls == ["economic_link"]
    assert session.packet()["state"]["cost_units_used"] == 3
    assert submit(session, lab, test_action("input_audit"))["error_code"] == "DIAGNOSTIC_BUDGET_EXCEEDED"
    assert "backend secrets" not in original.canonical(session.export())


def test_chain_integrity_and_stale_revision(tmp_path):
    lab, session = setup_case(tmp_path)
    with pytest.raises(ValueError, match="Stale"):
        session.submit(test_action("input_audit"), request_id="stale", expected_revision=100, execute=lab.run)
    with session._connect() as db:
        db.execute("UPDATE events SET sha='changed' WHERE revision=0")
    with pytest.raises(ValueError, match="integrity"):
        session.packet()
