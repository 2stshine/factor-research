"""Synthetic-only production adapter tests; no I/O, campaigns, OOS or network."""
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from engine.factors import Factor
from engine.research_production_evidence import (
    MANDATORY, _definition, _digest, prepare_discovery_evidence, validate_diagnostic_plan,
)
from engine.research_real_diagnostics import RealDiagnosticLab


def never_compute(frame):
    raise AssertionError("The candidate must never execute in evidence capture")
    return frame["adj_close"].groupby(frame["asset_id"]).pct_change(6)


def fixture():
    months = pd.period_range("2015-01", "2022-12", freq="M")
    month = np.repeat(months, 80)
    asset = np.tile(np.arange(80), len(months))
    date = pd.PeriodIndex(month).end_time.normalize()
    rng = np.random.default_rng(345)
    frame = pd.DataFrame({"asset_id": asset, "ym": month, "trade_date": date,
        "available_date": date - pd.Timedelta(days=5),
        "f_new_generic_factor": rng.normal(size=len(month)), "fwd_mid": rng.normal(size=len(month)),
        "adj_close": 10 + asset, "market_cap": 1000 + asset, "adv20": 100 + asset,
        "market": np.where(asset % 2, "KOSPI", "KOSDAQ"),
        "total_assets": 1000. + asset, "net_income_ttm": 10. + asset + np.arange(len(month)) / 100,
        "operating_income_ttm": 20. + asset + np.arange(len(month)) / 50,
        "current_industry_unverified": np.where(asset % 3, "A", "B"),
        "industry_available_at": date - pd.Timedelta(days=10),
        "unassigned_private_column": "MUST_NOT_BE_EXPOSED"})
    factor = Factor(name="new_generic_factor", category="quality", hypothesis="Synthetic measurement only",
        predicted_sign=1, compute=never_compute, params={"lookback_months": 6},
        needs=("net_income_ttm", "total_assets"))
    panel = SimpleNamespace(monthly=frame, investable=pd.Series(True, index=frame.index))
    campaign = {"campaign_id": "synthetic-production", "discovery": {"data_cutoff": "2021-06-30", "signal_end": "2021-05"},
                "oos": {"start": "2021-07"}, "snapshot": {"discovery_input_digest": "a" * 64}}
    result = SimpleNamespace(factor=factor.name, definition_hash=factor.definition_hash, checks=[],
                             metrics={"gross": 100, "net": 99, "cost": 1})
    spec = {"strategy_sha256": "b" * 64}
    return panel, frame, factor, result, campaign, spec


def prepare(**kwargs):
    return prepare_discovery_evidence(*fixture(), **kwargs)


def economic_plan(**overrides):
    outcome = {"numerator": "operating_income_ttm", "denominator": "total_assets",
        "available_at": "available_date", "horizon_months": 12, "measurement_kind": "CHANGE",
        "rationale": "The preregistered thesis predicts changes in operating profitability, not net ROA.",
        "dataset_id": "synthetic-certified-silver-operating-profitability"}
    outcome.update(overrides)
    return {"economic_outcome": outcome}


def test_arbitrary_factor_reuses_signal_and_does_not_default_to_financial_roa():
    bundle = prepare()
    assert bundle["status"] == "PREPARED"
    assert bundle["contract"]["economic"] is None
    assert bundle["contract"]["execution"] is None
    assert bundle["readiness"]["economic"]["status"] == "NOT_PREREGISTERED"
    assert bundle["readiness"]["execution"]["aggregate_gate_metrics_used_as_execution_evidence"] is False
    assert bundle["required_diagnostics"] == list(MANDATORY)
    assert not bundle["candidate_recomputed"] and not bundle["gate_decision_modified"]
    assert "unassigned_private_column" not in bundle["frame"]
    assert "current_industry_unverified" not in bundle["frame"]
    lab = RealDiagnosticLab(bundle["frame"], bundle["contract"])
    assert lab.run("association")["status"] == "COMPUTED"
    assert lab.run("economic_link")["status"] == "NOT_COMPUTED"
    assert lab.run("execution_cost")["status"] == "NOT_COMPUTED"


