import json
import sys
from pathlib import Path

import pytest

from scripts.factor_memory import (
    INDEX_FILE, build_factor_index, main, render_attempt_summary, write_factor_index,
)


def _fixture(tmp_path):
    root = tmp_path / "research"
    directory = tmp_path / "factors/candidates"
    directory.mkdir(parents=True)
    root.mkdir()
    source = '''raise RuntimeError("must never execute")
LOOKBACK = 12
PART = 1 / 3
def compute(frame):
    """OLD_OOS_SCORE_DO_NOT_EXPORT"""
    # COMMENT_RESULT_DO_NOT_EXPORT
    return frame["total_assets"] / frame["current_liabilities"]
FACTOR = Factor(name="operating_asset_growth_12m", family="asset_growth", category="quality",
    hypothesis="OLD_HYPOTHESIS_RESULT_DO_NOT_EXPORT", predicted_sign=-1,
    params={"lookback_months": LOOKBACK, "weight": PART},
    needs=("total_assets", "current_liabilities"), compute=compute)
RESEARCH_SPEC = {"mechanism": "SEALED_OOS_DO_NOT_EXPORT"}
'''
    (directory / "one.py").write_text(source)
    records = [
        {"cycle_id": "cycle0001", "factor": "operating_asset_growth_12m", "family": "asset_growth",
         "definition_hash": "old_hash", "strategy_file": "factors/candidates/one.py", "ruleset_version": "v1",
         "verdict": "SEALED_RESULT_DO_NOT_EXPORT", "failed_checks": ["SECRET_CHECK"],
         "report": "research/runs/forbidden/report.md"},
        {"cycle_id": "cycle0002", "factor": "operating_asset_growth_12m", "family": "asset_growth",
         "definition_hash": "new_hash", "strategy_file": "factors/candidates/one.py", "ruleset_version": "v2"},
        {"cycle_id": "cycle0003", "factor": "deleted_factor", "family": "legacy",
         "definition_hash": "missing_hash", "strategy_file": "deleted.py", "ruleset_version": "v0"},
    ]
    (root / "history.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records))
    return root


def test_static_inventory_preserves_trials_and_omits_results(tmp_path):
    root = _fixture(tmp_path)
    index = build_factor_index(root)
    assert len(index["trials"]) == 3
    assert [row["definition_hash"] for row in index["trials"]] == ["old_hash", "new_hash", "missing_hash"]
    assert all(row["current_definition_binding"] == "NOT_VERIFIED" for row in index["trials"])
    source = next(row for row in index["definitions"] if row["name"] == "operating_asset_growth_12m")
    assert source["params"] == {"lookback_months": 12, "weight": 1 / 3}
    assert source["referenced_fields"] == ["current_liabilities", "total_assets"]
    assert source["source_path"] == "factors/candidates/one.py"
    assert source["group"] == "investment"
    missing = next(row for row in index["definitions"] if row["name"] == "deleted_factor")
    assert missing["definition_status"] == "HISTORICAL_IDENTITY_ONLY"
    encoded = json.dumps(index)
    assert "DO_NOT_EXPORT" not in encoded
    assert "SECRET_CHECK" not in encoded
    assert "forbidden/report.md" not in encoded
    assert "hypothesis" not in source or source["hypothesis"] is None


def test_builtin_lambda_is_static_and_no_narrative_is_exported(tmp_path):
    root = _fixture(tmp_path)
    (tmp_path / "factors/builtin.py").write_text('''"""MODULE_RESULT_DO_NOT_EXPORT"""
_add(name="value_ep", category="value", hypothesis="OBSERVED_IC_DO_NOT_EXPORT", predicted_sign=1,
     needs=("net_income_ttm",), compute=lambda d: d["net_income_ttm"] / d["market_cap"])
''')
    index = build_factor_index(root)
    row = next(row for row in index["definitions"] if row["name"] == "value_ep")
    assert row["group"] == "valuation"
    assert row["calculation"].startswith("lambda d:")
    assert row["referenced_fields"] == ["market_cap", "net_income_ttm"]
    assert "DO_NOT_EXPORT" not in json.dumps(index)


def test_identity_fallback_and_regeneration_are_stable(tmp_path):
    root = _fixture(tmp_path)
    registry = [{"name": "registry_only", "category": "value", "family": "old", "definition_hash": "abc", "needs": ["x"], "verdict": "LEAK"}]
    first = build_factor_index(root, registry)
    path = write_factor_index(root, first)
    body = path.read_bytes()
    second = build_factor_index(root)
    write_factor_index(root, second)
    assert first == second
    assert body == path.read_bytes()
    assert "LEAK" not in body.decode()
    row = next(row for row in second["definitions"] if row["name"] == "registry_only")
    assert row["definition_status"] == "SOURCE_UNAVAILABLE"
    # An explicitly fresh empty registry is not an instruction to reuse old metadata.
    fresh = build_factor_index(root, [])
    assert fresh["observed_registry_rows"] == []
    assert "registry_only" not in {row["name"] for row in fresh["definitions"]}


def test_no_campaign_table_or_trial_table_in_compact_summary(tmp_path):
    root = _fixture(tmp_path)
    summary = render_attempt_summary(build_factor_index(root))
    assert "## 무엇을 이미 정의·시도했나" in summary
    assert "원장 시행 3건" in summary
    assert "자산·운전자본 성장" in summary
    assert "12개월" in summary
    assert INDEX_FILE in summary
    assert "cycle0001" not in summary
    assert "old_hash" not in summary
    assert "DO_NOT_EXPORT" not in summary


@pytest.mark.parametrize("change", ["candidate", "new_candidate", "history"])
def test_changed_source_fails_closed(tmp_path, monkeypatch, change):
    root = _fixture(tmp_path)
    index = build_factor_index(root)
    write_factor_index(root, index)
    if change == "candidate":
        source = tmp_path / "factors/candidates/one.py"
        source.write_text(source.read_text() + "\n# changed\n")
    elif change == "new_candidate":
        (tmp_path / "factors/candidates/two.py").write_text("# new source\n")
    else:
        with (root / "history.jsonl").open("a") as handle:
            handle.write(json.dumps({"cycle_id": "cycle0004", "factor": "extra"}) + "\n")
    with pytest.raises(ValueError, match="Stale"):
        write_factor_index(root, index)
    monkeypatch.setattr(sys, "argv", ["factor_memory", "--root", str(root), "--group", "investment"])
    with pytest.raises(SystemExit) as failure:
        main()
    assert failure.value.code == 2


@pytest.mark.parametrize("flag,value", [("--query", "total_assets"), ("--query", "자산"), ("--group", "investment"), ("--factor", "operating_asset_growth_12m")])
def test_lookup_only_returns_selected_identity_and_definition(tmp_path, monkeypatch, capsys, flag, value):
    root = _fixture(tmp_path)
    write_factor_index(root, build_factor_index(root))
    monkeypatch.setattr(sys, "argv", ["factor_memory", "--root", str(root), flag, value])
    main()
    result = json.loads(capsys.readouterr().out)
    assert len(result["definitions"]) == 1
    assert len(result["trials"]) == 2
    assert "DO_NOT_EXPORT" not in json.dumps(result)


def test_duplicate_trial_and_duplicate_definition_are_errors(tmp_path):
    root = _fixture(tmp_path)
    history = root / "history.jsonl"
    original = history.read_text()
    history.write_text(original + original.splitlines()[0] + "\n")
    with pytest.raises(ValueError, match="trial identity"):
        build_factor_index(root)
    history.write_text(original)
    source = tmp_path / "factors/candidates/one.py"
    (source.parent / "copy.py").write_text(source.read_text())
    with pytest.raises(ValueError, match="Duplicate static"):
        build_factor_index(root)


def test_empty_project_is_supported(tmp_path):
    root = tmp_path / "research"
    root.mkdir()
    index = build_factor_index(root)
    assert index["definitions"] == index["trials"] == []
    assert "원장 시행 0건" in render_attempt_summary(index)


def test_historical_hyphenated_cycle_is_preserved(tmp_path):
    root = _fixture(tmp_path)
    history = root / "history.jsonl"
    history.write_text(history.read_text().replace("cycle0001", "old-full-sample"))
    assert build_factor_index(root)["trials"][0]["cycle_id"] == "old-full-sample"
