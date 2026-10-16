"""Synthetic fixtures only: no market cache, campaign, OOS, network or DB."""
from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from engine.research_real_diagnostics import (
    CATALOG, RealDiagnosticLab, _estimate, frame_hash, make_real_contract,
)


def fixture_frame(month_count=48, assets=60):
    rng = np.random.default_rng(92821)
    periods = pd.period_range("2018-01", periods=month_count, freq="M")
    month = np.repeat(periods, assets)
    signal = rng.normal(size=len(month))
    size = rng.normal(size=len(month))
    liquidity = rng.normal(size=len(month))
    return pd.DataFrame({
        "ym": month, "asset_id": np.tile(np.arange(assets), month_count),
        "signal": signal, "signal_known": pd.PeriodIndex(month).end_time.normalize(),
        "return": .01 * signal + .006 * size + rng.normal(scale=.02, size=len(month)),
        "return_known": (pd.PeriodIndex(month) + 1).end_time.normalize(),
        "size": size, "liquidity": liquidity,
        "market": np.tile(np.where(np.arange(assets) % 2 == 0, "KOSPI", "KOSDAQ"), month_count),
        "controls_known": pd.PeriodIndex(month).end_time.normalize(),
    })


def fixture_contract(frame, **overrides):
    args = dict(
        capability_id="fixture-capability", dataset_id="fixture-only",
        snapshot_sha256="a" * 64, factor_definition_hash="b" * 64,
        signal_start=str(min(frame.ym)), signal_end=str(max(frame.ym)),
        maturity_cutoff=str((max(frame.ym) + 13).end_time.date()),
        sealed_start=str(max(frame.ym) + 14),
        columns={"month": "ym", "asset_id": "asset_id", "signal": "signal",
                 "signal_known_at": "signal_known", "forward_return": "return", "return_known_at": "return_known"},
        controls=[{"name": "size", "column": "size", "kind": "numeric", "known_at": "controls_known"},
                  {"name": "liquidity", "column": "liquidity", "kind": "numeric", "known_at": "controls_known"},
                  {"name": "market", "column": "market", "kind": "categorical", "known_at": "controls_known"}],
    )
    args.update(overrides)
    return make_real_contract(frame, **args)


def economic_fixture(frame):
    frame = frame.copy()
    rng = np.random.default_rng(32)
    frame["economic"] = .4 * frame.signal + rng.normal(size=len(frame))
    frame["economic_known"] = (pd.PeriodIndex(frame.ym) + 12).end_time.normalize()
    spec = {"column": "economic", "known_at": "economic_known", "horizon_months": 12,
            "dataset_id": "fixture-public-roa-change"}
    return frame, spec