def test_same_run_input_history_reports_six_month_candidate_not_36_month_requirement():
    history = prepare()["input_history"]
    assert history["formula_max_lag_bound_months"] == 6
    assert history["policy_maximum_months"] == 36
    assert history["policy_maximum_is_not_required_warmup"]
    assert not history["evaluation_start_modified"]
    assert history["baseline_evaluation_start"] == "2018-03"
    columns = {x["input_id"]: x for x in history["inputs"]}
    assert columns["net_income_ttm"]["source_history_months"] is None
    assert columns["net_income_ttm"]["nominal_source_window_months"] == 12
    assert columns["adj_close"]["dependency_basis"] == "STATIC_COMMON_FIELD_REFERENCE"


def test_scope_excludes_support_and_oos_before_economic_join_or_history_profiles():
    args = list(fixture())
    args[-1]["diagnostic_plan"] = economic_plan()
    before = prepare_discovery_evidence(*args)
    changed = args[1].copy(deep=True)
    sealed = changed.ym.ge(pd.Period("2021-06", freq="M"))
    changed.loc[sealed, ["fwd_mid", "f_new_generic_factor", "net_income_ttm", "operating_income_ttm", "adj_close"]] = -900000
    args[1] = changed
    after = prepare_discovery_evidence(*args)
    pd.testing.assert_frame_equal(before["frame"], after["frame"])
    assert before["contract"] == after["contract"]
    assert before["input_history"] == after["input_history"]
    assert before["input_profiles"] == after["input_profiles"]
    assert after["frame"].month.min() == "2018-03"
    assert after["frame"].month.max() == "2021-05"


def test_hypothesis_specific_economic_measurement_respects_exact_calendar_and_fresh_filing():
    args = list(fixture())
    args[-1]["diagnostic_plan"] = economic_plan()
    bundle = prepare_discovery_evidence(*args)
    assert "economic_link" in bundle["required_diagnostics"]
    assert bundle["readiness"]["economic"]["measurement"]["numerator"] == "operating_income_ttm"
    first = bundle["frame"].query("month == '2018-03'").iloc[0]
    current = args[1].query("asset_id == 0").set_index("ym")
    expected = (current.loc[pd.Period("2019-03"), "operating_income_ttm"] - current.loc[pd.Period("2018-03"), "operating_income_ttm"]) / 1000
    assert first.economic_outcome == pytest.approx(expected)
    assert bundle["frame"].query("month == '2021-05'").economic_outcome.isna().all()
    args[1].loc[args[1].ym.eq(pd.Period("2019-03")), "available_date"] = pd.Timestamp("2018-03-01")
    stale = prepare_discovery_evidence(*args)
    assert stale["frame"].query("month == '2018-03'").economic_outcome.isna().all()


def test_economic_missing_exit_is_not_forward_filled():
    args = list(fixture())
    args[-1]["diagnostic_plan"] = economic_plan(measurement_kind="LEVEL")
    keep = ~(args[1].ym.eq(pd.Period("2019-03")) & args[1].asset_id.eq(0))
    args[1] = args[1].loc[keep].copy()
    args[0] = SimpleNamespace(monthly=args[1], investable=pd.Series(True, index=args[1].index))
    bundle = prepare_discovery_evidence(*args)
    assert bundle["frame"].query("month == '2018-03' and asset_id == 0").economic_outcome.isna().all()


def test_unconnected_source_not_claimed_absent_even_when_column_exists():
    args = list(fixture())
    args[-1]["diagnostic_plan"] = economic_plan(numerator="operating_cash_flow_ttm")
    args[1]["operating_cash_flow_ttm"] = 5.
    bundle = prepare_discovery_evidence(*args)
    assert bundle["readiness"]["economic"]["status"] == "NOT_CONNECTED"
    assert bundle["readiness"]["economic"]["source_absence_established"] is False
    assert bundle["contract"]["economic"] is None


def test_future_filing_is_masked_in_signal_audit_not_declared_pit_verified():
    args = list(fixture())
    args[1].loc[args[1].ym.eq(pd.Period("2018-03")), "available_date"] = pd.Timestamp("2018-04-01")
    bundle = prepare_discovery_evidence(*args)
    report = RealDiagnosticLab(bundle["frame"], bundle["contract"]).run("input_audit")
    assert report["metrics"]["late_signal_fraction"] > 0
    assert not report["metrics"]["historical_first_release_verified"]


