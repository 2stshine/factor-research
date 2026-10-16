from copy import deepcopy

import numpy as np
import pytest

from engine.research_comparison_lab import CATALOG, ComparisonLab, SCENARIOS_BY_QUESTION
from engine.research_diagnostic_lab import DiagnosticLab, DIAGNOSTIC_CATALOG


@pytest.mark.parametrize("question", SCENARIOS_BY_QUESTION)
def test_same_public_metadata_for_every_scenario_in_question(question):
    cases = [ComparisonLab(11, s, question).public_case() for s in SCENARIOS_BY_QUESTION[question]]
    assert all(case == cases[0] for case in cases)
    assert "seed" not in cases[0] and "scenario" not in cases[0]
    assert ComparisonLab(12, SCENARIOS_BY_QUESTION[question][0], question).public_case() == cases[0]


@pytest.mark.parametrize("question,scenario", [
    (q, s) for q, ss in SCENARIOS_BY_QUESTION.items() for s in ss
])
def test_reports_computed_from_panel_and_reproducible(question, scenario):
    first, second = ComparisonLab(11, scenario, question), ComparisonLab(11, scenario, question)
    for test in CATALOG:
        report = first.run(test)
        assert report == second.run(test)
        assert report["status"] in {"COMPUTED", "NOT_COMPUTED"}
        assert "scenario" not in report and "seed" not in report
        assert report["diagnostic_id"] == test


def test_old_lab_and_catalog_unchanged():
    old = DiagnosticLab(11, "clean")
    new = ComparisonLab(11, "clean", "PREDICTIVE")
    for test in CATALOG:
        translated = new.run(test)
        translated.pop("report_contract_version")
        translated["status"] = "AVAILABLE"
        assert translated == old.run(test)
    assert DIAGNOSTIC_CATALOG["economic_link"]["description"] != CATALOG["economic_link"]["description"]


def test_economic_null_uses_different_outcomes_and_real_estimates():
    clean = ComparisonLab(11, "economic_supported", "ECONOMIC")
    null = ComparisonLab(11, "economic_null", "ECONOMIC")
    assert np.array_equal(clean._lab._signal, null._lab._signal)
    assert np.array_equal(clean._lab._returns, null._lab._returns)
    assert not np.array_equal(clean._lab._economic_change, null._lab._economic_change)
    original = deepcopy(null.run("economic_link"))
    null._lab._economic_change = clean._lab._signal.copy()
    null._lab._cache.clear()
    changed = null.run("economic_link")
    assert changed != original
    assert changed["metrics"]["signal_to_economic_change_ic"]["mean"] == pytest.approx(1)


def test_late_economic_labels_do_not_make_formation_features_late():
    valid = ComparisonLab(11, "economic_supported", "ECONOMIC")
    invalid = ComparisonLab(11, "economic_lookahead", "ECONOMIC")
    assert valid.run("input_audit")["metrics"]["late_signal_fraction"] == 0
    assert valid.run("economic_link")["metrics"]["outcome_availability_lag_months"] == 2
    assert invalid.run("input_audit")["metrics"]["late_signal_fraction"] == 1


def test_missing_outcome_not_a_zero_association():
    case = ComparisonLab(11, "economic_missing", "ECONOMIC")
    result = case.run("economic_link")
    assert result["status"] == "NOT_COMPUTED"
    assert result["missing_datasets"] == ["next_period_economic_change"]
    assert not result["metrics"]
    assert case.oracle()["expected_economic_decision"] == "NEEDS_DATA"


def test_copy_isolation_and_oracle_distinction():
    case = ComparisonLab(11, "economic_supported", "ECONOMIC")
    report = case.run("economic_link")
    report["metrics"].clear()
    assert case.run("economic_link")["metrics"]
    public = case.public_case()
    public["diagnostics"].clear()
    assert case.public_case()["diagnostics"]
    assert case.oracle()["acceptable_conclusions"] == ["ECONOMIC_LINK_SUPPORTED"]
    assert case.oracle()["mechanism_identified"] is False


@pytest.mark.parametrize("seed,scenario,question", [
    (-1, "clean", "PREDICTIVE"), (True, "clean", "PREDICTIVE"),
    (1, "economic_null", "PREDICTIVE"), (1, "clean", "ECONOMIC"),
    (1, "clean", "UNKNOWN"),
])
def test_invalid_config(seed, scenario, question):
    with pytest.raises(ValueError):
        ComparisonLab(seed, scenario, question)
