"""Synthetic broker fixtures only; no real results or actual LLM review claims."""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from engine.research_memory_v2 import MemoryCapability, MemoryStore, digest
from engine.research_v2_release import (ARMS, CHECKS, NAMESPACE, activate, draft_template, load_bundle,
                                       memory_arguments, prepare_review, public_filter, stage,
                                       validate_critic, validate_draft)


class SyntheticBroker:
    def __init__(self, root):
        self.cases = {f"fixture_{i}": {"case_id": f"fixture_{i}", "data_contract_sha256": digest(f"contract{i}"),
                                      "definition_sha256": digest(f"definition{i}")} for i in range(6)}
        self.manifest = {"manifest_sha256": digest("SYNTHETIC_MANIFEST_NOT_ACTUAL_RESEARCH"),
                         "factor_admission_trials": 0, "oos_reads": 0,
                         "discovery_snapshot_sha256": digest("SYNTHETIC_SNAPSHOT")}
        self.frozen = {"signal_start": "2016-02", "signal_end": "2020-12", "regime_contract_sha256": digest("REGIME_FIXTURE")}

    def export(self, cid, arm):
        case = self.cases[cid]
        evidence = []
        for name, status in (("association", "COMPUTED"), ("economic_link", "NOT_COMPUTED")):
            response = {"diagnostic_id": name, "status": status, "scope": "FROZEN_DISCOVERY_ONLY",
                        "metrics": {"synthetic_test_statistic": 0.123} if status == "COMPUTED" else {},
                        "evidence_scope": {"contract_sha256": case["data_contract_sha256"]},
                        "causal_identification": False, "limitations": ["SYNTHETIC_TEST_NOT_REAL_RESULT"],
                        "missing_datasets": [] if status == "COMPUTED" else ["FIXTURE_ECONOMIC_INPUT"]}
            evidence.append({"evidence_id": "e-" + name, "diagnostic_id": name,
                             "response": response, "response_sha256": digest(response)})
        created = {"type": "CREATED", "contract": {"data_contract_sha256": case["data_contract_sha256"]}}
        terminal = {"type": "RESULT", "status": "STOPPED", "decision": {
            "kind": "STOP", "payload": {"conclusion": "INCONCLUSIVE", "observations": [],
                                         "mechanism_identified": False, "limitations": "SYNTHETIC_FIXTURE"}}}
        return {"case_id": cid, "arm": arm, "pilot_manifest_sha256": self.manifest["manifest_sha256"],
                "mode": "REAL_DISCOVERY_REANALYSIS", "state": {"state": "STOPPED", "evidence": evidence},
                "events": [created, terminal], "explanation_complete": False,
                "unperformed_required_diagnostics": ["regime_interaction"]}


def prepared(tmp_path, factory=SyntheticBroker):
    root = tmp_path / "release-fixture"
    prepare_review(tmp_path / "NO_REAL_PILOT_IS_OPENED", root, broker_factory=factory)
    return root, load_bundle(root)


def draft_for(bundle, cid):
    draft = draft_template(bundle, cid)
    ids = bundle["cases"][cid]["evidence_ids"]
    draft.update(author="synthetic-fixture-analyst", title_ko="관측된 관계와 미확인 경제 경로를 구분하기",
                 facts=[{"text": "관계 진단은 수행됐지만 경제 경로 진단은 미산출로 남았다.", "evidence_ids": ids}],
                 interpretations=[{"text": "자료 부족은 경제 가설의 반증과 다르다.", "evidence_ids": ids}],
                 unknowns=["경제 경로와 다른 설명의 기여는 미확인이다."],
                 limitations=["합성 절차 시험이며 실제 시장 증거가 아니다.", "반복 해석은 독립 재현이 아니다."],
                 competing_explanations=[
                     {"explanation": "경제적 특성의 관계일 수 있다.", "status": "UNTESTED", "evidence_ids": [], "distinguishing_evidence": "같은 범위의 경제 결과가 필요하다."},
                     {"explanation": "동반 노출의 관계일 수 있다.", "status": "UNTESTED", "evidence_ids": [], "distinguishing_evidence": "같은 표본의 통제 비교가 필요하다."}],
                 next_tests=[{"question": "경제 경로를 측정할 수 있는가?", "design": "미산출 자료를 확보한 뒤 새 계약에서 검토한다.",
                              "status": "PROPOSED_NOT_RUN", "evidence_ids": ids}])
    return draft


