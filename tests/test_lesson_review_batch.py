"""Synthetic-only batch adoption; no live research, DB, or model calls."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from engine.lesson_evidence import digest, review_template
from engine.scientist_review import augment_template, critique_template
from scripts import lesson_review_batch as batch
from scripts.candidate_lessons import refresh_candidate_lessons
from scripts.lessons import read_jsonl


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "research"
    for cid, names, status in (("c", ["f", "g", "h"], "CLOSED_NO_QUALIFIED"),
                               ("sealed", ["private"], "OPEN")):
        write(root / f"campaigns/{cid}/manifest.json", {"campaign_id": cid, "status": status,
              "oos": {"status": "SEALED"}, "epochs": [{"epoch_id": "e"}]})
        for name in names:
            write(root / f"runs/{name}/result.json", {"campaign_id": cid, "epoch_id": "e",
                "factor": {"name": name, "definition_hash": name, "family": "test"},
                "research_spec": {"thesis": "synthetic hypothesis " + name},
                "evaluation": {"metrics": {"ic": 987.654}, "checks": [
                    {"tier": "T2", "name": "예측력", "passed": False, "value": 987.654}]}})
    def load_epoch(_root, cid, _eid):
        names = ["f", "g", "h"] if cid == "c" else ["private"]
        return {"status": "CLOSED", "candidates": [
            {"name": n, "cycle_id": n, "definition_hash": n, "verdict": "REJECT"} for n in names]}
    monkeypatch.setattr("scripts.candidate_lessons.epochs.load_epoch", load_epoch)
    rows = refresh_candidate_lessons(root)
    h = next(r for r in rows if r["record_id"] == "c/e/h")
    h["review"] = {"status": "REVIEWED", "basis": h["review_basis"],
                   "economic_interpretation": "기존 해석", "general_lesson": "기존 교훈", "scope": "기존 범위"}
    (root / "memory/candidate_lessons.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (root / "KNOWLEDGE.md").write_text("## Frozen research state\n- Synthetic frozen context\n")
    write(root / "memory/lesson_reviews/existing.json", {"preserve": "exact old bytes"})
    return root


def staged(workspace, tmp_path):
    output = tmp_path / "prepared"
    manifest = batch.prepare_batch(workspace, ["c/e/g", "c/e/f"], output)
    items = []
    for entry in manifest["entries"]:
        rid = entry["record_id"]
        review = json.loads((output / entry["template_path"]).read_text())
        packet = json.loads((workspace / entry["packet_path"]).read_text())
        review.update({"status": "REVIEWED", "lesson_key": "synthetic_principle",
            "observations": [{"text": "검사상 예측력이 통과하지 못함", "evidence_ids": ["discovery.check.0"]}],
            "economic_interpretation": "검사 실패만으로 경제적 원인을 식별하지 못한다",
            "general_lesson": "측정의 의미와 가격 예측의 검증은 구분한다",
            "scope": "합성 표본에만 해당하며 인과 식별은 미확인",
            "alternative_explanations": ["입력 측정과 동반 노출이 다른 설명일 수 있다"],
            "unresolved": ["직접 경제적 변화와 비용 기록 없음"],
            "follow_up": {"question": "경제적 경로와 노출을 구분할 수 있는가", "data_needed": "당시 경제 관측",
                          "distinguishes": ["mechanism", "rival"], "execution": "PROPOSED_NOT_RUN"}})
        for explanation in review["explanations"]:
            explanation.update(claim="확인되지 않은 경쟁 설명", distinguishing_observation="동일 표본의 별도 경제 관측")
        critic = critique_template(review, packet)
        critic.update(decision="ACCEPT", findings=[{"severity": "INFO", "issue": "합성 fixture 검토", "evidence_ids": ["discovery.check.0"]}])
        critic["checks"] = {k: True for k in critic["checks"]}
        name = rid.split("/")[-1]
        write(output / f"{name}.review.json", review)
        write(output / f"{name}.critic.json", critic)
        items.append({"record_id": rid, "review_path": f"{name}.review.json", "critic_path": f"{name}.critic.json",
                      "analyst_agent_id": "synthetic-analyst", "critic_agent_id": "synthetic-critic"})
    write(output / "submissions.json", {"items": items})
    return output, manifest, items


def current_rows(root):
    return {r["record_id"]: r for r in read_jsonl(root / "memory/candidate_lessons.jsonl")}


def assert_no_adoption(root):
    rows = current_rows(root)
    assert "review" not in rows["c/e/f"] and "review" not in rows["c/e/g"]
    assert set(p.name for p in (root / "memory/lesson_reviews").glob("*.json")) == {"existing.json"}


def test_prepare_sorted_empty_scientist_templates_and_explicit_allowlist(workspace, tmp_path):
    before = current_rows(workspace)
    output = tmp_path / "prepare"
    manifest = batch.prepare_batch(workspace, ["c/e/g", "c/e/f"], output)
    assert [e["record_id"] for e in manifest["entries"]] == ["c/e/f", "c/e/g"]
    for entry in manifest["entries"]:
        template = json.loads((output / entry["template_path"]).read_text())
        assert template["status"] == "DRAFT"
        assert template["scientist_version"] == "mechanism-scientist-v1"
        assert "critic" not in template and template["general_lesson"] == ""
        assert "987.654" not in json.dumps(template)
    assert current_rows(workspace)["c/e/h"] == before["c/e/h"]
    assert current_rows(workspace)["sealed/e/private"] == before["sealed/e/private"]
    assert_no_adoption(workspace)


@pytest.mark.parametrize("ids", [["c/e/f", "c/e/f"], ["sealed/e/private"], ["c/e/h"], ["absent"]])
def test_prepare_rejects_duplicates_sealed_reviewed_and_missing(workspace, tmp_path, ids):
    with pytest.raises(ValueError):
        batch.prepare_batch(workspace, ids, tmp_path / "new")
    assert not (tmp_path / "new").exists()


def test_batch_one_authentication_one_knowledge_render_preserves_others(workspace, tmp_path, monkeypatch):
    output, manifest, items = staged(workspace, tmp_path)
    before = current_rows(workspace)
    old_archive = (workspace / "memory/lesson_reviews/existing.json").read_bytes()
    calls = {"auth": 0, "render": 0}
    original = batch.refresh_candidate_lessons
    def authenticate(root):
        calls["auth"] += 1
        return original(root)
    monkeypatch.setattr(batch, "refresh_candidate_lessons", authenticate)
    from scripts import knowledge
    render = knowledge._render_knowledge
    def render_once(*args):
        calls["render"] += 1
        return render(*args)
    monkeypatch.setattr(knowledge, "_render_knowledge", render_once)
    receipt = batch.save_batch(workspace, output / "manifest.json", output / "submissions.json")
    assert calls == {"auth": 1, "render": 1}
    assert len(receipt["items"]) == 2
    rows = current_rows(workspace)
    assert rows["c/e/h"] == before["c/e/h"]
    assert rows["sealed/e/private"] == before["sealed/e/private"]
    for rid in ("c/e/f", "c/e/g"):
        assert rows[rid]["review_validation"] == "CURRENT"
        review = rows[rid]["review"]
        assert (workspace / f"memory/lesson_reviews/{digest(review)}.json").exists()
    text = (workspace / "KNOWLEDGE.md").read_text()
    assert "synthetic_principle" in text and "987.654" not in text and "sealed/e/private" not in text
    assert (workspace / "memory/lesson_reviews/existing.json").read_bytes() == old_archive
    assert not (workspace / "memory/.lesson_review_batch_transaction.json").exists()
    with pytest.raises(ValueError, match="already reviewed"):
        batch.save_batch(workspace, output / "manifest.json", output / "submissions.json")


def test_individual_subsets_of_one_allowlist_can_be_saved_in_sequence(workspace, tmp_path):
    output, _, items = staged(workspace, tmp_path)
    for item in items:
        write(output / "subset.json", {"items": [item]})
        batch.save_batch(workspace, output / "manifest.json", output / "subset.json")
    assert current_rows(workspace)["c/e/f"]["review_validation"] == "CURRENT"
    assert current_rows(workspace)["c/e/g"]["review_validation"] == "CURRENT"


@pytest.mark.parametrize("change", ["duplicate", "same_agent", "bad_critic", "bad_second_review", "outside", "missing_diagnostic"])
def test_invalid_partial_batch_adopts_nothing(workspace, tmp_path, change):
    output, _, items = staged(workspace, tmp_path)
    if change == "duplicate":
        items.append(items[0])
    elif change == "same_agent":
        items[-1]["critic_agent_id"] = items[-1]["analyst_agent_id"]
    elif change == "outside":
        items[-1]["record_id"] = "sealed/e/private"
    else:
        key = "critic_path" if change == "bad_critic" else "review_path"
        path = output / items[-1][key]
        data = json.loads(path.read_text())
        if change == "bad_critic":
            data["review_sha256"] = "wrong"
        elif change == "missing_diagnostic":
            data["missing_evidence"] = []
        else:
            data["basis"] = "wrong"
        write(path, data)
    write(output / "submissions.json", {"items": items})
    before = (workspace / "KNOWLEDGE.md").read_bytes()
    with pytest.raises(ValueError):
        batch.save_batch(workspace, output / "manifest.json", output / "submissions.json")
    assert_no_adoption(workspace)
    assert (workspace / "KNOWLEDGE.md").read_bytes() == before


@pytest.mark.parametrize("change", ["manifest", "epoch", "packet", "basis"])
def test_prepared_inputs_changed_fail_closed(workspace, tmp_path, change):
    output, manifest, _ = staged(workspace, tmp_path)
    if change == "manifest":
        with (workspace / "campaigns/c/manifest.json").open("a") as stream:
            stream.write("\n")
    elif change == "epoch":
        write(workspace / "campaigns/c/epochs/e.json", {"changed": True})
    elif change == "packet":
        write(workspace / manifest["entries"][0]["packet_path"], {"changed": True})
    else:
        manifest["entries"][0]["review_basis"] = "wrong"
        manifest["manifest_sha256"] = digest({k: v for k, v in manifest.items() if k != "manifest_sha256"})
        write(output / "manifest.json", manifest)
    with pytest.raises(ValueError):
        batch.save_batch(workspace, output / "manifest.json", output / "submissions.json")
    assert_no_adoption(workspace)


@pytest.mark.parametrize("target", ["source", "submission", "ledger", "packet"])
def test_change_during_validation_aborts_before_adoption(workspace, tmp_path, monkeypatch, target):
    output, manifest, _ = staged(workspace, tmp_path)
    original = batch.validate_review
    changed = False
    def racing(review, record, packet):
        nonlocal changed
        original(review, record, packet)
        if not changed:
            changed = True
            path = {"source": workspace / "campaigns/c/manifest.json",
                    "submission": output / "submissions.json",
                    "ledger": workspace / "memory/candidate_lessons.jsonl",
                    "packet": workspace / manifest["entries"][0]["packet_path"]}[target]
            with path.open("a") as stream:
                stream.write("\n")
    monkeypatch.setattr(batch, "validate_review", racing)
    with pytest.raises(ValueError, match="changed"):
        batch.save_batch(workspace, output / "manifest.json", output / "submissions.json")
    assert_no_adoption(workspace)


def test_io_failure_rolls_back_archives_and_knowledge_before_ledger(workspace, tmp_path, monkeypatch):
    output, _, _ = staged(workspace, tmp_path)
    knowledge_before = (workspace / "KNOWLEDGE.md").read_bytes()
    replace = batch.os.replace
    failed = False
    def fail_ledger(source, destination):
        nonlocal failed
        if not failed and Path(destination).name == "candidate_lessons.jsonl" and Path(source).suffix == ".new":
            failed = True
            raise OSError("synthetic disk failure")
        return replace(source, destination)
    monkeypatch.setattr(batch.os, "replace", fail_ledger)
    with pytest.raises(OSError, match="synthetic disk"):
        batch.save_batch(workspace, output / "manifest.json", output / "submissions.json")
    assert_no_adoption(workspace)
    assert (workspace / "KNOWLEDGE.md").read_bytes() == knowledge_before
    assert not (workspace / "memory/.lesson_review_batch_transaction.json").exists()


def test_active_writer_and_crash_journal_fail_closed(workspace, tmp_path):
    with batch._writer(workspace):
        with pytest.raises(ValueError, match="writer"):
            batch.prepare_batch(workspace, ["c/e/f"], tmp_path / "blocked")
    write(workspace / "memory/.lesson_review_batch_transaction.json", {"state": "PREPARED"})
    with pytest.raises(ValueError, match="recovery"):
        batch.prepare_batch(workspace, ["c/e/f"], tmp_path / "blocked")


def test_submitted_paths_cannot_read_raw_research(workspace, tmp_path):
    output, _, items = staged(workspace, tmp_path)
    items[0]["review_path"] = str(workspace / "runs/private/result.json")
    write(output / "submissions.json", {"items": items})
    with pytest.raises(ValueError, match="raw research"):
        batch.save_batch(workspace, output / "manifest.json", output / "submissions.json")
    assert_no_adoption(workspace)


def test_ledger_change_after_archiving_is_detected_and_archives_rolled_back(workspace, tmp_path, monkeypatch):
    output, _, _ = staged(workspace, tmp_path)
    original = batch.os.link
    changed = False
    def racing(source, target):
        nonlocal changed
        original(source, target)
        if not changed:
            changed = True
            with (workspace / "memory/candidate_lessons.jsonl").open("a") as stream:
                stream.write("\n")
    monkeypatch.setattr(batch.os, "link", racing)
    with pytest.raises(ValueError, match="changed"):
        batch.save_batch(workspace, output / "manifest.json", output / "submissions.json")
    assert_no_adoption(workspace)


def test_normal_knowledge_refresh_always_authenticates(workspace, monkeypatch):
    from scripts import candidate_lessons, knowledge
    called = []
    original = candidate_lessons.refresh_candidate_lessons
    def record_call(root):
        called.append(root)
        return original(root)
    monkeypatch.setattr(candidate_lessons, "refresh_candidate_lessons", record_call)
    knowledge.refresh_knowledge(workspace)
    assert called == [workspace]


def test_atomic_batch_preserves_restrictive_output_modes(workspace, tmp_path):
    output, _, _ = staged(workspace, tmp_path)
    ledger = workspace / "memory/candidate_lessons.jsonl"
    knowledge = workspace / "KNOWLEDGE.md"
    ledger.chmod(0o600)
    knowledge.chmod(0o600)
    batch.save_batch(workspace, output / "manifest.json", output / "submissions.json")
    assert ledger.stat().st_mode & 0o777 == 0o600
    assert knowledge.stat().st_mode & 0o777 == 0o600
