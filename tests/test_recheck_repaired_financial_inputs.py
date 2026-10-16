"""Synthetic same-candidate input diagnostics; no DB or archived outcomes."""
import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from engine import fundamental_contract, gate, panel, research_policy, silver
from factors.candidates.sales_growth_acceleration_12m import FACTOR
from scripts import recheck_repaired_financial_inputs as recheck


@pytest.fixture
def setup(tmp_path, monkeypatch):
    campaign = tmp_path / "closed-campaign"
    campaign.mkdir()
    source = tmp_path / "candidate.py"
    source.write_text("# synthetic immutable candidate source identity\n")
    panel_path = tmp_path / "repaired-panel.pkl"
    panel_path.write_bytes(b"synthetic loader fixture; never unpickle")
    manifest = {
        "campaign_id": "synthetic-reference", "status": "CLOSED_ABORTED",
        "discovery": {"data_cutoff": "2023-07-31", "signal_end": "2023-06"},
        "oos": {"start": "2023-08", "status": "NOT_USED"},
        "snapshot": {"discovery_input_digest": "a" * 64},
    }
    prior = {
        "campaign_id": "synthetic-reference",
        "candidate_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "input_feasibility": {
            "snapshot_digest": "a" * 64, "signal_start": str(gate.RESEARCH_START), "signal_end": "2023-06",
            "minimum_coverage": gate.TH["coverage"], "minimum_monthly_coverage_p10": gate.TH["monthly_coverage_p10"],
            "factors": [{"factor": FACTOR.name, "definition_hash": FACTOR.definition_hash}],
        },
    }
    manifest_path = campaign / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    prior_path = campaign / "candidate-input-check-sales-growth-acceleration.json"
    prior_path.write_text(json.dumps(prior))
    dates = pd.date_range("2014-12-31", "2023-09-30", freq="ME")
    n = len(dates)
    monthly = pd.DataFrame({
        "asset_id": [1] * n, "Code": ["000001"] * n, "ym": dates.to_period("M"), "trade_date": dates,
        "instrument_type": ["common_stock"] * n, "market": ["KOSPI"] * n,
        "in_universe": [True] * n, "market_cap": [100.0] * n, "adj_close": [100.0] * n,
        "available_date": dates - pd.Timedelta(days=1), "revenue_ttm": np.arange(n, dtype=float) + 100.0,
        "total_return_close": [999.0] * n, "fwd_mid": [999.0] * n, "f_old": [999.0] * n,
        # Zero liquidity must not silently change the existing universe rule.
        "adv20": [0.0] * n,
    })
    monthly.attrs["forbidden_parent_metadata"] = "not a candidate input"
    repaired = panel.Panel(monthly, pd.Series(dtype="datetime64[ns]"), {
        fundamental_contract.META_KEY: {"sha256": "b" * 64},
    })
    monkeypatch.setattr(recheck, "CAMPAIGN", campaign)
    monkeypatch.setattr(recheck, "SOURCE", source)
    monkeypatch.setattr(recheck.factors, "REGISTRY", {FACTOR.name: FACTOR})
    monkeypatch.setattr(recheck.run, "load_registry", lambda: None)
    original_cache = recheck.run.PANEL_CACHE

    def load():
        assert recheck.run.PANEL_CACHE == panel_path
        return repaired

    monkeypatch.setattr(recheck.run, "_load", load)
    monkeypatch.setattr(fundamental_contract, "verify", lambda *a, **k: {"status": "SYNTHETIC_BINDING_TEST"})
    monkeypatch.setattr(silver, "connect", lambda *a, **k: pytest.fail("No live DB"))
    for helper in ("_scope_discovery_panel", "_rebuild_scoped_panel", "_ensure_factor_columns", "_research_input_panel"):
        monkeypatch.setattr(recheck.run, helper, lambda *a, **k: pytest.fail("Return-capable or logging helper forbidden"))
    monkeypatch.setattr(panel, "forward_returns", lambda *a, **k: pytest.fail("Forward labels must not be recomputed"))
    return SimpleNamespace(campaign=campaign, source=source, panel_path=panel_path, manifest=manifest,
                           manifest_path=manifest_path, prior=prior, prior_path=prior_path, repaired=repaired,
                           output=tmp_path / "diagnostic.json", original_cache=original_cache)


def test_strict_label_free_scope_keeps_original_universe_and_history(setup, monkeypatch):
    original_compute = research_policy.compute_factor
    visible = []

    def compute(candidate, frame, **kwargs):
        assert frame.ym.min() == pd.Period("2015-01", "M")
        assert frame.ym.max() == pd.Period("2023-07", "M")
        assert "total_return_close" not in frame and not any(c.startswith(("fwd_", "f_")) for c in frame)
        assert frame.attrs == {}
        visible.append(frame.copy())
        return original_compute(candidate, frame, **kwargs)

    monkeypatch.setattr(research_policy, "compute_factor", compute)
    protected = {path: path.read_bytes() for path in (setup.manifest_path, setup.prior_path, setup.source, setup.panel_path)}
    receipt = recheck.check(setup.panel_path, setup.output)
    assert len(visible) == 1
    assert recheck.run.PANEL_CACHE == setup.original_cache
    assert all(path.read_bytes() == original for path, original in protected.items())
    assert receipt["input_feasibility"]["status"] == "PASS"
    assert receipt["input_feasibility"]["factors"][0]["coverage"] == 1.0
    assert len(receipt["monthly_input_coverage"]) == 64
    assert receipt["monthly_input_coverage"][0]["month"] == "2018-03"
    assert receipt["monthly_input_coverage"][-1]["month"] == "2023-06"
    assert all(row["universe_rows"] == 1 for row in receipt["monthly_input_coverage"])
    assert receipt["reference_full_discovery_digest"] == "a" * 64
    assert len(receipt["new_label_free_input_digest"]) == 64
    assert "Different scopes" in receipt["digest_comparison"]
    assert receipt["forward_labels_recomputed"] is False
    assert receipt["live_identity_checked_by_this_check"] is False
    assert receipt["registration_attempted"] is receipt["registration_authorized"] is False
    assert receipt["return_evaluations"] == receipt["oos_performance_evaluations"] == receipt["gold_writes"] == 0


