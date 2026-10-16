"""Synthetic orchestration checks; fake rows do NOT establish real SQL parity.

Every filesystem operation is confined to tmp_path. No real connection, default
cache, factor evaluation, OOS access, or Gold publication is exercised.
"""
from datetime import date
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import research_panel_query_parity as parity_module
from scripts import research_panel_refresh as refresh_module


PATHS = {"PANEL_CACHE": "panel.pkl", "PANEL_ARCHIVE": "panels",
         "TRIAL_DB": "trials.sqlite3", "PARITY_CHECKPOINT_ROOT": "implementation-parity-checkpoints",
         "GOLD_SIGNAL_CACHE_ROOT": "gold-signals"}


class FakeSource:
    def __init__(self, *, read_only="on", isolation="repeatable read", autocommit=False, second_rows=None):
        row = (1, "005930", date(2024, 1, 31), Decimal("100.25"))
        self.results = [[row], [row] if second_rows is None else second_rows]
        self.mode, self.isolation = read_only, isolation
        self.autocommit = autocommit
        self.description = [SimpleNamespace(name=name) for name in ("asset_id", "Code", "trade_date", "close")]
        self.data_queries, self.connect_calls = [], []

    def connect(self, *, read_only):
        self.connect_calls.append(read_only)
        assert read_only is True
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self

    def execute(self, query, params=None):
        self.last_query = query
        if query.startswith(("SHOW ", "SET LOCAL statement_timeout")):
            return
        assert query.lstrip().startswith("WITH certified AS (")
        assert query.count("AND p.asset_id = ANY(%s)") == 1
        assert params == ([1],)
        self.data_queries.append(query)

    def fetchone(self):
        return (self.mode if self.last_query == "SHOW transaction_read_only" else self.isolation,)

    def fetchmany(self, count):
        assert count == 5001
        return self.results[len(self.data_queries) - 1]


class FakeRunner:
    def __init__(self, cache, original, *, fail=False):
        self.CACHE, self.original, self.fail, self.calls = cache, original, fail, []
        for key, child in PATHS.items():
            setattr(self, key, cache / child)

    def __getattr__(self, name):
        raise AssertionError(f"Unexpected runner hook or attribute: {name}")

    def cmd_build(self, argument):
        assert argument is None
        self.calls.append("cmd_build")
        assert refresh_module.silver.PRICE_SNAPSHOT_SQL != self.original
        assert Path(os.environ["CACHE_DIR"]) == self.CACHE
        timing = Path(os.environ["RESEARCH_TIMING_LOG"])
        assert timing.parent == self.CACHE
        if self.fail:
            raise RuntimeError("synthetic build failure")
        self.PANEL_CACHE.write_bytes(b"synthetic panel, not actual market data")
        timing.write_text("synthetic timing event\n")

    @staticmethod
    def _file_sha256(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh_module, "ROOT", tmp_path)
    monkeypatch.setattr(refresh_module.silver, "connect", lambda **kwargs: pytest.fail("real source touched"))
    monkeypatch.setenv("CACHE_DIR", "previous-cache-setting")
    monkeypatch.setenv("RESEARCH_TIMING_LOG", "previous-timing-setting")
    default = tmp_path / ".cache"
    default.mkdir()
    sentinel = default / "panel.pkl"
    sentinel.write_bytes(b"default cache must remain unchanged")
    record = tmp_path / "synthetic-parity.json"
    parity_module.probe([1], record, connect=FakeSource().connect)
    return SimpleNamespace(root=tmp_path, cache=default / "isolated", record=record,
                           sentinel=sentinel, original=refresh_module.silver.PRICE_SNAPSHOT_SQL)


def assert_restored(setup):
    assert refresh_module.silver.PRICE_SNAPSHOT_SQL == setup.original
    assert os.environ["CACHE_DIR"] == "previous-cache-setting"
    assert os.environ["RESEARCH_TIMING_LOG"] == "previous-timing-setting"
    assert setup.sentinel.read_bytes() == b"default cache must remain unchanged"


