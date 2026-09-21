"""Synthetic-only checkout portability and immutable legacy review contracts."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from engine.lesson_evidence import (
    LEGACY_VERSION, VERSION, build_packet, digest, portable_provenance,
    review_template, validate_review,
)
from scripts.candidate_lessons import (
    evidence_packet_path, refresh_candidate_lessons, render_grouped_lessons,
)
from scripts.lesson_review import current_evidence, save_review
from tests.test_candidate_lessons import completed_review, setup_batch


def _write_legacy(root, *, reviewed=True, scientist=False):
    """Write the exact old exporter contract, including its absolute locator."""
    record = refresh_candidate_lessons(root)[0]
    record["evidence"].pop("result_identity_contract")
    record["evidence"]["result"] = str(root / "runs/x/result.json")
    payload = json.loads((root / "runs/x/result.json").read_text())
    packet = build_packet(record, payload, None, schema_version=LEGACY_VERSION)
    sha = digest(packet)
    packet_path = evidence_packet_path(root, sha)
    # Deliberately noncanonical whitespace: a refresh must not rewrite bytes.
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=1) + "\n\n")
    record["evidence_packet"] = {
        "path": str(packet_path), "sha256": sha,
        "missing": [key for key, value in packet["diagnostics"].items()
                    if value["status"] != "AVAILABLE"],
    }
    record["review_basis"] = digest({
        "validation": record["validation"], "evidence": record["evidence"],
        "packet_sha256": sha,
    })
    review = review_template(record, packet)
    review.update({
        "status": "REVIEWED", "lesson_key": "measurement_vs_prediction",
        "observations": [{"text": "예측력 검사가 통과하지 못함",
                          "evidence_ids": ["discovery.check.0"]}],
        "economic_interpretation": "다른 노출이 작용했을 가능성은 있으나 원인은 미확인",
        "general_lesson": "경제적 측정과 가격 예측을 구분해야 한다",
        "scope": "현재 표본에 한정하며 독립 재현은 미확인",
        "alternative_explanations": ["동반 노출도 설명이 될 수 있음"],
        "unresolved": ["실적 변화 자료가 없음"],
    })
    if scientist:
        from tests.test_scientist_review import accept, analysis
        review = analysis(record, packet)
        review["critic"] = accept(review, packet)
    if reviewed:
        validate_review(review, record, packet)
        record["review"] = review
        record["review_validation"] = "CURRENT"
        archive = root / "memory/lesson_reviews" / f"{digest(review)}.json"
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_text(json.dumps(review, ensure_ascii=False, indent=1) + "\n\n")
    (root / "memory/candidate_lessons.jsonl").write_text(json.dumps(record, ensure_ascii=False) + "\n")
    return record, packet, review


def test_fresh_packets_and_bases_are_identical_across_checkouts(tmp_path, monkeypatch):
    first, second = tmp_path / "checkout-a/research", tmp_path / "checkout-b/research"
    setup_batch(first, monkeypatch, "CLOSED_NO_QUALIFIED")
    setup_batch(second, monkeypatch, "CLOSED_NO_QUALIFIED")
    records = [refresh_candidate_lessons(root)[0] for root in (first, second)]
    assert records[0]["review_basis"] == records[1]["review_basis"]
    assert records[0]["evidence_packet"]["sha256"] == records[1]["evidence_packet"]["sha256"]
    for root, record in zip((first, second), records):
        packet = json.loads(evidence_packet_path(root, record["evidence_packet"]["sha256"]).read_text())
        assert packet["schema_version"] == VERSION
        assert packet["provenance"]["result"] == "runs/x/result.json"
        assert packet["provenance"]["result_identity_contract"] == "research-root-relative-v1"
        assert str(tmp_path) not in json.dumps(packet)


def test_relative_and_absolute_root_keep_the_same_accepted_review(tmp_path, monkeypatch):
    root = tmp_path / "research"
    setup_batch(root, monkeypatch, "CLOSED_NO_QUALIFIED")
    _, _, review = completed_review(root)
    save_review(root, review)
    monkeypatch.chdir(tmp_path)
    record, packet = current_evidence(Path("research"), "c/e/f")
    assert record["review"] == review
    assert record["review_validation"] == "CURRENT"
    assert digest(packet) == review["packet_sha256"]
    save_review(Path("research"), review)


@pytest.mark.parametrize("reviewed", [False, True])
def test_legacy_packet_and_review_are_unchanged_after_clone(tmp_path, monkeypatch, reviewed):
    original = tmp_path / "old/research"
    cloned = tmp_path / "new/research"
    setup_batch(original, monkeypatch, "CLOSED_NO_QUALIFIED")
    before, packet, review = _write_legacy(original, reviewed=reviewed)
    sha = digest(packet)
    old_packet_bytes = evidence_packet_path(original, sha).read_bytes()
    shutil.copytree(original, cloned)
    # Make the stored old locator unusable, proving it is never read.
    original.rename(tmp_path / "relocated-original")
    after, current_packet = current_evidence(cloned, "c/e/f")
    assert current_packet == packet
    assert after["review_basis"] == before["review_basis"]
    assert after["evidence_packet"]["sha256"] == sha
    assert evidence_packet_path(cloned, sha).read_bytes() == old_packet_bytes
    assert review_template(after, current_packet)["schema_version"] == LEGACY_VERSION
    if reviewed:
        archive = cloned / "memory/lesson_reviews" / f"{digest(review)}.json"
        archive_bytes = archive.read_bytes()
        assert after["review"] == review
        assert after["review_validation"] == "CURRENT"
        assert review["general_lesson"] in render_grouped_lessons([after])
        save_review(cloned, review)
        assert archive.read_bytes() == archive_bytes
        assert evidence_packet_path(cloned, sha).read_bytes() == old_packet_bytes


@pytest.mark.parametrize("change", ["source", "validation", "logical_identity", "missing_packet"])
def test_legacy_compatibility_does_not_bypass_changed_evidence(tmp_path, monkeypatch, change):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    before, packet, review = _write_legacy(tmp_path)
    old_path = evidence_packet_path(tmp_path, digest(packet))
    old_bytes = old_path.read_bytes()
    if change == "source":
        path = tmp_path / "runs/x/result.json"
        payload = json.loads(path.read_text())
        payload["evaluation"]["metrics"]["ic"] = 123.456
        path.write_text(json.dumps(payload))
    elif change == "validation":
        monkeypatch.setattr("scripts.candidate_lessons.epochs.load_epoch", lambda *args: {
            "status": "CLOSED", "candidates": [{"name": "f", "cycle_id": "x",
                "definition_hash": "h", "verdict": "NEEDS_REVIEW"}],
        })
    elif change == "logical_identity":
        packet["provenance"]["epoch"] = "other-epoch"
        sha = digest(packet)
        evidence_packet_path(tmp_path, sha).write_text(json.dumps(packet))
        before["evidence_packet"]["sha256"] = sha
        (tmp_path / "memory/candidate_lessons.jsonl").write_text(json.dumps(before) + "\n")
    else:
        old_path.rename(old_path.with_suffix(".unavailable"))
    after = refresh_candidate_lessons(tmp_path)[0]
    assert after["review"] == review
    assert after["review_validation"] == "STALE_OR_INVALID"
    assert review["general_lesson"] not in render_grouped_lessons([after])
    if change != "missing_packet":
        assert old_path.read_bytes() == old_bytes
    with pytest.raises(ValueError, match="stale"):
        save_review(tmp_path, review)


def test_tampered_legacy_archive_is_not_rewritten_or_accepted(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    record, packet, _ = _write_legacy(tmp_path)
    path = evidence_packet_path(tmp_path, digest(packet))
    packet["source_sha256"] = "f" * 64
    path.write_text(json.dumps(packet))
    corrupted = path.read_bytes()
    with pytest.raises(ValueError, match="packet hash mismatch"):
        refresh_candidate_lessons(tmp_path)
    assert path.read_bytes() == corrupted


def test_legacy_review_still_requires_current_release(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    _, _, review = _write_legacy(tmp_path)
    path = tmp_path / "campaigns/c/manifest.json"
    payload = json.loads(path.read_text())
    payload["status"] = "OPEN"
    path.write_text(json.dumps(payload))
    after = refresh_candidate_lessons(tmp_path)[0]
    assert after["visibility"] == "PENDING"
    assert after["review_validation"] == "STALE_OR_INVALID"
    with pytest.raises(ValueError, match="released"):
        save_review(tmp_path, review)


def test_legacy_scientist_critic_remains_exactly_bound_after_clone(tmp_path, monkeypatch):
    from engine.mechanism_capture import capture_discovery
    from tests.test_mechanism_capture import fixture
    original, cloned = tmp_path / "old/research", tmp_path / "new/research"
    setup_batch(original, monkeypatch, "CLOSED_NO_QUALIFIED")
    panel, frame, factor, result, campaign = fixture()
    factor.definition_hash = "h"
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    path = original / "runs/x/result.json"
    payload = json.loads(path.read_text())
    payload["mechanism_study"] = study
    path.write_text(json.dumps(payload))
    source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr("scripts.candidate_lessons.epochs.load_epoch", lambda *args: {
        "status": "CLOSED", "candidates": [{"name": "f", "cycle_id": "x",
            "definition_hash": "h", "verdict": "REJECT",
            "discovery_result_artifact_sha256": source_sha}],
    })
    before, packet, review = _write_legacy(original, scientist=True)
    shutil.copytree(original, cloned)
    record, current = current_evidence(cloned, "c/e/f")
    assert current == packet
    assert record["review_basis"] == before["review_basis"]
    assert record["review"]["critic"] == review["critic"]
    assert record["review_validation"] == "CURRENT"
    validate_review(review, record, current)
    save_review(cloned, review)


@pytest.mark.parametrize("result", ["runs/other/result.json", "runs/../x/result.json", "/etc/passwd"])
def test_portable_identity_rejects_mismatched_or_traversing_locator(result):
    with pytest.raises(ValueError, match="cycle"):
        portable_provenance({"cycle": "x", "result": result})


def test_unknown_schema_cannot_be_treated_as_unstructured_legacy_review(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    record, packet, review = completed_review(tmp_path)
    review["schema_version"] = "lesson-evidence-unreviewed"
    record["review"] = review
    record["review_validation"] = "CURRENT"
    assert review["general_lesson"] not in render_grouped_lessons([record])
    with pytest.raises(ValueError, match="stale"):
        validate_review(review, record, packet)
