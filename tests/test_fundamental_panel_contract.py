"""Synthetic financial-cache integrity tests: no DB, OOS, or real cache reads."""
from copy import deepcopy
import pickle

import pandas as pd
import pytest

from engine import fundamental_contract as contract
from engine import fundamentals, panel as panels, silver
from scripts import run


@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    monkeypatch.setattr(silver, "connect", lambda *a, **k: pytest.fail("Unexpected database access"))


@pytest.fixture
def raw():
    dates = pd.to_datetime(["2015-03-31", "2015-06-30", "2015-09-30", "2015-12-31"])
    return pd.DataFrame({
        "asset_id": [1] * 4, "period_end": dates,
        "fiscal_period": ["Q1", "Q2", "Q3", "Q4"], "fs_type": ["CFS"] * 4,
        "statement_type": ["IS"] * 4,
        "available_date": dates + pd.Timedelta(days=45),
        "available_at": dates + pd.Timedelta(days=45),
        "metric": ["revenue"] * 4, "value": [10.0, 20.0, 30.0, 40.0],
        "revision_key": ["synthetic-1", "synthetic-2", "synthetic-3", "synthetic-4"],
        "quality_run_id": ["synthetic-certified-run-a"] * 3 + ["synthetic-certified-run-b"],
    })


@pytest.fixture
def price_only():
    dates = pd.to_datetime(["2016-01-29", "2016-02-29", "2016-03-31"])
    return panels.Panel(pd.DataFrame({
        "asset_id": [1] * 3, "Code": ["000001"] * 3,
        "ym": dates.to_period("M"), "trade_date": dates,
        "adj_close": [100.0, 101.0, 102.0],
    }), pd.Series(dtype="datetime64[ns]"), {"source": "SYNTHETIC"})


@pytest.fixture
def replay(raw):
    return contract.materialize(raw, verbose=False)


@pytest.fixture
def financial(price_only, replay):
    price_only.monthly = fundamentals.attach(
        price_only.monthly, replay, sorted(fundamentals.PIT_FEATURES),
    )
    return price_only


@pytest.fixture
def bound(financial, raw, replay):
    contract.bind(financial, raw, materialized=replay)
    return financial


def test_replay_binding_has_actual_content_and_quality_run_provenance(bound):
    result = contract.verify(bound, require_financial=True)
    assert result["status"] == "VERIFIED_LOCAL_REPLAY_BINDING"
    meta = bound.meta[contract.META_KEY]
    assert meta["methodology_version"] == fundamentals.FUNDAMENTAL_METHODOLOGY_VERSION
    assert meta["materializer_source_sha256"] == fundamentals.source_sha256()
    assert meta["ledger"]["row_count"] == 4
    assert meta["ledger"]["quality_run_count"] == 2
    assert meta["ledger"]["rows_by_quality_run"] == {
        "synthetic-certified-run-a": 3, "synthetic-certified-run-b": 1,
    }
    assert meta["ledger"]["independent_first_vintage_verification"] is False
    assert meta["financial_features"] == sorted(fundamentals.PIT_FEATURES)
    assert pd.isna(bound.monthly.iloc[0]["revenue_ttm"])
    assert bound.monthly.iloc[1]["revenue_ttm"] == 100.0


def test_bind_without_precomputed_replay_is_supported(financial, raw):
    contract.bind(financial, raw)
    assert contract.verify(financial)["status"] == "VERIFIED_LOCAL_REPLAY_BINDING"


def test_legacy_and_overlay_provenance_cannot_coexist(bound):
    bound.meta[contract.OVERLAY_META_KEY] = {"sha256": "untrusted"}
    with pytest.raises(RuntimeError, match="Ambiguous"):
        contract.verify(bound)


def test_unknown_overlay_never_falls_back_to_price_only(price_only):
    price_only.meta[contract.OVERLAY_META_KEY] = {}
    with pytest.raises(ValueError):
        contract.verify(price_only)


def test_row_order_does_not_change_ledger_or_panel_contract(bound, raw, replay):
    before = deepcopy(bound.meta[contract.META_KEY])
    bound.monthly = bound.monthly.iloc[::-1].reset_index(drop=True)
    contract.bind(bound, raw.iloc[::-1].reset_index(drop=True), materialized=replay)
    assert bound.meta[contract.META_KEY] == before
    contract.verify(bound)


@pytest.mark.parametrize("change", ["value", "quality_run_id", "available_at", "revision_key"])
def test_receipt_cannot_be_reused_for_another_raw_ledger(financial, raw, replay, change):
    altered = raw.copy()
    altered.loc[0, change] = {
        "value": 99.0, "quality_run_id": "another-run",
        "available_at": pd.Timestamp("2015-05-18"), "revision_key": "another-revision",
    }[change]
    with pytest.raises(ValueError, match="receipt changed"):
        contract.bind(financial, altered, materialized=replay)
    assert contract.META_KEY not in financial.meta


@pytest.mark.parametrize("change", ["missing_receipt", "materialized_value", "panel_value", "partial_features"])
def test_old_or_changed_values_cannot_be_blessed(financial, raw, replay, change):
    if change == "missing_receipt":
        replay.attrs.clear()
    elif change == "materialized_value":
        replay.loc[replay.index[-1], "revenue_ttm"] = 12345.0
    elif change == "panel_value":
        financial.monthly.loc[financial.monthly.index[-1], "revenue_ttm"] = 12345.0
    else:
        financial.monthly = financial.monthly.drop(columns="sue_score")
    with pytest.raises(ValueError):
        contract.bind(financial, raw, materialized=replay)
    assert contract.META_KEY not in financial.meta


