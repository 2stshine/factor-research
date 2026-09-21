from copy import deepcopy
import xml.etree.ElementTree as ET

import pytest

from engine.lesson_evidence import build_packet, review_template, validate_review, digest
from engine.scientist_review import (
    critique_template, plan_template, run_review_cycle, validate_plan,
)
from tests.test_mechanism_capture import fixture
from engine.mechanism_capture import capture_discovery


def evidence():
    panel, frame, factor, result, campaign = fixture()
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    record = {"visibility": "RELEASED_QUALITATIVE", "record_id": "c/e/test",
              "review_basis": "basis", "hypothesis_and_calculation": {}, "evidence": {}}
    payload = {"factor": {"definition_hash": "d"}, "mechanism_study": study,
               "evaluation": {"checks": [{"name": "example", "passed": False}], "metrics": {}}}
    packet = build_packet(record, payload, None)
    return record, packet


def analysis(record, packet):
    review = review_template(record, packet)
    review.update({
        "status": "REVIEWED", "lesson_key": "cash_persistence_vs_pricing",
        "observations": [{"text": "순위별 공개 실적의 변화가 관측됨",
                          "evidence_ids": ["diagnostic.discovery.economic_outcomes"]}],
        "economic_interpretation": "실적 지속성과 가격 반영은 구분할 필요가 있음",
        "general_lesson": "기업 실적의 예측과 초과수익의 원인은 동일하지 않을 수 있다",
        "scope": "관측 표본에 한정하며 가격 기대의 직접 측정은 없음",
        "alternative_explanations": ["기업 규모나 유동성이 함께 작용할 수 있음"],
        "unresolved": ["시장 기대 및 공시 이벤트 자료 없음"],
        "follow_up": {"question": "가격 기대 차이를 관측할 수 있는가", "data_needed": "당시 컨센서스",
                      "distinguishes": ["mechanism", "rival"], "execution": "PROPOSED_NOT_RUN"},
    })
    for explanation in review["explanations"]:
        explanation["claim"] = "실적 또는 동반 노출의 설명 가능성"
        explanation["distinguishing_observation"] = "공통표본 통제 후에도 경제적 변화가 남는지 확인"
    return review


def accept(review, packet):
    critic = critique_template(review, packet)
    critic.update({"decision": "ACCEPT", "findings": []})
    critic["checks"] = {key: True for key in critic["checks"]}
    return critic


def test_actual_diagnostics_and_svg_are_bound_into_packet():
    record, packet = evidence()
    assert packet["diagnostics"]["economic_outcomes"]["status"] == "PARTIAL"
    assert packet["diagnostics"]["regime_comparison"]["status"] == "NOT_COLLECTED"
    assert packet["diagnostics"]["execution_costs"]["status"] == "NOT_COLLECTED"
    charts = packet["diagnostics"]["charts"]
    assert charts["status"] == "AVAILABLE"
    assert len(charts["data"]) == 3
    for chart in charts["data"]:
        assert ET.fromstring(chart["svg"]).tag.endswith("svg")
        assert chart["source_evidence_ids"]
    assert "charts" not in review_template(record, packet)["missing_evidence"]


@pytest.mark.parametrize("sign,direction", [
    (-1, "LOWER_RAW_VALUE"), (1, "HIGHER_RAW_VALUE"), (None, "UNKNOWN"),
])
def test_packet_preserves_signed_group_meaning_and_holding_period(sign, direction):
    panel, frame, factor, result, campaign = fixture()
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    record = {"visibility": "RELEASED_QUALITATIVE", "record_id": "c/e/test",
              "hypothesis_and_calculation": {}, "evidence": {}}
    payload = {"factor": {"definition_hash": "d", "predicted_sign": sign,
                           "rebalance_months": 3}, "mechanism_study": study}
    packet = build_packet(record, payload, None)
    context = packet["scientist"]["study_context"]
    assert context["top_group_raw_direction"] == direction
    assert context["candidate_rebalance_months"] == 3
    assert context["diagnostic_groups"] == "MONTHLY_REFORMED_NOT_IMPLEMENTED_HOLDINGS"
    assert context["data_cutoff"] == "2021-06-30"
    assert "Public PIT ROA change" in context["economic_outcome_notes"][0]
    study.pop("signal_orientation")
    assert build_packet(record, payload, None)["scientist"]["study_context"][
        "top_group_raw_direction"] == "UNKNOWN"


