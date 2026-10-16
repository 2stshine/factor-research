"""Synthetic graph -> existing execution-engine contract tests, not market evidence."""
from copy import deepcopy
import json

import pytest

from engine.phenomenon_research import digest
from engine import phenomenon_runtime as runtime
from tests.test_phenomenon_research import NOW, LATER, SCOPE, add, reviewed, strategy_payload, world


def bundle_fixture():
    field = "reference_value"
    measurements = [{"signal_month": month, "asset_id": asset, "eligible": True, "market_cap": 100. + asset, "available_at": cutoff, field: float(asset)}
                    for month, cutoff in [("2020-01", "2020-01-31T23:59:59+09:00"), ("2020-02", "2020-02-29T23:59:59+09:00")] for asset in range(1, 11)]
    opens = {"2020-02": "2020-02-03T09:00:00+09:00", "2020-03": "2020-03-02T09:00:00+09:00", "2020-04": "2020-04-01T09:00:00+09:00"}
    windows = [("2020-01", "2020-02", "2020-03"), ("2020-02", "2020-03", "2020-04")]
    bundle = {"origin": "SYNTHETIC", "reference": {"reference_id": "synthetic-size", "definition_sha256": digest({"formula": "fixture_only"}), "role": "MEASUREMENT_ONLY_NO_ALPHA_APPROVAL", "provenance": "synthetic fixture, no DB", "origin": "SYNTHETIC"},
              "measurements": measurements, "sessions": [{"session_month": month, "open_at": value} for month, value in opens.items()],
              "asset_windows": [{"signal_month": month, "asset_id": asset, "entry_at": opens[entry], "exit_at": opens[exit], "entry_open": 100., "gross_total_return_multiplier": 1 + asset / 1000, "return_available_at": opens[exit]} for month, entry, exit in windows for asset in range(1, 11)],
              "market_windows": [{"signal_month": month, "entry_at": opens[entry], "exit_at": opens[exit], "gross_total_return_multiplier": 1.003, "return_available_at": opens[exit]} for month, entry, exit in windows]}
    bundle["evidence"] = {"schema_version": "monthly-execution-evidence-v1", "data_sha256": runtime.bundle_data_sha256(bundle), "as_of": "2020-04-02T09:00:00+09:00", **{flag: True for flag in runtime.monthly.EVIDENCE_FLAGS}}
    return bundle


def runtime_contract(bundle):
    return {"schema": runtime.SCHEMA, "score_rule": {"kind": "DIRECT_REFERENCE", "field": "reference_value", "orientation": 1, "reference_id": bundle["reference"]["reference_id"], "definition_sha256": bundle["reference"]["definition_sha256"]},
            "variants": list(runtime.VARIANTS), "benchmarks": runtime.BENCHMARKS.copy(), "costs": {"buy_rate": .0015, "sell_rate": .0015, "sell_tax_by_year": {"2020": .0023}}, "initial_nav": 1.,
            "scope": {"origin": "SYNTHETIC", "universe": SCOPE["universe"], "signal_months": ["2020-01", "2020-02"]}, "execution": runtime.EXECUTION.copy(),
            "decision_clock": "CALENDAR_MONTH_END_23_59_59_ASIA_SEOUL", "historical_reuse_acknowledged": True,
            "source_artifacts": {name: digest(bundle[name]) for name in runtime.ARRAYS}, "input_bundle_sha256": digest(bundle)}


def setup_run(tmp_path, *, mutate_bundle=None, mutate_contract=None, mutate_strategy=None):
    w = world(tmp_path)
    _, claim = reviewed(w)
    bundle = bundle_fixture()
    if mutate_bundle:
        mutate_bundle(bundle)
        bundle["evidence"]["data_sha256"] = runtime.bundle_data_sha256(bundle)
    contract = runtime_contract(bundle)
    if mutate_contract:
        mutate_contract(contract)
    strategy = strategy_payload()
    strategy.update({"runtime_contract": contract, "execution": runtime.EXECUTION.copy(), "costs": {"commission_bps": 5., "slippage_bps": 10., "tax_model": "DATED_SELL_TAX_SCHEDULE", "sell_tax_by_year": {"2020": .0023}}})
    if mutate_strategy:
        mutate_strategy(strategy)
    snapshot = w["g"].snapshot([claim["id"]], as_of=NOW)
    node = w["g"].create_strategy(strategy, snapshot, actor="strategist", known_at=NOW)
    return w, node, bundle


def register(w, node, bundle, tmp_path):
    return runtime.register_execution(w["g"], node["id"], bundle, tmp_path / "runs", registered_at=NOW)