@pytest.mark.parametrize("change", ["version", "source", "query"])
def test_cache_is_stale_after_materialization_contract_changes(bound, monkeypatch, change):
    if change == "version":
        monkeypatch.setattr(fundamentals, "FUNDAMENTAL_METHODOLOGY_VERSION", "future-method")
    elif change == "source":
        monkeypatch.setattr(fundamentals, "source_sha256", lambda: "f" * 64)
    else:
        monkeypatch.setattr(silver, "FUNDAMENTAL_SQL", silver.FUNDAMENTAL_SQL + "\n-- changed")
    with pytest.raises(RuntimeError, match="methodology/source changed"):
        contract.verify(bound)


@pytest.mark.parametrize("change", ["value", "date", "asset", "row_count", "duplicate", "feature"])
def test_execution_rejects_tampered_financial_frame(bound, change):
    if change == "value":
        bound.monthly.loc[0, "revenue_ttm"] = 123.0
    elif change == "date":
        bound.monthly.loc[0, "available_date"] = pd.Timestamp("2016-01-01")
    elif change == "asset":
        bound.monthly.loc[0, "asset_id"] = 2
    elif change == "row_count":
        bound.monthly = bound.monthly.iloc[1:].copy()
    elif change == "duplicate":
        bound.monthly = pd.concat([bound.monthly, bound.monthly.iloc[:1]], ignore_index=True)
    else:
        bound.monthly = bound.monthly.drop(columns="revenue_ttm")
    with pytest.raises(RuntimeError):
        contract.verify(bound)


def test_downstream_outcome_columns_are_not_financial_input_evidence(bound):
    before = contract.verify(bound)
    bound.monthly["fwd_mid"] = [0.9, -0.8, 0.7]
    assert contract.verify(bound) == before


def test_missing_financial_contract_rejects_old_cache(financial):
    financial.meta["fundamental_methodology_version"] = fundamentals.FUNDAMENTAL_METHODOLOGY_VERSION
    with pytest.raises(RuntimeError, match="lacks a versioned replay contract"):
        contract.verify(financial)


def test_price_only_synthetic_panels_skip_but_execution_requires_binding(price_only):
    assert contract.verify(price_only)["status"] == "SKIPPED_PRICE_ONLY_PANEL"
    with pytest.raises(RuntimeError):
        contract.verify(price_only, require_financial=True)


@pytest.mark.parametrize("change", ["empty", "null_run", "blank_run", "missing_column"])
def test_raw_ledger_provenance_is_required(raw, change):
    if change == "empty":
        raw = raw.iloc[:0]
    elif change == "missing_column":
        raw = raw.drop(columns="available_at")
    else:
        raw.loc[0, "quality_run_id"] = None if change == "null_run" else " "
    with pytest.raises(ValueError):
        contract.materialize(raw, verbose=False)


@pytest.mark.parametrize("change", ["hash", "receipt", "run_counts", "ledger_hash"])
def test_contract_structure_is_validated_even_if_outer_hash_is_recomputed(bound, change):
    meta = bound.meta[contract.META_KEY]
    if change == "hash":
        meta["sha256"] = "f" * 64
    else:
        if change == "receipt":
            meta["materialization_receipt_sha256"] = "f" * 64
        elif change == "run_counts":
            meta["ledger"]["rows_by_quality_run"]["synthetic-certified-run-a"] = 999
        else:
            meta["ledger"]["ledger_sha256"] = "not-a-sha"
        meta["sha256"] = contract._digest({k: v for k, v in meta.items() if k != "sha256"})
    with pytest.raises(RuntimeError):
        contract.verify(bound)


def test_execution_loader_fails_closed_without_touching_old_cache(financial, tmp_path, monkeypatch):
    path = tmp_path / "old-panel.pkl"
    original = pickle.dumps(financial)
    path.write_bytes(original)
    monkeypatch.setattr(run, "PANEL_CACHE", path)
    with pytest.raises(SystemExit, match="재무 TTM"):
        run._load()
    assert path.read_bytes() == original


def test_activation_rejects_unbound_financial_panel_before_write(financial, tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setattr(run, "CACHE", cache)
    monkeypatch.setattr(run, "PANEL_CACHE", cache / "panel.pkl")
    monkeypatch.setattr(panels, "verify_return_roles", lambda p: None)
    monkeypatch.setattr(panels, "verify_asset_identity", lambda p: {"asset_identity_digest": "a" * 64})
    with pytest.raises(RuntimeError, match="lacks a versioned replay contract"):
        run._activate_panel_cache(financial)
    assert not list(cache.glob("*.pkl"))


def test_scoped_metadata_preserves_origin_without_mutating_it(bound, monkeypatch):
    original = deepcopy(bound.meta[contract.META_KEY])
    monkeypatch.setattr(panels, "bind_asset_identity", lambda p: None)
    monkeypatch.setattr(panels, "forward_returns", lambda p, **k: pd.Series(0.0, index=p.monthly.index))
    scoped = run._rebuild_scoped_panel(bound, bound.monthly.iloc[:2])
    assert scoped.meta[contract.META_KEY] == original
    scoped.meta[contract.META_KEY]["ledger"]["row_count"] = -1
    assert bound.meta[contract.META_KEY] == original
    contract.verify(bound)
