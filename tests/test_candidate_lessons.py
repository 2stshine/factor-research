import json
from copy import deepcopy
from pathlib import Path
import hashlib

import pytest

from engine.lesson_evidence import digest, review_template, validate_review
from scripts.lesson_review import current_evidence, save_review

from scripts.candidate_lessons import refresh_candidate_lessons, render_grouped_lessons


def setup_batch(tmp_path, monkeypatch, status="OPEN"):
    directory = tmp_path / "campaigns/c"
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(json.dumps({"campaign_id": "c", "status": status,
        "oos": {"status": "SEALED"}, "epochs": [{"epoch_id": "e"}]}))
    monkeypatch.setattr("scripts.candidate_lessons.epochs.load_epoch", lambda *a: {
        "status": "CLOSED", "candidates": [{"name": "f", "cycle_id": "x", "definition_hash": "h", "verdict": "REJECT"}]})
    run = tmp_path / "runs/x"
    run.mkdir(parents=True)
    (run / "result.json").write_text(json.dumps({"campaign_id": "c", "epoch_id": "e",
        "factor": {"name": "f", "definition_hash": "h", "family": "value"},
        "research_spec": {"thesis": "test"}, "evaluation": {"metrics": {"ic": 999.123},
        "checks": [{"tier": "T2", "name": "예측력", "passed": False, "value": 999.123}]}}))


def test_pending_records_no_results(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch)
    rows = refresh_candidate_lessons(tmp_path)
    assert rows[0]["visibility"] == "PENDING"
    assert rows[0]["validation"]["checks"] == []
    assert "예측력" not in render_grouped_lessons(rows)
    assert "999.123" not in (tmp_path / "memory/candidate_lessons.jsonl").read_text()


