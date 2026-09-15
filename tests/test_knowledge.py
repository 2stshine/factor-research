from pathlib import Path

import pytest

from scripts.knowledge import refresh_knowledge


def test_missing_filtered_sources_fail_closed(tmp_path):
    with pytest.raises(ValueError):
        refresh_knowledge(tmp_path)
    assert not (tmp_path / "KNOWLEDGE.md").exists()


def test_knowledge_keeps_identity_not_duplicate_rules_or_recent_results(tmp_path, monkeypatch):
    context = (
        "# context\n## Frozen research state\ncutoff\n"
        "## Prior autonomous cycles\nSECRET_RECENT_RESULT\n"
    )
    memory = (
        "## 1. 이번 회차의 제약\n봉인\n"
        "## 2. 후보 하나가 갖춰야 할 것\nDUPLICATE_RULE\n"
        "## 3. 어느 쪽이 이미 채워졌나\nvalue: 1\n"
        "### 구조적 교훈\n**campaign-1 / epoch-1**\n"
        "sealed-factor — 시행함\n봉인 경계 뒤\n"
        "## 4. 시행 전량\ntrial-1 | factor-1 | family-1\n"
    )
    monkeypatch.setattr("scripts.lessons.render_memory", lambda *a, **kw: memory)
    text = refresh_knowledge(tmp_path, context_text=context).read_text()
    assert not (tmp_path / "context/latest.md").exists()
    assert not (tmp_path / "memory/lessons.md").exists()
    assert "trial-1 | factor-1 | family-1" in text
    assert "value: 1" in text
    assert "SECRET_RECENT_RESULT" not in text
    assert "DUPLICATE_RULE" not in text
    assert "sealed-factor" not in text


def test_direct_memory_without_legacy_markdown(tmp_path):
    context = "## Frozen research state\n- Strategy context cutoff: `-`\n"
    text = refresh_knowledge(tmp_path, context_text=context).read_text()
    assert "전체 시행 정체성" in text
    assert not (tmp_path / "memory/lessons.md").exists()