def critic_for(bundle, draft):
    return {"draft_sha256": digest(draft), "evidence_bundle_sha256": bundle["bundle_sha256"],
            "reviewer": "synthetic-fixture-independent-critic", "decision": "ACCEPT", "issues": [],
            "checks": dict.fromkeys(CHECKS, True), "reviewed_at": datetime.now(timezone.utc).isoformat()}


def accepted_all(root, bundle):
    for cid in bundle["cases"]:
        draft = draft_for(bundle, cid)
        stage(root, draft, critic_for(bundle, draft))


def test_prepare_requires_all_twelve_sessions_explicitly_closed(tmp_path):
    class Pending(SyntheticBroker):
        def export(self, cid, arm):
            value = super().export(cid, arm)
            if cid == "fixture_5" and arm == "HOST_LLM":
                value["state"]["state"] = "ACTIVE"
            return value
    with pytest.raises(ValueError, match="twelve"):
        prepared(tmp_path, Pending)
    assert not (tmp_path / "release-fixture").exists()


def test_prepare_deduplicates_same_case_report_across_arms_and_preserves_missing_status(tmp_path):
    root, bundle = prepared(tmp_path)
    assert len(bundle["cases"]) == 6 and len(bundle["evidence"]) == 12
    case = bundle["cases"]["fixture_0"]
    assert len(case["sources"]) == 2 and len(case["evidence_ids"]) == 2
    assert set(case["source_statuses"].values()) == {"COMPUTED", "NOT_COMPUTED"}
    assert all(bundle["evidence"][eid]["source_arms"] == list(ARMS) for eid in case["evidence_ids"])
    assert len({bundle["evidence"][eid]["root_id"] for eid in case["evidence_ids"]}) == 1
    assert not bundle["same_case_arms_are_independent_evidence"]
    assert (root / "templates" / "fixture_0.json").exists()
    with pytest.raises(FileExistsError):
        prepare_review(tmp_path / "NOT_READ", root, broker_factory=SyntheticBroker)


def test_invalid_contract_or_non_discovery_source_is_rejected(tmp_path):
    class BadScope(SyntheticBroker):
        def export(self, cid, arm):
            value = super().export(cid, arm)
            response = value["state"]["evidence"][0]["response"]
            response["scope"] = "SEALED_OOS"
            value["state"]["evidence"][0]["response_sha256"] = digest(response)
            return value
    with pytest.raises(ValueError, match="unauthorized"):
        prepared(tmp_path, BadScope)


def test_later_read_prompt_does_not_change_frozen_terminal_export(tmp_path):
    normal = SyntheticBroker(tmp_path).export("fixture_0", "HOST_LLM")
    from engine.research_v2_release import _closed_export
    changed = deepcopy(normal)
    changed["events"].append({"type": "PROMPT", "packet": "later read-only delivery"})
    case = SyntheticBroker(tmp_path).cases["fixture_0"]
    assert _closed_export(normal, case, "HOST_LLM", normal["pilot_manifest_sha256"]) == _closed_export(changed, case, "HOST_LLM", normal["pilot_manifest_sha256"])


def test_draft_requires_citations_qualitative_prose_unchanged_status_and_unrun_proposals(tmp_path):
    _, bundle = prepared(tmp_path)
    good = draft_for(bundle, "fixture_0")
    assert validate_draft(bundle, good) == digest(good)
    for change in (
        {"title_ko": "English title only"}, {"causal_claim": True}, {"source_statuses": {}},
        {"facts": [{"text": "검사했다.", "evidence_ids": ["missing-source"]}]},
        {"facts": [{"text": "IC가 0.123이다.", "evidence_ids": good["facts"][0]["evidence_ids"]}]},
        {"competing_explanations": []}, {"unknowns": []},
        {"next_tests": [dict(good["next_tests"][0], status="COMPLETED")]},
    ):
        with pytest.raises(ValueError):
            validate_draft(bundle, good | change)


def test_critic_requires_independent_exact_hash_full_checks_and_accept(tmp_path):
    _, bundle = prepared(tmp_path)
    draft = draft_for(bundle, "fixture_0")
    good = critic_for(bundle, draft)
    assert validate_critic(bundle, draft, good) == digest(good)
    for change in ({"reviewer": draft["author"]}, {"draft_sha256": "changed"}, {"decision": "REVISE"},
                   {"checks": {}}, {"checks": dict(good["checks"], no_causal_claim=False)},
                   {"issues": [{"severity": "MAJOR", "note": "Unsupported", "evidence_ids": []}]},
                   {"reviewed_at": "2000-01-01T00:00:00Z"}):
        with pytest.raises(ValueError):
            validate_critic(bundle, draft, good | change)