@pytest.mark.parametrize("kind", ["default", "existing", "outside", "nested", "dangling_symlink"])
def test_invalid_cache_paths_fail_before_runner_or_writes(setup, kind):
    paths = {"default": setup.cache.parent, "existing": setup.cache,
             "outside": setup.root / "outside", "nested": setup.cache / "nested",
             "dangling_symlink": setup.cache}
    if kind == "existing":
        setup.cache.mkdir()
    if kind == "dangling_symlink":
        setup.cache.symlink_to(setup.cache.parent / "new-target", target_is_directory=True)
    runner = FakeRunner(paths[kind], setup.original)
    with pytest.raises(ValueError):
        refresh_module.refresh(paths[kind], setup.record, runner=runner)
    assert runner.calls == []
    assert_restored(setup)
    assert not (setup.cache.parent / "new-target").exists()
    assert not (paths[kind] / "input-query-contract.json").exists()


def test_symlinked_cache_root_cannot_redirect_build_outside_repository(setup, monkeypatch):
    project, external = setup.root / "project", setup.root / "external"
    project.mkdir()
    external.mkdir()
    (project / ".cache").symlink_to(external, target_is_directory=True)
    monkeypatch.setattr(refresh_module, "ROOT", project)
    candidate = project / ".cache" / "isolated"
    runner = FakeRunner(candidate, setup.original)
    with pytest.raises(ValueError):
        refresh_module.refresh(candidate, setup.record, runner=runner)
    assert runner.calls == [] and list(external.iterdir()) == []
    assert_restored(setup)


@pytest.mark.parametrize("key", ["CACHE", *PATHS])
def test_every_runner_cache_global_is_bound_before_build(setup, key):
    runner = FakeRunner(setup.cache, setup.original)
    setattr(runner, key, setup.root / "wrong-location")
    with pytest.raises(ValueError):
        refresh_module.refresh(setup.cache, setup.record, runner=runner)
    assert runner.calls == [] and not setup.cache.exists()
    assert_restored(setup)


@pytest.mark.parametrize("field,value", [
    ("schema_version", "wrong"), ("parity_pass", False), ("read_only", False),
    ("same_database_snapshot", False), ("exact_columns_and_row_values_equal", False),
    ("requested_cohort_observed", False), ("scope", "UNIVERSE_CERTIFIED"),
    ("original_query_sha256", "0" * 64), ("optimized_query_sha256", "0" * 64),
    ("query_sha256", ["0" * 64, "0" * 64]), ("queries", ["SELECT 1", "SELECT 1"]),
    ("rows", [0, 0]), ("rows", [1, 2]), ("rows", [True, True]), ("rows", [5001, 5001]),
    ("observed_asset_ids", [[2], [2]]), ("observed_asset_ids", [[True], [True]]),
    ("observed_asset_ids", [[1.0], [1.0]]), ("asset_ids", [1, 1]),
    ("result_sha256", ["0" * 64, "1" * 64]), ("result_sha256", ["z" * 64, "z" * 64]),
])
def test_inconsistent_parity_records_fail_before_build(setup, field, value):
    evidence = json.loads(setup.record.read_text())
    evidence[field] = value
    setup.record.write_text(json.dumps(evidence))
    runner = FakeRunner(setup.cache, setup.original)
    with pytest.raises(ValueError):
        refresh_module.refresh(setup.cache, setup.record, runner=runner)
    assert runner.calls == [] and not setup.cache.exists()
    assert_restored(setup)


def test_changed_source_query_fails_before_runner(setup, monkeypatch):
    monkeypatch.setattr(refresh_module.silver, "PRICE_SNAPSHOT_SQL", setup.original + " ")
    runner = FakeRunner(setup.cache, setup.original)
    with pytest.raises(ValueError):
        refresh_module.refresh(setup.cache, setup.record, runner=runner)
    assert runner.calls == [] and not setup.cache.exists()
    assert os.environ["CACHE_DIR"] == "previous-cache-setting"
    assert os.environ["RESEARCH_TIMING_LOG"] == "previous-timing-setting"


def test_claimed_distinct_cohort_cannot_exceed_result_rows(setup):
    evidence = json.loads(setup.record.read_text())
    evidence.update(asset_ids=[1, 2], observed_asset_ids=[[1, 2], [1, 2]])
    setup.record.write_text(json.dumps(evidence))
    runner = FakeRunner(setup.cache, setup.original)
    with pytest.raises(ValueError):
        refresh_module.refresh(setup.cache, setup.record, runner=runner)
    assert runner.calls == [] and not setup.cache.exists()
    assert_restored(setup)


