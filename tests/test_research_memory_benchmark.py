"""Harness tests use explicit scripted fixtures, never claim real HOST_LLM results."""
from collections import Counter
import json
import sqlite3

import pytest

from engine.research_memory_benchmark import ARMS, MemoryBenchmark, _build_bank, _rubric, initialize
from engine.research_memory_v2 import MemoryStore
from scripts.research_memory_comparison import main


def benchmark(tmp_path):
    root = tmp_path / "synthetic-procedural-benchmark"
    initialize(root, model="SCRIPTED_UNIT_TEST_NOT_ACTUAL_LLM")
    return MemoryBenchmark(root)


def final(decision, citations, reads, **kwargs):
    action = {"kind": "FINAL", "decision": decision, "observations": ["Synthetic fixture observation."],
              "interpretation": "Bounded test-fixture interpretation, not causal proof.",
              "unknowns": ["No market-performance implication."], "evidence_ids": citations,
              "performed_actions": ["READ_EVIDENCE:" + sid for sid in reads], "causal_claim": False}
    return action | kwargs


def complete_with_scripted_oracle(b, *, corrupt=None):
    """Private test helper only; no equivalent completion routine exists in runtime."""
    truth = _rubric()
    for arm in ARMS:
        for cid in b.plan["cases"]:
            packet = b.packet(arm, cid)
            read = []
            for doc in packet["source_catalog"]:
                b.act(arm, cid, {"kind": "READ_EVIDENCE", "source_id": doc["source_id"]})
                read.append(doc["source_id"])
            action = final(truth[cid]["decision"], truth[cid]["required_source_sets"][0], read)
            if corrupt and (arm, cid) == corrupt[0]:
                action.update(corrupt[1])
            b.act(arm, cid, action)


def test_bank_has_twelve_distinct_cases_six_families_and_no_market_data():
    bank = _build_bank()
    assert len(bank["cases"]) == 12
    assert set(Counter(c["family"] for c in bank["cases"]).values()) == {2}
    assert len({c["case_id"] for c in bank["cases"]}) == 12
    assert all(c["scope"]["market"] == "SYNTHETIC_ONLY" for c in bank["cases"])
    assert "required_source_sets" not in json.dumps(bank)
    assert len({r["decision"] for r in _rubric().values()}) > 6


def test_all_arms_share_sources_policy_question_budget_and_no_grader(tmp_path):
    b = benchmark(tmp_path)
    packets = [b.packet(arm, "schema_units") for arm in ARMS]
    for key in ("case", "source_catalog", "policy", "max_reads", "allowed_decisions"):
        assert all(p[key] == packets[0][key] for p in packets)
    assert packets[0]["memory"] == []
    assert packets[1]["memory"] and packets[2]["memory"]
    assert len(packets[2]["memory"]) <= 3
    assert all("private_rubric" not in json.dumps(p) and "required_source_sets" not in json.dumps(p) for p in packets)
    docs = [b.act(arm, "schema_units", {"kind": "READ_EVIDENCE", "source_id": "schema_units.v2"}) for arm in ARMS]
    assert docs[0] == docs[1] == docs[2]


def test_correction_b2_uses_new_revision_b1_preserves_explicit_history(tmp_path):
    b = benchmark(tmp_path)
    old = b.packet("B1", "correction_revision")["memory"]
    new = b.packet("B2", "correction_revision")["memory"]
    assert len(old) == 2 and len(new) == 1
    assert old[0]["reviewed_at"] < old[1]["reviewed_at"]
    assert new[0]["memory_id"].endswith("@2")
    assert "NOT_REPORTED" in json.dumps(new)
    assert new[0]["counterevidence"]
    assert "withdrawn" not in old[0]["text"]


def test_asof_hides_future_review_for_every_arm_and_not_just_b2(tmp_path):
    b = benchmark(tmp_path)
    for arm in ARMS:
        packet = b.packet(arm, "asof_pending")
        assert packet["memory"] == []
        assert [d["source_id"] for d in packet["source_catalog"]] == ["asof_pending.draft"]
        with pytest.raises(ValueError, match="unavailable"):
            b.act(arm, "asof_pending", {"kind": "READ_EVIDENCE", "source_id": "asof_pending.approval"})


def test_counterevidence_is_injected_for_b2(tmp_path):
    b = benchmark(tmp_path)
    memory = b.packet("B2", "counterevidence_mixed")["memory"]
    assert memory[0]["counterevidence"][0]["evidence_id"] == "counterevidence_mixed.setting_b"
    assert "not support" in memory[0]["counterevidence"][0]["text"]


def test_scoped_store_omits_out_of_universe_note_but_sources_remain_accessible(tmp_path):
    b = benchmark(tmp_path)
    assert b.packet("B1", "scope_market")["memory"]
    assert b.packet("B2", "scope_market")["memory"] == []
    doc = b.act("B2", "scope_market", {"kind": "READ_EVIDENCE", "source_id": "scope_market.lesson"})
    assert doc["scope"]["universe"] == "KOSDAQ_SMALL"


def test_packet_resume_is_stable_and_does_not_add_duplicate_reads(tmp_path):
    b = benchmark(tmp_path)
    first = b.packet("B2", "schema_units")
    second = b.packet("B2", "schema_units")
    assert first == second
    b.act("B2", "schema_units", {"kind": "READ_EVIDENCE", "source_id": "schema_units.v1"})
    resumed = b.packet("B2", "schema_units")
    assert resumed["reads_remaining"] == 2 and len(resumed["read_evidence"]) == 1


