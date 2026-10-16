"""Synthetic-only validation of timing, training isolation and numerical rules."""
from copy import deepcopy
from dataclasses import replace
import json

import numpy as np
import pandas as pd
import pytest

from engine import reference_portfolio as rp
from scripts import reference_portfolio as cli


def fixture():
    frame, manifest, config = cli.synthetic_fixture()
    return frame, manifest, replace(config, last_test_month="2020-03")


def test_intercept_is_not_penalized_even_with_extreme_ridge_penalty():
    model = rp.fit_ridge([[1, 7], [2, 6], [3, 4], [4, 3]], [17, 17, 17, 17], alpha=1e12)
    np.testing.assert_allclose(model.coefficients, 0, atol=1e-15)
    np.testing.assert_allclose(model.predict([[999, -999]]), 17)
    assert model.intercept == 17


def test_ridge_matches_closed_form_with_train_only_scaling():
    x = np.array([[1, 8], [2, 5], [4, 4], [6, 2]], dtype=float)
    y = np.array([4, 2, 1, 7], dtype=float)
    model = rp.fit_ridge(x, y, alpha=2.5)
    z = (x - x.mean(axis=0)) / x.std(axis=0)
    expected = np.linalg.solve(z.T @ z + 2.5 * np.eye(2), z.T @ (y - y.mean()))
    np.testing.assert_allclose(model.coefficients, expected)
    np.testing.assert_allclose(model.predict(x), z @ expected + y.mean())


def test_imputation_and_pca_are_trainfit_not_recomputed_on_test_batch():
    x = np.array([[1, 2, np.nan], [2, 4, 6], [4, 1, 9], [8, 2, 12]], dtype=float)
    model = rp.fit_ridge(x, np.arange(4), alpha=1, pca_components=2)
    before = deepcopy(model.audit())
    alone = model.predict([[np.nan, 3, 7]])[0]
    joint = model.predict([[np.nan, 3, 7], [1e12, -1e12, 1e10]])[0]
    assert alone == pytest.approx(joint)
    assert model.audit() == before
    np.testing.assert_array_equal(model.medians, [3, 2, 9])
    np.testing.assert_allclose(model.components @ model.components.T, np.eye(2), atol=1e-12)


@pytest.mark.parametrize("alpha", [0, -1, float("nan"), float("inf")])
def test_invalid_ridge_alpha_rejected(alpha):
    with pytest.raises(ValueError, match="alpha"):
        rp.fit_ridge([[1], [2]], [1, 2], alpha=alpha)


def test_all_missing_train_feature_is_not_filled_from_future_test():
    with pytest.raises(ValueError, match="two observed"):
        rp.fit_ridge([[np.nan], [np.nan]], [1, 2], alpha=1)


def test_walk_forward_produces_baseline_and_pca_predictions_no_outer_metrics():
    frame, manifest, config = fixture()
    result = rp.walk_forward_predict(frame, manifest, config)
    assert len(result["predictions"]) == 24
    assert len(result["folds"]) == 3
    assert not result["financial_claims"]
    assert not result["implementation"]["portfolio_optimization"]
    assert not result["implementation"]["outer_test_metrics_computed"]
    for row in result["predictions"]:
        assert all(np.isfinite(row[key]) for key in ("prediction_selected", "prediction_ridge_no_pca", "prediction_pca_ridge"))
        assert "next_month_return" not in row
    for fold in result["folds"]:
        assert pd.Timestamp(fold["max_train_label_available_at"]) < pd.Timestamp(fold["fit_cutoff"])
        assert max(map(rp._month, fold["train_months"])) < rp._month(fold["signal_month"]) - 1
        for inner in fold["inner_folds"]:
            assert not set(inner["train_months"]) & set(inner["validation_months"])
            assert max(map(rp._month, inner["train_months"])) < min(map(rp._month, inner["validation_months"])) - 1
            assert pd.Timestamp(inner["max_train_label_available_at"]) < pd.Timestamp(inner["fit_cutoff"])


