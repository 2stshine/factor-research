"""Synthetic end-to-end context evidence, without campaigns or market data."""
import json
import hashlib

import numpy as np
import pandas as pd
import pytest

from engine.mechanism_diagnostics import _regime_comparison, build_diagnostics
from engine.regimes import RULES, RULES_HASH, classify_monthly_market


def labels():
    months = pd.period_range("2014-01", periods=100, freq="M")
    observations = pd.DataFrame({"month": months.astype(str), "known_at": months.to_timestamp("M"),
                                 "close": 100 * np.cumprod(1 + .01 + .05 * np.sin(np.arange(100)))})
    return classify_monthly_market(observations, as_of="2022-04-30", market_id="SYNTHETIC", source_id="fixture")


def performance(context):
    return [{"month": m, "rank_ic": .04, "top_minus_bottom": .003, "n_pairs": 50}
            for m in context.month]


def test_detailed_classification_flows_into_diagnostic_evidence_with_all_cells():
    context = labels()
    result = _regime_comparison(context, performance(context))
    json.dumps(result, allow_nan=False)
    data = result["data"]
    assert data["classification_rules"] == [{"version": RULES["version"], "sha256": RULES_HASH}]
    assert len(data["views"]["regime_detail"]) == 17  # sixteen + UNKNOWN, never choose only winners
    assert set(data["views"]) == {"trend_long", "trend_short", "volatility_long", "volatility_short",
                                  "trend_phase", "volatility_phase", "regime_detail"}
    for dimension, rows in data["views"].items():
        assert sum(row["n_months"] for row in rows) == len(context)
        for row in rows:
            if row["support"] != "DESCRIPTIVE_SUPPORT_ONLY":
                assert row["rank_ic"]["ci95"] is None
    assert data["monthly"][-1]["regime_detail"] == context.iloc[-1].regime_detail


def test_unavailable_short_or_long_axis_does_not_invent_the_other():
    context = labels().iloc[27:36]
    evidence = _regime_comparison(context, performance(context))
    assert evidence["status"] == "PARTIAL"
    result = evidence["data"]
    assert all(row["regime"] == "UNKNOWN" for row in result["monthly"])
    assert all(row["volatility_short"] != "UNKNOWN" for row in result["monthly"])
    assert all(row["volatility_long"] == "UNKNOWN" for row in result["monthly"])


@pytest.mark.parametrize("field,value", [("rules_sha256", "wrong"), ("regime_detail", "fake"),
    ("trend_short", "UNKNOWN"), ("status", "READY"), ("market_id", "OTHER")])
def test_tampered_or_mixed_detailed_context_rejected(field, value):
    context = labels()
    row = 0 if field == "status" else len(context) - 1
    context.loc[row, field] = value
    with pytest.raises(ValueError):
        _regime_comparison(context, performance(context))


def test_incomplete_extended_schema_cannot_silently_fall_back_to_coarse():
    context = labels()
    with pytest.raises(ValueError, match="require all axes"):
        _regime_comparison(context.drop(columns="trend_short"), performance(context))
    with pytest.raises(ValueError, match="requires detailed axes"):
        _regime_comparison(context[["month", "effective_month", "regime", "status", "rules_version", "rules_sha256"]], performance(context))


def test_single_long_episode_does_not_become_independent_support():
    months = pd.period_range("2018-01", periods=24, freq="M")
    context = pd.DataFrame({"month": months.astype(str), "effective_month": (months + 1).astype(str),
                            "regime": "UP_LOW", "status": "READY"})
    row = _regime_comparison(context, performance(context))["data"]["regimes"][0]
    assert row["n_joint_usable_months"] == 24
    assert row["n_joint_usable_episodes"] == 1
    assert row["support"] == "INSUFFICIENT_SUPPORT"
    assert row["rank_ic"]["mean"] == pytest.approx(.04)
    assert row["rank_ic"]["ci95"] is None


def test_missing_outcomes_and_unknown_months_do_not_manufacture_regime_episodes():
    months = pd.period_range("2018-01", periods=36, freq="M")
    context = pd.DataFrame({"month": months.astype(str), "effective_month": (months + 1).astype(str),
                            "regime": "UP_LOW", "status": "READY"})
    records = performance(context)
    for i in range(0, 36, 6):
        records[i]["rank_ic"] = records[i]["top_minus_bottom"] = None
    row = _regime_comparison(context, records)["data"]["regimes"][0]
    assert row["n_joint_usable_months"] == 30
    assert row["n_joint_usable_episodes"] == 1
    assert row["support"] == "INSUFFICIENT_SUPPORT"
    context.loc[[5, 11, 17, 23], ["regime", "status"]] = ["UNKNOWN", "INSUFFICIENT_DATA"]
    result = _regime_comparison(context, [r for i, r in enumerate(records) if i % 6 != 1])
    row = next(r for r in result["data"]["regimes"] if r["regime"] == "UP_LOW")
    assert row["n_joint_usable_episodes"] == 1
    assert row["rank_ic"]["ci95"] is None