def test_three_read_budget_closed_case_and_source_scope_enforced(tmp_path):
    b = benchmark(tmp_path)
    b.packet("B0", "schema_units")
    for _ in range(3):
        b.act("B0", "schema_units", {"kind": "READ_EVIDENCE", "source_id": "schema_units.v1"})
    with pytest.raises(ValueError, match="budget"):
        b.act("B0", "schema_units", {"kind": "READ_EVIDENCE", "source_id": "schema_units.v2"})
    b.act("B0", "schema_units", final("BLOCK_SCHEMA_MISMATCH", ["schema_units.v1"], ["schema_units.v1"] * 3))
    with pytest.raises(ValueError, match="finalized"):
        b.act("B0", "schema_units", final("ALLOW_USE", [], []))
    b.packet("B1", "schema_units")
    with pytest.raises(ValueError, match="unavailable"):
        b.act("B1", "schema_units", {"kind": "READ_EVIDENCE", "source_id": "schema_alias.alias"})


def test_cannot_score_early_or_obtain_answers_from_status(tmp_path):
    b = benchmark(tmp_path)
    with pytest.raises(ValueError, match="all 36"):
        b.score()
    status = b.status()
    assert status["completed"] == {"B0": 0, "B1": 0, "B2": 0}
    assert "decision" not in json.dumps(status)


def test_scripted_harness_path_scores_all_answers_but_demands_semantic_review(tmp_path):
    b = benchmark(tmp_path)
    complete_with_scripted_oracle(b)
    score = b.score()
    assert all(v["quality_pass"] == 12 for v in score["summary"].values())
    assert all(v["model_tokens"] is None for v in score["summary"].values())
    assert not score["general_efficacy_established"]
    assert score["semantic_review_status"] == "PENDING_INDEPENDENT_REVIEW"
    assert all(r["wall_clock_seconds"] >= 0 for r in score["rows"])
    assert all(r["source_reads"] <= 3 for r in score["rows"])


def test_unsupported_citation_causal_and_execution_claims_are_flagged_not_silently_repaired(tmp_path):
    b = benchmark(tmp_path)
    complete_with_scripted_oracle(b, corrupt=(("B0", "schema_units"),
        {"evidence_ids": ["schema_units.v1", "schema_units.v2", "never_read"], "causal_claim": True, "performed_actions": []}))
    row = b.score()["rows"][0]
    assert row["decision_correct"] and not row["quality_pass"]
    assert set(row["unsupported_claim_flags"]) >= {"UNSUPPORTED_OR_MISSING_CITATION", "CAUSAL_OVERCLAIM", "FALSE_OR_OMITTED_EXECUTION_CLAIM"}


def test_injected_memory_citation_is_valid_secondary_evidence(tmp_path):
    b = benchmark(tmp_path)
    truth = _rubric()
    for arm in ARMS:
        for cid in b.plan["cases"]:
            packet = b.packet(arm, cid)
            if arm == "B2" and cid == "schema_units":
                b.act(arm, cid, final(truth[cid]["decision"], [packet["memory"][0]["memory_id"]], []))
                continue
            read = [d["source_id"] for d in packet["source_catalog"]]
            for sid in read:
                b.act(arm, cid, {"kind": "READ_EVIDENCE", "source_id": sid})
            b.act(arm, cid, final(truth[cid]["decision"], read, read))
    row = next(r for r in b.score()["rows"] if r["arm"] == "B2" and r["case_id"] == "schema_units")
    assert row["quality_pass"] and row["source_reads"] == 0


def test_frozen_input_and_event_tampering_detected(tmp_path):
    b = benchmark(tmp_path)
    b.packet("B0", "schema_units")
    with sqlite3.connect(b.root / "sessions.sqlite") as db:
        db.execute("UPDATE events SET body='{}'")
    with pytest.raises((ValueError, KeyError)):
        b.status()
    bank = b.root / "public_bank.json"
    bank.write_text("{}")
    with pytest.raises(ValueError, match="mismatch"):
        MemoryBenchmark(b.root)


def test_init_refuses_existing_root_and_cli_only_reports_progress(tmp_path, capsys):
    root = tmp_path / "bench"
    main(["init", "--root", str(root), "--model", "SCRIPTED_TEST", "--context-mode", "ARM_BUNDLED"])
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["context_mode"] == "ARM_BUNDLED"
    with pytest.raises(FileExistsError):
        initialize(root, model="SCRIPTED_TEST")
    main(["status", "--root", str(root)])
    assert json.loads(capsys.readouterr().out)["completed"] == {"B0": 0, "B1": 0, "B2": 0}


def test_learning_or_retirement_during_evaluation_breaks_frozen_memory_contract(tmp_path):
    b = benchmark(tmp_path)
    mem = MemoryStore(b.root / "memory" / "schema_units.sqlite", namespace="research-v2:procedural-benchmark")
    mem.retire("schema_units@1", actor="test-curator", reason="Unregistered change", key="unregistered")
    with pytest.raises(ValueError, match="Frozen memory corpus"):
        b.packet("B2", "schema_units")


def test_denied_source_request_is_durably_audited(tmp_path):
    b = benchmark(tmp_path)
    b.packet("B0", "schema_units")
    with pytest.raises(ValueError, match="unavailable"):
        b.act("B0", "schema_units", {"kind": "READ_EVIDENCE", "source_id": "private-answer"})
    complete_with_scripted_oracle(b)
    row = b.score()["rows"][0]
    assert row["decision_correct"] and not row["quality_pass"]
    assert "UNAUTHORIZED_SOURCE_REQUEST" in row["unsupported_claim_flags"]
    assert row["rejected_actions"] == 1
