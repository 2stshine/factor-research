"""Public process status must not open result files or emit evidence payloads."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from engine.adaptive_research import canonical, digest
from scripts.export_production_v2 import build_summary, _session_metadata


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def bind(value):
    return {**value, "sha256": digest(value)}


@pytest.fixture
def source(tmp_path):
    policy = {"version": "production-research-v2-v1", "enabled": True,
              "graph_retrieval": False, "utility_ranking_weight": 0,
              "automatic_gold_publication": False, "legacy_campaign_migration": False,
              "mandatory_diagnostics": ["input_audit", "association", "controls", "regime_interaction"]}
    save(tmp_path / "research/v2/production-policy.json", policy)
    for name in ("engine/research_production.py", "engine/research_production_evidence.py",
                 "engine/research_regime_production.py", "engine/research_memory_transfer.py",
                 "scripts/research.py", "engine/epochs.py"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# synthetic display source identity only\n")
    config = bind({"version": policy["version"], "policy": policy})
    folder = tmp_path / "research/campaigns/new-example"
    plans = {"cost_intensity": {"definition": "fixed", "private_narrative": "DO_NOT_EXPORT_PLAN"}}
    campaign = {"campaign_id": "new-example", "status": "OPEN", "created_at": "2026-10-02T10:00:00+09:00",
                "research_v2": config, "epochs": [{"epoch_id": "epoch-001"}],
                "oos": {"DO_NOT_EXPORT_OOS": 999999}, "qualified_factors": ["DO_NOT_EXPORT_VERDICT"]}
    save(folder / "manifest.json", campaign)
    save(folder / "epochs/epoch-001/manifest.json", {"research_v2_sha256": config["sha256"],
         "research_v2_plans": plans, "research_v2_plans_sha256": digest(plans),
         "candidates": [{"private_metric": "DO_NOT_EXPORT_RESULT"}]})
    handoff = bind({"version": policy["version"], "campaign_id": "new-example", "epoch_id": "epoch-001",
                   "factor": "cost_intensity", "campaign_sha256": config["sha256"],
                   "data_contract_sha256": "a" * 64, "regime_labs": {"KOSPI": {}, "KOSDAQ": {}},
                   "macro_labs": {}, "input_profiles": {"private": "DO_NOT_EXPORT_INPUT"}})
    handoff_dir = folder / "v2/epoch-001/cost_intensity"
    save(handoff_dir / "manifest.json", handoff)
    (handoff_dir / "frame.parquet").write_text("MUST_NOT_READ_FRAME")
    (folder / "result.json").write_text("INVALID_JSON_MUST_NOT_READ_RESULT")
    save(tmp_path / "research/campaigns/legacy-example/manifest.json", {"status": "REVEALED", "oos": "MUST_NOT_EXPORT"})
    return tmp_path, folder, handoff_dir, handoff


def add_session(path, *, stopped=False, incomplete=False, bad_binding=False):
    events = [dict(type="CREATED", contract={"data_contract_sha256": ("b" if bad_binding else "a") * 64,
                                           "planner_kind": "HOST_LLM", "max_actions": 12})]
    events += [{"type": "ACTION", "request_id": "one", "action": {"reason": "DO_NOT_EXPORT_PROSE"}},
               {"type": "RESULT", "request_id": "one", "status": "OBSERVED",
                "evidence": {"diagnostic_id": "association", "response": {"metrics": {"IC": "DO_NOT_EXPORT_METRIC"}}}}]
    if stopped:
        events += [{"type": "ACTION", "request_id": "stop"},
                   {"type": "RESULT", "request_id": "stop", "status": "STOPPED",
                    "decision": {"private": "DO_NOT_EXPORT_INTERPRETATION"}}]
    if incomplete:
        events.append({"type": "ACTION", "request_id": "unfinished"})
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE events (revision INTEGER PRIMARY KEY, body TEXT NOT NULL, sha TEXT NOT NULL)")
        previous = ""
        for index, event in enumerate(events):
            event.update(revision=index, previous_sha256=previous)
            previous = digest(event)
            db.execute("INSERT INTO events VALUES (?, ?, ?)", (index, canonical(event), previous))


def test_metadata_only_dynamic_counts_and_legacy_exclusion(source, monkeypatch):
    root, _folder, handoff_dir, _manifest = source
    add_session(handoff_dir / "session.sqlite", stopped=True)
    original = Path.read_text
    def guarded(path, *args, **kwargs):
        assert path.name in {"production-policy.json", "manifest.json"}, f"Unexpected result read: {path}"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", guarded)
    result = build_summary(repo_root=root, generated_at="2026-10-02T12:00:00+09:00")
    assert result["counts"] == {"new_campaigns": 1, "aborted_campaigns": 0,
                               "campaigns_with_registered_candidates": 1, "registered_candidates": 1,
                               "prepared_handoffs": 1, "explicitly_stopped_sessions": 1,
                               "pending_host_sessions": 0}
    assert "DO_NOT_EXPORT" not in json.dumps(result)
    assert "MUST_NOT" not in json.dumps(result)
    assert result["campaigns"][0]["handoffs"][0]["markets"] == ["KOSDAQ", "KOSPI"]
    assert result["campaigns"][0]["process_stage"] == "HOST_STOPPED_REVIEW_SEPARATE"
    assert not result["production_lessons_included"]
    assert "NOT_EXPORTED" in result["campaigns"][0]["handoffs"][0]["review_status"]


def test_active_not_fake_reviewed_or_complete(source):
    root, _folder, handoff_dir, _manifest = source
    add_session(handoff_dir / "session.sqlite")
    result = build_summary(repo_root=root)
    assert result["counts"]["explicitly_stopped_sessions"] == 0
    assert result["counts"]["pending_host_sessions"] == 1
    assert result["campaigns"][0]["handoffs"][0]["session"]["status"] == "ACTIVE"
    assert result["campaigns"][0]["process_stage"] == "HANDOFF_READY_HOST_PENDING_OR_ACTIVE"


def test_registration_and_handoff_stages_are_not_inferred_from_preflight(source):
    root, folder, handoff_dir, _manifest = source
    # An incomplete/staged bundle is not a prepared handoff.
    handoff_dir.rename(handoff_dir.with_name(".cost_intensity-preparing"))
    value = build_summary(repo_root=root)
    assert value["campaigns"][0]["process_stage"] == "CANDIDATES_REGISTERED_NO_HANDOFF"
    assert value["counts"]["registered_candidates"] == 1
    assert value["counts"]["prepared_handoffs"] == 0
    path = folder / "manifest.json"
    campaign = json.loads(path.read_text())
    campaign["epochs"] = []
    campaign["input_preflight"] = {"status": "PASS", "coverage": .92}
    save(path, campaign)
    value = build_summary(repo_root=root)
    assert value["campaigns"][0]["process_stage"] == "CAMPAIGN_FROZEN_NO_REGISTERED_CANDIDATE"
    assert value["campaigns"][0]["registered_epochs"] == 0
    assert value["counts"]["registered_candidates"] == 0
    campaign["status"] = "CLOSED_ABORTED"
    save(path, campaign)
    value = build_summary(repo_root=root)
    assert value["campaigns"][0]["process_stage"] == "ABORTED_BEFORE_REGISTRATION"
    assert value["counts"]["new_campaigns"] == value["counts"]["aborted_campaigns"] == 1
    assert value["counts"]["campaigns_with_registered_candidates"] == 0


def test_no_session_and_pending_action_are_distinct(source):
    _root, _folder, handoff_dir, manifest = source
    path = handoff_dir / "session.sqlite"
    assert _session_metadata(path, manifest)["status"] == "NOT_INITIALIZED"
    add_session(path, incomplete=True)
    assert _session_metadata(path, manifest)["status"] == "PENDING_RECONCILIATION"


def test_wrong_session_contract_fails_closed(source):
    root, _folder, handoff_dir, _manifest = source
    add_session(handoff_dir / "session.sqlite", bad_binding=True)
    with pytest.raises(ValueError, match="bound"):
        build_summary(repo_root=root)


def test_changed_manifest_and_unregistered_handoff_are_not_published(source):
    root, _folder, handoff_dir, manifest = source
    changed = deepcopy(manifest)
    changed["factor"] = "not-registered"
    save(handoff_dir / "manifest.json", changed)
    with pytest.raises(ValueError, match="Changed"):
        build_summary(repo_root=root)
    changed.pop("sha256")
    save(handoff_dir / "manifest.json", bind(changed))
    with pytest.raises(ValueError, match="registered"):
        build_summary(repo_root=root)


def test_policy_cannot_silently_enable_gold_or_graph(source):
    root, *_ = source
    path = root / "research/v2/production-policy.json"
    policy = json.loads(path.read_text())
    policy["automatic_gold_publication"] = True
    save(path, policy)
    with pytest.raises(ValueError, match="policy"):
        build_summary(repo_root=root)