def test_graph_to_execution_all_variants_and_receipts(tmp_path):
    w, node, bundle = setup_run(tmp_path)
    registration = register(w, node, bundle, tmp_path)
    result = runtime.execute_registered(w["g"], registration["run_dir"])
    assert result["empirical_use"] == "SOFTWARE_TEST_ONLY"
    assert result["variant_order"] == list(runtime.VARIANTS)
    assert result["selected_variant"] is None
    assert not result["publication_authorized"] and not result["independent_confirmation"]
    assert len(result["output_file_sha256"]) == 5
    assert runtime.verify_result(w["g"], registration["run_dir"]) == result
    from pathlib import Path
    data = json.loads((Path(registration["run_dir"]) / "q20_equal.json").read_text())
    assert len(data["monthly"]) == 2
    assert data["monthly"][0]["n_selected"] == 2
    assert data["monthly"][0]["cost_fraction"] > 0
    assert data["monthly"][0]["net_excess_market"] != data["monthly"][0]["net_excess_universe"]
    with pytest.raises(ValueError, match="already attempted"):
        runtime.execute_registered(w["g"], registration["run_dir"])


@pytest.mark.parametrize("change,match", [
    (lambda c: c.update(variants=["q10_equal"]), "four fixed"),
    (lambda c: c.update(benchmarks=["MARKET_TR"]), "benchmark"),
    (lambda c: c["costs"].update(buy_rate=.0001), "rates differ"),
    (lambda c: c["costs"]["sell_tax_by_year"].update({"2020": 0}), "tax schedules"),
    (lambda c: c.update(historical_reuse_acknowledged=False), "Historical"),
    (lambda c: c["scope"].update(signal_months=["2020-01"]), "months differ"),
    (lambda c: c["score_rule"].update(orientation=0), "orientation"),
    (lambda c: c["score_rule"].update(kind="eval"), "score rule"),
    (lambda c: c["source_artifacts"].update(sessions="0" * 64), "digest"),
    (lambda c: c["execution"].update(fill="MONTH_END_CLOSE"), "timing"),
])
def test_contract_injection_rejected(tmp_path, change, match):
    w, node, bundle = setup_run(tmp_path, mutate_contract=change)
    with pytest.raises(ValueError, match=match):
        register(w, node, bundle, tmp_path)


def test_bundle_tampering_is_not_rehashed_into_execution(tmp_path):
    w, node, bundle = setup_run(tmp_path)
    bundle["asset_windows"][0]["gross_total_return_multiplier"] = 1000
    with pytest.raises(ValueError, match="bundle differs"):
        register(w, node, bundle, tmp_path)


def test_frozen_file_hash_tamper_rejected(tmp_path):
    from pathlib import Path
    w, node, bundle = setup_run(tmp_path)
    reg = register(w, node, bundle, tmp_path)
    file = Path(reg["run_dir"]) / "input_bundle.json"
    file.chmod(0o644)
    file.write_text(file.read_text().replace("1.001", "1.999"))
    with pytest.raises(ValueError, match="artifact hash"):
        runtime.execute_registered(w["g"], reg["run_dir"])


def test_future_feature_timestamp_rejected_and_failure_saved(tmp_path):
    from pathlib import Path
    w, node, bundle = setup_run(tmp_path, mutate_bundle=lambda b: b["measurements"][0].update(available_at="2020-02-01T00:00:00+09:00"))
    reg = register(w, node, bundle, tmp_path)
    with pytest.raises(ValueError, match="availability exceeds"):
        runtime.execute_registered(w["g"], reg["run_dir"])
    assert (Path(reg["run_dir"]) / "failure.json").exists()
    assert not (Path(reg["run_dir"]) / "result_manifest.json").exists()


def test_future_outcome_timestamp_rejected(tmp_path):
    w, node, bundle = setup_run(tmp_path, mutate_bundle=lambda b: b["asset_windows"][0].update(return_available_at="2027-02-01T00:00:00+09:00"))
    reg = register(w, node, bundle, tmp_path)
    with pytest.raises(ValueError, match="Return availability"):
        runtime.execute_registered(w["g"], reg["run_dir"])


def test_future_research_evidence_rejected(tmp_path):
    w, node, bundle = setup_run(tmp_path, mutate_bundle=lambda b: b["evidence"].update(as_of="2027-02-01T00:00:00+09:00"))
    with pytest.raises(ValueError, match="future research"):
        register(w, node, bundle, tmp_path)


def test_stale_graph_before_run_rejected(tmp_path):
    w, node, bundle = setup_run(tmp_path)
    reg = register(w, node, bundle, tmp_path)
    add(w["g"], "question", {"title": "New question", "question": "Changes graph head"})
    with pytest.raises(ValueError, match="Stale knowledge"):
        runtime.execute_registered(w["g"], reg["run_dir"])


