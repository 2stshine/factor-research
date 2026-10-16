"""Synthetic isolated-repair tests; every input/output is in pytest tmp_path.

No live DB, historical return artifact, Gold, campaign, or real cache is read.
The legacy replay in orchestration tests is explicitly a synthetic stub.
"""
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
import pickle
from types import SimpleNamespace

import pandas as pd
import pytest

from engine import fundamental_contract, fundamentals, panel, silver
from scripts import repair_fundamental_panel as repair


@pytest.fixture(autouse=True)
def no_live_access(monkeypatch):
    monkeypatch.setattr(silver, "connect", lambda *a, **k: pytest.fail("Live DB access forbidden"))
    monkeypatch.setattr(repair.subprocess, "run", lambda *a, **k: pytest.fail("CLI access forbidden"))
    monkeypatch.setattr(repair.subprocess, "check_output", lambda *a, **k: pytest.fail("External process forbidden"))


@pytest.fixture
def raw():
    ends = pd.to_datetime(["2015-03-31", "2015-06-30", "2015-09-30", "2015-12-31"])
    return pd.DataFrame({
        "asset_id": [1] * 4, "period_end": ends,
        "fiscal_period": ["Q1", "Q2", "Q3", "Q4"], "fs_type": ["CFS"] * 4,
        "statement_type": ["IS"] * 4, "metric": ["revenue"] * 4,
        "available_date": ends + pd.Timedelta(days=45),
        "available_at": (ends + pd.Timedelta(days=45)).tz_localize("UTC"),
        "value": ["10", "20", "30", "40"],
        "revision_key": ["q1", "q2", "q3", "q4"],
        "quality_run_id": ["synthetic-quality-run"] * 4,
    })


def save_extract(directory, rows):
    directory.mkdir()
    parquet = directory / "certified-financial-rows.parquet"
    rows.to_parquet(parquet, index=False)
    receipt = {
        "schema_version": "certified-financial-ledger-extract-v1",
        "query_sha256": hashlib.sha256(silver.FUNDAMENTAL_SQL.encode()).hexdigest(),
        "query": silver.FUNDAMENTAL_SQL, "read_only": True, "isolation": "REPEATABLE_READ",
        "metrics": sorted(fundamentals.ALL_METRICS), "row_count": len(rows),
        "asset_count": int(rows.asset_id.nunique()),
        "quality_run_ids": sorted(rows.quality_run_id.unique()),
        "parquet_sha256": repair.file_sha(parquet),
    }
    (directory / "source-receipt.json").write_text(json.dumps(receipt))
    return receipt


@pytest.fixture
def setup(tmp_path, monkeypatch, raw):
    monkeypatch.setattr(repair, "ROOT", tmp_path)
    cache = tmp_path / ".cache"
    cache.mkdir()
    directory = cache / "financial-repair"
    save_extract(directory, raw)
    dates = pd.to_datetime(["2016-01-29", "2016-02-29", "2016-03-31"])
    monthly = pd.DataFrame({
        "asset_id": [1] * 3, "Code": ["000001"] * 3,
        "ym": dates.to_period("M"), "trade_date": dates,
        "adj_close": [100.0, 101.0, 102.0], "total_return_close": [100.0, 101.0, 102.0],
        "fwd_mid": [0.0, 0.0, 0.0], "revenue_ttm": [999.0] * 3,
        "available_date": pd.to_datetime(["2015-01-01"] * 3),
        "f_old_score": [42.0] * 3,
    })
    parent = panel.Panel(monthly, pd.Series(dtype="datetime64[ns]"), {
        "source": "SYNTHETIC", "return_contract_validation_evidence": {"synthetic": True},
        fundamental_contract.META_KEY: {"deliberately_obsolete": True},
    })
    parent_path = cache / "panel.pkl"
    original = pickle.dumps(parent)
    parent_path.write_bytes(original)
    calls = []
    monkeypatch.setattr(panel, "verify_return_roles", lambda p: calls.append("return_roles"))
    monkeypatch.setattr(panel, "verify_asset_identity", lambda p: calls.append("local_identity"))
    monkeypatch.setattr(silver, "verify_total_return_validation_evidence", lambda e: calls.append("return_evidence"))

    def legacy_replay(rows, *, verbose):
        pd.testing.assert_frame_equal(rows, raw)
        calls.append("legacy_same_ledger")
        result = fundamentals.materialize_pit(rows, verbose=False)
        result["revenue_ttm"] = 100.0
        return result

    monkeypatch.setattr(repair, "_legacy_materializer", lambda: SimpleNamespace(materialize_pit=legacy_replay))
    return SimpleNamespace(root=tmp_path, cache=cache, directory=directory, parent=parent,
                           parent_path=parent_path, original=original, calls=calls)