def test_real_observed_state_transitions_count_as_separate_descriptive_episodes():
    months = pd.period_range("2018-01", periods=24, freq="M")
    context = pd.DataFrame({"month": months.astype(str), "effective_month": (months + 1).astype(str),
                            "regime": ["UP_LOW"] * 6 + ["DOWN_HIGH"] * 3 + ["UP_LOW"] * 6
                                      + ["DOWN_HIGH"] * 3 + ["UP_LOW"] * 6, "status": "READY"})
    row = next(r for r in _regime_comparison(context, performance(context))["data"]["regimes"]
               if r["regime"] == "UP_LOW")
    assert row["n_joint_usable_months"] == 18
    assert row["n_joint_usable_episodes"] == 3
    assert row["support"] == "DESCRIPTIVE_SUPPORT_ONLY"


def test_diagnostics_accepts_versioned_regimes_without_modifying_numeric_gates():
    context = labels()
    months = context.month.iloc[-24:]
    frame = pd.DataFrame([{"asset_id": asset, "ym": month, "score": float(asset),
                           "fwd": asset / 100, "fwd__known_at": "2022-05-31"}
                          for month in months for asset in range(20)])
    args = dict(signal="score", forward_return="fwd", controls=[], outcomes=[], as_of="2022-05-31")
    without = build_diagnostics(frame, **args)
    with_context = build_diagnostics(frame, regimes=context, **args)
    for section in without:
        if section != "regime_comparison":
            assert without[section] == with_context[section]
    assert with_context["regime_comparison"]["status"] == "AVAILABLE"


def test_actual_regime_evidence_to_review_to_knowledge_round_trip(tmp_path, monkeypatch):
    from engine.mechanism_capture import capture_discovery
    from scripts.candidate_lessons import refresh_candidate_lessons
    from scripts.knowledge import refresh_knowledge
    from scripts.lesson_review import current_evidence, save_review
    from tests.test_mechanism_capture import fixture
    from tests.test_scientist_review import analysis, accept

    panel, frame, factor, result, campaign = fixture()
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    performance_rows = study["sections"]["monthly_performance"]["data"]["monthly"]
    study["sections"]["regime_comparison"] = _regime_comparison(labels(), performance_rows)
    root = tmp_path
    (root / "campaigns/c").mkdir(parents=True)
    (root / "campaigns/c/manifest.json").write_text(json.dumps({
        "campaign_id": "c", "status": "CLOSED_NO_QUALIFIED", "oos": {"status": "SEALED"},
        "epochs": [{"epoch_id": "e"}],
    }))
    payload = {"campaign_id": "c", "epoch_id": "e", "ruleset_version": "synthetic",
               "factor": {"name": "test", "definition_hash": "d", "family": "synthetic"},
               "mechanism_study": study, "evaluation": {"checks": [], "metrics": {}}, "research_spec": {}}
    (root / "runs/x").mkdir(parents=True)
    result_path = root / "runs/x/result.json"
    result_path.write_text(json.dumps(payload, allow_nan=False))
    binding = hashlib.sha256(result_path.read_bytes()).hexdigest()
    monkeypatch.setattr("scripts.candidate_lessons.epochs.load_epoch", lambda *args: {
        "status": "CLOSED", "candidates": [{"name": "test", "cycle_id": "x", "definition_hash": "d",
            "discovery_result_artifact_sha256": binding, "verdict": "REJECT"}],
    })
    record, packet = current_evidence(root, "c/e/test")
    assert packet["diagnostics"]["regime_comparison"]["data"]["classification_rules"]
    # These are explicitly synthetic analyst/critic responses, not a real LLM run.
    review = analysis(record, packet)
    review["scope"] = "장기 상승과 단기 조정 환경의 관측이며 다른 환경은 미확인"
    review["observations"].append({"text": "장단기 국면별 관측 개월과 표본 부족을 구분함",
                                    "evidence_ids": ["diagnostic.discovery.regime_comparison"]})
    review["critic"] = accept(review, packet)
    save_review(root, review)
    monkeypatch.setattr("scripts.lessons.render_memory", lambda *a, **kw: (
        "## 1. 이번 회차의 제약\n동결\n## 2. 후보 하나가 갖춰야 할 것\n지침\n"
        "## 3. 어느 쪽이 이미 채워졌나\n분포\n### 구조적 교훈\n## 4. 시행 전량\n시행 정체성\n"))
    first = refresh_knowledge(root, context_text="## Frozen research state\nsynthetic\n").read_bytes()
    assert refresh_knowledge(root).read_bytes() == first
    text = first.decode()
    assert review["general_lesson"] in text and review["scope"] in text
    assert RULES["version"] in text
    assert "regime_detail" not in text and "top_minus_bottom" not in text
    records = refresh_candidate_lessons(root)
    assert records[0]["review_validation"] == "CURRENT"
    assert records[0]["regime_rules"] == [{"version": RULES["version"], "sha256": RULES_HASH}]
    assert result_path.read_bytes() == json.dumps(payload, allow_nan=False).encode()
