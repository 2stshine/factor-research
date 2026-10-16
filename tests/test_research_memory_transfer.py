"""Synthetic temporary releases only; never open real memory or research data."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from engine.research_memory_v2 import SCOPE_KEYS, digest
from engine.research_memory_transfer import (CHECKS, SOURCE_CASES, activate_production_release, approve_transfer, load_active_memory,
    prepare_campaign_context, record_campaign_usage, require_campaign_memory_usage, transfer_template,
    validate_transfer_approval, validate_transfer_proposal, write_artifact)
from engine.research_v2_release import NAMESPACE, activate, load_bundle, prepare_review
from test_research_v2_release import SyntheticBroker, accepted_all


class NamedSyntheticBroker(SyntheticBroker):
    def __init__(self, root):
        super().__init__(root)
        self.cases = {name: dict(case, case_id=name)
                      for name, case in zip(sorted(SOURCE_CASES), self.cases.values())}


def now():
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def activated(tmp_path):
    root = tmp_path / "SYNTHETIC-release"
    prepare_review(tmp_path / "NOT_OPENED", root, broker_factory=NamedSyntheticBroker)
    accepted_all(root, load_bundle(root))
    activate(root, root / "memory.sqlite")
    pointer = tmp_path / "pointer.json"
    write_artifact(pointer, {"schema_version": "research-v2-active-memory-pointer-v1", "namespace": NAMESPACE,
        "reviewed_lessons": 6, "release_root": "SYNTHETIC-release", "database": "SYNTHETIC-release/memory.sqlite",
        "activation_receipt": "SYNTHETIC-release/activation.json", "legacy_memory_imported": False,
        "usage_record_required": True, "graph_enabled": False, "utility_weight": 0})
    return pointer, tmp_path, load_active_memory(pointer, repo_root=tmp_path)


def target_scope():
    return {k: "SYNTHETIC_EXACT_TARGET_" + k for k in SCOPE_KEYS}


def proposal(active, revision_id="pilot-net_roa@1"):
    value = transfer_template(active, revision_id, target_scope(), author="transfer-author")
    for item in value["changed_dimensions"].values():
        item["rationale"] = "Only the need for a diagnostic is transferred, never the source empirical result."
    value["statements"] = [{"kind": "PROCEDURAL_CAUTION", "text": "자료 부족과 가설 반증을 구분한다.",
                            "source_evidence_ids": [value["source_evidence_id"]]}]
    value["limitations"] = ["다른 범위의 실제 효과는 별도 검증해야 한다."]
    return value


def critic(value):
    return {"proposal_sha256": digest(value), "reviewer": "separate-transfer-critic", "decision": "ACCEPT",
            "checks": dict.fromkeys(CHECKS, True), "issues": [], "rationale": "Procedure only; target effects remain untested.",
            "reviewed_at": now()}


def context(activated, **changes):
    pointer, root, active = activated
    params = {"target_scope": target_scope(), "task_id": "candidate-task", "query": "자료",
              "research_as_of": now(), "repo_root": root}
    return prepare_campaign_context(pointer, **(params | changes))


def check(activated, value, **changes):
    pointer, root, active = activated
    params = {"expected_scope": target_scope(), "task_id": "candidate-task", "repo_root": root}
    return require_campaign_memory_usage(pointer, value, **(params | changes))


def usage(activated, value, **changes):
    pointer, root, active = activated
    params = {"used": {}, "rejected": {}, "actor": "candidate-task", "key": "usage", "repo_root": root}
    return record_campaign_usage(pointer, value, **(params | changes))


def test_cross_scope_is_empty_until_reviewed_and_empty_usage_is_required(activated):
    value = context(activated)
    assert not value["context"] and value["research_reuse_status"] == "NO_MEMORY_INJECTED"
    with pytest.raises(ValueError, match="usage"):
        check(activated, value)
    usage(activated, value)
    assert check(activated, value)["status"] == "MEMORY_USAGE_VERIFIED"


def test_exact_target_transfer_preserves_source_evidence_and_requires_accounting(activated):
    pointer, root, active = activated
    draft = proposal(active)
    approved = approve_transfer(active, draft, critic(draft))
    value = context(activated, transfer_approvals=[approved])
    entry = value["context"][0]
    assert entry["source_scope"] == draft["source_scope"]
    assert entry["source_memory"]["scope"] != entry["target_scope"]
    assert entry["source_memory"]["unknowns"] and entry["source_memory"]["limitations"]
    assert not entry["source_findings_apply_to_target"] and not entry["independent_target_validation"]
    assert entry["applicability"] == "PROCEDURAL_ONLY_NOT_TARGET_EVIDENCE"
    assert "0.123" not in json.dumps(value)
    with pytest.raises(ValueError, match="every"):
        usage(activated, value)
    usage(activated, value, used={entry["entry_id"]: "입력 부족을 반증으로 해석하지 않는 절차에 참고한다."})
    checked = check(activated, value)
    assert checked["used_entry_ids"] == [entry["entry_id"]]
    assert checked["independent_oos_claim"] is False
    assert any(e["kind"] == "USED" for e in active.memory._events())


def test_source_case_can_retrieve_without_transfer_but_new_definition_cannot(activated):
    active = activated[2]
    source = active.sources["pilot-net_roa@1"]["revision"]["scope"]
    exact = target_scope() | source
    value = context(activated, target_scope=exact)
    assert value["context"][0]["applicability"] == "EXACT_SOURCE_SCOPE"
    assert not context(activated, target_scope=exact | {"feature_definition": "different"})["context"]


@pytest.mark.parametrize("change", ["source", "dimension", "citation", "numeric", "wildcard", "claim"])
def test_transfer_draft_cannot_change_source_skip_scope_or_smuggle_results(activated, change):
    active = activated[2]
    value = proposal(active)
    if change == "source":
        value["source_scope"]["market"] = "OTHER"
    elif change == "dimension":
        value["changed_dimensions"].pop("market")
    elif change == "citation":
        value["statements"][0]["source_evidence_ids"] = ["not-in-source"]
    elif change == "numeric":
        value["statements"][0]["text"] = "IC was 0.123"
    elif change == "wildcard":
        value["target_scope"]["market"] = "*"
    else:
        value["target_empirical_validation"] = "VALIDATED"
    with pytest.raises(ValueError):
        validate_transfer_proposal(active, value)


@pytest.mark.parametrize("change", ["author", "hash", "checks", "revise", "future", "issues"])
def test_transfer_requires_independent_exact_review(activated, change):
    active = activated[2]
    value = proposal(active)
    review = critic(value)
    if change == "author":
        review["reviewer"] = value["author"]
    elif change == "hash":
        review["proposal_sha256"] = "wrong"
    elif change == "checks":
        review["checks"]["no_target_empirical_claim"] = False
    elif change == "revise":
        review["decision"] = "REVISE"
    elif change == "future":
        review["reviewed_at"] = "2099-01-01T00:00:00Z"
    else:
        review["issues"] = ["Unresolved"]
    with pytest.raises(ValueError):
        approve_transfer(active, value, review)


def test_transfer_not_available_before_review_and_not_other_target(activated):
    active = activated[2]
    value = proposal(active)
    before = value["proposed_at"]
    approved = approve_transfer(active, value, critic(value))
    with pytest.raises(ValueError, match="knowledge time"):
        validate_transfer_approval(active, approved, target_scope(), before)
    with pytest.raises(ValueError, match="different exact"):
        validate_transfer_approval(active, approved, target_scope() | {"market": "different"}, now())


def test_invalidation_after_usage_blocks_registration_without_rewriting_memory(activated):
    active = activated[2]
    draft = proposal(active)
    approved = approve_transfer(active, draft, critic(draft))
    value = context(activated, transfer_approvals=[approved])
    entry = value["context"][0]
    usage(activated, value, rejected={entry["entry_id"]: "추가 질문과 관련이 낮아 사용하지 않는다."})
    assert check(activated, value)["status"] == "MEMORY_USAGE_VERIFIED"
    active.memory.invalidate_evidence(draft["source_evidence_id"], actor="curator", reason="Fixture provenance revoked.", key="invalidate")
    with pytest.raises(ValueError, match="unavailable"):
        check(activated, value)


def test_forged_context_rehashed_wrong_task_or_scope_is_rejected(activated):
    value = context(activated)
    usage(activated, value)
    forged = deepcopy(value)
    forged["instructions"] = "forged"
    forged.pop("context_sha256")
    forged["context_sha256"] = digest(forged)
    with pytest.raises(ValueError, match="actual audited"):
        check(activated, forged)
    with pytest.raises(ValueError, match="target/task"):
        check(activated, value, task_id="different")
    with pytest.raises(ValueError, match="actor"):
        usage(activated, value, actor="different", key="another-usage")


def test_pointer_does_not_initialize_missing_database_or_import_other_corpus(activated):
    pointer, root, active = activated
    original = json.loads(pointer.read_text())
    pointer.write_text(json.dumps(original | {"database": "not-existing.sqlite"}))
    with pytest.raises(ValueError, match="Activated memory"):
        load_active_memory(pointer, repo_root=root)
    assert not (root / "not-existing.sqlite").exists()
    pointer.write_text(json.dumps(original | {"legacy_memory_imported": True}))
    with pytest.raises(ValueError, match="policy"):
        load_active_memory(pointer, repo_root=root)


def test_repeat_same_context_is_idempotent_and_no_mutation_of_source(activated):
    active = activated[2]
    before = deepcopy(active.sources)
    moment = now()
    first = context(activated, research_as_of=moment)
    assert context(activated, research_as_of=moment) == first
    usage(activated, first)
    usage(activated, first)
    assert active.sources == before


def test_immutable_export_refuses_replacement(tmp_path):
    path = tmp_path / "receipt.json"
    write_artifact(path, {"value": "original"})
    write_artifact(path, {"value": "original"})
    with pytest.raises(ValueError, match="immutable"):
        write_artifact(path, {"value": "changed"})


def test_reviewed_production_activation_appends_without_rewriting_source_or_auto_pointer(activated):
    pointer, root, active = activated
    original = pointer.read_text()
    prior_context = context(activated)
    usage(activated, prior_context)
    new_root = root / "SYNTHETIC-production-release"
    prepare_review(root / "NOT_OPENED", new_root, broker_factory=SyntheticBroker)
    bundle = load_bundle(new_root)
    # Synthetic standalone release format fixture: a production preparer is
    # responsible for building the source exports and restricted review bundle.
    bundle.pop("bundle_sha256")
    bundle["release_mode"] = "PRODUCTION_DISCOVERY"
    bundle["bundle_sha256"] = digest(bundle)
    (new_root / "review-bundle.json").write_text(json.dumps(bundle))
    accepted_all(new_root, bundle)
    result = activate_production_release(pointer, new_root, repo_root=root)
    assert pointer.read_text() == original and not result["pointer_updated"]
    assert result["proposed_pointer"]["reviewed_lessons"] == 12
    assert len(load_active_memory(pointer, repo_root=root).sources) == 6
    assert result == activate_production_release(pointer, new_root, repo_root=root)
    pointer.write_text(json.dumps(result["proposed_pointer"]))
    expanded = load_active_memory(pointer, repo_root=root)
    assert len(expanded.sources) == 12
    assert all(expanded.sources[rid] == source for rid, source in active.sources.items())
    # An additive new release does not invalidate the frozen earlier context.
    assert check(activated, prior_context)["status"] == "MEMORY_USAGE_VERIFIED"
    new_id = next(rid for rid in expanded.sources if rid.startswith("production:"))
    scope = target_scope() | expanded.sources[new_id]["revision"]["scope"]
    value = context(activated, target_scope=scope)
    assert any(entry["source_revision_id"] == new_id for entry in value["context"])


def test_production_activation_requires_explicit_mode_and_reviewed_release(activated):
    pointer, root, active = activated
    with pytest.raises(ValueError, match="production Discovery"):
        activate_production_release(pointer, root / "SYNTHETIC-release", repo_root=root)


def test_total_eligible_memory_count_is_bounded_before_any_retrieval_write(activated):
    active = activated[2]
    approvals = []
    for rid in sorted(active.sources)[:4]:
        draft = proposal(active, rid)
        approvals.append(approve_transfer(active, draft, critic(draft)))
    before = active.memory._events()
    with pytest.raises(ValueError, match="three eligible memories"):
        context(activated, transfer_approvals=approvals)
    assert active.memory._events() == before


def test_total_utf8_budget_rejects_without_truncation_or_retrieval_writes(activated):
    active = activated[2]
    draft = proposal(active)
    draft["limitations"] = ["가" * 3500 + ending for ending in ("나", "다", "라")]
    approval = approve_transfer(active, draft, critic(draft))
    before = active.memory._events()
    with pytest.raises(ValueError, match="UTF-8 byte budget"):
        context(activated, transfer_approvals=[approval])
    assert active.memory._events() == before


def test_context_publishes_whole_receipted_memory_within_total_budget(activated):
    from engine.research_memory_transfer import MAX_CONTEXT_BYTES, MAX_CONTEXT_ITEMS
    from engine.research_memory_v2 import canonical
    active = activated[2]
    draft = proposal(active)
    approval = approve_transfer(active, draft, critic(draft))
    value = context(activated, transfer_approvals=[approval])
    assert len(value["context"]) == 1 <= MAX_CONTEXT_ITEMS
    assert len(canonical(value).encode("utf-8")) <= MAX_CONTEXT_BYTES
    assert value["context"][0]["transfer_approval"] == approval
    assert value["context_budget"] == {"max_items": 3, "max_utf8_bytes": 32768}