def test_rebuild_preserves_parent_and_nonfinancial_inputs_and_stays_inactive(setup):
    receipt = repair.rebuild(setup.directory, setup.parent_path)
    assert setup.parent_path.read_bytes() == setup.original
    assert receipt["parent_unchanged"] is True
    assert receipt["parent_sha256"] == hashlib.sha256(setup.original).hexdigest()
    assert receipt["status"] == "LOCAL_REPLAY_VERIFIED_LIVE_PRICE_IDENTITY_RECHECK_PENDING"
    assert receipt["activated"] is False
    assert receipt["default_cache_changed"] is False
    assert receipt["historical_backfill_applied"] is False
    assert receipt["real_factor_trials"] == 0
    assert receipt["oos_reveal"] is False
    assert receipt["gold_write"] is False
    assert receipt["full_parent_bytes_loaded_for_preservation"] is True
    assert receipt["oos_performance_evaluations"] == receipt["oos_performance_inspections"] == 0
    with (setup.directory / "panel.pkl").open("rb") as stream:
        actual = pickle.load(stream)
    fundamental_contract.verify(actual, require_financial=True)
    assert actual.monthly.revenue_ttm.tolist()[1:] == [100.0, 100.0]
    assert pd.isna(actual.monthly.revenue_ttm.iloc[0])
    assert "f_old_score" not in actual.monthly
    columns = ["asset_id", "Code", "ym", "trade_date", "adj_close", "total_return_close", "fwd_mid"]
    pd.testing.assert_frame_equal(actual.monthly[columns], setup.parent.monthly[columns])
    assert setup.calls == ["return_roles", "local_identity", "return_evidence", "return_roles", "local_identity", "legacy_same_ledger"]
    audit = json.loads((setup.directory / "input-change-audit.json").read_text())
    revenue = next(row for row in audit["changes"] if row["field"] == "revenue_ttm")
    assert revenue["changed_rows"] == 1
    assert revenue["finite_to_missing"] == 1
    assert all(row["field"] in fundamentals.PIT_FEATURES for row in audit["changes"])
    assert audit["return_evaluations"] == audit["gold_writes"] == 0
    assert "oos_reads" not in audit
    assert audit["full_parent_bytes_loaded_for_preservation"] is True
    assert audit["oos_performance_evaluations"] == audit["oos_performance_inspections"] == 0


@pytest.mark.parametrize("output", ["panel.pkl", "materialized-v2.pkl", "build-receipt.json", "input-change-audit.json"])
def test_existing_repair_output_is_never_overwritten(setup, output):
    path = setup.directory / output
    path.write_bytes(b"existing output")
    with pytest.raises(ValueError, match="Refusing to replace"):
        repair.rebuild(setup.directory, setup.parent_path)
    assert path.read_bytes() == b"existing output"
    assert setup.parent_path.read_bytes() == setup.original
    assert setup.calls == []


def test_parent_directory_is_not_a_repair_destination(setup):
    with pytest.raises(ValueError, match="separate direct cache child"):
        repair.rebuild(setup.cache, setup.parent_path)
    assert setup.parent_path.read_bytes() == setup.original


