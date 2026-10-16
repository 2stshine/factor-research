import json
import sqlite3

import pytest

from engine.adaptive_research import DiagnosticSession, make_contract, CONCLUSIONS, FINDINGS


CATALOG = {"input_audit": {"cost": 1}, "controls": {"cost": 3}}


def make(tmp_path, **kwargs):
    return DiagnosticSession(tmp_path / "session.sqlite", make_contract(
        {"question": "Does a fixed signal have an incremental association?"}, CATALOG,
        planner_kind="HOST_LLM", **kwargs))


def test_action(test="input_audit"):
    return {"kind": "TEST", "reason": "Compare valid measurement against availability error.",
            "evidence_ids": [], "payload": {"diagnostic_id": test,
                "rivals": [{"explanation": "valid", "expected_if_true": "no late values"},
                           {"explanation": "leak", "expected_if_true": "late values"}],
                "changes_mind_if": "Late values invalidate the measured signal."}}


test_action.__test__ = False


def backend(test):
    return {"diagnostic_id": test, "status": "AVAILABLE", "metrics": {"late": 0}}


def submit(session, action, key="one", **kwargs):
    return session.submit(action, request_id=key, expected_revision=session.packet()["state"]["revision"],
                          execute=kwargs.get("execute", backend))


def test_resume_and_idempotency(tmp_path):
    s = make(tmp_path)
    first = submit(s, test_action())
    reopened = DiagnosticSession(s.path)
    assert reopened.packet()["state"]["cost_units_used"] == 1
    assert reopened.submit(test_action(), request_id="one", expected_revision=0,
                           execute=lambda _: pytest.fail("reran")) == first
    with pytest.raises(ValueError, match="payload conflict"):
        submit(reopened, test_action("controls"))


def test_revision_and_non_overwrite(tmp_path):
    s = make(tmp_path)
    submit(s, test_action())
    with pytest.raises(ValueError, match="Stale"):
        s.submit(test_action("controls"), request_id="two", expected_revision=0, execute=backend)
    with pytest.raises(FileExistsError):
        make(tmp_path)


@pytest.mark.parametrize("action", [None, {}, {"kind": "SQL"}, test_action("reveal_oos"),
    dict(test_action(), evidence_ids=["foreign-evidence"]),
    dict(test_action(), path="../sealed.json"),
    dict(test_action(), kind={}), dict(test_action(), payload={}),
    {"kind": "STOP", "reason": "guess", "evidence_ids": [], "payload": {
        "conclusion": "ASSOCIATION_REMAINS", "findings": [], "limitations": "unknown", "mechanism_identified": False}},
    {"kind": "STOP", "reason": "guess", "evidence_ids": [], "payload": {
        "conclusion": {}, "findings": [], "limitations": "unknown", "mechanism_identified": False}},
])
def test_invalid_actions_bounded(tmp_path, action):
    s = make(tmp_path, max_actions=1)
    result = submit(s, action, execute=lambda _: pytest.fail("invalid action executed"))
    assert result["status"] == "REJECTED"
    assert s.packet()["state"]["state"] == "ACTION_BUDGET_EXHAUSTED"


def test_budget_reserved_before_handler_and_not_refunded(tmp_path):
    s = make(tmp_path, max_cost_units=3)
    def broken(test):
        assert DiagnosticSession(s.path).packet()["state"]["cost_units_used"] == 3
        raise RuntimeError("ORACLE SECRET file and key")
    result = submit(s, test_action("controls"), execute=broken)
    assert result["status"] == "EXECUTION_FAILED"
    assert "SECRET" not in json.dumps(s.export())
    assert submit(s, test_action(), key="two")["error_code"] == "DIAGNOSTIC_BUDGET_EXCEEDED"


def test_repeated_diagnostic_does_not_create_new_evidence(tmp_path):
    s = make(tmp_path)
    submit(s, test_action())
    assert submit(s, test_action(), key="two")["error_code"] == "DIAGNOSTIC_ALREADY_OBSERVED"
    assert len(s.packet()["state"]["evidence"]) == 1