def test_future_feature_and_label_perturbation_does_not_change_past_models_or_predictions():
    frame, manifest, config = fixture()
    baseline = rp.walk_forward_predict(frame, manifest, config)
    changed = frame.copy(deep=True)
    future = changed.signal_month.gt("2020-03")
    changed.loc[future, "synthetic_quality"] = 1e9
    changed.loc[future, "synthetic_value"] = -1e8
    changed.loc[future, "next_month_return"] = 1e7
    repeated = rp.walk_forward_predict(changed, manifest, config)
    assert repeated["predictions"] == baseline["predictions"]
    assert repeated["folds"] == baseline["folds"]


def test_current_outer_test_labels_not_used_in_prediction_or_tuning():
    frame, manifest, config = fixture()
    config = replace(config, last_test_month=config.first_test_month)
    expected = rp.walk_forward_predict(frame, manifest, config)
    frame.loc[frame.signal_month.ge(config.first_test_month), "next_month_return"] = np.nan
    actual = rp.walk_forward_predict(frame, manifest, config)
    assert actual["predictions"] == expected["predictions"]
    assert actual["folds"] == expected["folds"]


def test_one_late_label_purges_its_entire_month_and_exact_cutoff_is_not_available():
    frame, manifest, config = fixture()
    config = replace(config, last_test_month=config.first_test_month)
    cutoff = frame.loc[frame.signal_month.eq("2020-01"), "decision_at"].iloc[0]
    frame.loc[frame.signal_month.eq("2018-03") & frame.asset_id.eq(1), "label_available_at"] = cutoff
    result = rp.walk_forward_predict(frame, manifest, config)
    fold = result["folds"][0]
    assert "2018-03" not in fold["train_months"]
    assert "2018-03" in fold["unavailable_label_months_excluded"]


def test_missing_feature_values_use_train_median_without_dropping_month_groups():
    frame, manifest, config = fixture()
    frame.loc[frame.asset_id.eq(2), "synthetic_value"] = np.nan
    result = rp.walk_forward_predict(frame, manifest, config)
    assert len(result["predictions"]) == 24
    assert all(np.isfinite(row["prediction_selected"]) for row in result["predictions"])


@pytest.mark.parametrize("case", ["missing_column", "naive_decision", "naive_known_at", "ambiguous_month", "stale", "future", "duplicate", "different_decisions", "wrong_label_month", "availability_before_end", "infinite_feature"])
def test_missing_stale_future_or_ambiguous_input_rejected(case):
    frame, manifest, config = fixture()
    if case == "missing_column":
        frame = frame.drop(columns="synthetic_growth__known_at")
    elif case == "naive_decision":
        frame.loc[0, "decision_at"] = "2018-01-31"
    elif case == "naive_known_at":
        frame.loc[0, "synthetic_growth__known_at"] = "2018-01-30"
    elif case == "ambiguous_month":
        frame.loc[0, "signal_month"] = "01/2018"
    elif case == "stale":
        frame.loc[0, "synthetic_quality__known_at"] = "2010-01-01T00:00:00+09:00"
    elif case == "future":
        frame.loc[0, "synthetic_quality__known_at"] = "2025-01-01T00:00:00+09:00"
    elif case == "duplicate":
        frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    elif case == "different_decisions":
        frame.loc[0, "decision_at"] = "2018-01-31T19:00:00+09:00"
    elif case == "wrong_label_month":
        frame.loc[0, "label_end_at"] = "2018-04-01T00:00:00+09:00"
    elif case == "availability_before_end":
        frame.loc[0, "label_available_at"] = frame.loc[0, "decision_at"]
    else:
        frame.loc[0, "synthetic_value"] = np.inf
    with pytest.raises(ValueError):
        rp.walk_forward_predict(frame, manifest, config)


