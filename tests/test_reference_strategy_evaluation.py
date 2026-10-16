from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from engine import reference_admission as admission, reference_strategy_evaluation as evaluation
from engine.research_generation import digest
from tests.test_phenomenon_ridge import ridge_fixture, ridge_bundle_and_contract


def report_for(bundle):
    # Explicit SOFTWARE_TEST_ONLY registry; never claim actual Gold verification.
    rows = [{"reference_id": f["reference_id"], "definition_sha256": f["definition_sha256"], "status": "ADMITTED"}
            for f in bundle["reference"]["features"]]
    result = {"schema": admission.SCHEMA, "program_sha256": "a" * 64, "origin": "SYNTHETIC",
              "live_database_verified": False, "status": "SOFTWARE_TEST_ONLY", "decisions": rows}
    result["admission_sha256"] = digest(result)
    return result


def test_three_models_four_portfolios_same_sample_and_no_automatic_winner():
    b, c = ridge_bundle_and_contract()
    r = evaluation.compare(b, c, report_for(b), program_sha256="a" * 64,
                           selected_max_features=2, pca_components=1, registered_at="2020-04-06T00:00:00+09:00")
    assert list(r["models"]) == list(evaluation.MODELS)
    assert r["selected_model"] is None and not r["alpha_approved"]
    assert r["empirical_use"] == "SOFTWARE_TEST_ONLY"
    counts = []
    for model in r["models"].values():
        assert len(model["execution"]["variants"]) == 4
        assert len(model["summary"]) == 4
        counts.append(len(model["ridge"]["scores"]))
    assert counts == [20, 20, 20]
    assert r["models"]["selected_ridge"]["ridge"]["folds"][0]["selection_outcome_scope"] == "KNOWN_TRAIN_LABELS_ONLY"


def test_unadmitted_feature_never_silently_enters_strategy():
    b, c = ridge_bundle_and_contract()
    a = report_for(b)
    a["decisions"][0]["status"] = "REJECTED"
    a["admission_sha256"] = digest({k: v for k, v in a.items() if k != "admission_sha256"})
    with pytest.raises(ValueError, match="admitted definitions"):
        evaluation.compare(b, c, a, program_sha256="a" * 64, selected_max_features=2,
                           pca_components=1, registered_at="2020-04-06T00:00:00+09:00")


def test_train_ic_selection_is_unchanged_by_future_returns():
    f = ridge_fixture()
    f["rule"]["selection"]["method"] = "TRAIN_IC_CORRELATION"
    r = evaluation.ridge.generate_scores(**f)
    for row in f["training_labels"]:
        if row["signal_month"] >= "2019-12":
            row["gross_total_return_multiplier"] = float(row["asset_id"] * 10)
    changed = evaluation.ridge.generate_scores(**f)
    assert r["folds"][0] == changed["folds"][0]
    assert r["scores"][:10] == changed["scores"][:10]


def test_all_usable_keeps_risk_controls_but_skips_training_missing_feature():
    f = ridge_fixture()
    f["rule"]["selection"].update(method="ALL_USABLE", max_features=3)
    f["rule"]["pca_components"] = None
    for row in f["training_features"]:
        row["liquidity"] = None
    r = evaluation.ridge.generate_scores(**f)
    assert r["folds"][0]["selected_features"] == ["size", "size_duplicate"]
    assert r["folds"][0]["dropped_features"]["liquidity"] == "INSUFFICIENT_TRAIN_OBSERVATIONS"


def test_gold_projection_values_and_individual_availability_must_match():
    f = ridge_fixture()
    rows = [{"reference_id": "size", "asset_id": r["asset_id"],
             "date": str(pd.Period(r["signal_month"], freq="M").end_time.date()),
             "known_at": r["size__known_at"], "value": r["size"]} for r in f["training_features"]]
    frame = pd.DataFrame(rows)
    evaluation.verify_feature_projection(f, "size", "size", frame)
    changed = deepcopy(f)
    changed["measurements"][0]["size"] += 1
    with pytest.raises(ValueError, match="values differ"):
        evaluation.verify_feature_projection(changed, "size", "size", frame)
    changed = deepcopy(f)
    changed["measurements"][0]["size__known_at"] = "2020-01-01T00:00:00+09:00"
    with pytest.raises(ValueError, match="known_at differs"):
        evaluation.verify_feature_projection(changed, "size", "size", frame)


def test_supports_existing_108_without_old_64_limit():
    f = ridge_fixture()
    features = [{"field": "feature_" + str(i), "reference_id": "ref_" + str(i), "definition_sha256": "b" * 64} for i in range(108)]
    f["rule"]["features"] = features
    f["reference"]["features"] = features
    assert len(evaluation.ridge.validate_rule(f["rule"], f["reference"], "SYNTHETIC")) == 108


def test_training_months_not_pooled_row_count_determine_ic():
    x = np.array([[1], [2], [3], [1], [2], [3], [4], [5], [6]], dtype=float)
    y = np.array([1, 2, 3, 6, 5, 4, 3, 2, 1], dtype=float)
    r = evaluation.ridge._training_ic(x, y, ["a"] * 3 + ["b"] * 6, ["x"])
    assert r["x"]["mean_rank_ic"] == pytest.approx(0.)
    assert r["x"]["valid_months"] == 2


def test_full_108_feature_three_model_execution_is_software_only():
    b, c = ridge_bundle_and_contract()
    specs = [{"field": f"feature_{i}", "reference_id": f"reference_{i}",
              "definition_sha256": digest({"synthetic_feature": i})} for i in range(108)]
    rng = np.random.default_rng(821)
    generated = {}
    for row in b["training_features"]:
        generated[(row["signal_month"], row["asset_id"])] = rng.normal(size=108)
    for array in ("measurements", "training_features"):
        converted = []
        for row in b[array]:
            keep = {k: row[k] for k in ("signal_month", "asset_id", "eligible", "available_at")}
            if array == "measurements":
                keep["market_cap"] = row["market_cap"]
            values = generated[(row["signal_month"], row["asset_id"])]
            for i, spec in enumerate(specs):
                keep[spec["field"]] = float(values[i])
                keep[spec["field"] + "__known_at"] = row["available_at"]
            converted.append(keep)
        b[array] = converted
    b["reference"]["features"] = specs
    c["score_rule"]["features"] = specs
    c["score_rule"]["pca_components"] = None
    c["score_rule"]["selection"].update(method="ALL_USABLE", max_features=108)
    b["evidence"]["data_sha256"] = evaluation.runtime.bundle_data_sha256(b)
    c["input_bundle_sha256"] = digest(b)
    c["source_artifacts"] = {k: digest(b[k]) for k in c["source_artifacts"]}
    r = evaluation.compare(b, c, report_for(b), program_sha256="a" * 64,
                           selected_max_features=30, pca_components=10, registered_at="2020-04-06T00:00:00+09:00")
    assert r["empirical_use"] == "SOFTWARE_TEST_ONLY"
    assert len(r["models"]["all_usable_ridge"]["ridge"]["folds"][0]["selected_features"]) == 108
    assert len(r["models"]["selected_ridge"]["ridge"]["folds"][0]["selected_features"]) == 30
    assert r["models"]["selected_pca_ridge"]["ridge"]["folds"][0]["models"]["configured"]["pca_components"] == 10


def test_missing_measurement_can_have_no_known_at_instead_of_fake_timestamp():
    f = ridge_fixture()
    f["measurements"][0]["size"] = None
    f["measurements"][0]["size__known_at"] = None
    r = evaluation.ridge.generate_scores(**f)
    assert np.isfinite(r["scores"][0]["signed_score"])