def test_verified_historical_industry_contract_connected_and_late_rows_masked():
    args = list(fixture())
    args[-1]["diagnostic_plan"] = {"industry_control": {"column": "current_industry_unverified",
        "known_at": "industry_available_at", "source_ref": "synthetic-historical-industry-contract",
        "evidence_sha256": "c" * 64, "pit_status": "VERIFIED"}}
    bundle = prepare_discovery_evidence(*args)
    assert bundle["readiness"]["industry"]["status"] == "CONNECTED"
    assert bundle["readiness"]["industry"]["source_independently_reverified"] is False
    report = RealDiagnosticLab(bundle["frame"], bundle["contract"]).run("controls")
    assert report["metrics"]["industry_control_available"]


def projection(frame):
    frame = frame.copy()
    frame["market_regime"] = np.where(frame.market.eq("KOSPI"), "UP_LOW", "DOWN_HIGH")
    frame["regime_known_at"] = pd.PeriodIndex(frame.month, freq="M").end_time
    regime = {"column": "market_regime", "known_at": "regime_known_at", "labels": ["UP_LOW", "DOWN_HIGH"],
              "contrast": ["UP_LOW", "DOWN_HIGH"], "definition_sha256": "d" * 64, "pit_status": "PIT_ASSUMED"}
    return frame, {"market_views": {market: {"regime": regime,
        "row_indices": list(np.flatnonzero(frame.market.eq(market)))} for market in ("KOSPI", "KOSDAQ")}}


def test_market_specific_child_labs_do_not_use_kospi_for_kosdaq_or_pollute_primary():
    bundle = prepare(regime_projection=projection)
    assert bundle["contract"]["regime"] is None
    assert "market_regime" not in bundle["frame"]
    assert set(bundle["regime_labs"]) == {"KOSPI", "KOSDAQ"}
    for market, expected in (("KOSPI", "UP_LOW"), ("KOSDAQ", "DOWN_HIGH")):
        child = bundle["regime_labs"][market]
        assert child["frame"].market_regime.eq(expected).all()
        report = RealDiagnosticLab(child["frame"], child["contract"]).run("regime_interaction")
        assert report.get("reason") != "INCONSISTENT_MARKET_STATE_WITHIN_MONTH"


def test_projection_cannot_change_primary_evidence():
    def bad(frame):
        frame.loc[0, "signal"] = 999.
        return frame, {}
    with pytest.raises(ValueError, match="modified primary"):
        prepare(regime_projection=bad)


def test_macro_contrast_must_be_preregistered_and_declaration_bounded():
    with pytest.raises(ValueError, match="contrast"):
        validate_diagnostic_plan({"macro_axes": ["policy_rate"]})
    assert validate_diagnostic_plan({"macro_axes": ["policy_rate"],
        "macro_contrasts": {"policy_rate": ["LOW", "HIGH"]}})["macro_axes"] == ["policy_rate"]
    with pytest.raises(ValueError, match="At most two"):
        validate_diagnostic_plan({"macro_axes": ["a", "b", "c"]})


def test_unregistered_execution_aggregate_is_not_portfolio_evidence():
    bundle = prepare()
    assert bundle["readiness"]["execution"]["status"] == "NOT_CONNECTED"
    assert bundle["contract"]["execution"] is None
    with pytest.raises(ValueError, match="exact Discovery"):
        prepare(execution_artifact={"binding": {"phase": "OOS"}})