def test_public_guard_denies_modified_envelope_and_source_tampering(tmp_path):
    root, bundle = prepared(tmp_path)
    draft = draft_for(bundle, "fixture_0")
    accepted = stage(root, draft, critic_for(bundle, draft))
    guard, envelope = public_filter(root), accepted["envelope"]
    now = datetime.now(timezone.utc).isoformat()
    assert guard(envelope, now)
    assert not guard(envelope | {"payload": "forged"}, now)
    assert not guard(envelope, "2000-01-01T00:00:00Z")
    source = root / bundle["cases"]["fixture_0"]["sources"][0]["path"]
    source.write_text("{}")
    assert not guard(envelope, now)


def test_accepted_draft_critic_tampering_revokes_guard(tmp_path):
    root, bundle = prepared(tmp_path)
    draft = draft_for(bundle, "fixture_0")
    critic = critic_for(bundle, draft)
    accepted = stage(root, draft, critic)
    (root / "critics" / f"{digest(critic)}.json").write_text(json.dumps(critic | {"decision": "REJECT"}))
    assert not public_filter(root)(accepted["envelope"], datetime.now(timezone.utc).isoformat())


def test_activation_requires_every_case_and_is_idempotent_exact_transform(tmp_path):
    root, bundle = prepared(tmp_path)
    with pytest.raises(ValueError, match="All six"):
        activate(root, tmp_path / "memory.sqlite")
    accepted_all(root, bundle)
    result = activate(root, tmp_path / "memory.sqlite")
    assert result == activate(root, tmp_path / "memory.sqlite")
    assert len(result["receipts"]) == 6 and not result["legacy_memory_imported"]
    mem = MemoryStore(tmp_path / "memory.sqlite", namespace=NAMESPACE, public_filter=public_filter(root))
    proposals = [e["payload"] for e in mem._events() if e["kind"] == "PROPOSED"]
    assert len(proposals) == 6
    for proposal in proposals:
        cid = proposal["claim_id"].removeprefix("pilot-")
        accepted = json.loads((root / "accepted" / f"{cid}.json").read_text())
        draft = json.loads((root / "drafts" / f"{accepted['draft_sha256']}.json").read_text())
        args = memory_arguments(draft, accepted["envelope"])
        assert proposal["facts"] == args["facts"]
        assert proposal["interpretations"] == args["interpretations"]
        assert proposal["unknowns"] == args["unknowns"]
        assert any("NOT_COMPUTED" in x for x in proposal["limitations"])
        assert any("PROPOSED_NOT_RUN" in x for x in proposal["unknowns"])
        assert "0.123" not in json.dumps(proposal)
    assert all(not r["new_model_review_performed"] for r in result["receipts"])


def test_memory_retrieval_reauthenticates_accepted_qualitative_release(tmp_path):
    root, bundle = prepared(tmp_path)
    accepted_all(root, bundle)
    activate(root, tmp_path / "memory.sqlite")
    accepted = json.loads((root / "accepted" / "fixture_0.json").read_text())
    mem = MemoryStore(tmp_path / "memory.sqlite", namespace=NAMESPACE, public_filter=public_filter(root))
    cap = MemoryCapability("release-test", NAMESPACE, bundle["cases"]["fixture_0"]["scope"],
                           (accepted["envelope"]["evidence_id"],), "2099-01-01T00:00:00Z")
    receipt = mem.retrieve("자료", scope=cap.scope, research_as_of=datetime.now(timezone.utc).isoformat(),
                           capability=cap, task_id="synthetic-retrieval-test", key="retrieve")
    assert receipt["injected_revision_ids"] == ["pilot-fixture_0@1"]
    source = root / bundle["cases"]["fixture_0"]["sources"][0]["path"]
    source.write_text("{}")
    empty = mem.retrieve("자료", scope=cap.scope, research_as_of=datetime.now(timezone.utc).isoformat(),
                         capability=cap, task_id="synthetic-retrieval-test", key="revoked")
    assert empty["context"] == []
