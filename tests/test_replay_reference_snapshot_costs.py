import json
import socket

import pytest

from engine import reference_snapshot_strategy as snapshot
from engine.research_generation import digest
from scripts import replay_reference_snapshot_costs as replay
from tests.test_reference_snapshot_strategy import fixture


def test_offline_replay_preserves_parent_and_targets(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: pytest.fail("No network allowed"))
    panel, settings = fixture()
    manifest = {"snapshot_sha256": "a" * 64, "pit_status": "SYNTHETIC_TEST_FIXTURE"}
    monkeypatch.setattr(snapshot, "load_snapshot", lambda *a: (panel, manifest, {}))
    parent = tmp_path / "parent"
    months = ["2019-05", "2019-06"]
    plan = {"signal_months": months, "snapshot_sha256": manifest["snapshot_sha256"], "round_trip_cost_scenario_bps": 50.}
    snapshot.write_json(parent / "plan.json", plan)
    folds = [snapshot.run_month(panel, ["f_a", "f_b"], settings, month, round_trip_bps=50) for month in months]
    for fold in folds:
        snapshot.write_json(parent / "months" / (fold["signal_month"] + ".json"),
                            {"plan_sha256": digest(plan), "fold_sha256": digest(fold), "fold": fold})
    snapshot.write_json(parent / "result.json", {"plan_sha256": digest(plan), "snapshot_sha256": manifest["snapshot_sha256"],
                                                  "summary": snapshot.summarize(folds)})
    before = {str(p): snapshot.file_hash(p) for p in parent.rglob("*.json")}
    monkeypatch.setattr(snapshot, "run_month", lambda *a, **kw: pytest.fail("No refit allowed"))
    args = replay.parser().parse_args(["--run", str(parent), "--snapshot", str(tmp_path), "--output", str(tmp_path / "replay")])
    result = replay.run(args)
    assert not result["targets_changed"] and not result["model_refitted"] and not result["source_refreshed"]
    assert result["audit"]["portfolio_scenario_months"] == 48
    assert result["audit"]["old_gross_outcomes_identical"]
    assert before == {str(p): snapshot.file_hash(p) for p in parent.rglob("*.json")}
    assert replay.run(args) == result
    checkpoint = parent / "months/2019-05.json"
    modified = json.loads(checkpoint.read_text())
    modified["fold"]["train_rows"] += 1
    checkpoint.write_text(json.dumps(modified))
    with pytest.raises(ValueError, match="checkpoint identity"):
        replay.run(args)