def test_two_stage_runner_calls_distinct_roles_without_experiments():
    record, packet = evidence()
    calls = []
    def complete(*, role, prompt, payload):
        calls.append(role)
        assert prompt
        if role == "analyst":
            return analysis(record, packet)
        return accept(payload["draft"], packet)
    review = run_review_cycle(record, packet, complete)
    assert calls == ["analyst", "critic"]
    validate_review(review, record, packet)


@pytest.mark.parametrize("rank,spread,warn", [
    (.2, -20., True), (-.2, 20., True), (.2, 20., False),
    (0., -20., False), (None, -20., False),
])
def test_economic_disagreement_warning_does_not_change_evidence(rank, spread, warn):
    panel, frame, factor, result, campaign = fixture()
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    outcome = study["sections"]["economic_outcomes"]["data"]["outcomes"][0]
    outcome["rank_ic"]["mean"] = rank
    outcome["top_minus_bottom"]["mean"] = spread
    before = deepcopy(study)
    record = {"visibility": "RELEASED_QUALITATIVE", "record_id": "c/e/test",
              "hypothesis_and_calculation": {}, "evidence": {}}
    payload = {"factor": {"definition_hash": "d"}, "mechanism_study": study}
    packet = build_packet(record, payload, None)
    warnings = packet["scientist"]["interpretation_warnings"]
    assert bool(warnings) is warn
    if warn:
        assert warnings[0]["code"] == "ECONOMIC_RANK_MEAN_DISAGREEMENT"
        assert warnings[0]["evidence_ids"] == ["diagnostic.discovery.economic_outcomes"]
    assert study == before
    assert packet["diagnostics"]["economic_outcomes"] == before["sections"]["economic_outcomes"]


def test_critic_revision_and_stale_critique_block_memory():
    record, packet = evidence()
    review = analysis(record, packet)
    review["critic"] = critique_template(review, packet)
    with pytest.raises(ValueError, match="revision"):
        validate_review(review, record, packet)
    review["critic"] = accept(review, packet)
    review["economic_interpretation"] = "기존 해석 수정"
    with pytest.raises(ValueError, match="stale"):
        validate_review(review, record, packet)


def test_economic_link_cannot_be_supported_by_return_gate():
    record, packet = evidence()
    review = analysis(record, packet)
    link = next(row for row in review["mechanism_assessment"] if row["link"] == "economic_change")
    link.update({"assessment": "SUPPORTED", "evidence_ids": ["discovery.check.0"]})
    with pytest.raises(ValueError, match="economic_outcomes"):
        validate_review(review, record, packet, require_critic=False)


def test_cost_link_untested_when_execution_data_missing():
    record, packet = evidence()
    review = analysis(record, packet)
    review["mechanism_assessment"][-1].update({"assessment": "SUPPORTED", "evidence_ids": ["diagnostic.discovery.monthly_performance"]})
    with pytest.raises(ValueError, match="execution_costs"):
        validate_review(review, record, packet, require_critic=False)


def test_plan_must_predict_observations_and_rivals_before_registration():
    plan = plan_template()
    with pytest.raises(ValueError):
        validate_plan(plan)
    for link in plan["links"]:
        link.update({"claim": "경제적 연결", "expected_observation": "예상한 차이", "would_weaken": "차이가 반대로 나타남"})
    for rival in plan["rivals"]:
        rival.update({"claim": "다른 설명", "distinguishing_observation": "구분 가능한 관측"})
    validate_plan(plan)
    plan["negative_control"]["status"] = "PLANNED_NOT_RUN"
    with pytest.raises(ValueError, match="assumptions"):
        validate_plan(plan)


def test_graph_claim_without_artifact_is_blocked():
    record, packet = evidence()
    packet["diagnostics"]["charts"]["status"] = "NOT_COLLECTED"
    review = analysis(record, packet)
    review["visual_inspection"] = "VIEWED"
    with pytest.raises(ValueError, match="charts"):
        validate_review(review, record, packet, require_critic=False)