def test_parent_change_during_rebuild_aborts_activation_and_final_output(setup, monkeypatch):
    original_compare = repair.compare_financial_inputs

    def mutate_parent(*args, **kwargs):
        setup.parent_path.write_bytes(b"external concurrent parent change")
        return original_compare(*args, **kwargs)

    monkeypatch.setattr(repair, "compare_financial_inputs", mutate_parent)
    with pytest.raises(ValueError, match="Parent panel changed"):
        repair.rebuild(setup.directory, setup.parent_path)
    assert not (setup.directory / "panel.pkl").exists()
    assert not (setup.directory / "build-receipt.json").exists()


@pytest.mark.parametrize("change", ["parquet", "query", "query_text", "metrics", "read_only", "row_count",
                                    "schema", "asset_count", "run_ids", "isolation", "truthy_read_only"])
def test_extract_mismatch_rejects_before_loading_parent(setup, change):
    receipt_path = setup.directory / "source-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    if change == "parquet":
        with (setup.directory / "certified-financial-rows.parquet").open("ab") as stream:
            stream.write(b"changed")
    else:
        key, value = {
            "query": ("query_sha256", "f" * 64), "metrics": ("metrics", ["revenue"]),
            "read_only": ("read_only", False), "row_count": ("row_count", 999),
            "query_text": ("query", "SELECT * FROM another_table"),
            "schema": ("schema_version", "unrecognized-schema"), "asset_count": ("asset_count", 999),
            "run_ids": ("quality_run_ids", ["not-the-run"]), "isolation": ("isolation", "READ_COMMITTED"),
            "truthy_read_only": ("read_only", "false"),
        }[change]
        receipt[key] = value
        receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        repair.rebuild(setup.directory, setup.parent_path)
    assert setup.calls == []
    assert setup.parent_path.read_bytes() == setup.original


def test_input_audit_ignores_downstream_labels_and_outside_window(monkeypatch):
    dates = pd.to_datetime(["2014-12-31", "2015-01-31", "2023-06-30", "2023-07-31"])
    before = pd.DataFrame({"asset_id": [1] * 4, "ym": dates.to_period("M")})
    for feature in fundamentals.PIT_FEATURES:
        before[feature] = 10.0
    before["fwd_mid"] = 0.0
    after = before.copy()
    after["revenue_ttm"] = [100.0, None, 20.0, 100.0]
    after["fwd_mid"] = [999.0] * 4
    original_numeric = pd.to_numeric

    def only_scoped_financials(values, **kwargs):
        assert values.name in fundamentals.PIT_FEATURES
        assert len(values) == 2
        return original_numeric(values, **kwargs)

    monkeypatch.setattr(pd, "to_numeric", only_scoped_financials)
    report = repair.compare_financial_inputs(before, after)
    revenue = next(row for row in report if row["field"] == "revenue_ttm")
    assert revenue == {"field": "revenue_ttm", "rows_in_scope": 2, "changed_rows": 2,
                       "assets_with_changes": 1, "finite_to_missing": 1,
                       "missing_to_finite": 0, "both_finite_changed": 1}
    assert sum(row["changed_rows"] for row in report) == 2


def test_input_audit_rejects_reversed_date_window(raw):
    frame = pd.DataFrame({"asset_id": [1], "ym": pd.period_range("2016-01", periods=1, freq="M")})
    with pytest.raises(ValueError, match="end precedes"):
        repair.compare_financial_inputs(frame, frame, end_month="2014-12")


class FakeSource:
    def __init__(self, *, read_only="on", isolation="repeatable read"):
        self.read_only, self.isolation, self.queries = read_only, isolation, []

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        self.queries.append((query, params))

    def fetchone(self):
        return (self.isolation if "isolation" in self.queries[-1][0] else self.read_only,)