def test_terminal_records_idempotent_and_review_preserved(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    rows = refresh_candidate_lessons(tmp_path)
    record = rows[0]
    record["review"] = {"basis": record["review_basis"], "status": "REVIEWED",
        "economic_interpretation": "因果 미확인", "general_lesson": "측정과 해석을 구분", "scope": "해당 표본에 한정"}
    path = tmp_path / "memory/candidate_lessons.jsonl"
    path.write_text(json.dumps(record) + "\n")
    rows = refresh_candidate_lessons(tmp_path)
    first = path.read_text()
    refresh_candidate_lessons(tmp_path)
    assert path.read_text() == first
    summary = render_grouped_lessons(rows)
    assert "측정과 해석을 구분" in summary
    assert "FAIL" in summary
    assert "999.123" not in summary
    rows[0]["review"]["basis"] = "stale"
    assert "측정과 해석을 구분" not in render_grouped_lessons(rows)


def test_revealed_confirmation_is_qualitative_and_bad_binding_is_withheld(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "REVEALED")
    path = tmp_path / "campaigns/c/manifest.json"
    campaign = json.loads(path.read_text())
    campaign["oos"]["status"] = "REVEALED"
    path.write_text(json.dumps(campaign))
    monkeypatch.setattr("scripts.candidate_lessons.epochs.load_confirmation", lambda *a: {
        "confirmations": [{"factor": "f", "verdict": "PROMOTE", "evaluation": {
            "metrics": {"oos_ic": 999.123}, "checks": [{"tier": "T4", "name": "보정", "passed": True}]}}]})
    rows = refresh_candidate_lessons(tmp_path)
    assert rows[0]["validation"]["phase"] == "confirmation"
    assert "999.123" not in json.dumps(rows)
    def bad(*args):
        raise ValueError("bad binding")
    monkeypatch.setattr("scripts.candidate_lessons.epochs.load_confirmation", bad)
    rows = refresh_candidate_lessons(tmp_path)
    assert rows[0]["visibility"] == "PENDING"
    assert "보정" not in render_grouped_lessons(rows)


def completed_review(root):
    record, packet = current_evidence(root, "c/e/f")
    review = review_template(record, packet)
    review.update({
        "status": "REVIEWED", "lesson_key": "measurement_vs_prediction",
        "observations": [{"text": "예측력 검사에서 통과하지 못함", "evidence_ids": ["discovery.check.0"]}],
        "economic_interpretation": "측정과 가격 반영의 차이일 가능성은 있으나 원인은 미확인",
        "general_lesson": "경제적 특성의 측정과 주가 예측력을 구분해야 한다",
        "scope": "현재 검증 표본에 한정하며 이후 기업 실적은 미확인",
        "alternative_explanations": ["표본 부족이나 기존 노출로도 설명될 수 있음"],
        "unresolved": ["이후 기업 실적 자료가 없음"],
    })
    return record, packet, review


def test_packet_has_actual_metrics_but_memory_does_not(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    row = refresh_candidate_lessons(tmp_path)[0]
    packet = json.loads(Path(row["evidence_packet"]["path"]).read_text())
    assert digest(packet) == row["evidence_packet"]["sha256"]
    assert "999.123" in json.dumps(packet)
    assert "999.123" not in json.dumps(row)
    assert all(v["status"] == "NOT_COLLECTED" for v in packet["diagnostics"].values())
    assert not any(e["id"].startswith("confirmation.") for e in packet["evidence"])
    summary = render_grouped_lessons([row])
    assert "검토 대기: 1건" in summary
    assert "### value" not in summary


def test_pending_does_not_create_evidence_packet(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch)
    rows = refresh_candidate_lessons(tmp_path)
    assert "evidence_packet" not in rows[0]
    assert not (tmp_path / "memory/lesson_evidence").exists()
    with pytest.raises(ValueError, match="released"):
        current_evidence(tmp_path, "c/e/f")


def test_structured_review_round_trip_and_source_change_invalidates(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    record, packet, review = completed_review(tmp_path)
    save_review(tmp_path, review)
    rows = refresh_candidate_lessons(tmp_path)
    assert rows[0]["review_validation"] == "CURRENT"
    assert review["general_lesson"] in render_grouped_lessons(rows)
    assert list((tmp_path / "memory/lesson_reviews").glob("*.json"))
    original_packet = record["evidence_packet"]["sha256"]
    path = tmp_path / "runs/x/result.json"
    payload = json.loads(path.read_text())
    payload["evaluation"]["metrics"]["ic"] = 998.0
    path.write_text(json.dumps(payload))
    rows = refresh_candidate_lessons(tmp_path)
    assert rows[0]["evidence_packet"]["sha256"] != original_packet
    assert rows[0]["review_validation"] == "STALE_OR_INVALID"
    assert review["general_lesson"] not in render_grouped_lessons(rows)
    assert len(list((tmp_path / "memory/lesson_evidence").glob("*.json"))) == 2
    with pytest.raises(ValueError, match="stale"):
        save_review(tmp_path, review)


@pytest.mark.parametrize("error", ["draft", "unknown_ref", "hypothesis_only", "missing_data",
                                   "numeric_summary", "alternatives", "basis", "mechanism"])
def test_invalid_reviews_rejected(tmp_path, monkeypatch, error):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    record, packet, review = completed_review(tmp_path)
    if error == "draft":
        review["status"] = "DRAFT"
    elif error == "unknown_ref":
        review["observations"][0]["evidence_ids"] = ["charts.invented"]
    elif error == "hypothesis_only":
        review["observations"][0]["evidence_ids"] = ["hypothesis"]
    elif error == "missing_data":
        review["missing_evidence"] = []
    elif error == "numeric_summary":
        review["general_lesson"] = "수익률 20%"
    elif error == "alternatives":
        review["alternative_explanations"] = []
    elif error == "basis":
        review["basis"] = "old"
    else:
        review["mechanism_assessment"][0]["assessment"] = "SUPPORTED"
    with pytest.raises(ValueError):
        validate_review(review, record, packet)


def test_retracted_release_hides_previous_review(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    _, _, review = completed_review(tmp_path)
    save_review(tmp_path, review)
    path = tmp_path / "campaigns/c/manifest.json"
    campaign = json.loads(path.read_text())
    campaign["status"] = "AWAITING_IMPLEMENTATION"
    path.write_text(json.dumps(campaign))
    with pytest.raises(ValueError, match="released"):
        save_review(tmp_path, review)
    rows = refresh_candidate_lessons(tmp_path)
    assert rows[0]["visibility"] == "PENDING"
    assert review["general_lesson"] not in render_grouped_lessons(rows)


def test_compaction_merges_principle_preserves_counterevidence_and_scope(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    _, _, review = completed_review(tmp_path)
    save_review(tmp_path, review)
    original = refresh_candidate_lessons(tmp_path)[0]
    rows = []
    for i in range(10):
        row = deepcopy(original)
        row["record_id"] = f"c/e/f{i}"
        row["review"]["stance"] = "CONTRADICTS" if i == 9 else "SUPPORTS"
        rows.append(row)
    text = render_grouped_lessons(rows)
    assert text.count("### measurement_vs_prediction") == 1
    assert "반례 있음" in text
    assert "CONTRADICTS 관측 1건" in text
    assert "외 5건" in text
    rows[-1]["review"]["scope"] = "다른 표본에 한정"
    assert render_grouped_lessons(rows).count("### measurement_vs_prediction") == 2


def test_new_study_cannot_be_downgraded_to_unverified_legacy(tmp_path, monkeypatch):
    setup_batch(tmp_path, monkeypatch, "CLOSED_NO_QUALIFIED")
    path = tmp_path / "runs/x/result.json"
    payload = json.loads(path.read_text())
    payload["mechanism_study"] = {"status": "NOT_COLLECTED", "reason": "missing"}
    path.write_text(json.dumps(payload))
    binding = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr("scripts.candidate_lessons.epochs.load_epoch", lambda *args: {
        "status": "CLOSED", "candidates": [{"name": "f", "cycle_id": "x", "definition_hash": "h",
            "verdict": "REJECT", "discovery_result_artifact_sha256": binding}]})
    assert refresh_candidate_lessons(tmp_path)[0]["visibility"] == "RELEASED_QUALITATIVE"
    del payload["mechanism_study"]
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="frozen discovery"):
        refresh_candidate_lessons(tmp_path)
