from pathlib import Path
import json

import pytest

from scripts.knowledge import refresh_knowledge


def test_missing_filtered_sources_fail_closed(tmp_path):
    with pytest.raises(ValueError):
        refresh_knowledge(tmp_path)
    assert not (tmp_path / "KNOWLEDGE.md").exists()


def test_knowledge_compacts_definitions_but_keeps_all_identities_in_lookup(tmp_path, monkeypatch):
    context = (
        "# context\n## Frozen research state\n- Strategy context cutoff: `2023-06-30`\n"
        "- Active sealed campaign: `secret-campaign`\n- Recorded autonomous cycles: `2`\n"
        "## Sealed-OOS campaigns\nSECRET_CAMPAIGN_STATUS\n"
        "## Available strategy inputs\n| column | overall coverage | latest-month coverage |\n"
        "|---|---:|---:|\n| `total_assets` | 90% | 95% |\n"
        "## Registered factors (코드 정의 목록·연구 승인 아님)\n"
        "| factor | category | family | definition hash | inputs |\n"
        "|---|---|---|---|---|\n"
        "| `asset_growth_12m` | quality | `asset_growth` | `abc` | total_assets |\n"
        "| `asset_growth_24m` | quality | `asset_growth` | `def` | total_assets |\n"
        "## Prior autonomous cycles\nSECRET_RECENT_RESULT\n"
    )
    rows = [dict(cycle_id=f"trial-{i}", factor=f"asset_growth_{months}m", family="asset_growth",
                 definition_hash=definition, ruleset_version="rules-v1", verdict="SECRET_VERDICT",
                 metrics={"ic": 987.654}, report="SECRET_REPORT")
            for i, months, definition in [(1, 12, "abc"), (2, 24, "def")]]
    history = tmp_path / "history.jsonl"
    history.write_text("".join(json.dumps(row) + "\n" for row in rows))
    before = history.read_bytes()
    # The old reflection renderer is no longer an input to candidate knowledge.
    def legacy_forbidden(*args, **kwargs):
        raise AssertionError("legacy report must not be used")
    monkeypatch.setattr("scripts.lessons.render_memory", legacy_forbidden)
    text = refresh_knowledge(tmp_path, context_text=context).read_text()
    assert not (tmp_path / "context/latest.md").exists()
    assert not (tmp_path / "memory/lessons.md").exists()
    assert "## 무엇을 이미 정의·시도했나" in text
    assert "`total_assets` | 90% | 95%" in text
    assert "2023-06-30" in text
    assert not any(token in text for token in (
        "Sealed-OOS campaigns", "Registered factors", "전체 시행 정체성", "구조적 교훈",
        "SECRET", "secret-campaign", "987.654", "trial-1", "trial-2"))
    index_path = tmp_path / "memory/factor_index.json"
    index = index_path.read_text()
    assert all(token in index for token in ("trial-1", "trial-2", "asset_growth_12m", "asset_growth_24m", "abc", "def"))
    assert "SECRET" not in index and "987.654" not in index
    assert history.read_bytes() == before
    assert refresh_knowledge(tmp_path).read_text() == text
    assert index_path.read_text() == index


def test_direct_memory_without_legacy_markdown(tmp_path):
    context = "## Frozen research state\n- Strategy context cutoff: `-`\n"
    text = refresh_knowledge(tmp_path, context_text=context).read_text()
    assert "## 무엇을 이미 정의·시도했나" in text
    assert "전체 시행 정체성" not in text
    assert not (tmp_path / "memory/lessons.md").exists()


def test_duplicate_data_sections_fail_without_rewriting_existing_knowledge(tmp_path):
    target = tmp_path / "KNOWLEDGE.md"
    target.write_text("PRESERVE")
    with pytest.raises(ValueError, match="Duplicate"):
        refresh_knowledge(tmp_path, context_text="## Frozen research state\na\n## Frozen research state\nb\n")
    assert target.read_text() == "PRESERVE"