def test_hash_bound_same_window_execution_artifact_is_read_without_rebacktest():
    args = list(fixture())
    args[-1]["diagnostic_plan"] = {"execution_cost": True}
    periods = pd.period_range("2018-03", "2021-05", freq="M")
    holdings = [{"month": str(m), "asset_id": 0, "weight": 1.} for m in periods]
    returns, costs = {"name": "synthetic-month-end-excess-return"}, {"name": "synthetic-cost-model"}
    contract = {"gross": "gross", "net": "net", "cost": "cost", "turnover": "turnover", "known_at": "known_at",
        "holdings_sha256": _digest(holdings), "return_contract_sha256": _digest(returns), "cost_model_sha256": _digest(costs),
        "timing_contract": "SYNTHETIC_MONTH_END_NOT_NEXT_OPEN_FILLS", "horizon_months": 1}
    artifact = {"binding": {"campaign_id": args[4]["campaign_id"],
        "factor_definition_hash": _definition(args[2], args[5])["definition_sha256"],
        "snapshot_sha256": "a" * 64, "signal_start": "2018-03", "signal_end": "2021-05", "phase": "DISCOVERY"},
        "contract": contract, "holdings": holdings, "return_contract": returns, "cost_model": costs,
        "monthly": [{"month": str(m), "gross": .02, "net": .017, "cost": .003, "turnover": .7,
                     "known_at": str((m + 1).end_time.date())} for m in periods]}
    bundle = prepare_discovery_evidence(*args, execution_artifact=artifact)
    assert "execution_cost" in bundle["required_diagnostics"]
    report = RealDiagnosticLab(bundle["frame"], bundle["contract"]).run("execution_cost")
    assert report["status"] == "COMPUTED"
    assert report["metrics"]["estimated_cost"]["mean"] == pytest.approx(.003)
    assert not bundle["readiness"]["execution"]["actual_fills_verified"]
    artifact["holdings"][0]["weight"] = .5
    with pytest.raises(ValueError, match="hash-bound"):
        prepare_discovery_evidence(*args, execution_artifact=artifact)


@pytest.mark.parametrize("mutation,reason", [
    (lambda args: args[4]["discovery"].update(signal_end="2021-06"), "boundaries"),
    (lambda args: args[4]["snapshot"].update(discovery_input_digest="invalid"), "snapshot identity"),
    (lambda args: setattr(args[3], "factor", "different_factor"), "Result definition"),
])
def test_reject_scope_and_identity_mismatch(mutation, reason):
    args = list(fixture())
    mutation(args)
    with pytest.raises(ValueError, match=reason):
        prepare_discovery_evidence(*args)


def test_failed_t0_is_not_an_economic_failure_or_second_factor_evaluation():
    args = list(fixture())
    args[3].checks = [SimpleNamespace(tier="T0.1", passed=False)]
    assert prepare_discovery_evidence(*args) == {"status": "NOT_COLLECTED", "reason": "SIGNAL_INTEGRITY_FAILED"}


def test_plan_rejects_future_label_outcomes_and_current_industry_without_contract():
    with pytest.raises(ValueError, match="non-label"):
        validate_diagnostic_plan(economic_plan(numerator="fwd_mid"))
    with pytest.raises(ValueError, match="source and PIT"):
        validate_diagnostic_plan({"industry_control": {"column": "current_industry"}})


def test_capture_does_not_mutate_panel_factor_spec_or_result():
    args = list(fixture())
    args[-1]["diagnostic_plan"] = economic_plan()
    old_frame, old_spec = args[1].copy(deep=True), deepcopy(args[-1])
    prepare_discovery_evidence(*args)
    pd.testing.assert_frame_equal(args[1], old_frame)
    assert args[-1] == old_spec
    assert args[3].metrics == {"gross": 100, "net": 99, "cost": 1}


def test_preregistered_ratio_control_connected_without_changing_candidate_score():
    args = list(fixture())
    args[1]["revenue_ttm"] = args[1].asset_id * 3. + 100.
    args[-1]["diagnostic_plan"] = {"ratio_controls": [{"name": "asset_turnover", "numerator": "revenue_ttm",
        "denominator": "total_assets", "available_at": "available_date"}]}
    bundle = prepare_discovery_evidence(*args)
    assert bundle["readiness"]["ratio_controls"]["asset_turnover"]["status"] == "CONNECTED"
    controls = RealDiagnosticLab(bundle["frame"], bundle["contract"]).run("controls")["metrics"]
    assert "asset_turnover" in controls["controls_applied"]
    expected = args[1].loc[args[1].ym.between(pd.Period("2018-03"), pd.Period("2021-05")), "f_new_generic_factor"]
    assert np.array_equal(bundle["frame"].signal.to_numpy(), expected.to_numpy())
    args[1] = args[1].drop(columns="revenue_ttm")
    missing = prepare_discovery_evidence(*args)
    assert missing["readiness"]["ratio_controls"]["asset_turnover"]["status"] == "NOT_CONNECTED"


