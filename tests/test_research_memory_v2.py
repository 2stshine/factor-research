"""Synthetic-only tests; never open campaign, result, panel, DB or OOS artifacts."""
from copy import deepcopy
import json
import sqlite3

import pytest

from engine.research_memory_v2 import MemoryCapability, MemoryStore, NAMESPACE, digest, main


SCOPE = {"market": "KOSPI", "protocol_version": "diagnostic-test-v1", "task_class": "measurement"}


def at(day):
    return f"2026-10-{day:02d}T00:00:00Z"


def evidence(eid="e1", *, scope=None, payload="Measured input had no future timestamp.", root=None):
    return {"evidence_id": eid, "root_id": root or f"root-{eid}", "source_sha256": digest({"source": eid}),
            "payload": payload, "payload_sha256": digest(payload), "scope": scope or dict(SCOPE),
            "released_at": at(1), "visibility": "SYNTHETIC", "origin": "SYNTHETIC_FIXTURE",
            "release_receipt_id": "fixture-release"}


def store(tmp_path, **kwargs):
    return MemoryStore(tmp_path / "memory.sqlite", **kwargs)


def cap(ids=("e1", "e2"), **kwargs):
    defaults = dict(capability_id="test-cap", namespace=NAMESPACE, scope=dict(SCOPE),
                    allowed_evidence_ids=tuple(ids), expires_at=at(30))
    return MemoryCapability(**(defaults | kwargs))


def propose(mem, *, cid="input-check", eid="e1", rev=0, day=2, supports=None, counters=None, **kwargs):
    defaults = dict(claim_id=cid, author="analyst", facts=[{"text": "Input timestamp measured.", "evidence_ids": [eid]}],
                    interpretations=[{"text": "Input validity does not establish an economic mechanism.", "evidence_ids": [eid]}],
                    unknowns=["Economic mechanism remains untested."], limitations=["Synthetic fixture only."],
                    scope=dict(SCOPE), supports=supports or [eid], counterevidence=counters or [],
                    expected_revision=rev, key=f"propose-{cid}-{rev + 1}", at=at(day))
    return mem.propose(**(defaults | kwargs))


def accept(mem, proposal, *, day=3, **kwargs):
    defaults = dict(expected_sha256=proposal["content_sha256"], reviewer="independent-critic", decision="ACCEPT",
                    rationale="References and scope checked; no causal claim.",
                    key=f"review-{proposal['revision_id']}", at=at(day))
    return mem.review(proposal["revision_id"], **(defaults | kwargs))


def retrieve(mem, *, day=4, query="Input", scope=None, capability=None, key="retrieval", research_as_of=None, **kwargs):
    return mem.retrieve(query, scope=scope or dict(SCOPE), research_as_of=research_as_of or at(day),
                        capability=capability or cap(), task_id="fixture-task", key=key, at=at(day), **kwargs)


def ready(tmp_path):
    mem = store(tmp_path)
    mem.register_evidence(evidence(), key="evidence", at=at(1))
    proposal = propose(mem)
    accept(mem, proposal)
    return mem, proposal


def test_reviewed_memory_persists_with_bound_evidence_and_separated_meanings(tmp_path):
    mem, proposal = ready(tmp_path)
    result = retrieve(mem)
    assert result["injected_revision_ids"] == ["input-check@1"]
    item = result["context"][0]
    assert item["facts"] and item["interpretations"] and item["unknowns"] and item["limitations"]
    assert item["evidence_bindings"][0]["payload_sha256"] == evidence()["payload_sha256"]
    assert item["content_sha256"] == proposal["content_sha256"]
    assert result["utility_weight"] == 0 and not result["legacy_memory_imported"]
    assert result["actual_tokens"] is None
    reopened = store(tmp_path)
    assert retrieve(reopened, day=5, key="again", research_as_of=at(4))["context"] == result["context"]


