from copy import deepcopy

import pytest

from engine.research_real_runtime import RealDiagnosticSession, make_contract


CATALOG = {x: {"cost": c, "description": x} for x, c in
           [("input_audit", 1), ("controls", 3), ("regime_interaction", 3), ("association", 2)]}


def session(tmp_path, **kwargs):
    contract = make_contract({"question": "Explain", "factor_approval_allowed": False}, CATALOG,
                             planner_kind="HOST_LLM", required_diagnostics=["input_audit", "controls", "regime_interaction"],
                             data_contract_sha256="a" * 64, **kwargs)
    return RealDiagnosticSession(tmp_path / "session.sqlite", contract)


def action(test):
    return {"kind": "TEST", "reason": "Discriminate explanations", "evidence_ids": [],
            "payload": {"diagnostic_id": test, "rivals": [
                {"explanation": "Input problem", "expected_if_true": "Invalid rows"},
                {"explanation": "Observed relation", "expected_if_true": "Valid observations"}],
                "changes_mind_if": "The evidence contradicts the current account"}}


def submit(s, a, response=None):
    p = s.request()
    def execute(test):
        value = deepcopy(response) if response is not None else {
            "diagnostic_id": test, "status": "COMPUTED", "metrics": {}, "missing_datasets": []}
        value.setdefault("evidence_scope", {"contract_sha256": "a" * 64})
        return value
    return s.submit(a, request_id=f"step-{p['state']['actions_used']}",
                    expected_revision=p["state"]["revision"], execute=execute)


def stop(s, unresolved=None):
    refs = [e["evidence_id"] for e in s.packet()["state"]["evidence"]]
    return {"kind": "STOP", "reason": "Explanation complete", "evidence_ids": refs,
            "payload": {"conclusion": "EXPLANATION_COMPLETE_WITH_LIMITATIONS",
                        "observations": [{"statement": "These are observed diagnostic reports", "evidence_ids": refs}],
                        "unresolved": unresolved or [], "limitations": "Historical reuse; no causal or OOS claim",
                        "mechanism_identified": False}}


def test_real_session_cannot_skip_input_or_required_regime(tmp_path):
    s = session(tmp_path)
    assert submit(s, action("controls"))["error_code"] == "INPUT_AUDIT_REQUIRED_FIRST"
    assert submit(s, action("input_audit"))["status"] == "OBSERVED"
    assert submit(s, action("controls"))["status"] == "OBSERVED"
    assert submit(s, stop(s))["error_code"] == "REQUIRED_EXPLANATORY_EVIDENCE_UNPERFORMED"
    assert submit(s, action("regime_interaction"))["status"] == "OBSERVED"
    assert submit(s, stop(s))["status"] == "STOPPED"
    exported = s.export()
    assert exported["mode"] == "REAL_DISCOVERY_REANALYSIS"
    assert not exported["independent_oos_claim"] and exported["gold_writes"] == 0


def test_optional_diagnostic_cannot_consume_required_budget(tmp_path):
    s = session(tmp_path, max_cost_units=7)
    submit(s, action("input_audit"))
    assert submit(s, action("association"))["error_code"] == "PRESERVE_REQUIRED_EVIDENCE_BUDGET"


def test_missing_required_evidence_is_not_silently_successful(tmp_path):
    s = session(tmp_path)
    submit(s, action("input_audit"))
    submit(s, action("controls"), {"diagnostic_id": "controls", "status": "NOT_COMPUTED",
                                   "missing_datasets": ["industry"], "metrics": {}})
    submit(s, action("regime_interaction"))
    assert submit(s, stop(s))["error_code"] == "MISSING_EVIDENCE_MUST_REMAIN_UNRESOLVED"
    assert submit(s, stop(s, ["Industry missing; its explanation is unresolved"]))["status"] == "STOPPED"


def test_unknown_reference_and_unobserved_missing_request_rejected(tmp_path):
    s = session(tmp_path)
    submit(s, action("input_audit"))
    a = {"kind": "REQUEST_DATA", "reason": "Need evidence", "evidence_ids": [],
         "payload": {"dataset": "invented", "distinguishes": "rivals", "expected_value": "test"}}
    assert submit(s, a)["error_code"] == "DATA_REQUEST_REQUIRES_OBSERVED_MISSING_DATASET"
    a["evidence_ids"] = ["made-up"]
    assert submit(s, a)["error_code"] == "UNKNOWN_OR_DUPLICATE_EVIDENCE"


