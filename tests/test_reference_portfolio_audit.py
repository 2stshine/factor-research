"""Independent synthetic timing audit; never load real features or outcomes."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from engine import reference_portfolio as rp
from engine.research_generation import make_factor_entry, make_generation
from scripts.reference_portfolio import synthetic_fixture


def fixture():
    frame, manifest, config = synthetic_fixture()
    return frame, manifest, replace(config, last_test_month="2020-01", alphas=(1.0,), pca_components=(None, 1))


@pytest.mark.parametrize("missing_month", ["2020-01", "2020-02", "2020-03"])
def test_requested_outer_range_cannot_silently_skip_a_calendar_month(missing_month):
    frame, manifest, config = fixture()
    frame = frame.loc[frame.signal_month.ne(missing_month)].copy()
    with pytest.raises(ValueError, match="month|range|coverage"):
        rp.walk_forward_predict(frame, manifest, replace(config, last_test_month="2020-03"))


def test_current_outer_feature_batch_cannot_change_training_or_tuning():
    frame, manifest, config = fixture()
    expected = rp.walk_forward_predict(frame, manifest, config)
    current = frame.signal_month.eq(config.first_test_month)
    frame.loc[current, "synthetic_quality"] = np.linspace(100, 200, current.sum())
    frame.loc[current, "synthetic_value"] = np.nan
    actual = rp.walk_forward_predict(frame, manifest, config)
    assert actual["folds"] == expected["folds"]
    assert actual["predictions"] != expected["predictions"]
    assert not actual["implementation"]["raw_feature_content_authenticated"]


def test_each_actual_fit_receives_only_its_cutoff_eligible_targets(monkeypatch):
    frame, manifest, config = fixture()
    # Unique synthetic target tags allow checking the actual fit arguments, not
    # just the reported fold metadata. These are not financial observations.
    frame["next_month_return"] = np.arange(1, len(frame) + 1, dtype=float) / 1000
    delayed = frame.signal_month.eq("2018-08") & frame.asset_id.eq(1)
    frame.loc[delayed, "label_available_at"] = "2019-10-01T00:00:00+09:00"
    plans = rp.walk_forward_predict(frame, manifest, config)["folds"][0]
    assert "2018-08" in plans["train_months"]
    assert "2018-08" not in plans["inner_folds"][0]["train_months"]
    features = [entry["factor_id"] for entry in manifest["approved_factors"]]
    planned = []
    for audit in [*plans["inner_folds"], plans]:
        rows = frame.loc[frame.signal_month.isin(audit["train_months"])].sort_values(["signal_month", "asset_id"])
        cutoff = pd.Timestamp(audit["fit_cutoff"])
        assert all(pd.Timestamp(stamp) < cutoff for stamp in rows.label_available_at)
        planned.append((rows[features].to_numpy(float), rows.next_month_return.to_numpy(float), cutoff))
    actual_fit = rp.fit_ridge
    seen = []

    def audited_fit(values, targets, **kwargs):
        matches = [i for i, (x, y, _) in enumerate(planned)
                   if np.array_equal(values, x, equal_nan=True) and np.array_equal(targets, y)]
        assert matches, "Fit consumed rows not in any pre-cutoff training fold"
        seen.append(matches[0])
        return actual_fit(values, targets, **kwargs)

    monkeypatch.setattr(rp, "fit_ridge", audited_fit)
    result = rp.walk_forward_predict(frame, manifest, config)
    assert set(seen) == set(range(len(planned)))
    assert len(seen) == len(config.alphas) * len(config.pca_components) * config.inner_splits + 3
    assert result["folds"][0]["test_labels_scored"] is False


def test_approval_before_outer_but_after_inner_fit_still_rejects():
    frame, manifest, config = fixture()
    entries = []
    for old in manifest["approved_factors"]:
        fields = {key: old[key] for key in ("generation_id", "factor_id", "definition_sha256",
                  "implementation_sha256", "feature_sha256", "approval_evidence_sha256")}
        entries.append(make_factor_entry(**fields, admitted_at="2019-12-01T00:00:00+09:00"))
    manifest = make_generation(generation_id=manifest["generation_id"], purpose="SYNTHETIC", approved_factors=entries)
    frame.attrs["feature_entries"] = [{key: entry[key] for key in ("factor_id", "generation_id", "entry_sha256")}
                                     for entry in entries]
    with pytest.raises(ValueError, match="admitted|admission|decision"):
        rp.walk_forward_predict(frame, manifest, config)


def test_numeric_current_and_future_outcomes_do_not_change_the_same_outer_fit():
    frame, manifest, config = fixture()
    expected = rp.walk_forward_predict(frame, manifest, config)
    frame.loc[frame.signal_month.ge(config.first_test_month), "next_month_return"] = -99999.0
    actual = rp.walk_forward_predict(frame, manifest, config)
    assert actual == expected