@pytest.mark.parametrize("kind,payload,status", [
    ("PROPOSE_TEST", {"question": "A new contrast", "design": "import os; dangerous()",
                      "distinguishes": "rival A vs rival B"}, "NEW_TEST_PENDING_REVIEW"),
    ("REQUEST_DATA", {"dataset": "historical industry", "distinguishes": "A vs B",
                      "expected_value": "separate confounding"}, "DATA_REQUESTED_NOT_ACQUIRED")])
def test_proposal_never_executes(tmp_path, kind, payload, status):
    s = make(tmp_path)
    result = submit(s, {"kind": kind, "reason": "Need more evidence", "evidence_ids": [], "payload": payload},
                    execute=lambda _: pytest.fail("proposal executed"))
    assert result["status"] == status
    assert s.packet()["state"]["state"] == "STOPPED"


def test_no_causal_proof_flag(tmp_path):
    s = make(tmp_path)
    e = submit(s, test_action())["evidence"]["evidence_id"]
    action = {"kind": "STOP", "reason": "Claim", "evidence_ids": [e], "payload": {
        "conclusion": "ASSOCIATION_REMAINS", "findings": [], "limitations": "observational",
        "mechanism_identified": True}}
    assert submit(s, action, key="two")["status"] == "REJECTED"
    action["payload"]["mechanism_identified"] = False
    assert submit(s, action, key="three")["status"] == "STOPPED"


def test_integrity_check_detects_mutation(tmp_path):
    s = make(tmp_path)
    with sqlite3.connect(s.path) as db:
        db.execute("UPDATE events SET body = ? WHERE revision=0", ('{}',))
    with pytest.raises(ValueError, match="integrity"):
        s.packet()


def test_prompt_receipt_and_callback_copy(tmp_path):
    s = make(tmp_path)
    p = s.request()
    assert p == s.request()
    assert s.events()[-1]["type"] == "PROMPT"
    p["public_case"]["question"] = "mutated"
    assert s.packet()["public_case"]["question"] != "mutated"
    def planner(packet):
        assert s.events()[-1]["packet"]["state"]["revision"] == packet["state"]["revision"]
        return {"kind": "STOP", "reason": "No evidence yet", "evidence_ids": [], "payload": {
            "conclusion": "INCONCLUSIVE", "findings": [], "limitations": "not investigated",
            "mechanism_identified": False}}
    result = s.run(planner, backend)
    assert result["state"]["state"] == "STOPPED"
    assert result["economic_or_statistical_truth_certified"] is False


def test_every_accepted_enum_is_public_before_decision(tmp_path):
    packet = make(tmp_path).request()
    assert set(packet["allowed_conclusions"]) == CONCLUSIONS
    assert set(packet["allowed_findings"]) == FINDINGS
    assert all(value in packet["prompt"] for value in CONCLUSIONS | FINDINGS)
    assert "NOT an array" in packet["action_schema"]["STOP"]["limitations"]


def test_stop_type_error_is_distinct_from_scientific_conclusion(tmp_path):
    s = make(tmp_path)
    e = submit(s, test_action())["evidence"]["evidence_id"]
    action = {"kind": "STOP", "reason": "Observed limitation", "evidence_ids": [e], "payload": {
        "conclusion": "INCONCLUSIVE", "findings": [], "limitations": ["unmeasured"], "mechanism_identified": False}}
    assert submit(s, action, key="two")["error_code"] == "LIMITATIONS_MUST_BE_NONEMPTY_STRING_MAX_2000"
    action["payload"]["limitations"] = "unmeasured"
    assert submit(s, action, key="three")["status"] == "STOPPED"


def test_interrupt_keeps_reserved_pending_no_automatic_retry(tmp_path):
    s = make(tmp_path)
    def interruption(_):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        submit(s, test_action(), execute=interruption)
    assert DiagnosticSession(s.path).packet()["state"]["state"] == "PENDING_RECONCILIATION"
    assert submit(s, test_action(), execute=lambda _: pytest.fail("retry"))["status"] == "PENDING_RECONCILIATION"


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nonfinite_rejected_before_executor(tmp_path, bad):
    s = make(tmp_path)
    action = test_action()
    action["payload"]["extra"] = bad
    with pytest.raises(ValueError):
        submit(s, action, execute=lambda _: pytest.fail("executed"))