def test_cited_required_and_no_causal_claim(tmp_path):
    s = session(tmp_path)
    for test in ("input_audit", "controls", "regime_interaction"):
        submit(s, action(test))
    a = stop(s)
    a["payload"]["mechanism_identified"] = True
    assert submit(s, a)["error_code"] == "UNSUPPORTED_CONCLUSION"
    a = stop(s)
    a["evidence_ids"] = a["evidence_ids"][:1]
    a["payload"]["observations"][0]["evidence_ids"] = a["evidence_ids"]
    assert submit(s, a)["error_code"] == "REQUIRED_EXPLANATORY_EVIDENCE_NOT_CITED"


def test_required_evidence_cannot_be_global_citation_without_observation(tmp_path):
    s = session(tmp_path)
    for test in ("input_audit", "controls", "regime_interaction"):
        submit(s, action(test))
    a = stop(s)
    # Listing all global refs must not substitute for actually accounting for
    # those diagnostic results in the observations used in the explanation.
    a["payload"]["observations"][0]["evidence_ids"] = a["evidence_ids"][:1]
    assert submit(s, a)["status"] == "REJECTED"


def test_reopening_and_changed_contract_are_detected(tmp_path):
    s = session(tmp_path)
    submit(s, action("input_audit"))
    assert RealDiagnosticSession(s.path).packet() == s.packet()
    c = deepcopy(s.events()[0]["contract"])
    c["mode"] = "SYNTHETIC_ONLY"
    with pytest.raises(ValueError):
        RealDiagnosticSession(tmp_path / "bad.sqlite", c)


def test_idempotent_and_failed_handler_cannot_leak_errors(tmp_path):
    s = session(tmp_path)
    p = s.request()
    def failed(test):
        raise RuntimeError("PRIVATE_CANARY")
    kwargs = dict(request_id="one", expected_revision=p["state"]["revision"], execute=failed)
    result = s.submit(action("input_audit"), **kwargs)
    assert result["status"] == "EXECUTION_FAILED"
    assert s.submit(action("input_audit"), **kwargs) == result
    assert "PRIVATE_CANARY" not in str(s.export())


def test_budget_must_cover_required_work(tmp_path):
    with pytest.raises(ValueError, match="Budget"):
        session(tmp_path, max_cost_units=6)


@pytest.mark.parametrize("kind", [[], {}, ["TEST"], {"kind": "STOP"}])
def test_malformed_json_action_kind_is_rejected_and_audited(tmp_path, kind):
    s = session(tmp_path)
    a = action("input_audit")
    a["kind"] = kind
    result = submit(s, a)
    assert result["status"] == "REJECTED"
    assert s.packet()["state"]["actions_used"] == 1
    assert not s.packet()["state"]["evidence"]


@pytest.mark.parametrize("conclusion", [[], {}, ["INPUT_INVALID"]])
def test_malformed_json_conclusion_is_rejected_not_crash(tmp_path, conclusion):
    s = session(tmp_path)
    submit(s, action("input_audit"))
    a = stop(s)
    a["payload"]["conclusion"] = conclusion
    assert submit(s, a)["status"] == "REJECTED"


def test_input_invalid_must_cite_the_computed_audit_defect(tmp_path):
    s = session(tmp_path)
    submit(s, action("input_audit"), {"diagnostic_id": "input_audit", "status": "COMPUTED",
        "metrics": {"duplicate_key_count": 1, "late_signal_fraction": 0, "late_control_fraction": 0}})
    submit(s, action("controls"))
    a = stop(s)
    a["payload"]["conclusion"] = "INPUT_INVALID"
    a["evidence_ids"] = a["evidence_ids"][1:]
    a["payload"]["observations"][0]["evidence_ids"] = a["evidence_ids"]
    assert submit(s, a)["status"] == "REJECTED"


@pytest.mark.parametrize("status,defect", [("NOT_COMPUTED", 1), ("COMPUTED", True)])
def test_input_invalid_cannot_use_noncomputed_or_boolean_defect(tmp_path, status, defect):
    s = session(tmp_path)
    submit(s, action("input_audit"), {"diagnostic_id": "input_audit", "status": status,
        "metrics": {"duplicate_key_count": defect}})
    a = stop(s)
    a["payload"]["conclusion"] = "INPUT_INVALID"
    assert submit(s, a)["status"] == "REJECTED"


def test_needs_data_stop_requires_cited_observed_missing_dataset(tmp_path):
    s = session(tmp_path)
    submit(s, action("input_audit"))
    a = stop(s, ["I suspect missing industry, but have not checked"])
    a["payload"]["conclusion"] = "NEEDS_DATA"
    assert submit(s, a)["status"] == "REJECTED"


