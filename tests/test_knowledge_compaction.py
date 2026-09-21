"""Synthetic-only memory tests: never regenerate the repository's research files."""
from copy import deepcopy
import json
import random

import pytest

from engine.lesson_evidence import VERSION, review_template
from scripts.candidate_lessons import _regime_rules, refresh_candidate_lessons, render_grouped_lessons
from scripts.knowledge import refresh_knowledge
from scripts.lesson_review import current_evidence, save_review


def reviewed_record(index=0, stance="SUPPORTS"):
    return {
        "record_id": f"campaign/epoch/factor-{index:03d}",
        "visibility": "RELEASED_QUALITATIVE", "family": "value", "ruleset": "rules-v1",
        "regime_rules": [{"version": "regime-v2", "sha256": "a" * 64}],
        "validation": {"phase": "discovery", "checks": []},
        "review_basis": "bound", "review_validation": "CURRENT",
        "review": {
            "schema_version": VERSION, "status": "REVIEWED", "basis": "bound",
            "lesson_key": "measurement_and_price", "stance": stance,
            "economic_interpretation": "기업 특성이 가격 기대에 반영됐을 가능성은 있으나 원인은 미확인",
            "general_lesson": "경제적 변화와 가격 반영을 구분해야 한다",
            "scope": "장기 상승과 단기 하락 환경에 한정하며 다른 환경은 미확인",
        },
    }


def test_many_observations_compact_without_losing_opposition_or_uncertainty():
    rows = [reviewed_record(i, ("SUPPORTS", "CONTRADICTS", "UNCERTAIN")[i % 3])
            for i in range(90)]
    text = render_grouped_lessons(rows)
    assert text.count("### measurement_and_price") == 1
    for stance in ("SUPPORTS", "CONTRADICTS", "UNCERTAIN"):
        assert f"{stance} 관측 30건" in text
    assert "반례 있음" in text and "외 85건" in text
    assert len(text) < len(json.dumps(rows, ensure_ascii=False)) / 10
    assert "같은 표본의 반복은 독립 증거가 아니다" in text


def test_compaction_is_order_independent_and_identical_rows_are_not_extra_evidence():
    rows = [reviewed_record(i) for i in range(12)]
    expected = render_grouped_lessons(rows)
    shuffled = deepcopy(rows)
    random.Random(2026).shuffle(shuffled)
    shuffled.extend(deepcopy(rows))
    assert render_grouped_lessons(shuffled) == expected
    assert "SUPPORTS 관측 12건" in expected
    references = next(line for line in expected.splitlines() if line.startswith("- 근거:"))
    assert references.count("campaign/epoch/") == 5
    assert "factor-000" in references and "factor-004" in references


def test_different_scope_ruleset_or_regime_definition_never_merge():
    rows = [reviewed_record(i) for i in range(6)]
    rows[1]["review"]["scope"] = "장기 하락과 단기 상승 환경에 한정"
    rows[2]["ruleset"] = "rules-v2"
    rows[3]["regime_rules"][0]["version"] = "regime-v3"
    rows[4]["regime_rules"][0]["sha256"] = "b" * 64
    rows[5]["regime_rules"] = []
    text = render_grouped_lessons(rows)
    assert text.count("### measurement_and_price") == 6
    assert "rules-v1" in text and "rules-v2" in text
    assert "regime-v2" in text and "regime-v3" in text
    assert "aaaaaaaaaaaa" in text and "bbbbbbbbbbbb" in text
    assert "미연결/기준 미상" in text


def test_regime_definition_order_is_canonical():
    rows = [reviewed_record(i) for i in range(2)]
    rows[0]["regime_rules"].append({"version": "regime-v1", "sha256": "b" * 64})
    rows[1]["regime_rules"] = list(reversed(rows[0]["regime_rules"]))
    assert render_grouped_lessons(rows).count("### measurement_and_price") == 1


def test_interpretations_are_bounded_and_omissions_are_visible():
    rows = [reviewed_record(i) for i in range(3)]
    interpretations = ["가설의 측정 한계가 남음", "대안 노출이 남음", "비용 설명이 남음"]
    for row, interpretation in zip(rows, interpretations):
        row["review"]["economic_interpretation"] = interpretation
    text = render_grouped_lessons(rows)
    assert sum(interpretation in text for interpretation in interpretations) == 2
    assert "다른 해석 1개는 후보 원장에 보존" in text


def test_legacy_group_also_has_bounded_deterministic_references():
    rows = [reviewed_record(i) for i in range(20)]
    for row in rows:
        del row["review"]["schema_version"]
    text = render_grouped_lessons(rows)
    assert render_grouped_lessons(list(reversed(rows))) == text
    assert "외 15건" in text
    assert text.count("campaign/epoch/") == 5


def test_conflicting_same_identity_is_withheld_instead_of_counted_twice():
    original = reviewed_record()
    conflict = deepcopy(original)
    conflict["review"]["stance"] = "CONTRADICTS"
    text = render_grouped_lessons([original, conflict])
    assert "상충 버전 1건" in text
    assert "### measurement_and_price" not in text
    assert render_grouped_lessons([conflict, original]) == text


@pytest.mark.parametrize("change", ["sealed", "stale", "numeric", "too_long", "draft"])
def test_nonpublic_or_invalid_interpretations_never_enter_summary(change):
    row = reviewed_record()
    if change == "sealed":
        row["visibility"] = "PENDING"
    elif change == "stale":
        row["review_validation"] = "STALE_OR_INVALID"
    elif change == "numeric":
        row["review"]["scope"] = "수익률 99%"
    elif change == "too_long":
        row["review"]["scope"] = "가" * 601
    else:
        row["review"]["status"] = "DRAFT"
    assert "### measurement_and_price" not in render_grouped_lessons([row])


