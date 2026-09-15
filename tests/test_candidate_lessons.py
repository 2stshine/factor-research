import json

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