def test_optional_work_cannot_spend_required_action_slots(tmp_path):
    s = session(tmp_path, max_actions=4)
    submit(s, action("input_audit"))
    result = submit(s, action("association"))
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "PRESERVE_REQUIRED_ACTION_BUDGET"


@pytest.mark.parametrize("mutation", ["wrong_scope", "missing_scope", "bad_metrics", "bad_missing_datasets", "unknown_status"])
def test_malformed_or_cross_contract_handler_report_is_not_evidence(tmp_path, mutation):
    s = session(tmp_path)
    p = s.request()
    report = {"diagnostic_id": "input_audit", "status": "COMPUTED", "metrics": {},
              "missing_datasets": [], "evidence_scope": {"contract_sha256": "a" * 64}}
    if mutation == "wrong_scope":
        report["evidence_scope"]["contract_sha256"] = "b" * 64
    elif mutation == "missing_scope":
        report.pop("evidence_scope")
    elif mutation == "bad_metrics":
        report["metrics"] = []
    elif mutation == "bad_missing_datasets":
        report["missing_datasets"] = [{"private": "CANARY"}]
    else:
        report["status"] = "AVAILABLE"
    result = s.submit(action("input_audit"), request_id="malformed-report",
                      expected_revision=p["state"]["revision"], execute=lambda _: report)
    assert result["status"] == "EXECUTION_FAILED"
    assert s.packet()["state"]["evidence"] == []
    assert "CANARY" not in str(s.export())


def test_data_contract_hash_must_be_hex_sha256(tmp_path):
    with pytest.raises(ValueError):
        make_contract({"question": "Explain", "factor_approval_allowed": False}, CATALOG,
            planner_kind="HOST_LLM", required_diagnostics=["input_audit"],
            data_contract_sha256="not-a-real-hash".ljust(64, "z"))


def test_early_data_request_is_suspension_not_explanation_completion(tmp_path):
    s = session(tmp_path)
    submit(s, action("input_audit"), {"diagnostic_id": "input_audit", "status": "NOT_COMPUTED",
        "missing_datasets": ["known_at"], "metrics": {}})
    ref = s.packet()["state"]["evidence"][0]["evidence_id"]
    a = {"kind": "REQUEST_DATA", "reason": "Timestamp evidence unavailable", "evidence_ids": [ref],
         "payload": {"dataset": "known_at", "distinguishes": "Input validity", "expected_value": "Audit inputs"}}
    assert submit(s, a)["status"] == "DATA_REQUESTED_NOT_ACQUIRED"
    exported = s.export()
    assert exported["explanation_complete"] is False
    assert set(exported["unperformed_required_diagnostics"]) == {"controls", "regime_interaction"}


def test_early_test_proposal_is_not_explanation_completion(tmp_path):
    s = session(tmp_path)
    a = {"kind": "PROPOSE_TEST", "reason": "New evidence required", "evidence_ids": [],
         "payload": {"question": "Unanswered rival", "design": "An inert proposal", "distinguishes": "Two explanations"}}
    assert submit(s, a)["status"] == "NEW_TEST_PENDING_REVIEW"
    exported = s.export()
    assert exported["explanation_complete"] is False
    assert set(exported["unperformed_required_diagnostics"]) == {"input_audit", "controls", "regime_interaction"}


def test_observed_real_adapter_is_accepted_with_matching_data_contract(tmp_path):
    from engine.research_real_diagnostics import CATALOG as REAL_CATALOG, RealDiagnosticLab, frame_hash
    from engine.adaptive_research import digest
    from tests.test_research_real_diagnostics import fixture_frame, fixture_contract
    frame = fixture_frame()
    contract = fixture_contract(frame)
    lab = RealDiagnosticLab(frame, contract)
    runtime = make_contract(lab.public_case(), REAL_CATALOG, planner_kind="HOST_LLM",
        required_diagnostics=["input_audit", "controls", "regime_interaction", "economic_link"],
        data_contract_sha256=digest(contract))
    s = RealDiagnosticSession(tmp_path / "real-adapter.sqlite", runtime)
    for i, diagnostic in enumerate(runtime["required_diagnostics"]):
        packet = s.request()
        response = s.submit(action(diagnostic), request_id=f"adapter-{i}",
            expected_revision=packet["state"]["revision"], execute=lab.run)
        assert response["status"] == "OBSERVED"
        assert response["evidence"]["response"]["evidence_scope"]["frame_sha256"] == frame_hash(frame)
    assert submit(s, stop(s, ["Regime/economic datasets absent; these claims remain unresolved"]))["status"] == "STOPPED"