@pytest.fixture
def released_root(tmp_path, monkeypatch):
    directory = tmp_path / "campaigns/c"
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(json.dumps({
        "campaign_id": "c", "status": "CLOSED_NO_QUALIFIED",
        "oos": {"status": "SEALED"}, "epochs": [{"epoch_id": "e"}],
    }))
    monkeypatch.setattr("scripts.candidate_lessons.epochs.load_epoch", lambda *args: {
        "status": "CLOSED", "candidates": [{"name": "f", "cycle_id": "x",
            "definition_hash": "h", "verdict": "REJECT"}],
    })
    run = tmp_path / "runs/x"
    run.mkdir(parents=True)
    (run / "result.json").write_text(json.dumps({
        "campaign_id": "c", "epoch_id": "e", "ruleset_version": "rules-v1",
        "factor": {"name": "f", "definition_hash": "h", "family": "value"},
        "research_spec": {"thesis": "가격과 경제적 변화의 관계"},
        "evaluation": {"metrics": {"ic": 987.654}, "checks": [
            {"tier": "T2", "name": "예측력", "passed": False}]},
    }))
    return tmp_path


def save_synthetic_review(root):
    record, packet = current_evidence(root, "c/e/f")
    review = review_template(record, packet)
    review.update({
        "status": "REVIEWED", "lesson_key": "measurement_and_price", "stance": "UNCERTAIN",
        "observations": [{"text": "예측력 검사가 통과하지 못함", "evidence_ids": ["discovery.check.0"]}],
        "economic_interpretation": "다른 노출의 영향일 가능성은 있으나 원인은 미확인",
        "general_lesson": "경제적 변화와 가격 반영을 구분해야 한다",
        "scope": "현재 표본에 한정하며 다른 레짐에서의 작동 여부는 미확인",
        "alternative_explanations": ["표본 부족도 설명이 될 수 있음"],
        "unresolved": ["실적 변화 자료가 없음"],
    })
    save_review(root, review)
    return review


def test_full_knowledge_refresh_is_idempotent_and_preserves_records(released_root, monkeypatch):
    root = released_root
    review = save_synthetic_review(root)
    memory = (
        "## 1. 이번 회차의 제약\n고정 입력\n"
        "## 2. 후보 하나가 갖춰야 할 것\nDUPLICATE_RULE\n"
        "## 3. 어느 쪽이 이미 채워졌나\nvalue: 1\n### 구조적 교훈\n"
        "## 4. 시행 전량\ntrial-x | factor-f | value\n"
    )
    monkeypatch.setattr("scripts.lessons.render_memory", lambda *args, **kwargs: memory)
    context = "## Frozen research state\ncutoff\n## Prior autonomous cycles\nRECENT_RESULT\n"
    first = refresh_knowledge(root, context_text=context).read_bytes()
    ledger = (root / "memory/candidate_lessons.jsonl").read_bytes()
    assert refresh_knowledge(root).read_bytes() == first
    assert (root / "memory/candidate_lessons.jsonl").read_bytes() == ledger
    text = first.decode()
    assert text.count("## 누적 검증 교훈") == 1
    assert review["general_lesson"] in text
    assert "## 무엇을 이미 정의·시도했나" in text
    assert "trial-x | factor-f | value" not in text
    assert all(forbidden not in text for forbidden in ("987.654", "DUPLICATE_RULE", "RECENT_RESULT"))


def test_regime_rule_metadata_is_bound_to_review_and_never_copies_metrics(released_root, monkeypatch):
    root = released_root
    from scripts import candidate_lessons
    original_build = candidate_lessons.build_packet
    current_sha = ["a" * 64]

    def packet_with_regime(*args):
        packet = original_build(*args)
        packet["diagnostics"]["regime_comparison"] = {
            "status": "PARTIAL", "data": {
                "classification_rules": [{"version": "regime-v2", "sha256": current_sha[0]}],
                "state_performance": {"ic": 987.654},
            },
        }
        return packet

    monkeypatch.setattr(candidate_lessons, "build_packet", packet_with_regime)
    review = save_synthetic_review(root)
    row = refresh_candidate_lessons(root)[0]
    assert row["regime_rules"] == [{"version": "regime-v2", "sha256": "a" * 64}]
    assert "987.654" not in json.dumps(row)
    assert "regime_comparison" in row["evidence_packet"]["missing"]
    current_sha[0] = "b" * 64
    changed = refresh_candidate_lessons(root)[0]
    assert changed["review_validation"] == "STALE_OR_INVALID"
    assert review["general_lesson"] not in render_grouped_lessons([changed])


def test_unavailable_original_is_preserved_but_not_republished(released_root):
    root = released_root
    review = save_synthetic_review(root)
    (root / "runs/x/result.json").unlink()
    assert refresh_candidate_lessons(root) == []
    assert review["general_lesson"] in (root / "memory/candidate_lessons.jsonl").read_text()
    assert review["general_lesson"] not in render_grouped_lessons([])


@pytest.mark.parametrize("rules", [None, {}, [{}], [{"version": "bad\ntext", "sha256": "a" * 64}],
                                  [{"version": "regime-v2", "sha256": "not-a-digest"}]])
def test_invalid_classification_metadata_fails_closed(rules):
    with pytest.raises(ValueError, match="regime classification"):
        _regime_rules({"diagnostics": {"regime_comparison": {
            "status": "AVAILABLE", "data": {"classification_rules": rules}}}})
