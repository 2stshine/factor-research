"""Prefreeze contracts: development seeds only, never the evaluation manifest."""
from copy import deepcopy

import pytest

from engine.research_comparison_lab import CATALOG, ComparisonLab, SCENARIOS_BY_QUESTION
from engine.research_comparison_runtime import ComparisonSession, make_contract
from engine.research_comparison_policies import (
    conclusion_supported, economic_assessed, lean_fixed, observed_findings,
    score_episode, valid_input,
)


def estimate(mean=.2, lo=.1, hi=.3):
    return {"mean": mean, "ci95": [lo, hi]}


def valid_audit():
    return {"status": "COMPUTED", "metrics": dict.fromkeys((
        "duplicate_key_count", "late_signal_fraction", "late_control_fraction",
        "missing_signal_fraction", "missing_return_fraction"), 0)}


def evidence_data():
    return {
        "input_audit": valid_audit(),
        "controls": {"status": "COMPUTED", "metrics": {
            "raw_ic": estimate(), "fully_adjusted_ic": estimate()}},
        "execution_cost": {"status": "COMPUTED", "metrics": {
            "gross_spread": estimate(), "net_spread": estimate()}},
        "economic_link": {"status": "COMPUTED", "metrics": {
            "signal_to_economic_change_ic": estimate(),
            "economic_change_to_return_ic": estimate()}},
    }


@pytest.mark.parametrize("question,conclusion", [
    ("PREDICTIVE", "ASSOCIATION_REMAINS"),
    ("ECONOMIC", "ECONOMIC_LINK_SUPPORTED"),
])
def test_positive_terminal_requires_valid_audit_and_question(question, conclusion):
    data = evidence_data()
    assert conclusion_supported(conclusion, data, question)
    data.pop("input_audit")
    assert not conclusion_supported(conclusion, data, question)
    data = evidence_data()
    other = "ECONOMIC" if question == "PREDICTIVE" else "PREDICTIVE"
    assert not conclusion_supported(conclusion, data, other)


@pytest.mark.parametrize("key", list(valid_audit()["metrics"]))
def test_audit_requires_every_zero_field(key):
    data = evidence_data()
    del data["input_audit"]["metrics"][key]
    assert not valid_input(data)


@pytest.mark.parametrize("bad", [None, [], [0], [float("nan"), .2], [.3, .4]])
def test_economic_assessment_requires_valid_uncertainty(bad):
    data = evidence_data()
    data["economic_link"]["metrics"]["signal_to_economic_change_ic"]["ci95"] = bad
    assert not economic_assessed(data)
    assert not conclusion_supported("ECONOMIC_LINK_NOT_SUPPORTED", data, "ECONOMIC")


def test_economic_uncertainty_not_path_absence():
    data = evidence_data()
    data["economic_link"]["metrics"]["signal_to_economic_change_ic"] = estimate(0, -.1, .1)
    assert conclusion_supported("ECONOMIC_LINK_NOT_SUPPORTED", data, "ECONOMIC")
    assert not conclusion_supported("ECONOMIC_LINK_SUPPORTED", data, "ECONOMIC")


@pytest.mark.parametrize("conclusion", [
    "INPUT_INVALID", "COST_ERASED", "CONDITIONAL", "EXPLAINED_BY_EXPOSURES", "MIXED", "NEEDS_DATA",
])
def test_no_evidence_does_not_support_specific_terminal(conclusion):
    assert not conclusion_supported(conclusion, {}, "PREDICTIVE")


def test_cost_regime_and_exposure_need_matching_observations():
    data = evidence_data()
    assert not conclusion_supported("COST_ERASED", data, "PREDICTIVE")
    data["execution_cost"]["metrics"]["net_spread"] = estimate(-.2, -.3, -.1)
    assert conclusion_supported("COST_ERASED", data, "PREDICTIVE")
    assert not conclusion_supported("CONDITIONAL", data, "PREDICTIVE")
    data["regime_interaction"] = {"status": "COMPUTED", "metrics": {"interaction": estimate(.02, .01, .03)}}
    assert conclusion_supported("CONDITIONAL", data, "PREDICTIVE")
    assert conclusion_supported("MIXED", data, "PREDICTIVE")
    assert not conclusion_supported("EXPLAINED_BY_EXPOSURES", data, "PREDICTIVE")
    data["controls"]["metrics"].update({
        "sector_attenuation": estimate(.1, .05, .15), "fully_adjusted_ic": estimate(0, -.1, .1)})
    assert conclusion_supported("EXPLAINED_BY_EXPOSURES", data, "PREDICTIVE")


def test_lean_controls_supply_raw_uncertainty_without_redundant_association():
    data = evidence_data()
    data["controls"]["metrics"]["raw_ic"] = estimate(0, -.1, .1)
    assert "NO_CLEAR_EFFECT" in observed_findings(data)


@pytest.mark.parametrize("question,scenario", [
    (question, scenario) for question, scenarios in SCENARIOS_BY_QUESTION.items() for scenario in scenarios
])
def test_lean_fixed_development_episode_ends_without_rejected_action(tmp_path, question, scenario):
    lab = ComparisonLab(11, scenario, question)
    session = ComparisonSession(tmp_path / "test.sqlite", make_contract(
        lab.public_case(), CATALOG, planner_kind="LEAN_FIXED_REFERENCE"))
    export = session.run(lean_fixed, lab.run)
    score = score_episode(export, lab.oracle())
    assert score["complete"]
    assert score["invalid_or_failed_actions"] == 0
    assert score["unsupported_conclusion"] is False
    assert score["unsupported_findings"] == []
    tests = [e["diagnostic_id"] for e in export["state"]["evidence"]]
    if "lookahead" in scenario:
        assert tests == ["input_audit"]
        assert score["conclusion"] == "INPUT_INVALID"
    elif question == "ECONOMIC":
        assert tests == ["input_audit", "economic_link"]
        assert score["tool_cost_units"] == 4
    else:
        assert "association" not in tests
        assert score["tool_cost_units"] == 10
    if scenario == "economic_missing":
        assert score["useful_data_request"]
        uncited = deepcopy(export)
        uncited["state"]["terminal"]["decision"]["evidence_ids"] = []
        bad_score = score_episode(uncited, lab.oracle())
        assert bad_score["unsupported_conclusion"]
        assert not bad_score["primary_correct"]


def test_neutral_limitation_is_neither_missing_fact_nor_false_finding(tmp_path):
    lab = ComparisonLab(12, "clean", "PREDICTIVE")
    session = ComparisonSession(tmp_path / "test.sqlite", make_contract(
        lab.public_case(), CATALOG, planner_kind="LEAN_FIXED_REFERENCE"))
    export = session.run(lean_fixed, lab.run)
    export["state"]["terminal"]["decision"]["payload"]["findings"].append("MECHANISM_UNIDENTIFIED")
    score = score_episode(export, lab.oracle())
    assert score["neutral_limitations"] == ["MECHANISM_UNIDENTIFIED"]
    assert "MECHANISM_UNIDENTIFIED" not in score["false_findings_vs_generator"]
    assert "MECHANISM_UNIDENTIFIED" not in score["unsupported_findings"]
    assert not score["data_requested"]