def regime_fixture(frame):
    frame = frame.copy()
    # Alternating 6-month blocks; each state has four observed episodes.
    frame["state"] = ["HIGH" if ((x.ordinal - min(frame.ym).ordinal) // 6) % 2 else "LOW" for x in frame.ym]
    frame["state_known"] = pd.PeriodIndex(frame.ym).end_time.normalize()
    spec = {"column": "state", "known_at": "state_known", "labels": ["LOW", "HIGH"],
            "contrast": ["LOW", "HIGH"], "definition_sha256": "c" * 64, "pit_status": "PIT_ASSUMED"}
    return frame, spec


def execution_fixture(frame):
    frame = frame.copy()
    frame["gross"] = .02
    frame["cost"] = .003
    frame["net"] = .017
    frame["turnover"] = .7
    spec = {"gross": "gross", "net": "net", "cost": "cost", "turnover": "turnover",
            "known_at": "return_known", "holdings_sha256": "d" * 64,
            "return_contract_sha256": "e" * 64, "cost_model_sha256": "f" * 64,
            "timing_contract": "fixture-month-end-only", "horizon_months": 1}
    return frame, spec


def test_core_reports_use_real_contract_not_synthetic_truth():
    frame = fixture_frame()
    lab = RealDiagnosticLab(frame, fixture_contract(frame))
    public = lab.public_case()
    assert public["data_kind"] == "REAL_FROZEN_DISCOVERY"
    assert "oracle" not in public and "shared_diagnostic_rubric" not in public
    assert not public["factor_approval_allowed"]
    audit = lab.run("input_audit")["metrics"]
    assert audit["late_signal_fraction"] == audit["late_control_fraction"] == 0
    assert audit["missing_signal_fraction"] == audit["missing_return_fraction"] == 0
    assert audit["historical_first_release_verified"] is False
    association = lab.run("association")
    assert association["status"] == "COMPUTED"
    assert association["metrics"]["raw_ic"]["mean"] > .1
    assert association["metrics"]["raw_ic"]["n_months"] == 48
    assert association["metrics"]["raw_ic"]["ci95"] is not None
    controls = lab.run("controls")["metrics"]
    assert controls["controls_applied"] == ["size", "liquidity", "market"]
    assert controls["industry_control_available"] is False
    assert "sector_adjusted_ic" not in controls
    assert controls["fully_adjusted_ic"]["mean"] is not None
    for diagnostic in CATALOG:
        json.dumps(lab.run(diagnostic), allow_nan=False)


def test_unavailable_cost_economic_and_regime_are_not_zero_or_failed_hypotheses():
    frame = fixture_frame()
    lab = RealDiagnosticLab(frame, fixture_contract(frame))
    for diagnostic in ("execution_cost", "economic_link", "regime_interaction"):
        result = lab.run(diagnostic)
        assert result["status"] == "NOT_COMPUTED"
        assert result["missing_datasets"]
        assert result["metrics"] == {}


def test_frozen_data_contract_and_cache_are_immutable_to_caller():
    frame = fixture_frame()
    contract = fixture_contract(frame)
    lab = RealDiagnosticLab(frame, contract)
    first = lab.run("association")
    frame["signal"] = 0
    contract["signal_end"] = "1900-01"
    first["metrics"]["raw_ic"]["mean"] = -999
    assert lab.run("association")["metrics"]["raw_ic"]["mean"] > 0
    with pytest.raises(ValueError, match="hash mismatch"):
        RealDiagnosticLab(frame, fixture_contract(fixture_frame()))


def test_hash_excludes_incidental_index_but_binds_values_order_dtype():
    frame = fixture_frame()
    assert frame_hash(frame) == frame_hash(frame.set_axis(range(1000, 1000 + len(frame))))
    assert frame_hash(frame) != frame_hash(frame.iloc[::-1])
    changed = frame.copy()
    changed["asset_id"] = changed.asset_id.astype(float)
    assert frame_hash(frame) != frame_hash(changed)


@pytest.mark.parametrize("change", ["extra", "sealed", "before", "phase", "write", "hash", "scope", "role"])
def test_boundary_fail_closed(change):
    frame = fixture_frame()
    contract = fixture_contract(frame)
    if change == "extra":
        frame["sealed_label"] = 123
    elif change == "sealed":
        contract["maturity_cutoff"] = f'{contract["sealed_start"]}-01'
    elif change == "before":
        contract["signal_start"] = "2018-02"
    elif change == "phase":
        contract["phase"] = "OOS"
    elif change == "write":
        contract["gold_write_allowed"] = True
    elif change == "hash":
        contract["snapshot_sha256"] = "unknown"
    elif change == "scope":
        contract["scope"] = "ALL_DATA"
    else:
        contract["columns"]["signal"] = "return"
    with pytest.raises(ValueError):
        RealDiagnosticLab(frame, contract)


def test_builder_cannot_bless_unassigned_extra_columns():
    frame = fixture_frame()
    frame["some_secret_field"] = 12
    with pytest.raises(ValueError, match="Unassigned extra"):
        fixture_contract(frame)


def test_intraday_cutoff_not_silently_broadened_to_end_of_day():
    with pytest.raises(ValueError, match="date-only"):
        fixture_contract(fixture_frame(), maturity_cutoff="2022-12-31T12:00:00")


def test_outcomes_cannot_be_relabelled_as_control_features():
    frame = fixture_frame().drop(columns="size")
    controls = [{"name": "size", "column": "return", "kind": "numeric", "known_at": "controls_known"},
                {"name": "liquidity", "column": "liquidity", "kind": "numeric", "known_at": "controls_known"},
                {"name": "market", "column": "market", "kind": "categorical", "known_at": "controls_known"}]
    with pytest.raises(ValueError, match="roles must not overlap"):
        fixture_contract(frame, controls=controls)


def test_late_signal_control_and_missing_timestamp_audited_and_masked():
    frame = fixture_frame()
    frame.loc[0, "signal_known"] = pd.Timestamp("2030-01-01")
    frame.loc[1, "controls_known"] = pd.Timestamp("2030-01-01")
    frame.loc[2, "signal_known"] = pd.NaT
    lab = RealDiagnosticLab(frame, fixture_contract(frame))
    metrics = lab.run("input_audit")["metrics"]
    assert metrics["late_signal_fraction"] == 1 / len(frame)
    assert metrics["late_control_fraction"] == 1 / len(frame)
    assert metrics["signal_availability"]["missing_known_at"] == 1
    assert lab.run("association")["metrics"]["monthly"][0]["n_pairs"] == 58
    assert lab.run("controls")["metrics"]["monthly"][0]["n_common"] == 57


def test_policy_bound_features_do_not_invent_timestamps_or_verified_status():
    frame = fixture_frame().drop(columns=["signal_known", "controls_known"])
    mapping = {"month": "ym", "asset_id": "asset_id", "signal": "signal", "signal_known_at": None,
               "forward_return": "return", "return_known_at": "return_known"}
    controls = [{"name": name, "column": name, "kind": kind, "known_at": None} for name, kind in
                (("size", "numeric"), ("liquidity", "numeric"), ("market", "categorical"))]
    with pytest.raises(ValueError, match="availability policy"):
        fixture_contract(frame, columns=mapping, controls=controls)
    policy = {"policy_id": "frozen-pit-formation", "status": "POLICY_BOUND", "evidence_sha256": "a" * 64}
    lab = RealDiagnosticLab(frame, fixture_contract(frame, columns=mapping, controls=controls, feature_availability=policy))
    audit = lab.run("input_audit")["metrics"]
    assert audit["late_signal_fraction"] is None
    assert audit["late_control_fraction"] is None
    assert audit["signal_availability"]["status"] == "POLICY_BOUND"
    assert audit["historical_first_release_verified"] is False
    assert lab.run("controls")["status"] == "COMPUTED"


def test_duplicates_visible_in_audit_but_block_numeric_diagnostics():
    frame = fixture_frame()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    lab = RealDiagnosticLab(frame, fixture_contract(frame))
    assert lab.run("input_audit")["metrics"]["duplicate_key_count"] == 1
    for diagnostic in set(CATALOG) - {"input_audit"}:
        assert lab.run(diagnostic)["reason"] == "DUPLICATE_INPUT_KEYS"


def test_return_maturity_bounds_even_when_supplied_known_timestamp_is_early():
    frame = fixture_frame()
    # Supplier's early date cannot make a December -> January label mature in December.
    frame.loc[frame.ym.eq(max(frame.ym)), "return_known"] = pd.Timestamp("2021-12-31")
    lab = RealDiagnosticLab(frame, fixture_contract(frame, maturity_cutoff="2021-12-31", sealed_start="2022-01"))
    audit = lab.run("input_audit")["metrics"]
    assert audit["return_maturity"]["n_immature"] == 60
    assert lab.run("association")["metrics"]["raw_ic"]["n_months"] == 47


def test_integer_or_future_label_availability_is_not_valid():
    frame = fixture_frame()
    frame["return_known"] = frame.return_known.astype(object)
    frame.loc[0, "return_known"] = 0
    frame.loc[1, "return_known"] = "2040-01-01"
    lab = RealDiagnosticLab(frame, fixture_contract(frame))
    metrics = lab.run("input_audit")["metrics"]["return_maturity"]
    assert metrics["n_invalid_known_at"] == metrics["n_late_known_at"] == 1
    assert metrics["n_usable"] == len(frame) - 2


def test_matched_controls_retain_missingness_and_no_fake_sector():
    frame = fixture_frame()
    frame.loc[frame.asset_id.eq(0), "size"] = np.nan
    lab = RealDiagnosticLab(frame, fixture_contract(frame))
    metrics = lab.run("controls")["metrics"]
    assert all(row["n_common"] == 59 for row in metrics["monthly"])
    assert "sector_attenuation" not in metrics


def test_economic_horizon_maturity_and_overlapping_hac():
    frame, economic = economic_fixture(fixture_frame())
    lab = RealDiagnosticLab(frame, fixture_contract(frame, economic=economic,
        maturity_cutoff="2021-12-31", sealed_start="2022-01"))
    result = lab.run("economic_link")
    assert result["status"] == "COMPUTED"
    metrics = result["metrics"]
    assert metrics["outcome_maturity"]["n_immature"] == 12 * 60
    assert metrics["signal_to_economic_change_ic"]["n_months"] == 36
    assert metrics["signal_to_economic_change_ic"]["hac_lags"] == 11
    assert metrics["signal_to_economic_change_ic"]["minimum_months"] == 24
    assert metrics["same_horizon"] is False
    assert metrics["temporal_mediation_identified"] is False
    assert any("horizons differ" in note for note in result["limitations"])


def test_economic_level_is_never_mislabeled_as_change():
    frame, economic = economic_fixture(fixture_frame())
    economic["measurement_kind"] = "LEVEL"
    economic["dataset_id"] = "future-public-roa-level-fixture"
    metrics = RealDiagnosticLab(frame, fixture_contract(frame, economic=economic)).run("economic_link")["metrics"]
    assert metrics["economic_measurement_kind"] == "LEVEL"
    assert metrics["economic_dataset_id"] == "future-public-roa-level-fixture"
    assert metrics["economic_variable_column"] == "economic"
    assert metrics["signal_to_economic_level_ic"]["mean"] is not None
    assert metrics["economic_level_to_return_ic"]["mean"] is not None
    assert "signal_to_economic_change_ic" not in metrics
    assert "economic_change_to_return_ic" not in metrics


def test_unsupported_economic_measurement_kind_rejected():
    frame, economic = economic_fixture(fixture_frame())
    economic["measurement_kind"] = "CAUSAL_MEDIATOR"
    with pytest.raises(ValueError, match="economic outcome specification"):
        fixture_contract(frame, economic=economic)


def test_economic_insufficient_is_not_missing_dataset_or_null_hypothesis_failure():
    frame, economic = economic_fixture(fixture_frame(month_count=12))
    result = RealDiagnosticLab(frame, fixture_contract(frame, economic=economic,
        maturity_cutoff="2018-12-31", sealed_start="2019-01")).run("economic_link")
    assert result["status"] == "NOT_COMPUTED"
    assert result["reason"] == "NO_MATURE_COMMON_ECONOMIC_SAMPLE"
    assert "missing_datasets" not in result


def test_regime_interaction_preserves_predeclared_direction_and_pit_assumption():
    frame, regime = regime_fixture(fixture_frame())
    frame["return"] += .04 * frame.signal * frame.state.eq("HIGH")
    result = RealDiagnosticLab(frame, fixture_contract(frame, regime=regime)).run("regime_interaction")
    metrics = result["metrics"]
    assert result["status"] == "COMPUTED"
    assert metrics["interaction"]["mean"] > .03
    assert metrics["interaction"]["ci95"] is not None
    assert metrics["pit_status"] == "PIT_ASSUMED"
    assert metrics["regimes"]["HIGH"]["n_episodes"] == 4
    assert set(metrics["regimes"]) == {"LOW", "HIGH"}


def test_regime_no_episode_creation_from_missing_outcomes_or_unknown_months():
    frame, regime = regime_fixture(fixture_frame())
    ordinal = pd.PeriodIndex(frame.ym).asi8 - min(frame.ym).ordinal
    frame["state"] = np.where(ordinal < 24, "LOW", "HIGH")
    frame.loc[ordinal % 3 == 0, "state"] = "UNKNOWN"
    result = RealDiagnosticLab(frame, fixture_contract(frame, regime=regime)).run("regime_interaction")
    assert result["metrics"]["regimes"]["HIGH"]["n_episodes"] == 1
    assert result["metrics"]["regimes"]["LOW"]["n_episodes"] == 1
    assert result["metrics"]["interaction"]["ci95"] is None


def test_monthly_regime_must_be_constant_across_assets():
    frame, regime = regime_fixture(fixture_frame())
    frame.loc[0, "state"] = "HIGH"
    result = RealDiagnosticLab(frame, fixture_contract(frame, regime=regime)).run("regime_interaction")
    assert result["status"] == "NOT_COMPUTED"
    assert result["reason"] == "INCONSISTENT_MARKET_STATE_WITHIN_MONTH"


def test_execution_reads_only_explicit_monthly_same_window_artifact():
    frame, execution = execution_fixture(fixture_frame())
    metrics = RealDiagnosticLab(frame, fixture_contract(frame, execution=execution)).run("execution_cost")["metrics"]
    assert metrics["net_spread"]["mean"] == pytest.approx(.017)
    assert metrics["holdings_recomputed_here"] is False
    assert metrics["timing_contract"] == "fixture-month-end-only"


def test_execution_partial_month_uses_matched_complete_months_for_all_metrics():
    frame, execution = execution_fixture(fixture_frame())
    frame.loc[frame.ym.eq(min(frame.ym)), "net"] = np.nan
    metrics = RealDiagnosticLab(frame, fixture_contract(frame, execution=execution)).run("execution_cost")["metrics"]
    assert all(metrics[key]["n_months"] == 47 for key in ("gross_spread", "net_spread", "estimated_cost", "turnover"))
    assert metrics["monthly"][0]["unavailable_fields"] == ["net_spread"]


def test_economic_both_links_use_same_estimable_months_not_just_rows():
    frame, economic = economic_fixture(fixture_frame())
    frame.loc[frame.ym.eq(min(frame.ym)), "signal"] = 1.0
    metrics = RealDiagnosticLab(frame, fixture_contract(frame, economic=economic)).run("economic_link")["metrics"]
    assert metrics["signal_to_economic_change_ic"]["n_months"] == 47
    assert metrics["economic_change_to_return_ic"]["n_months"] == 47
    assert metrics["joint_estimable_months"] == 47


@pytest.mark.parametrize("mutation,reason", [("wrong_net", "PORTFOLIO_COST_IDENTITY_FAILED"),
    ("negative_cost", "PORTFOLIO_COST_IDENTITY_FAILED"), ("inconsistent", "INCONSISTENT_MONTHLY_PORTFOLIO_MEASUREMENT")])
def test_execution_bad_arithmetic_or_asset_specific_fake_aggregate_rejected(mutation, reason):
    frame, execution = execution_fixture(fixture_frame())
    if mutation == "wrong_net":
        frame["net"] = .2
    elif mutation == "negative_cost":
        frame["cost"], frame["net"] = -.003, .023
    else:
        frame.loc[0, "gross"] = .2
    result = RealDiagnosticLab(frame, fixture_contract(frame, execution=execution)).run("execution_cost")
    assert result["reason"] == reason
    assert result["status"] == "NOT_COMPUTED"


def test_calendar_hac_does_not_compress_gaps():
    values = np.tile([1.0, 1.0, -1.0, -1.0], 8)
    consecutive = pd.period_range("2010-01", periods=len(values), freq="M")
    gapped = pd.PeriodIndex([consecutive[0] + 6 * i for i in range(len(values))], freq="M")
    first, second = _estimate(consecutive, values), _estimate(gapped, values)
    assert first["mean"] == second["mean"]
    assert first["standard_error"] != second["standard_error"]
    assert second["standard_error"] == pytest.approx(np.std(values, ddof=1) / np.sqrt(len(values)))


def test_ties_not_arbitrarily_split_into_top_bottom():
    frame = fixture_frame()
    frame["signal"] = 1.0
    result = RealDiagnosticLab(frame, fixture_contract(frame)).run("association")
    assert result["status"] == "NOT_COMPUTED"
    assert result["metrics"]["gross_spread"]["mean"] is None


def test_unknown_diagnostic_rejected_without_execution():
    frame = fixture_frame()
    lab = RealDiagnosticLab(frame, fixture_contract(frame))
    with pytest.raises(ValueError, match="Unregistered"):
        lab.run("custom_python")
