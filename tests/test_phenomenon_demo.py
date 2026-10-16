import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine.phenomenon_research import GraphStore, digest
from scripts.phenomenon_demo import run_demo, synthetic_execution_bundle, synthetic_research_rows, synthetic_ridge_inputs


def test_demo_full_persistent_path_never_becomes_market_result(tmp_path):
    root = tmp_path / "demo"
    result = run_demo(root)
    assert result["status"] == "ALL_CHECKS_PASSED"
    assert all(result["checks"].values())
    assert len(result["checks"]) >= 20
    assert len(result["expected_failures"]) >= 7
    assert all(case["expected"] for case in result["expected_failures"])
    assert result["empirical_use"] == "SOFTWARE_TEST_ONLY"
    assert all(result[field] is False for field in ["real_llm_review_performed", "market_findings_created", "database_accessed", "gold_published", "orders_submitted"])
    persisted = json.loads((root / "manifest.json").read_text())
    assert persisted == result
    assert result["manifest_sha256"] == digest({k: v for k, v in result.items() if k != "manifest_sha256"})
    graph = GraphStore(root / "graph")
    assert graph.validate()["statuses"][result["strategy_id"]] == "DEPENDENCY_BLOCKED"
    assert graph.validate()["statuses"][result["claim_id"]] == "DEPENDENCY_BLOCKED"
    assert graph.validate()["statuses"][result["ridge_strategy_id"]] == "DEPENDENCY_BLOCKED"
    assert graph.packet(result["study_id"])["stop_decision"]["payload"]["status"] == "DATA_BLOCKED"
    assert graph.packet(result["study_id"])["unresolved_requirement_ids"]
    assert not (root / "failure.json").exists()
    assert result["data_intake"]["method"] == "explicit_local_exact_hash"
    assert result["data_intake"]["network_accessed"] is False
    assert result["data_intake"]["question_id"] == graph.get(result["study_id"])["payload"]["question_id"]
    runtime = Path(result["runtime"]["run_dir"])
    for name in ["q20_equal", "q10_equal", "q20_sqrt_cap", "q10_sqrt_cap"]:
        artifact = json.loads((runtime / f"{name}.json").read_text())
        assert len(artifact["monthly"]) == 2
    ridge_root = Path(result["ridge_runtime"]["run_dir"])
    audit = json.loads((ridge_root / "ridge_audit.json").read_text())
    assert len(audit["scores"]) == len(audit["baseline_predictions"]) == 20
    assert all(not fold["test_labels_used"] for fold in audit["folds"])
    assert not audit["hyperparameter_search"] and not audit["winner_selected"]


def test_demo_existing_output_not_overwritten(tmp_path):
    root = tmp_path / "existing"
    root.mkdir()
    marker = root / "keep.txt"
    marker.write_text("preserve")
    with pytest.raises(ValueError, match="fresh output"):
        run_demo(root)
    assert marker.read_text() == "preserve"


def test_demo_cli_runs_from_real_entrypoint(tmp_path):
    root = tmp_path / "cli"
    completed = subprocess.run([sys.executable, "-m", "scripts.phenomenon_demo", "--output", str(root)],
                               cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["status"] == "ALL_CHECKS_PASSED"
    assert report["final_strategy_state"] == "DEPENDENCY_BLOCKED"
    assert len(report["runtime_variants"]) == 4


def test_fixtures_explicitly_synthetic_and_hash_consistent():
    from engine import phenomenon_runtime as runtime
    bundle = synthetic_execution_bundle()
    assert bundle["origin"] == bundle["reference"]["origin"] == "SYNTHETIC"
    assert bundle["evidence"]["data_sha256"] == runtime.bundle_data_sha256(bundle)
    assert len(bundle["measurements"]) == 20
    rows = synthetic_research_rows()
    assert len(rows) == 6 and sum(row["attention_proxy"] == "NOT_OBSERVED" for row in rows) == 1


def test_ridge_fixture_freezes_selection_and_separates_training_labels():
    from engine import phenomenon_runtime as runtime
    bundle, payload = synthetic_ridge_inputs()
    rule = payload["runtime_contract"]["score_rule"]
    assert rule["kind"] == "TRAIN_ONLY_RIDGE" and rule["pca_components"] == 1
    assert len(bundle["training_features"]) == len(bundle["training_labels"]) == 50
    assert all("gross_total_return_multiplier" not in row for row in bundle["training_features"])
    assert bundle["evidence"]["data_sha256"] == runtime.bundle_data_sha256(bundle)
    assert payload["runtime_contract"]["input_bundle_sha256"] == digest(bundle)