@pytest.mark.parametrize("case", ["absent", "mixed_generation", "wrong_entry", "empty_approved"])
def test_generation_lineage_never_falls_back_to_old_gold(case):
    frame, manifest, config = fixture()
    if case == "absent":
        frame.attrs.clear()
    elif case == "mixed_generation":
        frame.attrs["feature_entries"][0]["generation_id"] = "legacy-gold"
    elif case == "wrong_entry":
        frame.attrs["feature_entries"][0]["entry_sha256"] = "0" * 64
    else:
        from engine.research_generation import make_generation
        manifest = make_generation(generation_id="synthetic-reference-demo", purpose="SYNTHETIC", approved_factors=[])
    with pytest.raises(ValueError):
        rp.walk_forward_predict(frame, manifest, config)


def test_factor_admitted_in_2026_cannot_be_presented_as_known_in_2020():
    from engine.research_generation import make_factor_entry, make_generation
    frame, manifest, config = fixture()
    entries = []
    for row in manifest["approved_factors"]:
        fields = {key: row[key] for key in ("generation_id", "factor_id", "definition_sha256", "implementation_sha256", "feature_sha256", "approval_evidence_sha256")}
        entries.append(make_factor_entry(**fields, admitted_at="2026-01-01T00:00:00+09:00"))
    manifest = make_generation(generation_id="synthetic-reference-demo", purpose="SYNTHETIC", approved_factors=entries)
    frame.attrs["feature_entries"] = [{key: row[key] for key in ("factor_id", "generation_id", "entry_sha256")} for row in entries]
    with pytest.raises(ValueError):
        rp.walk_forward_predict(frame, manifest, config)


def test_no_silent_performance_based_factor_subset_selection():
    frame, manifest, config = fixture()
    frame.attrs["feature_entries"] = frame.attrs["feature_entries"][:2]
    with pytest.raises(ValueError, match="Exact ordered"):
        rp.walk_forward_predict(frame, manifest, replace(config, pca_components=(None, 1)))


def test_even_approved_entry_cannot_name_return_label_as_a_feature():
    from engine.research_generation import make_factor_entry, make_generation
    frame, manifest, config = fixture()
    source = manifest["approved_factors"][0]
    fields = {key: source[key] for key in ("generation_id", "definition_sha256", "implementation_sha256", "feature_sha256", "approval_evidence_sha256", "admitted_at")}
    entry = make_factor_entry(**fields, factor_id="next_month_return")
    manifest = make_generation(generation_id="synthetic-reference-demo", purpose="SYNTHETIC", approved_factors=[entry])
    frame.attrs["feature_entries"] = [{key: entry[key] for key in ("factor_id", "generation_id", "entry_sha256")}]
    with pytest.raises(ValueError, match="Labels and metadata"):
        rp.walk_forward_predict(frame, manifest, replace(config, pca_components=(None, 1)))


@pytest.mark.parametrize("config_change", [{"purge_gap_months": 0}, {"pca_components": (1, 2)}, {"alphas": (1, 1)}, {"inner_splits": 100}])
def test_invalid_or_unsupported_tuning_contract_fails_closed(config_change):
    frame, manifest, config = fixture()
    with pytest.raises(ValueError):
        rp.walk_forward_predict(frame, manifest, replace(config, **config_change))


def test_input_order_does_not_change_folds_or_predictions():
    frame, manifest, config = fixture()
    expected = rp.walk_forward_predict(frame, manifest, config)
    actual = rp.walk_forward_predict(frame.sample(frac=1, random_state=19), manifest, config)
    assert actual["predictions"] == expected["predictions"]
    assert actual["folds"] == expected["folds"]


def test_cli_requires_explicit_synthetic_flag_and_never_overwrites(tmp_path):
    path = tmp_path / "demo.json"
    with pytest.raises(SystemExit):
        cli.main(["--output", str(path)])
    assert not path.exists()
    assert cli.main(["--synthetic-demo", "--output", str(path)]) == 0
    data = json.loads(path.read_text())
    assert not data["real_data_fitted"] and not data["financial_claims"]
    assert len(data["predictions"]) == 96
    assert "folds" not in data and "next_month_return" not in json.dumps(data)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        cli.main(["--synthetic-demo", "--output", str(path)])
    assert path.read_bytes() == original
