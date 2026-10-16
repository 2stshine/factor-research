import json

import pytest

from engine import reference_snapshot_strategy as snapshot
from scripts import report_reference_snapshot as reporter, run_reference_snapshot as runner
from tests.test_reference_snapshot_strategy import fixture


def test_metrics_include_initial_nav_in_drawdown():
    result = reporter.metrics([-.2, .1])
    assert result["cumulative_return"] == pytest.approx(-.12)
    assert result["maximum_drawdown"] == pytest.approx(-.2)
    with pytest.raises(ValueError):
        reporter.metrics([-1.1])


def test_report_recomputes_every_variant_and_checks_checkpoints(tmp_path, monkeypatch):
    p, settings = fixture()
    m = {"snapshot_sha256": "a" * 64, "first_month": "2019-01", "last_signal_month": "2019-07",
         "fields": [{"field": "f_a"}, {"field": "f_b"}], "return_basis": "SOFTWARE_TEST_ONLY",
         "pit_status": "SYNTHETIC_FIXTURE"}
    monkeypatch.setattr(snapshot, "load_snapshot", lambda *a: (p, m, {"strategy_comparison": settings}))
    args = runner.parser().parse_args(["run", "--snapshot", str(tmp_path), "--output", str(tmp_path / "run"),
                                      "--first-month", "2019-05", "--last-month", "2019-06"])
    runner.run(args)
    report = reporter.report(tmp_path / "run", tmp_path)
    assert len(report["paths"]) == 12
    assert len(report["comparison"]) == 24
    assert sum(len(p["monthly"]) for v in report["paths"].values() for p in v["scenarios"].values()) == 48
    assert report["selected_model"] is None
    assert "거래금액 기준 비용" in (tmp_path / "run/report.html").read_text()
    file = tmp_path / "run/months/2019-05.json"
    bad = json.loads(file.read_text())
    bad["fold"]["train_rows"] += 1
    file.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="checkpoint"):
        reporter.report(tmp_path / "run", tmp_path)


def test_legacy_fixed_cost_report_remains_readable(tmp_path, monkeypatch):
    p, settings = fixture()
    m = {"snapshot_sha256": "a" * 64, "first_month": "2019-01", "last_signal_month": "2019-07",
         "fields": [{"field": "f_a"}, {"field": "f_b"}], "return_basis": "SOFTWARE_TEST_ONLY", "pit_status": "SYNTHETIC_FIXTURE"}
    monkeypatch.setattr(snapshot, "load_snapshot", lambda *a: (p, m, {"strategy_comparison": settings}))
    args = runner.parser().parse_args(["run", "--snapshot", str(tmp_path), "--output", str(tmp_path / "run"),
                                      "--first-month", "2019-05", "--last-month", "2019-06"])
    result = runner.run(args)
    result.pop("primary_result")
    (tmp_path / "run/result.json").write_text(json.dumps(result))
    report = reporter.report(tmp_path / "run", tmp_path)
    assert len(report["rows"]) == 12
    assert len(report["monthly_scenario_series"]) == 48
    assert "2개 후보" in (tmp_path / "run/report.html").read_text()


def test_primary_turnover_tampering_is_rejected(tmp_path, monkeypatch):
    p, settings = fixture()
    m = {"snapshot_sha256": "a" * 64, "first_month": "2019-01", "last_signal_month": "2019-07",
         "fields": [{"field": "f_a"}, {"field": "f_b"}], "return_basis": "SOFTWARE_TEST_ONLY", "pit_status": "SYNTHETIC_FIXTURE"}
    monkeypatch.setattr(snapshot, "load_snapshot", lambda *a: (p, m, {"strategy_comparison": settings}))
    args = runner.parser().parse_args(["run", "--snapshot", str(tmp_path), "--output", str(tmp_path / "run"),
                                      "--first-month", "2019-05", "--last-month", "2019-06"])
    runner.run(args)
    (tmp_path / "run/turnover-result.json").write_text('{}')
    with pytest.raises(ValueError, match="accounting changed"):
        reporter.report(tmp_path / "run", tmp_path)


def test_worker_uses_same_chronological_kernel(tmp_path, monkeypatch):
    p, settings = fixture()
    m = {"snapshot_sha256": "a" * 64, "fields": [{"field": "f_a"}, {"field": "f_b"}]}
    monkeypatch.setattr(snapshot, "load_snapshot", lambda *a: (p, m, {"strategy_comparison": settings}))
    runner._worker_init(tmp_path, "a" * 64)
    assert runner._worker_month("2019-05", 50) == snapshot.run_month(p, ["f_a", "f_b"], settings, "2019-05", round_trip_bps=50)
    with pytest.raises(ValueError, match="identity"):
        runner._worker_init(tmp_path, "b" * 64)