def test_label_and_post_cutoff_changes_do_not_change_input_digest(setup):
    first = recheck._label_free_panel(setup.repaired, setup.manifest)
    before = panel.snapshot_digest(first)
    setup.repaired.monthly["fwd_mid"] = -987654.0
    setup.repaired.monthly["total_return_close"] = 0.0
    outside = setup.repaired.monthly.ym.gt(pd.Period("2023-07", "M"))
    setup.repaired.monthly.loc[outside, "revenue_ttm"] = -123456.0
    setup.repaired.monthly.loc[outside, "in_universe"] = False
    assert panel.snapshot_digest(recheck._label_free_panel(setup.repaired, setup.manifest)) == before


def test_fixed_universe_excludes_only_its_original_eligibility_terms(setup):
    frame = setup.repaired.monthly
    # Leave two valid research months with missing signal to distinguish all
    # universe rows from the available-only (incorrect) denominator.
    frame.loc[frame.ym.eq(pd.Period("2020-01", "M")), "revenue_ttm"] = np.nan
    frame.loc[frame.ym.eq(pd.Period("2020-02", "M")), "in_universe"] = False
    frame.loc[frame.ym.eq(pd.Period("2020-03", "M")), "market_cap"] = 0.0
    frame.loc[frame.ym.eq(pd.Period("2020-04", "M")), "adj_close"] = np.nan
    receipt = recheck.check(setup.panel_path, setup.output)
    months = {row["month"]: row for row in receipt["monthly_input_coverage"]}
    assert months["2020-01"]["universe_rows"] == 1
    assert months["2020-01"]["finite_signals"] == 0
    assert not {"2020-02", "2020-03", "2020-04"} & set(months)


@pytest.mark.parametrize("change", ["cutoff", "oos", "signal_end", "common_start", "coverage", "monthly_p10", "digest", "campaign"])
def test_reference_calendar_and_policy_cannot_be_relaxed(setup, change):
    manifest, prior = setup.manifest, setup.prior
    if change == "cutoff":
        manifest["discovery"]["data_cutoff"] = "2023-08-31"
    elif change == "oos":
        manifest["oos"]["start"] = "2023-09"
    elif change == "signal_end":
        manifest["discovery"]["signal_end"] = "2023-07"
    elif change == "campaign":
        prior["campaign_id"] = "different-campaign"
    else:
        key, value = {"common_start": ("signal_start", "2019-01"), "coverage": ("minimum_coverage", 0.1),
                      "monthly_p10": ("minimum_monthly_coverage_p10", 0.1), "digest": ("snapshot_digest", "f" * 64)}[change]
        prior["input_feasibility"][key] = value
    setup.manifest_path.write_text(json.dumps(manifest))
    setup.prior_path.write_text(json.dumps(prior))
    with pytest.raises(ValueError, match="Reference calendar"):
        recheck.check(setup.panel_path, setup.output)
    assert not setup.output.exists()


@pytest.mark.parametrize("change", ["source", "definition", "open_campaign", "oos_used"])
def test_candidate_and_campaign_state_remain_frozen(setup, change):
    if change == "source":
        setup.source.write_text("changed formula")
    elif change == "definition":
        setup.prior["input_feasibility"]["factors"][0]["definition_hash"] = "f" * 64
        setup.prior_path.write_text(json.dumps(setup.prior))
    else:
        if change == "open_campaign":
            setup.manifest["status"] = "ACTIVE"
        else:
            setup.manifest["oos"]["status"] = "REVEALED"
        setup.manifest_path.write_text(json.dumps(setup.manifest))
    with pytest.raises(ValueError):
        recheck.check(setup.panel_path, setup.output)
    assert not setup.output.exists()


def test_recheck_does_not_reuse_or_overwrite_existing_receipt(setup):
    setup.output.write_bytes(b"previous diagnostic")
    with pytest.raises(ValueError, match="overwrite"):
        recheck.check(setup.panel_path, setup.output)
    assert setup.output.read_bytes() == b"previous diagnostic"


def test_missing_cutoff_or_duplicate_rows_fail_before_compute(setup):
    original = setup.repaired.monthly.copy()
    setup.repaired.monthly = original.loc[original.ym.ne(pd.Period("2023-07", "M"))]
    with pytest.raises(ValueError, match="fixed Discovery cutoff"):
        recheck._label_free_panel(setup.repaired, setup.manifest)
    setup.repaired.monthly = pd.concat([original, original.iloc[1:2]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate asset/month"):
        recheck._label_free_panel(setup.repaired, setup.manifest)


def test_loader_failure_restores_default_cache_path(setup, monkeypatch):
    monkeypatch.setattr(recheck.run, "_load", lambda: (_ for _ in ()).throw(RuntimeError("synthetic bad contract")))
    with pytest.raises(RuntimeError, match="synthetic bad contract"):
        recheck.check(setup.panel_path, setup.output)
    assert recheck.run.PANEL_CACHE == setup.original_cache
    assert not setup.output.exists()
