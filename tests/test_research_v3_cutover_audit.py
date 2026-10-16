"""Adversarial v3 cutover guards. Only synthetic pointers/mocks; no DB/results."""
import importlib
import json
import sys

import pytest

from engine import research_transition_guard as guard


@pytest.fixture
def active(tmp_path, monkeypatch):
    policy = tmp_path / "research/active-generation.json"
    policy.parent.mkdir()
    policy.write_text(json.dumps({"generation_id":"reference-factor-v3", "approved_factors":[]}))
    monkeypatch.setattr(guard, "ACTIVE_POLICY", policy)
    return policy


def forbidden(*args, **kwargs):
    raise AssertionError("Cutover must reject before cache/data/DB/legacy execution")


def test_named_monthly_gold_factors_cannot_bypass_empty_v3_library(active, monkeypatch):
    from strategies import gold_signals
    monkeypatch.setattr(gold_signals, "_locate", forbidden)
    with pytest.raises(ValueError, match="archived"):
        gold_signals.load_signed(("legacy_named_factor",))


def test_legacy_fallback_tuple_never_wins_over_empty_new_generation(active, monkeypatch):
    from strategies import gold
    monkeypatch.setattr(gold, "_newest_generation", forbidden)
    assert gold.approved_factors(default=("old_hardcoded_factor",)) == ()


def test_gold_refresh_blocked_before_connection(active, monkeypatch):
    from strategies import gold
    monkeypatch.setattr(gold.silver, "connect", forbidden)
    with pytest.raises(ValueError, match="archived"):
        gold.refresh(verbose=False)


def test_explicit_daily_factor_names_cannot_bypass_cutover(active, monkeypatch):
    from strategies import daily_factors
    monkeypatch.setattr(daily_factors, "_load_inputs", forbidden)
    with pytest.raises(ValueError, match="archived"):
        daily_factors.build_cache(("realized_volatility_252d",), verbose=False)


def test_existing_daily_factor_cache_cannot_be_read_after_cutover(active, tmp_path, monkeypatch):
    from strategies import daily_factors
    cache = tmp_path / "synthetic-daily.parquet"
    cache.write_bytes(b"not actual research data")
    monkeypatch.setattr(daily_factors, "CACHE", cache)
    monkeypatch.setattr(daily_factors.pd, "read_parquet", forbidden)
    with pytest.raises(ValueError, match="archived"):
        daily_factors.load_daily_factors()


def test_direct_bootstrap_blocks_before_writable_connection(active, monkeypatch):
    from scripts import run
    monkeypatch.setattr(run.silver, "connect", forbidden)
    with pytest.raises(ValueError, match="read-only"):
        run.bootstrap_gold_signal_cache()


def test_low_level_gold_generation_bind_cannot_update_metadata(active):
    from engine import silver
    class Connection:
        cursor = staticmethod(forbidden)
    with pytest.raises(ValueError, match="read-only"):
        silver.bind_gold_generation(Connection(), "a" * 64)


@pytest.mark.parametrize("method", ["publish", "upsert_approved_metadata_atomic"])
def test_metadata_writers_reject_before_cursor_or_payload_execution(active, method):
    from engine import publish
    class Connection:
        cursor = staticmethod(forbidden)
    rows = [{"factor_key":"synthetic_old", "status":"APPROVED"}]
    with pytest.raises(ValueError, match="read-only"):
        if method == "publish":
            publish.publish(Connection(), rows, apply=True)
        else:
            publish.upsert_approved_metadata_atomic(Connection(), rows)


@pytest.mark.parametrize("command,args", [
    ("campaign-publish", ["--campaign","synthetic"]),
    ("campaign-reconcile-gold-batch", ["--campaign","synthetic"]),
    ("campaign-reveal", ["--campaign","synthetic"]),
    ("gold-cache-bootstrap", []),
])
def test_explicit_legacy_cli_never_enables_gold_writes(active, monkeypatch, command, args):
    from scripts import research
    monkeypatch.setattr(sys, "argv", ["research.py", "--legacy", command, *args])
    monkeypatch.setattr(research.run.silver, "connect", forbidden)
    monkeypatch.setattr(research.run, "_load", forbidden)
    with pytest.raises(ValueError, match="read-only"):
        research.main()


def test_run_publish_legacy_flag_is_not_an_escape_hatch(active, monkeypatch):
    from scripts import run
    monkeypatch.setattr(sys, "argv", ["run.py", "--legacy", "publish", "--apply"])
    monkeypatch.setattr(run, "cmd_publish", forbidden)
    with pytest.raises(ValueError, match="read-only"):
        run.main()


@pytest.mark.parametrize("module_name", ["run_backtest", "evaluate"])
def test_strategy_entrypoints_block_even_explicit_old_factor_config(active, monkeypatch, module_name):
    module = importlib.import_module("strategies." + module_name)
    monkeypatch.setattr(module.data, "load_panel", forbidden)
    with pytest.raises(ValueError, match="archived"):
        module.main(object())


def test_strategy_default_rechecks_generation_after_module_was_imported(active, monkeypatch):
    # A long-running Python process can import the old config before cutover.
    # Reproduce that state using a sentinel list, without reading old caches.
    from strategies import config, gold
    real_loader = gold.approved_factors
    monkeypatch.setattr(gold, "approved_factors", lambda default=(): ("synthetic_pre_cutover",))
    importlib.reload(config)
    monkeypatch.setattr(gold, "approved_factors", real_loader)
    try:
        assert config.StrategyConfig().factors == ()
    finally:
        importlib.reload(config)


@pytest.mark.parametrize("generation_id", ["reference-factor-v3", "reference-factor-v3-next"])
def test_missing_pointer_in_initialized_workspace_does_not_restore_legacy(active, generation_id):
    (active.parent / "generations" / generation_id).mkdir(parents=True)
    active.unlink()
    with pytest.raises(ValueError, match="missing"):
        guard.require_legacy_gold_write("synthetic")


@pytest.mark.parametrize("text", ["{}", "[]", "not-json"])
def test_malformed_pointer_cannot_enable_legacy_publishing(active, text):
    active.write_text(text)
    with pytest.raises(ValueError):
        guard.require_legacy_cli("publish", explicit=True, writes_gold=True)