def test_preregistered_macro_contrast_passes_to_separate_child_lab():
    args = list(fixture())
    args[-1]["diagnostic_plan"] = {"macro_axes": ["policy_rate"], "macro_contrasts": {"policy_rate": ["LOW", "HIGH"]}}
    def project(frame):
        out = frame.copy()
        out["macro_rate"] = "LOW"
        out["macro_known"] = pd.PeriodIndex(out.month, freq="M").end_time
        return out, {"macro_specs": {"policy_rate": {"column": "macro_rate", "known_at": "macro_known",
            "labels": ["LOW", "HIGH"], "contrast": None, "definition_sha256": "f" * 64, "pit_status": "PIT_ASSUMED"}}}
    bundle = prepare_discovery_evidence(*args, regime_projection=project)
    assert bundle["macro_labs"]["policy_rate"]["contract"]["regime"]["contrast"] == ["LOW", "HIGH"]
    assert "macro_rate" not in bundle["frame"]


def test_same_run_gate_capture_preserves_metrics_verdict_and_admission_evidence():
    from engine import gate
    from engine.panel import Panel
    from tests.test_invariants import RETURN_META
    months = pd.period_range("2018-03", periods=60, freq="M")
    frame = pd.DataFrame([{ "asset_id": int(asset), "ym": month,
        "trade_date": month.end_time.normalize(), "in_universe": True,
        "market_cap": float(asset + 100), "adj_close": 100., "total_return_close": 100.,
        "adv20": float(asset + 1), "market": "KOSPI" if asset % 2 else "KOSDAQ", "instrument_type": "common_stock",
        "f_candidate": float(asset + 100), "fwd_opt": float(asset) / 1000,
        "fwd_mid": float(asset) / 1000, "fwd_pess": float(asset) / 1000}
        for month in months for asset in range(1, 61)])
    panel = Panel(frame, pd.Series(dtype="datetime64[ns]"), meta=dict(RETURN_META))
    factor = Factor(name="candidate", category="other", hypothesis="Synthetic simulation capture",
        predicted_sign=1, compute=lambda data: data["market_cap"])
    kwargs = {"phase": "discovery", "data_cutoff": "2023-03-31", "oos_start": pd.Period("2023-04", freq="M")}
    baseline = gate.evaluate(factor, panel, frame, include_diagnostics=False, **kwargs)
    captured = gate.evaluate(factor, panel, frame, capture_execution_evidence=True, **kwargs)
    assert captured.verdict == baseline.verdict
    assert [(x.tier, x.name, x.passed) for x in captured.checks] == [(x.tier, x.name, x.passed) for x in baseline.checks]
    assert gate.discovery_evidence_digest(captured) == gate.discovery_evidence_digest(baseline)
    artifact = captured.diagnostic_execution_artifact
    assert artifact["timing_contract"] == "ORIGINAL_MONTH_END_GATE_SIMULATION_NOT_NEXT_OPEN"
    assert len(artifact["monthly"]) == 60
    assert max(x["month"] for x in artifact["monthly"]) == "2023-02"
    campaign = {"campaign_id": "synthetic-capture", "discovery": {"data_cutoff": "2023-03-31", "signal_end": "2023-02"},
        "oos": {"start": "2023-04"}, "snapshot": {"discovery_input_digest": "a" * 64}}
    bundle = prepare_discovery_evidence(panel, frame, factor, captured, campaign, {"strategy_sha256": "b" * 64})
    execution = RealDiagnosticLab(bundle["frame"], bundle["contract"]).run("execution_cost")
    assert execution["status"] == "COMPUTED"
    assert execution["metrics"]["net_spread"]["mean"] * 1200 == pytest.approx(captured.metrics["net"])
    assert bundle["readiness"]["execution"]["evidence_status"] == "SAME_RUN_GATE_SIMULATION_CAPTURE_NOT_NEXT_OPEN_FILLS"
    assert captured.diagnostic_execution_artifact is artifact


def test_execution_capture_requires_explicit_frozen_discovery_scope():
    from engine import gate
    with pytest.raises(ValueError, match="frozen Discovery"):
        gate.evaluate(None, None, None, capture_execution_evidence=True, phase="full")
