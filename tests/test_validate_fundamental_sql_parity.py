"""Synthetic safety tests; no RDS, AWS, or new research execution."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from engine import fundamental_sql, fundamentals, silver
from scripts import validate_fundamental_sql_parity as cli


SECRET = "SYNTHETIC_CREDENTIAL_MUST_NEVER_APPEAR"


@pytest.fixture(autouse=True)
def forbid_live_connection(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Synthetic tests must not open a live authenticated connection")
    monkeypatch.setattr(cli, "task_connection", forbidden)


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    source = tmp_path / ".cache" / "financial-fixture"
    source.mkdir(parents=True)
    points = [("2016-06-30", "Q2", 10), ("2016-09-30", "Q3", 20),
              ("2016-12-31", "Q4", 30), ("2017-03-31", "Q1", 40)]
    rows = []
    # Input order is intentionally descending; outcome values are identical.
    for asset in (44, 33, 22, 11):
        for metric in ("net_income", "revenue"):
            for index, (period, label, value) in enumerate(points):
                rows.append({"asset_id": asset, "period_end": pd.Timestamp(period),
                             "fiscal_period": label, "fs_type": "CFS", "metric": metric,
                             "available_date": pd.Timestamp(period) + pd.Timedelta(days=45),
                             "value": str(value), "revision_key": f"original-{index}",
                             "quality_run_id": "synthetic-certified-quality"})
    rows.extend([
        {**rows[-1], "period_end": pd.Timestamp("2014-09-30"),
         "available_date": pd.Timestamp("2014-11-15"), "revision_key": "before-boundary"},
        {**rows[-1], "period_end": pd.Timestamp("2023-06-30"),
         "available_date": pd.Timestamp("2023-08-15"), "revision_key": "after-boundary"},
    ])
    frame = pd.DataFrame(rows)
    output = tmp_path / "research" / "v2" / "fixture-parity.json"
    state = SimpleNamespace(source=source, output=output, frame=frame,
                            calls=[], connection_count=0, profiles=[],
                            transaction_read_only="on", isolation="repeatable read",
                            connection_read_only=True, raise_on_connect=None,
                            alter_result=None)

    def save():
        parquet = source / "certified-financial-rows.parquet"
        state.frame.to_parquet(parquet, index=False)
        receipt = {
            "schema_version": "certified-financial-ledger-extract-v1", "read_only": True,
            "isolation": "REPEATABLE_READ", "parquet_sha256": cli.file_sha(parquet),
            "query_sha256": hashlib.sha256(silver.FUNDAMENTAL_SQL.encode()).hexdigest(),
            "metrics": sorted(fundamentals.ALL_METRICS), "row_count": len(state.frame),
            "asset_count": int(state.frame.asset_id.nunique()),
            "quality_run_ids": sorted(state.frame.quality_run_id.unique().tolist()),
        }
        (source / "source-receipt.json").write_text(json.dumps(receipt))
    state.save = save
    state.save()

    class Cursor:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def execute(self, query, params=None):
            state.calls.append((query, params))
            self.query = query
            self.params = params
            if query == fundamental_sql.FLOW_TTM_SQL:
                self.description = [SimpleNamespace(name=name) for name in (
                    "target_id", "asset_id", "as_of_date", "metric", "ttm_value",
                    "standalone_value", "contiguous_four_quarters", "recent_quarters",
                )]
        def fetchone(self):
            if self.query == "SHOW transaction_read_only":
                return (state.transaction_read_only,)
            if self.query == "SHOW transaction_isolation":
                return (state.isolation,)
            if self.query == "SELECT set_config('statement_timeout', '60s', true)":
                return ("60s",)
            pytest.fail("Unexpected database operation in fixture")
        def fetchall(self):
            assert self.query == fundamental_sql.FLOW_TTM_SQL
            targets = json.loads(self.params[1])
            result = [[target["target_id"], target["asset_id"], pd.Timestamp(target["as_of_date"]),
                       target["metric"], 100.0, 40.0, True, []] for target in targets]
            return state.alter_result(result) if state.alter_result else result

    @contextmanager
    def connection(profile):
        state.connection_count += 1
        state.profiles.append(profile)
        if state.raise_on_connect:
            raise state.raise_on_connect
        yield SimpleNamespace(read_only=state.connection_read_only, cursor=Cursor)
    monkeypatch.setattr(cli, "task_connection", connection)
    return state


def _read(fixture):
    return json.loads(fixture.output.read_text())


def test_fixed_selection_boundaries_read_only_timeout_and_exact_parameter_scope(fixture):
    python_hash = fundamentals.source_sha256()
    sql_hash = fundamental_sql.sql_sha256()
    assert cli.validate(fixture.source, fixture.output)
    report = _read(fixture)
    assert report["selected_asset_ids"] == [11, 22, 33]
    assert report["selected_raw_rows"] == 24
    assert report["as_of_dates"] == ["2017-06-30", "2020-06-30", "2023-06-30"]
    assert report["metrics"] == ["revenue", "net_income"]
    assert report["target_count"] == report["matched_targets"] == 18
    assert report["mismatched_targets"] == 0
    assert report["full_ledger_parity_claim"] is False
    assert report["historical_first_vintage_verified"] is False
    assert fixture.connection_count == 1
    assert fixture.profiles == ["teamalpha"]
    assert [query for query, _ in fixture.calls[:3]] == [
        "SHOW transaction_read_only", "SHOW transaction_isolation",
        "SELECT set_config('statement_timeout', '60s', true)",
    ]
    assert len(fixture.calls) == 4
    query, params = fixture.calls[-1]
    assert query == fundamental_sql.FLOW_TTM_SQL
    raw, targets = map(json.loads, params)
    assert len(raw) == 24
    assert {row["asset_id"] for row in raw} == {11, 22, 33}
    assert {row["metric"] for row in raw} == {"revenue", "net_income"}
    assert all(cli.START <= row["available_date"][:10] <= cli.END for row in raw)
    assert all(set(row) == {"asset_id", "period_end", "fiscal_period", "fs_type",
                            "available_date", "metric", "value", "revision_key"} for row in raw)
    assert [target["target_id"] for target in targets] == list(range(18))
    assert report["return_evaluations"] == report["oos_reads"] == report["gold_reads"] == report["gold_writes"] == 0
    assert fundamentals.source_sha256() == python_hash
    assert fundamental_sql.sql_sha256() == sql_hash


@pytest.mark.parametrize("attribute,value", [
    ("transaction_read_only", "off"),
    ("isolation", "read committed"),
    ("connection_read_only", False),
])
def test_unverified_or_writable_connections_never_run_parity_query(fixture, attribute, value):
    setattr(fixture, attribute, value)
    assert cli.validate(fixture.source, fixture.output) is False
    report = _read(fixture)
    assert report["status"] == "ERROR"
    assert report["error_stage"] == "LIVE_READ_ONLY_SQL"
    assert all(query != fundamental_sql.FLOW_TTM_SQL for query, _ in fixture.calls)


def test_authentication_exception_text_and_credentials_are_not_persisted_or_printed(fixture, capsys):
    fixture.raise_on_connect = RuntimeError(f"authentication failed: {SECRET}")
    assert cli.validate(fixture.source, fixture.output) is False
    report_text = fixture.output.read_text()
    captured = capsys.readouterr()
    assert SECRET not in report_text + captured.out + captured.err
    assert _read(fixture)["error_type"] == "RuntimeError"
    assert _read(fixture)["error_stage"] == "LIVE_READ_ONLY_SQL"
    assert "error_message" not in _read(fixture)
    assert fixture.calls == []


def test_source_hash_failure_stops_before_connection_without_exception_details(fixture):
    receipt_path = fixture.source / "source-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["parquet_sha256"] = SECRET
    receipt_path.write_text(json.dumps(receipt))
    assert cli.validate(fixture.source, fixture.output) is False
    assert _read(fixture)["error_stage"] == "SOURCE_PROVENANCE"
    assert SECRET not in fixture.output.read_text()
    assert fixture.connection_count == 0


def test_frozen_source_drift_stops_before_connection(fixture, monkeypatch):
    monkeypatch.setattr(cli, "EXPECTED_PYTHON_SHA", "0" * 64)
    assert cli.validate(fixture.source, fixture.output) is False
    assert _read(fixture)["error_stage"] == "SOURCE_PROVENANCE"
    assert fixture.connection_count == 0


def test_duplicate_raw_priorities_are_reported_not_deduplicated(fixture):
    first_selected = fixture.frame[fixture.frame.asset_id.eq(11)].iloc[[0]].copy()
    fixture.frame = pd.concat([fixture.frame, first_selected], ignore_index=True)
    fixture.save()
    assert cli.validate(fixture.source, fixture.output) is False
    report = _read(fixture)
    assert report["error_stage"] == "RAW_AMBIGUITY_CHECK"
    assert report["raw_priority_duplicate_groups"] == 1
    assert report["raw_priority_duplicate_rows"] == 2
    assert len(report["raw_priority_duplicate_sample"]) == 2
    assert fixture.connection_count == 0


def test_non_numeric_raw_values_stop_before_connection(fixture):
    index = fixture.frame[fixture.frame.asset_id.eq(11)].index[0]
    fixture.frame.loc[index, "value"] = "unparseable"
    fixture.save()
    assert cli.validate(fixture.source, fixture.output) is False
    assert _read(fixture)["raw_non_numeric_values"] == 1
    assert fixture.connection_count == 0


@pytest.mark.parametrize("corruption", ["drop_target", "wrong_asset", "reorder_targets"])
def test_sql_output_identity_cannot_be_substituted(fixture, corruption):
    def alter(rows):
        if corruption == "drop_target":
            return rows[:-1]
        if corruption == "wrong_asset":
            rows[0][1] = 9999
        if corruption == "reorder_targets":
            rows = list(reversed(rows))
        return rows
    fixture.alter_result = alter
    assert cli.validate(fixture.source, fixture.output) is False
    assert _read(fixture)["error_stage"] == "OUTPUT_COMPARISON"


@pytest.mark.parametrize("bad_ttm", [None, 101.0])
def test_null_or_value_mismatch_is_an_explicit_fail_not_pass(fixture, bad_ttm):
    def alter(rows):
        rows[0][4] = bad_ttm
        return rows
    fixture.alter_result = alter
    assert cli.validate(fixture.source, fixture.output) is False
    report = _read(fixture)
    assert report["status"] == "FAIL"
    assert report["matched_targets"] == 17
    assert report["mismatched_targets"] == 1


def test_existing_report_is_not_overwritten(fixture):
    fixture.output.parent.mkdir(parents=True)
    fixture.output.write_text("preserve previous report")
    with pytest.raises(ValueError, match="already exists"):
        cli.validate(fixture.source, fixture.output)
    assert fixture.output.read_text() == "preserve previous report"
    assert fixture.connection_count == 0


def test_output_outside_research_v2_is_rejected_before_any_source_access(fixture):
    with pytest.raises(ValueError, match="research/v2"):
        cli.validate(fixture.source, fixture.source / "outside.json")
    assert fixture.connection_count == 0


def test_cli_only_forwards_declared_arguments(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "validate", lambda source, output, **kwargs:
                        calls.append((source, output, kwargs)) or True)
    monkeypatch.setattr(sys, "argv", ["validate", "--source", str(tmp_path / "source"),
                                     "--output", str(tmp_path / "report"),
                                     "--aws-cli-profile", "synthetic-profile"])
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 0
    assert calls == [(str(tmp_path / "source"), str(tmp_path / "report"), {"profile": "synthetic-profile"})]


@pytest.mark.parametrize("arguments,expected_code", [(["--help"], 0), ([], 2)])
def test_import_and_cli_usage_do_not_require_credentials(arguments, expected_code, monkeypatch):
    monkeypatch.setenv("SILVER_DB_URL", SECRET)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", SECRET)
    result = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.validate_fundamental_sql_parity", *arguments],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        timeout=20, check=False,
    )
    assert result.returncode == expected_code
    assert SECRET not in result.stdout + result.stderr
    assert "--source" in result.stdout + result.stderr
    assert "--output" in result.stdout + result.stderr
