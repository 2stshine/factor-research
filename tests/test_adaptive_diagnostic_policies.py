import pytest

from engine.adaptive_research import DiagnosticSession, make_contract
from engine.adaptive_diagnostic_policies import fixed_reference, adaptive_reference, score_episode
from engine.research_diagnostic_lab import DiagnosticLab, DIAGNOSTIC_CATALOG


@pytest.mark.parametrize("policy,kind", [(fixed_reference, "FIXED_REFERENCE"),
                                        (adaptive_reference, "SCRIPTED_ADAPTIVE_REFERENCE")])
def test_reference_is_bounded_and_does_not_receive_oracle(tmp_path, policy, kind):
    lab = DiagnosticLab(101, "clean")
    session = DiagnosticSession(tmp_path / "run.sqlite", make_contract(lab.public_case(), DIAGNOSTIC_CATALOG,
                                                                      planner_kind=kind))
    def checked(packet):
        assert "seed" not in packet["public_case"]
        assert "scenario" not in packet["public_case"]
        return policy(packet)
    export = session.run(checked, lab.run)
    score = score_episode(export, lab.oracle())
    assert score["complete"]
    assert score["tool_cost_units"] <= 10
    assert score["invalid_or_failed_actions"] == 0
    assert score["planner_monetary_cost"] is None


@pytest.mark.parametrize("conclusion", ["INCONCLUSIVE", "INPUT_INVALID"])
def test_always_abstain_or_reject_does_not_pass_clean_case(tmp_path, conclusion):
    lab = DiagnosticLab(101, "clean")
    session = DiagnosticSession(tmp_path / "run.sqlite", make_contract(lab.public_case(), DIAGNOSTIC_CATALOG,
                                                                      planner_kind="HOST_LLM"))
    def policy(packet):
        if not packet["state"]["evidence"]:
            return fixed_reference(packet)
        return {"kind": "STOP", "reason": "Always stop", "evidence_ids": [packet["state"]["evidence"][0]["evidence_id"]],
                "payload": {"conclusion": conclusion, "findings": [], "mechanism_identified": False,
                            "limitations": "An intentionally weak policy for scorer testing."}}
    score = score_episode(session.run(policy, lab.run), lab.oracle())
    assert score["primary_conclusion_correct"] is False
    assert score["normal_effect_preserved"] is False


def test_cited_input_audit_alone_cannot_establish_normal_association(tmp_path):
    lab = DiagnosticLab(101, "clean")
    session = DiagnosticSession(tmp_path / "run.sqlite", make_contract(lab.public_case(), DIAGNOSTIC_CATALOG,
                                                                      planner_kind="HOST_LLM"))
    def policy(packet):
        if not packet["state"]["evidence"]:
            return fixed_reference(packet)
        return {"kind": "STOP", "reason": "Unsupported inference", "evidence_ids": [packet["state"]["evidence"][0]["evidence_id"]],
                "payload": {"conclusion": "ASSOCIATION_REMAINS", "findings": [], "mechanism_identified": False,
                            "limitations": "No measurement of association or costs yet."}}
    score = score_episode(session.run(policy, lab.run), lab.oracle())
    assert score["unsupported_normal_conclusion"] is True