def test_fetch_only_extracts_financials_and_preserves_decimal_text(tmp_path, monkeypatch, raw):
    monkeypatch.setattr(repair, "ROOT", tmp_path)
    (tmp_path / ".cache").mkdir()
    source = FakeSource()
    rows = raw.copy()
    rows["value"] = [Decimal("10000000000000000.123456789")] * 4
    calls = []

    @contextmanager
    def connect(profile):
        assert profile is None
        yield source

    def load(conn, metrics):
        assert conn is source
        assert metrics == sorted(fundamentals.ALL_METRICS)
        calls.append("financial-ledger-only")
        return rows

    monkeypatch.setattr(repair, "task_connection", connect)
    monkeypatch.setattr(silver, "load_fundamentals", load)
    destination = tmp_path / ".cache" / "new-extract"
    repair.fetch(destination)
    extracted, receipt = repair._load_rows(destination)
    assert calls == ["financial-ledger-only"]
    assert extracted.value.tolist() == ["10000000000000000.123456789"] * 4
    assert receipt["historical_original_filing_values_verified_by_this_extraction"] is False
    assert receipt["read_only"] is True
    assert receipt["isolation"] == "REPEATABLE_READ"
    assert source.queries[:2] == [("SHOW transaction_read_only", None), ("SHOW transaction_isolation", None)]
    assert receipt["return_evaluations"] == receipt["oos_reads"] == receipt["gold_writes"] == 0


@pytest.mark.parametrize("read_only,isolation,error", [("off", "repeatable read", "read-only"),
                                                       ("on", "read committed", "repeatable-read")])
def test_fetch_checks_live_transaction_before_ledger_query(tmp_path, monkeypatch, read_only, isolation, error):
    monkeypatch.setattr(repair, "ROOT", tmp_path)
    (tmp_path / ".cache").mkdir()
    source = FakeSource(read_only=read_only, isolation=isolation)

    @contextmanager
    def connect(profile):
        yield source

    monkeypatch.setattr(repair, "task_connection", connect)
    monkeypatch.setattr(silver, "load_fundamentals", lambda *a, **k: pytest.fail("Unsafe ledger query"))
    destination = tmp_path / ".cache" / "new-extract"
    with pytest.raises(ValueError, match=error):
        repair.fetch(destination)
    assert not (destination / "source-receipt.json").exists()
    assert not (destination / "certified-financial-rows.parquet").exists()


@pytest.mark.parametrize("kind", ["existing", "outside", "nested", "symlink_cache"])
def test_fetch_invalid_destination_cannot_connect(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(repair, "ROOT", tmp_path)
    cache = tmp_path / ".cache"
    if kind == "symlink_cache":
        actual = tmp_path / "actual"
        actual.mkdir()
        cache.symlink_to(actual, target_is_directory=True)
    else:
        cache.mkdir()
    destination = cache / "new"
    if kind == "existing":
        destination.mkdir()
    elif kind == "outside":
        destination = tmp_path / "outside"
    elif kind == "nested":
        destination = cache / "nested" / "new"
    monkeypatch.setattr(repair, "task_connection", lambda *a, **k: pytest.fail("Invalid path connected"))
    with pytest.raises(ValueError):
        repair.fetch(destination)


def test_wrong_legacy_source_is_not_executed(monkeypatch):
    monkeypatch.setattr(repair.subprocess, "check_output", lambda *a, **k: b"raise AssertionError('must not execute')")
    with pytest.raises(ValueError, match="Legacy implementation differs"):
        repair._legacy_materializer()


def test_exact_reviewed_legacy_source_hash_is_required(monkeypatch):
    body = b"def materialize_pit(rows, verbose=False):\n    return rows\n"
    monkeypatch.setattr(repair.subprocess, "check_output", lambda *a, **k: body)
    monkeypatch.setattr(repair, "LEGACY_SOURCE_SHA256", hashlib.sha256(body).hexdigest())
    assert repair._legacy_materializer().materialize_pit("synthetic") == "synthetic"