def test_unreviewed_revise_and_reject_never_imported(tmp_path):
    mem = store(tmp_path)
    mem.register_evidence(evidence(), key="evidence", at=at(1))
    for cid in ("draft", "revise", "reject"):
        proposal = propose(mem, cid=cid)
        if cid != "draft":
            accept(mem, proposal, day=2, decision=cid.upper())
    assert retrieve(mem)["context"] == []


def test_false_lesson_correction_is_revision_not_overwrite_and_old_receipt_is_frozen(tmp_path):
    mem, first = ready(tmp_path)
    before = retrieve(mem)
    second = propose(mem, rev=1, day=5,
                     facts=[{"text": "Input audit was incomplete, validity is unknown.", "evidence_ids": ["e1"]}])
    assert retrieve(mem, day=5, key="draft-correction")["context"][0]["revision_id"] == first["revision_id"]
    accept(mem, second, day=6)
    after = retrieve(mem, day=7, key="corrected")
    assert after["context"][0]["revision_id"] == "input-check@2"
    past = retrieve(mem, day=7, key="past", research_as_of=at(4))
    assert past["context"] == before["context"]
    assert mem.receipt_requires_review(before["receipt_id"])
    assert not mem.receipt_requires_review(after["receipt_id"])


def test_retirement_does_not_resurrect_an_older_revision(tmp_path):
    mem, _ = ready(tmp_path)
    second = propose(mem, rev=1, day=4)
    accept(mem, second, day=5)
    mem.retire(second["revision_id"], reason="Incorrect scope", actor="curator", key="retire", at=at(6))
    assert retrieve(mem, day=7)["context"] == []
    assert retrieve(mem, day=7, key="old", research_as_of=at(5))["context"][0]["revision"] == 2


def test_available_at_cannot_precede_independent_review(tmp_path):
    mem, _ = ready(tmp_path)
    assert retrieve(mem, research_as_of=at(2))["context"] == []
    result = retrieve(mem, key="after-review")
    assert result["context"][0]["available_at"].startswith("2026-10-03")


def test_counterevidence_always_travels_with_the_claim(tmp_path):
    mem = store(tmp_path)
    mem.register_evidence(evidence(), key="e1", at=at(1))
    counter = evidence("e2", payload="Later audit found missing report availability times.")
    mem.register_evidence(counter, key="e2", at=at(1))
    proposal = propose(mem, counters=["e2"])
    accept(mem, proposal)
    receipt = retrieve(mem)
    assert receipt["included_counterevidence"] == ["e2"]
    assert counter["payload"] in receipt["rendered_context"]
    # A capability for support alone cannot obtain a one-sided version.
    assert retrieve(mem, key="support-only", capability=cap(("e1",)))["context"] == []
    tiny = retrieve(mem, key="too-short", max_chars=200)
    assert tiny["context"] == [] and tiny["actual_chars"] <= 200
    with pytest.raises(ValueError, match="trust warning"):
        retrieve(mem, key="impossibly-short", max_chars=30)


def test_missing_unknown_and_bad_evidence_refs_rejected(tmp_path):
    mem = store(tmp_path)
    with pytest.raises(ValueError, match="unavailable"):
        propose(mem)
    mem.register_evidence(evidence(), key="e1", at=at(1))
    with pytest.raises(ValueError, match="undeclared"):
        propose(mem, facts=[{"text": "Invented", "evidence_ids": ["not-measured"]}])
    malformed = evidence("other")
    malformed["payload"] = "Tampered"
    with pytest.raises(ValueError, match="hash mismatch"):
        mem.register_evidence(malformed, key="bad", at=at(1))


def test_scope_mismatch_on_evidence_and_retrieval(tmp_path):
    mem, _ = ready(tmp_path)
    changed = dict(SCOPE, protocol_version="different-policy")
    with pytest.raises(ValueError, match="incompatible"):
        propose(mem, cid="different", scope=changed, day=4)
    assert retrieve(mem, scope=changed, capability=cap(scope=changed))["context"] == []
    with pytest.raises(ValueError, match="capability"):
        retrieve(mem, scope=changed)


