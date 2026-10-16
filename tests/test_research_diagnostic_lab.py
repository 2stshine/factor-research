"""Synthetic mathematics tests only: no research artifacts or data services."""
import json

import numpy as np
import pytest

from engine.research_diagnostic_lab import DIAGNOSTIC_CATALOG, SCENARIOS, DiagnosticLab, _estimate


def test_public_interface_is_anonymous_and_uniform():
    cases = [DiagnosticLab(21, scenario).public_case() for scenario in SCENARIOS]
    assert all(case == cases[0] for case in cases)
    assert cases[0] == DiagnosticLab(22, "clean").public_case()
    assert not {"seed", "scenario", "oracle", "expected_findings"} & cases[0].keys()
    assert sum(item["cost"] for item in DIAGNOSTIC_CATALOG.values()) == 15


def test_reports_are_deterministic_finite_and_not_oracles():
    for scenario in SCENARIOS:
        left, right = DiagnosticLab(101, scenario), DiagnosticLab(101, scenario)
        for diagnostic in DIAGNOSTIC_CATALOG:
            report = left.run(diagnostic)
            assert report == right.run(diagnostic)
            serialized = json.dumps(report, allow_nan=False)
            assert "expected_findings" not in serialized and '"scenario"' not in serialized
            report["metrics"]["caller_mutation"] = True
            assert "caller_mutation" not in left.run(diagnostic)["metrics"]


def test_generation_is_numeric_seed_dependent_and_monthly_dependent():
    left, right = DiagnosticLab(101, "clean"), DiagnosticLab(102, "clean")
    assert left._signal.shape == left._returns.shape == (96, 120)
    assert left.run("association") != right.run("association")
    common = left._returns.mean(axis=1)
    assert np.corrcoef(common[:-1], common[1:])[0, 1] > .15
    report = left.run("association")["metrics"]["raw_ic"]
    assert report["n_months"] == 96
    assert "monthly_hac" in report["method"]


@pytest.mark.parametrize("seed", [3, 19, 101])
def test_known_generating_issues_have_observable_numeric_signatures(seed):
    clean = DiagnosticLab(seed, "clean")
    assert clean.run("controls")["metrics"]["fully_adjusted_ic"]["ci95"][0] > .1
    assert clean.run("execution_cost")["metrics"]["net_spread"]["ci95"][0] > 0
    assert DiagnosticLab(seed, "lookahead").run("input_audit")["metrics"]["late_signal_fraction"] == 1
    sector = DiagnosticLab(seed, "sector_confounding").run("controls")["metrics"]
    assert sector["raw_ic"]["mean"] > .3
    assert abs(sector["sector_adjusted_ic"]["mean"]) < .06
    exposure = DiagnosticLab(seed, "exposure_confounding").run("controls")["metrics"]
    assert exposure["raw_ic"]["mean"] > .3
    assert abs(exposure["size_liquidity_adjusted_ic"]["mean"]) < .06
    costs = DiagnosticLab(seed, "costs").run("execution_cost")["metrics"]
    assert costs["gross_spread"]["ci95"][0] > 0 > costs["net_spread"]["ci95"][1]
    regime = DiagnosticLab(seed, "regime").run("regime_interaction")["metrics"]
    assert regime["regime_0"]["ci95"][1] < 0 < regime["regime_1"]["ci95"][0]
    assert regime["interaction"]["ci95"][0] > 0
    assert regime["interaction"]["mean"] == pytest.approx(regime["regime_1"]["mean"] - regime["regime_0"]["mean"])
    weak = DiagnosticLab(seed, "weak").run("association")["metrics"]["raw_ic"]
    assert abs(weak["mean"]) < .05


def test_mixed_case_preserves_multiple_truths_and_direct_evidence():
    lab = DiagnosticLab(101, "mixed")
    assert len(lab.oracle()["expected_findings"]) == 4
    metrics = lab.run("controls")["metrics"]
    assert metrics["sector_attenuation"]["mean"] > .04
    assert metrics["size_liquidity_attenuation"]["mean"] > .04
    assert lab.run("execution_cost")["metrics"]["net_spread"]["ci95"][1] < 0
    assert lab.run("regime_interaction")["metrics"]["interaction"]["ci95"][0] > 0


def test_missing_mechanism_is_unknown_not_a_zero_or_a_factor_failure():
    lab = DiagnosticLab(101, "mechanism_missing")
    report = lab.run("economic_link")
    assert report["status"] == "NOT_COMPUTED" and report["metrics"] == {}
    assert report["missing_datasets"] == ["next_period_economic_change"]
    assert "ASSOCIATION_REMAINS" in lab.oracle()["acceptable_conclusions"]
    assert lab.run("controls")["metrics"]["fully_adjusted_ic"]["ci95"][0] > 0
    assert DiagnosticLab(101, "clean").run("economic_link")["metrics"]["causal_identification"] is False


def test_hac_uses_calendar_month_dependence_and_not_stock_count():
    data = np.repeat(np.array([-1., 1., -1., 1.]), 12)
    estimate = _estimate(data)
    assert estimate["standard_error"] > data.std(ddof=1) / np.sqrt(len(data))
    assert estimate["n_months"] == 48
    separated = np.where(np.arange(48) % 2 == 0, data, np.nan)
    assert _estimate(separated)["n_months"] == 24
    assert _estimate(separated)["standard_error"] != _estimate(separated[np.isfinite(separated)])["standard_error"]


def test_controls_and_cost_arithmetic_refer_to_actual_same_panel():
    lab = DiagnosticLab(101, "clean")
    controls = lab.run("controls")["metrics"]
    assert controls["n_rows"] == 96 * 120
    assert controls["raw_ic"]["mean"] == pytest.approx(lab.run("association")["metrics"]["raw_ic"]["mean"])
    costs = lab.run("execution_cost")["metrics"]
    assert costs["net_spread"]["mean"] == pytest.approx(costs["gross_spread"]["mean"] - costs["estimated_cost"]["mean"])
    # Changing observed returns changes computed evidence, not canned scenario reports.
    lab._returns = -lab._returns
    lab._cache.clear()
    assert lab.run("association")["metrics"]["raw_ic"]["mean"] < 0


def test_invalid_requests_fail_closed():
    with pytest.raises(ValueError):
        DiagnosticLab(101, "unknown")
    with pytest.raises(ValueError):
        DiagnosticLab(True, "clean")
    with pytest.raises(ValueError):
        DiagnosticLab(101, "clean").run("oracle")
