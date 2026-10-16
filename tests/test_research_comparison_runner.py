"""Broker integrity checks on a two-case development-only fixture (seeds11/12)."""
import pytest

from engine.adaptive_research import digest
from engine.research_comparison_policies import ORDERS, lean_fixed
from scripts import research_comparison as runner


@pytest.fixture
def development_run(tmp_path, monkeypatch):
    source = tmp_path / "source.py"
    source.write_text("# immutable fixture source\n")
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "SOURCES", ("source.py",))
    monkeypatch.setattr(runner, "SCENARIOS_BY_QUESTION", {"ECONOMIC": ("economic_missing",)})
    plan = {
        "runtime": {"mode": "SYNTHETIC_ONLY", "max_cost_units": 10, "max_actions": 10},
        "comparison": {
            "conditions": list(runner.PLANNERS),
            "question_families": {"ECONOMIC": ["economic_missing"]},
            "fixed_orders": {k: list(v) for k, v in ORDERS.items()},
            "replicate_seed_bases": [11, 12], "case_order_seed": 11,
            "episodes_per_planner": 2,
        },
    }
    path = tmp_path / "plan.json"
    runner.save(path, plan)
    run = tmp_path / "run"
    public = runner.init_run(run, path)
    return run, plan, public


def rewrite(path, obj):
    # Test-only tampering, not a workflow writer.
    import json
    path.write_text(json.dumps(obj))


def test_manifest_does_not_expose_truth_in_public_index(development_run):
    run, _, public = development_run
    manifest = runner.load_run(run)
    assert {c["seed"] for c in manifest["cases"]} == {11, 12}
    assert set(public) == {"version", "case_ids", "plan_sha256", "mode"}
    session, _ = runner.public_session(run, public["case_ids"][0])
    packet = session.request()
    assert "scenario" not in packet["public_case"]
    assert "seed" not in packet["public_case"]
    assert "oracle" not in packet


def test_scoreboard_blocked_until_all_cases_terminate(development_run):
    run, _, _ = development_run
    with pytest.raises(ValueError, match="terminate"):
        runner.score_run(run)
    runner.run_references(run)
    with pytest.raises(ValueError, match="terminate"):
        runner.score_run(run)


def test_data_request_terminal_is_completed_and_paired(development_run):
    run, _, public = development_run
    runner.run_references(run)
    for case_id in public["case_ids"]:
        session, lab = runner.public_session(run, case_id)
        session.run(lean_fixed, lab.run)
    status = runner.status_run(run)
    assert all(value == {"STOPPED": 2} for value in status["states"].values())
    result = runner.score_run(run)
    assert result["integration"] == "PASS"
    assert result["followup_preference"] == "LEAN_FIXED_DEFAULT"
    assert result["adaptive_general_superiority"] == "NOT_ESTABLISHED"
    assert result["statistical_significance_claim"] is False
    assert len(result["paired_cases"]) == 2
    assert all(pair["host_accuracy_result"] == "TIE" for pair in result["paired_cases"])
    for aggregate in result["aggregates"].values():
        assert aggregate["completed"] == 2
        assert aggregate["useful_data_requests"] == aggregate["expected_data_requests"] == 2
        assert aggregate["data_request_precision"] == aggregate["data_request_recall"] == 1
        assert aggregate["planner_tokens"] is None


def test_exhausted_case_is_reported_as_failure_not_hidden_from_scoreboard(development_run):
    run, _, public = development_run
    runner.run_references(run)
    for case_id in public["case_ids"]:
        session, lab = runner.public_session(run, case_id)
        for index in range(10):
            packet = session.request()
            session.submit({}, request_id=f"invalid-{index}",
                           expected_revision=packet["state"]["revision"], execute=lab.run)
        assert session.packet()["state"]["state"] == "ACTION_BUDGET_EXHAUSTED"
    result = runner.score_run(run)
    assert result["integration"] == "REVIEW_REQUIRED"
    assert result["bounded_pilot_readiness"] == "REVIEW_REQUIRED"
    assert result["aggregates"]["HOST_LLM"]["completed"] == 0
    assert result["aggregates"]["HOST_LLM"]["invalid_or_failed_actions"] == 20


@pytest.mark.parametrize("part", ["plan", "cases", "snapshot", "source"])
def test_frozen_manifest_and_source_tamper_rejected(development_run, part):
    run, _, _ = development_run
    manifest = runner.read(run / "private-manifest.json")
    if part == "plan":
        manifest["plan"]["runtime"]["max_actions"] += 1
        rewrite(run / "private-manifest.json", manifest)
    elif part == "cases":
        manifest["cases"][0]["seed"] = 99
        rewrite(run / "private-manifest.json", manifest)
    elif part == "snapshot":
        rewrite(run / "source-snapshot.json", {"source.py": "changed"})
    else:
        (run.parent / "source.py").write_text("changed")
    with pytest.raises(ValueError, match="mismatch"):
        runner.load_run(run)


def test_append_only_outputs_and_no_overwrite(development_run):
    run, plan, _ = development_run
    with pytest.raises(FileExistsError):
        runner.save(run / "public-index.json", {})
    with pytest.raises(FileExistsError):
        runner.init_run(run, run.parent / "plan.json")
    runner.run_references(run)
    with pytest.raises(FileExistsError):
        runner.run_references(run)
    assert runner.load_run(run)["plan_sha256"] == digest(plan)


def test_different_case_session_cannot_be_substituted(development_run):
    import shutil
    run, _, public = development_run
    first, second = public["case_ids"]
    source, lab = runner.public_session(run, first)
    source.run(lean_fixed, lab.run)
    destination = run / "sessions" / second / "HOST_LLM.sqlite"
    destination.parent.mkdir(parents=True)
    shutil.copyfile(source.path, destination)
    with pytest.raises(ValueError, match="frozen case identity"):
        runner.public_session(run, second)
    with pytest.raises(ValueError, match="frozen case identity"):
        runner.status_run(run)


def test_fixed_session_cannot_be_relabelled_host(development_run):
    import shutil
    run, _, public = development_run
    runner.run_references(run)
    directory = run / "sessions" / public["case_ids"][0]
    shutil.copyfile(directory / "LEAN_FIXED_REFERENCE.sqlite", directory / "HOST_LLM.sqlite")
    with pytest.raises(ValueError, match="frozen case identity"):
        runner.public_session(run, public["case_ids"][0])