def test_raw_legacy_and_self_asserted_public_evidence_cannot_be_imported(tmp_path):
    mem = store(tmp_path)
    for changes in ({"origin": "LEGACY"}, {"visibility": "SEALED"},
                    {"visibility": "RELEASED_QUALITATIVE", "origin": "V2_PUBLIC_EXPORT"}):
        with pytest.raises(ValueError):
            mem.register_evidence(evidence() | changes, key="forbidden", at=at(1))
    with pytest.raises(ValueError, match="namespace"):
        MemoryStore(tmp_path / "legacy.sqlite", namespace="legacy")


def test_public_export_guard_authenticates_full_envelope_and_rechecks_retrieval(tmp_path):
    allowed = evidence() | {"origin": "V2_PUBLIC_EXPORT", "visibility": "RELEASED_QUALITATIVE"}
    permitted = {digest(allowed)}
    calls = []
    def guard(envelope, timestamp):
        calls.append(timestamp)
        return digest(envelope) in permitted
    mem = store(tmp_path, public_filter=guard)
    mem.register_evidence(allowed, key="public", at=at(1))
    accept(mem, propose(mem))
    assert retrieve(mem)["context"]
    permitted.clear()
    assert retrieve(mem, day=5, key="revoked")["context"] == []
    assert len(calls) >= 5


def test_guard_exception_is_generic_denial_not_hidden_details(tmp_path):
    def guard(*args):
        raise RuntimeError("SEALED_SECRET_CANARY")
    mem = store(tmp_path, public_filter=guard)
    item = evidence() | {"origin": "V2_PUBLIC_EXPORT", "visibility": "RELEASED_QUALITATIVE"}
    with pytest.raises(ValueError, match="not available") as exc:
        mem.register_evidence(item, key="blocked", at=at(1))
    assert "CANARY" not in str(exc.value)


def test_exact_review_hash_and_independent_identity_required(tmp_path):
    mem = store(tmp_path)
    mem.register_evidence(evidence(), key="e1", at=at(1))
    proposal = propose(mem)
    with pytest.raises(ValueError, match="exact existing"):
        accept(mem, proposal, expected_sha256="wrong")
    with pytest.raises(ValueError, match="Independent"):
        accept(mem, proposal, reviewer="analyst")
    accept(mem, proposal)
    with pytest.raises(ValueError, match="already reviewed"):
        accept(mem, proposal, key="second-review")


def test_writer_idempotency_conflict_and_no_backdating(tmp_path):
    mem = store(tmp_path)
    mem.register_evidence(evidence(), key="e1", at=at(1))
    mem.register_evidence(evidence(), key="e1", at=at(2))
    assert len(mem._events()) == 1
    first = propose(mem)
    assert propose(mem, day=3) == first
    with pytest.raises(ValueError, match="Idempotency"):
        propose(mem, unknowns=["Changed"], day=3)
    with pytest.raises(ValueError, match="Revision conflict"):
        propose(mem, key="concurrent-write", day=3)
    with pytest.raises(ValueError, match="backdate"):
        mem.register_evidence(evidence("e2"), key="old-time", at=at(1))


def test_deterministic_ranking_tie_breaks_and_evidence_root_dedup(tmp_path):
    mem = store(tmp_path)
    for eid in ("e1", "e2", "e3"):
        mem.register_evidence(evidence(eid, root="shared" if eid != "e3" else "different"), key=eid, at=at(1))
    for cid, eid in (("z", "e1"), ("a", "e2"), ("b", "e3")):
        accept(mem, propose(mem, cid=cid, eid=eid), day=2)
    first = retrieve(mem, capability=cap(("e1", "e2", "e3")))
    assert first["injected_revision_ids"] == ["a@1", "b@1"]
    second = retrieve(mem, key="again", capability=cap(("e1", "e2", "e3")))
    assert first == second
    assert "DUPLICATE_EVIDENCE_ROOT" in first["exclusion_reason_codes"]


