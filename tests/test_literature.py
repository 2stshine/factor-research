"""Synthetic catalog tests; no browsing, RDS or factor execution."""
from copy import deepcopy
import json

import pytest

from scripts.knowledge import refresh_knowledge
from scripts.literature import load_literature, render_literature


def catalog():
    return {"schema_version": "factor-literature-v1", "reviewed_on": "2026-09-20", "entries": [{
        "id": "example_2025", "topic": "economic_mechanism", "label": "실적과 가격 구분",
        "title": "Example study", "authors": "Example Author", "year": 2025,
        "source_url": "https://example.org/paper", "source_locator": "Abstract",
        "read_scope": "PRIMARY_ABSTRACT", "finding": "논문에서 보고한 관측",
        "project_application": "새로운 측정 가설을 검토할 수 있다",
        "diagnostic_question": "경제적 변화와 가격 반응이 구분되는가?",
        "data_requirements": "PIT 입력 확인 필요", "limitations": "국내 표본 재현 없음",
        "local_replication": "NOT_ESTABLISHED",
    }]}


def write_catalog(root, value):
    (root / "memory").mkdir(exist_ok=True)
    (root / "memory/literature.json").write_text(json.dumps(value, ensure_ascii=False))


def test_missing_catalog_is_backward_compatible(tmp_path):
    assert load_literature(tmp_path) is None
    assert render_literature(tmp_path) == ""


@pytest.mark.parametrize("field,value", [
    ("local_replication", "APPROVED"), ("source_url", "javascript:alert(1)"),
    ("source_url", "https://user:password@example.org/paper"),
    ("read_scope", "ASSUMED_READ"), ("source_locator", ""),
    ("finding", "x" * 401), ("finding", "text\n## injected"),
    ("year", 2027), ("year", True), ("id", "../trial"),
])
def test_invalid_or_unverified_catalog_fails_closed(tmp_path, field, value):
    document = catalog()
    document["entries"][0][field] = value
    write_catalog(tmp_path, document)
    with pytest.raises(ValueError):
        render_literature(tmp_path)


def test_unique_id_and_no_trial_fields(tmp_path):
    document = catalog()
    document["entries"] *= 2
    write_catalog(tmp_path, document)
    with pytest.raises(ValueError, match="Duplicate"):
        render_literature(tmp_path)
    document = catalog()
    document["entries"][0]["verdict"] = "PROMOTE"
    write_catalog(tmp_path, document)
    with pytest.raises(ValueError, match="fields"):
        render_literature(tmp_path)


def test_render_is_deterministic_and_external_claims_are_separate(tmp_path):
    document = catalog()
    second = deepcopy(document["entries"][0])
    second.update(id="another_2025", topic="validation")
    document["entries"].append(second)
    write_catalog(tmp_path, document)
    before = (tmp_path / "memory/literature.json").read_bytes()
    text = render_literature(tmp_path)
    assert (tmp_path / "memory/literature.json").read_bytes() == before
    assert "논문 관측:" in text and "프로젝트 적용 **제안**:" in text
    assert "원저자/출판사 초록 확인" in text
    assert "국내 동일 정의 재현은 미확인" in text
    assert "SUPPORTS" not in text
    document["entries"].reverse()
    write_catalog(tmp_path, document)
    assert render_literature(tmp_path) == text


def test_refresh_preserves_literature_and_existing_internal_lessons(tmp_path, monkeypatch):
    write_catalog(tmp_path, catalog())
    context = "## Frozen research state\ncurrent cutoff\n## Prior autonomous cycles\nSEALED_RESULT\n"
    memory = (
        "## 1. 이번 회차의 제약\nfixed\n"
        "## 2. 후보 하나가 갖춰야 할 것\nDUPLICATE_RULE\n"
        "## 3. 어느 쪽이 이미 채워졌나\nvalue\n"
        "### 구조적 교훈\n**campaign-a**\nSEALED_NOTE\n봉인 경계 뒤\n"
        "## 4. 시행 전량\ntrial identity\n"
    )
    monkeypatch.setattr("scripts.lessons.render_memory", lambda *a, **kw: memory)
    monkeypatch.setattr("scripts.candidate_lessons.refresh_candidate_lessons", lambda *a, **kw: [])
    monkeypatch.setattr("scripts.candidate_lessons.render_grouped_lessons", lambda _: "## 누적 검증 교훈\nINTERNAL_LESSON\n")
    first = refresh_knowledge(tmp_path, context_text=context).read_bytes()
    assert refresh_knowledge(tmp_path).read_bytes() == first
    text = first.decode()
    assert text.count("## 외부 문헌 지식") == 1
    assert text.count("#### example_2025") == 1
    assert "INTERNAL_LESSON" in text
    assert not any(x in text for x in ["SEALED_RESULT", "SEALED_NOTE", "DUPLICATE_RULE"])
    assert "논문 지식은 미포함" not in text


def test_bad_catalog_never_overwrites_existing_knowledge(tmp_path):
    document = catalog()
    document["entries"][0]["source_url"] = "file:///private/data"
    write_catalog(tmp_path, document)
    target = tmp_path / "KNOWLEDGE.md"
    target.write_text("KEEP EXISTING CONTENT")
    with pytest.raises(ValueError):
        refresh_knowledge(tmp_path)
    assert target.read_text() == "KEEP EXISTING CONTENT"
