"""Train-only ridge/selection/PCA bridge checks using generated software data."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import phenomenon_ridge as ridge
from engine import phenomenon_runtime as runtime
from engine.phenomenon_research import digest
from tests.test_phenomenon_research import NOW, SCOPE, reviewed, strategy_payload, world


def ridge_fixture():
    fields = [{"field": name, "reference_id": "fixture-" + name, "definition_sha256": digest({"field": name})} for name in ["size", "size_duplicate", "liquidity"]]
    rule = {"kind": "TRAIN_ONLY_RIDGE", "features": fields, "alpha": 1.0, "pca_components": 1,
            "selection": {"method": "TRAIN_CORRELATION", "max_abs_correlation": .98, "max_missing_fraction": .4, "min_variance": 0., "max_features": 2},
            "train_window_months": 24, "min_train_months": 2, "min_train_rows": 10, "purge_gap_months": 1, "max_feature_age_days": 400,
            "label_contract": "VERIFIED_NEXT_OPEN_TO_FOLLOWING_OPEN_GROSS_RETURN_MINUS_ONE"}
    reference = {"features": fields, "role": "MEASUREMENT_ONLY_NO_ALPHA_APPROVAL", "origin": "SYNTHETIC", "provenance": "Synthetic contract fixture; not observed market factors"}
    # Arbitrary synthetic opens are explicitly declared, not represented as KRX.
    opens = {str(month): (month.start_time.tz_localize("Asia/Seoul") + pd.Timedelta(days=2, hours=9)).isoformat() for month in pd.period_range("2019-09", "2020-04", freq="M")}
    sessions = [{"session_month": month, "open_at": stamp} for month, stamp in opens.items()]
    features, labels, measurements = [], [], []
    for i, month in enumerate(pd.period_range("2019-08", "2020-02", freq="M")):
        cutoff = month.end_time.floor("s").tz_localize("Asia/Seoul").isoformat()
        for asset in range(1, 11):
            values = {"size": float(asset + i / 10), "size_duplicate": float((asset + i / 10) * 2), "liquidity": float((asset % 3) + i / 20)}
            row = {"signal_month": str(month), "asset_id": asset, "eligible": True, "available_at": cutoff, **values, **{name + "__known_at": cutoff for name in values}}
            features.append(row)
            labels.append({"signal_month": str(month), "asset_id": asset, "entry_at": opens[str(month + 1)], "exit_at": opens[str(month + 2)], "return_available_at": opens[str(month + 2)], "gross_total_return_multiplier": 1. + asset * .002 - (asset % 3) * .001})
            if month >= pd.Period("2020-01", freq="M"):
                measurements.append({**row, "market_cap": 100. + asset})
    return {"measurements": measurements, "training_features": features, "training_labels": labels, "sessions": sessions, "rule": rule, "reference": reference, "origin": "SYNTHETIC", "research_as_of": "2020-04-05T00:00:00+09:00"}


def run(fixture=None):
    f = fixture or ridge_fixture()
    return ridge.generate_scores(**f)


def test_fixed_train_only_selection_pca_ridge_generates_every_month():
    result = run()
    assert len(result["scores"]) == 20
    assert len(result["folds"]) == 2
    for fold in result["folds"]:
        assert fold["selected_features"] == ["size", "liquidity"]
        assert fold["dropped_features"]["size_duplicate"] == "TRAIN_CORRELATED_WITH_EARLIER_DECLARED_FEATURE"
        assert pd.Timestamp(fold["max_label_available_at"]) <= pd.Timestamp(fold["fit_cutoff"])
        assert not fold["test_labels_used"] and not fold["selection_used_outcomes"]
        assert fold["models"]["configured"]["pca_components"] == 1
        assert fold["models"]["ridge_no_pca"]["pca_components"] is None
    assert not result["hyperparameter_search"] and not result["winner_selected"]
    assert result["learned_claims"] == [] and result["empirical_use"] == "SOFTWARE_TEST_ONLY"


def test_future_feature_and_label_values_cannot_change_earlier_prediction():
    f = ridge_fixture()
    baseline = run(f)
    modified = deepcopy(f)
    for row in modified["training_features"]:
        if row["signal_month"] >= "2020-01":
            row["size"] = 99999999.
            row["liquidity"] = -8888888.
    for row in modified["training_labels"]:
        if row["signal_month"] >= "2019-12":
            row["gross_total_return_multiplier"] = 99.
    result = run(modified)
    assert result["scores"][:10] == baseline["scores"][:10]
    assert result["folds"][0] == baseline["folds"][0]


def test_unavailable_past_labels_are_excluded_not_future_filled():
    f = ridge_fixture()
    for row in f["training_labels"]:
        if row["signal_month"] == "2019-11":
            row["return_available_at"] = "2020-02-15T00:00:00+09:00"
    result = run(f)
    assert "2019-11" not in result["folds"][0]["train_months"]
    assert "2019-11" in result["folds"][1]["train_months"]
    assert result["folds"][0]["unavailable_or_missing_label_rows_excluded"] >= 10


def test_training_standardization_never_uses_test_cross_section():
    f = ridge_fixture()
    baseline = run(f)
    for row in f["measurements"]:
        row["size"] += 1000
    shifted = run(f)
    assert shifted["folds"] == baseline["folds"]
    assert shifted["scores"] != baseline["scores"]


def test_future_feature_clock_fails_even_with_frozen_hash():
    f = ridge_fixture()
    f["training_features"][0]["size__known_at"] = "2020-12-01T00:00:00+09:00"
    with pytest.raises(ValueError, match="Future feature"):
        run(f)


def test_outcome_column_cannot_be_used_as_feature():
    f = ridge_fixture()
    f["rule"]["features"][0]["field"] = "gross_total_return_multiplier"
    with pytest.raises(ValueError, match="Outcome/metadata"):
        run(f)
    f = ridge_fixture()
    f["training_features"][0]["next_month_return"] = 99
    with pytest.raises(ValueError, match="labels/extra"):
        run(f)


def test_training_label_horizon_and_availability_match_execution():
    f = ridge_fixture()
    f["training_labels"][0]["exit_at"] = "2019-09-30T15:30:00+09:00"
    with pytest.raises(ValueError, match="horizon"):
        run(f)
    f = ridge_fixture()
    f["training_labels"][0]["return_available_at"] = "2019-08-31T15:30:00+09:00"
    with pytest.raises(ValueError, match="availability"):
        run(f)


def test_insufficient_train_support_never_skips_month():
    f = ridge_fixture()
    f["rule"]["min_train_months"] = 20
    with pytest.raises(ValueError, match="no silent skipped month"):
        run(f)


def test_no_global_fit_or_hyperparameter_grid():
    f = ridge_fixture()
    f["rule"]["alpha"] = [0.1, 1.0, 10.0]
    with pytest.raises(ValueError, match="numeric"):
        run(f)
    f = ridge_fixture()
    f["rule"]["selection"]["method"] = "BEST_OUTER_SHARPE"
    with pytest.raises(ValueError, match="selection"):
        run(f)


def test_missing_value_imputation_uses_training_only():
    f = ridge_fixture()
    f["training_features"][0]["size"] = None
    f["measurements"][0]["size"] = None
    result = run(f)
    assert np.isfinite(result["scores"][0]["signed_score"])
    assert result["folds"][0]["models"]["configured"]["medians"][0] < 20


def test_all_selection_fails_instead_of_silently_dropping():
    f = ridge_fixture()
    f["rule"]["selection"].update(method="ALL", max_features=3)
    for row in f["training_features"]:
        row["liquidity"] = None
    with pytest.raises(ValueError, match="ALL feature"):
        run(f)


def test_no_usable_training_feature_is_not_a_hypothesis_failure():
    f = ridge_fixture()
    for row in f["training_features"]:
        for name in ["size", "size_duplicate", "liquidity"]:
            row[name] = 1.
    with pytest.raises(ValueError, match="No usable train-only"):
        run(f)


def ridge_bundle_and_contract():
    f = ridge_fixture()
    bundle = {"origin": "SYNTHETIC", "reference": f["reference"], "measurements": f["measurements"], "training_features": f["training_features"], "training_labels": f["training_labels"], "sessions": f["sessions"],
              "asset_windows": [{**row, "entry_open": 100.} for row in f["training_labels"] if row["signal_month"] >= "2020-01"],
              "market_windows": [{"signal_month": month, "entry_at": next(row["entry_at"] for row in f["training_labels"] if row["signal_month"] == month), "exit_at": next(row["exit_at"] for row in f["training_labels"] if row["signal_month"] == month), "return_available_at": next(row["exit_at"] for row in f["training_labels"] if row["signal_month"] == month), "gross_total_return_multiplier": 1.001} for month in ["2020-01", "2020-02"]]}
    bundle["evidence"] = {"schema_version": "monthly-execution-evidence-v1", "as_of": f["research_as_of"], "data_sha256": runtime.bundle_data_sha256(bundle), **{flag: True for flag in runtime.monthly.EVIDENCE_FLAGS}}
    contract = {"schema": runtime.SCHEMA, "score_rule": f["rule"], "variants": list(runtime.VARIANTS), "benchmarks": runtime.BENCHMARKS.copy(), "costs": {"buy_rate": .0015, "sell_rate": .0015, "sell_tax_by_year": {"2020": .0023}}, "initial_nav": 1.,
                "scope": {"origin": "SYNTHETIC", "universe": SCOPE["universe"], "signal_months": ["2020-01", "2020-02"]}, "execution": runtime.EXECUTION.copy(), "decision_clock": "CALENDAR_MONTH_END_23_59_59_ASIA_SEOUL", "historical_reuse_acknowledged": True,
                "source_artifacts": {name: digest(bundle[name]) for name in (*runtime.ARRAYS, *ridge.EXTRA_ARRAYS)}, "input_bundle_sha256": digest(bundle)}
    return bundle, contract


def test_ridge_runtime_full_four_variant_execution(tmp_path):
    w = world(tmp_path)
    _, claim = reviewed(w)
    bundle, contract = ridge_bundle_and_contract()
    strategy = strategy_payload()
    strategy.update(runtime_contract=contract, execution=runtime.EXECUTION.copy(), costs={"commission_bps": 5., "slippage_bps": 10., "tax_model": "DATED_SELL_TAX_SCHEDULE", "sell_tax_by_year": {"2020": .0023}})
    snapshot = w["g"].snapshot([claim["id"]], as_of=NOW)
    node = w["g"].create_strategy(strategy, snapshot, actor="strategist", known_at=NOW)
    reg = runtime.register_execution(w["g"], node["id"], bundle, tmp_path / "runs", registered_at=NOW)
    result = runtime.execute_registered(w["g"], reg["run_dir"])
    assert result["score_model"] == "TRAIN_ONLY_RIDGE"
    assert result["variant_order"] == list(runtime.VARIANTS)
    assert "ridge_audit.json" in result["output_file_sha256"]
    audit = json.loads((Path(reg["run_dir"]) / "ridge_audit.json").read_text())
    assert len(audit["scores"]) == 20 and len(audit["folds"]) == 2
    assert runtime.verify_result(w["g"], reg["run_dir"]) == result
