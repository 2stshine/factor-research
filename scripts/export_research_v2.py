"""Export only closed, independently reviewed pilot summaries to the dashboard."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from engine.research_memory_benchmark import MemoryBenchmark
from engine.research_memory_v2 import digest
from engine.research_regime_adoption import market_rows
from engine.research_v2_pilot import PilotBroker
from engine.research_v2_release import load_bundle, public_filter


LABELS = {
    "net_roa": ("순이익 자산수익률", "수익성", "높은 순이익 수익성이 이후 주가 수익과 이어지는가?"),
    "operating_roa": ("영업이익 자산수익률", "수익성", "영업 수익성과 이후 주가 수익의 관계를 다른 노출로 설명할 수 있는가?"),
    "asset_growth_12m": ("총자산 증가율", "투자·자본배분", "자산 증가와 이후 수익의 관계는 실적 변화와도 연결되는가?"),
    "current_assets_growth_12m": ("유동자산 증가율", "투자·자본배분", "유동자산 변화 점수에서 관측되는 관계는 무엇을 의미하는가?"),
    "price_momentum_6_1": ("중단기 가격 모멘텀", "가격 모멘텀", "과거 가격 추세와 이후 수익의 관계가 규모·유동성과 국면을 고려해도 남는가?"),
    "price_momentum_12_3": ("중기 가격 모멘텀", "가격 모멘텀", "최근 구간을 제외한 중기 추세의 관측 관계는 얼마나 일관적인가?"),
}


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_summary(pilot_root, release_root, memory_root, memory_review, real_review):
    pilot_root, release_root, memory_root = map(Path, (pilot_root, release_root, memory_root))
    # Publishing already closed evidence must not rerun it under today's code.
    # Archive mode still authenticates frozen inputs and the STOPPED audit chain.
    broker, bundle = PilotBroker(pilot_root, read_only=True), load_bundle(release_root)
    activation = read(release_root / "activation.json")
    if activation.get("status") != "SIX_REVIEWED_QUALITATIVE_MEMORIES_ACTIVE" or activation.get("evidence_bundle_sha256") != bundle["bundle_sha256"]:
        raise ValueError("Reviewed real memories have not been activated")
    now = datetime.now(timezone.utc).isoformat()
    guard, rows = public_filter(release_root), []
    for cid in broker.cases:
        accepted = read(release_root / "accepted" / f"{cid}.json")
        if not guard(accepted["envelope"], now):
            raise ValueError("Unreleased or stale lesson")
        draft = read(release_root / "drafts" / f"{accepted['draft_sha256']}.json")
        reports = {item["report"]["diagnostic_id"]: item["report"] for item in bundle["evidence"].values() if item["case_id"] == cid}
        fixed, adaptive = [broker.export(cid, arm) for arm in ("FIXED_REFERENCE", "HOST_LLM")]
        if any(x["state"]["state"] != "STOPPED" for x in (fixed, adaptive)):
            raise ValueError("Unclosed pilot session")
        audit = reports["input_audit"]["metrics"]
        assoc, control = reports["association"]["metrics"], reports["controls"]["metrics"]
        actions = []
        for event in adaptive["events"]:
            if event.get("type") == "ACTION" and event["action"].get("kind") == "TEST":
                diagnostic = event["action"]["payload"]["diagnostic_id"]
                result = next((x for x in adaptive["events"] if x.get("type") == "RESULT" and x.get("request_id") == event["request_id"]), {})
                actions.append({"diagnostic_id": diagnostic, "reason": event["action"]["reason"],
                                "status": result.get("evidence", {}).get("response", {}).get("status", result.get("status", "UNKNOWN"))})
        title, family, question = LABELS[cid]
        rows.append({"case_id": cid, "title_ko": title, "family_ko": family, "question_ko": question,
            "mean_rank_ic": control.get("raw_ic", {}).get("mean"),
            "controlled_ic": control.get("fully_adjusted_ic", {}).get("mean"),
            "months": control.get("raw_ic", {}).get("n_months"),
            "signal_coverage": 1 - audit["missing_signal_fraction"],
            "fixed_units": fixed["state"]["cost_units_used"], "adaptive_units": adaptive["state"]["cost_units_used"],
            "actions": actions, "explanation_complete": adaptive["explanation_complete"],
            "lesson": {"title_ko": draft["title_ko"], "facts": [x["text"] for x in draft["facts"]],
                "interpretation": " ".join(x["text"] for x in draft["interpretations"]),
                "unknowns": draft["unknowns"], "limitations": draft["limitations"],
                "rivals": [x["explanation"] + " — " + x["distinguishing_evidence"] for x in draft["competing_explanations"]],
                "next_tests": [x["question"] + " — " + x["design"] for x in draft["next_tests"]],
                "scope_note": "2016-02~2023-06, KOSPI·KOSDAQ 적격 표본, 다음 달 수익. 국면은 공통 KOSPI 기준. 과거 자료 재사용.",
                "evidence_note": "두 방식의 동일 근거는 한 근거로 처리했습니다. 독립 비평 후 정성 교훈만 활성 기억으로 공개했습니다.",
                "draft_sha256": accepted["draft_sha256"], "critic_sha256": accepted["critic_sha256"]}})
    review, score = read(memory_review), MemoryBenchmark(memory_root).score()
    if (review.get("decision") != "ACCEPT" or review.get("cases_checked") != 36 or review.get("material_issue_count") != 0
            or review["sources"]["manifest_file_sha256"] != sha(memory_root / "manifest.json")
            or review["sources"]["sessions_sqlite_file_sha256"] != sha(memory_root / "sessions.sqlite")):
        raise ValueError("Memory comparison lacks a matching independent semantic review")
    arms = []
    for arm, label in (("B0", "기억 없음"), ("B1", "과거 메모 그대로"), ("B2", "범위·수정 검토 기억")):
        scored = [r for r in score["rows"] if r["arm"] == arm]
        arms.append({"arm": arm, "label": label, "cases": len(scored), "correct": sum(r["decision_correct"] for r in scored),
                     "citation_supported": sum(r["evidence_supported"] for r in scored),
                     "evidence_reads": sum(r["source_reads"] for r in scored),
                     "safety_failures": sum(bool(r["unsupported_claim_flags"]) for r in scored)})
    explanation_review = read(real_review)
    if (explanation_review.get("bundle_sha256") != bundle["bundle_sha256"]
            or explanation_review.get("pilot_manifest_sha256") != broker.manifest["manifest_sha256"]
            or explanation_review.get("review_method", {}).get("verification", {}).get("stopped_sessions") != 12
            or len(explanation_review.get("cases", [])) != 6):
        raise ValueError("Actual paired explanation review does not match this pilot")
    review_summary = explanation_review["summary"]
    regime = read(pilot_root / "regime-contract.json")
    regimes = [{"market": market, "counts": dict(Counter(r["regime"] for r in market_rows(regime, market)))} for market in ("KOSPI", "KOSDAQ")]
    return {"schema_version": "public-research-v2-v1", "as_of": "2026-10-02", "generated_at": now,
        "independent_oos_claim": False, "causal_identification": False, "gold_writes": 0,
        "scope_note": "기존 정의 여섯 개를 성과와 무관하게 먼저 고르고, 같은 개발 표본에서 설명 절차를 재분석했습니다. 매월 다시 측정한 진단이며 원래 보유기간 전략의 백테스트가 아닙니다. 기존 연구 전체를 재실행하거나 재승인한 결과가 아닙니다.",
        "autonomy_note": "필수 증거와 예산은 고정합니다. 에이전트가 검사 순서·추가 검사·해석·미확인 사항을 결정합니다. 임의 수식 변경·봉인 결과 조회·새 데이터 구매는 할 수 없습니다.",
        "reviewed_lessons": len(rows), "cases": rows,
        "real_comparison": {
            "arms": [{"arm": arm, "label": label,
                      "nominal_units": sum(row[key] for row in rows),
                      "material_errors": review_summary["material_errors_detected"][arm],
                      "material_omissions": review_summary["material_omissions_detected"][arm],
                      "presentation_gaps": review_summary["separately_enumerated_presentation_gaps"][arm]}
                     for arm, label, key in (("FIXED_REFERENCE", "고정 순서", "fixed_units"), ("HOST_LLM", "에이전트 선택", "adaptive_units"))],
            "decision": "이번 비교에서 선택형의 우월성은 확인되지 않았습니다. 필수 검사는 유지하고 다음 검사 선택을 보조 기능으로 사용합니다.",
            "limitations": "여섯 쌍의 실제 최종 설명을 별도로 읽고 근거와 대조했습니다. 양쪽 모두 같은 근거를 사용했습니다. 선택형 일부 답변에서 국면 발생구간 등 세부 설명이 생략됐지만 중대한 결론 오류로 보지는 않았습니다. 이 건수는 과학적 품질 점수나 일반적인 오류율이 아닙니다. 단위 비용은 시간·토큰·금액이 아닙니다.",
            "review_sha256": sha(real_review)},
        "regime": {"markets": regimes, "note": "파일럿 신호월의 분류입니다. 추세는 월말 지수와 열 달 평균의 거리, 위험은 일별 수익률의 예순세 거래일 변동성을 직전 열두 달 위험과 비교합니다. 단기 위험 변화도 원본에 보존합니다. 개수를 균등하게 맞추지 않았습니다.",
            "limitations": "PIT_ASSUMED · 전체 거래일 달력 독립 인증 미완료. 저위험은 자기 과거 대비 상대적 분류이며 안전·상승 예측이 아닙니다. 모든 팩터는 공통 KOSPI 환경으로 진단했고 KOSDAQ 표는 분류 현황만 보여줍니다."},
        "lookback_note": "모든 팩터에 과거 삼 년을 강제하지 않습니다. 이번 정의는 자체 공식에 필요한 과거 기간만 사용합니다. 신호 계산의 룩백, 레짐 기준 기간, 이후 실적 관측 기간, 별도 검증 창은 서로 다릅니다. 기존 승인 검사의 삼 년 검증 창은 변경하지 않았습니다.",
        "memory_comparison": {"arms": arms, "scope_note": "정답이 정해진 합성 절차 과제 열두 개를 같은 모델 설정·원문 접근·예산으로 비교했습니다. 실제 팩터 수익률 시험과는 별개입니다.",
            "interpretation": "세 구성 모두 판정과 근거 인용이 맞았습니다. 검토 기억은 원문 재조회가 적었지만, 일반적인 연구 성능 우월성을 입증하지는 않았습니다.",
            "limitations": "구성별 한 에이전트가 과제를 묶어 수행해 문맥 의존성이 있습니다. 기억 작성·검토 비용은 제외됐고 토큰·원화 비용은 미측정입니다. 단순 과거 메모 구성은 명시적 기능 제거 비교입니다. 그래프 확장·효용 학습은 아직 채택하지 않습니다.",
            "semantic_review_sha256": sha(memory_review)},
        "stages": [
            {"name": "입력·실행 계약", "status_ko": "완료", "note": "원본 식별자와 총수익 계약을 대조했고, 동결 뒤 자료·수식·기간·코드 변경을 차단합니다."},
            {"name": "실제 진단 파일럿", "status_ko": "완료", "note": "여섯 정의를 두 방식으로 진단하고 각각 별도 에이전트가 해석했습니다. 일반적인 우월성 검증은 아닙니다."},
            {"name": "교훈·활성 기억", "status_ko": "완료", "note": "각 교훈을 별도 비평한 뒤 적용 범위·근거·미확인을 함께 저장했습니다. 과거 교훈을 자동 수입하지 않았습니다."},
            {"name": "동결 검증·승격", "status_ko": "이번 파일럿 대상 아님", "note": "새 팩터 승인 시행이 아니며 기존 캠페인에도 최종 확인 대기 대상이 없었습니다. 봉인 성과와 Gold는 건드리지 않았습니다."},
            {"name": "실전 비용·원인", "status_ko": "미검증 범위 명시", "note": "역사적 업종·가설별 현금흐름·실제 보유와 체결 비용은 이 파일럿에 연결하지 않았습니다. 자료 부족을 경제적 실패로 판정하지 않습니다."},
            {"name": "그래프·효용 학습", "status_ko": "비채택", "note": "소규모 통합 시험만으로 복잡한 검색과 보상 학습의 이익이 증명되지 않았습니다. 범위·수정 관리와 사용 기록부터 운영합니다."}],
        "provenance": {"pilot_manifest_sha256": broker.manifest["manifest_sha256"], "evidence_bundle_sha256": bundle["bundle_sha256"],
                       "regime_contract_sha256": regime["contract_sha256"], "memory_comparison_plan_sha256": score["plan_sha256"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pilot-root", "release-root", "memory-root", "memory-review", "real-review", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    value = build_summary(args.pilot_root, args.release_root, args.memory_root, args.memory_review, args.real_review)
    body = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    if re.search(r"postgres(?:ql)?://|/Users/|\b(?:AKIA|ASIA)[A-Z0-9]{16}|secret_access_key|access_token|password", body, re.I):
        raise ValueError("Private transport or credential content in public export")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(body + "\n")
    print(json.dumps({"status": "EXPORTED_REVIEWED_PUBLIC_SUMMARY", "cases": len(value["cases"]), "sha256": sha(args.output)}))


if __name__ == "__main__":
    main()