def test_inaccessible_candidates_do_not_affect_receipts_or_counts(tmp_path):
    mem, _ = ready(tmp_path)
    first = retrieve(mem)
    mem.register_evidence(evidence("hidden", payload="SECRET_CANARY"), key="hidden", at=at(4))
    accept(mem, propose(mem, cid="hidden", eid="hidden", day=4), day=4)
    second = retrieve(mem, key="after-hidden")
    assert first == second
    assert "hidden" not in json.dumps(second) and "CANARY" not in json.dumps(second)


def test_evidence_invalidation_cascades_and_flags_old_usage_but_preserves_replay(tmp_path):
    mem, _ = ready(tmp_path)
    before = retrieve(mem)
    mem.record_usage(before["receipt_id"], used={"input-check@1": "Checked input timing before interpretation."},
                     rejected={}, actor="planner", key="usage", at=at(4))
    assert not mem.receipt_requires_review(before["receipt_id"])
    mem.invalidate_evidence("e1", reason="Fixture provenance was incorrect", actor="curator", key="invalidate", at=at(5))
    assert retrieve(mem, day=6, key="after")["context"] == []
    assert mem.receipt_requires_review(before["receipt_id"])
    assert retrieve(mem, day=6, key="replay", research_as_of=at(4))["context"] == before["context"]
    with pytest.raises(ValueError, match="incompatible"):
        propose(mem, rev=1, day=6)


def test_usage_must_bind_exact_injected_set_and_remains_idempotent(tmp_path):
    mem, _ = ready(tmp_path)
    result = retrieve(mem)
    kwargs = dict(used={}, rejected={"input-check@1": "Not relevant for this decision."}, actor="planner", key="use", at=at(4))
    first = mem.record_usage(result["receipt_id"], **kwargs)
    assert mem.record_usage(result["receipt_id"], **kwargs) == first
    assert not first["causal_utility_claim"]
    with pytest.raises(ValueError, match="exactly"):
        mem.record_usage(result["receipt_id"], used={"not-injected@1": "Pretend"}, rejected={}, actor="planner", key="bad-use", at=at(4))


def test_expired_wrong_namespace_and_future_capability_requests_rejected(tmp_path):
    mem, _ = ready(tmp_path)
    for capability in (cap(expires_at=at(3)), cap(namespace="legacy"), cap(audience="SEALED_REVIEWER")):
        with pytest.raises(ValueError, match="capability"):
            retrieve(mem, capability=capability)
    with pytest.raises(ValueError, match="capability"):
        retrieve(mem, research_as_of=at(5))


def test_event_chain_tampering_is_detected(tmp_path):
    mem, _ = ready(tmp_path)
    with sqlite3.connect(mem.path) as db:
        db.execute("UPDATE memory_events SET body='{}' WHERE seq=1")
    with pytest.raises(ValueError, match="integrity"):
        store(tmp_path)


def test_missing_evidence_release_time_and_claim_hash_binding(tmp_path):
    mem = store(tmp_path)
    with pytest.raises(ValueError, match="not available"):
        mem.register_evidence(evidence() | {"released_at": at(2)}, key="future", at=at(1))
    mem.register_evidence(evidence(), key="e1", at=at(1))
    proposal = propose(mem)
    clone = deepcopy(proposal)
    saved = clone.pop("content_sha256")
    assert digest(clone) == saved
    clone["evidence_bindings"][0]["source_sha256"] = "0" * 64
    assert digest(clone) != saved


def test_initialize_cli_does_not_read_or_import_nearby_legacy_files(tmp_path, capsys):
    (tmp_path / "lessons.json").write_text('{"lesson":"LEGACY_CANARY"}')
    path = tmp_path / "fresh.sqlite"
    main(["initialize", "--database", str(path)])
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "INITIALIZED" and not result["legacy_memory_imported"]
    assert MemoryStore(path)._events() == []


def test_existing_unrelated_database_is_not_modified(tmp_path):
    path = tmp_path / "existing.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE legacy_lessons (body TEXT)")
        db.execute("INSERT INTO legacy_lessons VALUES ('KEEP_ME')")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="unrelated database"):
        MemoryStore(path)
    assert path.read_bytes() == before