def test_graph_change_during_run_has_no_published_manifest(tmp_path, monkeypatch):
    from pathlib import Path
    w, node, bundle = setup_run(tmp_path)
    reg = register(w, node, bundle, tmp_path)
    original = runtime.monthly.run_monthly_execution
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        w["g"].invalidate(w["source"]["id"], actor="curator", known_at=LATER, reason="Upstream source invalidated during computation")
        return result
    monkeypatch.setattr(runtime.monthly, "run_monthly_execution", changed)
    with pytest.raises(ValueError, match="Stale knowledge"):
        runtime.execute_registered(w["g"], reg["run_dir"])
    assert not (Path(reg["run_dir"]) / "result_manifest.json").exists()


def test_upstream_binding_rechecked_even_without_graph_change(tmp_path, monkeypatch):
    from engine import phenomenon_inputs
    w, node, bundle = setup_run(tmp_path)
    reg = register(w, node, bundle, tmp_path)
    def revoked(graph):
        raise ValueError("Upstream source permission revoked")
    monkeypatch.setattr(phenomenon_inputs, "assert_source_bindings", revoked)
    with pytest.raises(ValueError, match="revoked"):
        runtime.execute_registered(w["g"], reg["run_dir"])


def test_result_missing_variant_cannot_be_selected(tmp_path, monkeypatch):
    w, node, bundle = setup_run(tmp_path)
    reg = register(w, node, bundle, tmp_path)
    original = runtime.monthly.run_monthly_execution
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        del result["variants"]["q20_equal"]
        return result
    monkeypatch.setattr(runtime.monthly, "run_monthly_execution", changed)
    with pytest.raises(ValueError, match="omitted or injected"):
        runtime.execute_registered(w["g"], reg["run_dir"])


def test_synthetic_reference_cannot_be_claimed_observed(tmp_path):
    def change(b):
        b["origin"] = b["reference"]["origin"] = "OBSERVED"
    w, node, bundle = setup_run(tmp_path, mutate_bundle=change, mutate_contract=lambda c: c["scope"].update(origin="OBSERVED"))
    with pytest.raises(ValueError, match="source origins"):
        register(w, node, bundle, tmp_path)


def test_orientation_is_applied_once_and_input_unchanged(tmp_path):
    from pathlib import Path
    w, node, bundle = setup_run(tmp_path, mutate_contract=lambda c: c["score_rule"].update(orientation=-1))
    original = deepcopy(bundle)
    reg = register(w, node, bundle, tmp_path)
    runtime.execute_registered(w["g"], reg["run_dir"])
    scores = json.loads((Path(reg["run_dir"]) / "scores.json").read_text())["rows"]
    assert scores[0]["signed_score"] == -1
    assert bundle == original


@pytest.mark.parametrize("change", [
    {"origin": "OBSERVED"}, {"empirical_use": "HISTORICAL_REUSE_DESCRIPTIVE_RESEARCH"},
    {"publication_authorized": True}, {"independent_confirmation": True},
    {"orders_submitted": True}, {"actual_fill_verified": True}, {"selected_variant": "q10_equal"},
    {"benchmarks": ["MARKET_TR"]}, {"warnings": []}, {"extra_approval": True},
    {"variant_order": ["q10_equal"]}, {"costs": {"buy_rate": 0}},
])
def test_rehashed_semantic_manifest_rewrite_is_rejected(tmp_path, change):
    from pathlib import Path
    w, node, bundle = setup_run(tmp_path)
    reg = register(w, node, bundle, tmp_path)
    result = runtime.execute_registered(w["g"], reg["run_dir"])
    result.update(change)
    result["manifest_sha256"] = digest({k: v for k, v in result.items() if k != "manifest_sha256"})
    path = Path(reg["run_dir"]) / "result_manifest.json"
    path.chmod(0o644)
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="semantics"):
        runtime.verify_result(w["g"], reg["run_dir"])


def test_rehashed_manifest_cannot_omit_output_artifact(tmp_path):
    from pathlib import Path
    w, node, bundle = setup_run(tmp_path)
    reg = register(w, node, bundle, tmp_path)
    result = runtime.execute_registered(w["g"], reg["run_dir"])
    result["output_file_sha256"].pop("q20_equal.json")
    result["manifest_sha256"] = digest({k: v for k, v in result.items() if k != "manifest_sha256"})
    path = Path(reg["run_dir"]) / "result_manifest.json"
    path.chmod(0o644)
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="artifact set"):
        runtime.verify_result(w["g"], reg["run_dir"])