@pytest.mark.parametrize("fail", [False, True])
def test_build_restores_sql_environment_and_keeps_default_cache_intact(setup, fail):
    runner = FakeRunner(setup.cache, setup.original, fail=fail)
    if fail:
        with pytest.raises(RuntimeError, match="synthetic build failure"):
            refresh_module.refresh(setup.cache, setup.record, runner=runner)
    else:
        refresh_module.refresh(setup.cache, setup.record, runner=runner)
    assert runner.calls == ["cmd_build"]
    assert_restored(setup)
    contract = json.loads((setup.cache / "input-query-contract.json").read_text())
    assert contract["cache_dir"] == str(setup.cache)
    assert contract["parity_scope"] == "EXPLICIT_COHORT_ONLY"
    assert contract["real_factor_trials"] == 0 and contract["gold_write"] is False
    assert contract["default_cache_changed"] is False
    receipt_path = setup.cache / "build-receipt.json"
    assert receipt_path.exists() is (not fail)
    if not fail:
        receipt = json.loads(receipt_path.read_text())
        assert receipt["status"] == "BUILD_COMPLETED_IDENTITY_REAUDIT_PENDING"
        assert receipt["panel_sha256"] == runner._file_sha256(runner.PANEL_CACHE)
        assert receipt["real_factor_trials"] == 0 and receipt["gold_write"] is False


def test_previously_absent_environment_variables_remain_absent(setup, monkeypatch):
    for key in ("CACHE_DIR", "RESEARCH_TIMING_LOG"):
        monkeypatch.delenv(key)
    refresh_module.refresh(setup.cache, setup.record, runner=FakeRunner(setup.cache, setup.original))
    assert "CACHE_DIR" not in os.environ and "RESEARCH_TIMING_LOG" not in os.environ
    assert refresh_module.silver.PRICE_SNAPSHOT_SQL == setup.original


@pytest.mark.parametrize("kwargs", [{"read_only": "off"}, {"isolation": "read committed"}, {"autocommit": True}])
def test_fake_probe_requires_read_only_repeatable_snapshot_before_queries(tmp_path, kwargs):
    source, output = FakeSource(**kwargs), tmp_path / "parity.json"
    with pytest.raises(ValueError):
        parity_module.probe([1], output, connect=source.connect)
    assert source.connect_calls == [True]
    assert source.data_queries == [] and not output.exists()


def test_fake_probe_records_only_explicit_cohort_and_mismatch_fails(tmp_path):
    source, output = FakeSource(second_rows=[]), tmp_path / "mismatch.json"
    with pytest.raises(SystemExit):
        parity_module.probe([1], output, connect=source.connect)
    evidence = json.loads(output.read_text())
    assert source.connect_calls == [True] and len(source.data_queries) == 2
    assert evidence["asset_ids"] == [1] and evidence["observed_asset_ids"] == [[1], []]
    assert evidence["read_only"] is True and evidence["same_database_snapshot"] is True
    assert evidence["parity_pass"] is False and evidence["requested_cohort_observed"] is False
    assert evidence["scope"] == "EXPLICIT_COHORT_INPUT_PARITY_NOT_UNIVERSE_OR_PERFORMANCE_CERTIFICATION"
    assert evidence["raw_values_in_report"] is False
    assert evidence["factor_trials"] == 0 and evidence["gold_write"] is False


def test_equal_python_values_with_different_serializations_cannot_pass_hash_contract(tmp_path):
    row = (1, "005930", date(2024, 1, 31), Decimal("100.250"))
    source, output = FakeSource(second_rows=[row]), tmp_path / "hash-mismatch.json"
    assert source.results[0] == source.results[1]
    with pytest.raises(SystemExit):
        parity_module.probe([1], output, connect=source.connect)
    evidence = json.loads(output.read_text())
    assert evidence["result_sha256"][0] != evidence["result_sha256"][1]
    assert evidence["parity_pass"] is False
