"""Preregistered accounting operating-cost intensity; no outcome-based tuning."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    revenue = frame["revenue_ttm"].where(frame["revenue_ttm"] > 0)
    cost = revenue - frame["operating_income_ttm"]
    return cost.where(cost >= 0) / assets


FACTOR = Factor(
    name="operating_cost_intensity", family="operating_cost_gearing", category="quality",
    exploration_domain="profitability_quality", predicted_sign=1, params={}, rebalance_months=1,
    needs=("revenue_ttm", "operating_income_ttm", "total_assets"), compute=compute,
    hypothesis="자산 대비 회계상 영업비용이 큰 기업은 수요 충격에 대한 비용 조정 부담 때문에 더 높은 기대수익을 요구받을 수 있다.",
)

RESEARCH_SPEC = {
    "thesis": "당시 공개된 매출 TTM에서 영업이익 TTM을 뺀 값을 양의 총자산으로 나눈 단일 비율과 다음 달 수익률 순위의 양의 관계를 검토한다.",
    "mechanism": "Novy-Marx (2011), Operating Leverage, doi:10.1093/rof/rfq019의 영업비용 위험보상 가설을 참고한다. 매출 충격에 비용이 충분히 조정되지 않으면 영업위험이 커질 수 있다. 이 연구는 고정비나 비용 탄력성을 직접 측정하지 않으며 원 논문의 COGS+SG&A 계정을 정확히 재현한 것도 아니다.",
    "falsification": "비용 조정 경직성이나 업종 구성을 확인할 자료가 없으면 경제적 원인은 미확인으로 남긴다. 수익 연관성이 동반 규모·유동성 노출로 약해지거나 기존 매출회전율과 중복되면 독립적인 비용위험 설명이 약해진다. 팩터 승인 여부는 기존 고정 gate 전체를 따른다.",
    "expected_relationship": "asset_turnover의 매출/자산과 operating_roa의 영업이익/자산 차이에 대수적으로 해당하므로 높은 중복 가능성을 사전에 인정한다. 기존 점수의 합성은 아니며 하나의 회계상 비용 분자 비율이다. 효율성·수익성의 과소반영과 달리 비용위험 보상을 검토하며 기존 상관 사전검사를 우회하지 않는다.",
    "data_notes": "인증 Silver PIT revenue_ttm, operating_income_ttm, total_assets만 사용한다. 양의 매출·자산 및 음수가 아닌 계산 비용만 유효하며 결측을 대체하지 않는다. 추가 가격 룩백은 없지만 TTM 원천에는 네 분기 이력이 필요하다. 월별 리밸런싱이며 과거 노출이 있는 연구 구간을 독립 OOS라고 부르지 않는다. 문헌: https://doi.org/10.1093/rof/rfq019 ; 원문 https://tevgeniou.github.io/EquityRiskFactors/bibliography/OperatingLeverageFactor.pdf §2–3.",
    "diagnostic_plan": {
        "question_kind": "EXPLANATORY",
        "question": "비용집약도와 다음 달 수익의 관계를 규모·거래활동 및 각 시장 국면에서 검토하라. 수요 둔화와 물가 상승이 함께 나타나는 생산 하락·물가 상승 방향과 반대 환경을 사전 대비하되, 이 분류는 실제 매출충격이나 고정비 경직성의 직접 측정이 아니다. 자산회전율·영업수익성·업종 구성과 비용위험을 구분할 증거의 공백을 명시하라.",
        "execution_cost": True,
        "ratio_controls": [{"name": "asset_turnover", "numerator": "revenue_ttm", "denominator": "total_assets", "available_at": "available_date"}],
        "input_history": {
            "revenue_ttm": {"source_history_months": 12, "source_ref": "Silver certified four-quarter TTM contract"},
            "operating_income_ttm": {"source_history_months": 12, "source_ref": "Silver certified four-quarter TTM contract"},
            "total_assets": {"source_history_months": 0, "source_ref": "Silver PIT balance-sheet stock, not summed"}
        },
        "macro_axes": ["KR_PRODUCTION_INFLATION_DIRECTION"],
        "macro_contrasts": {"KR_PRODUCTION_INFLATION_DIRECTION": ["PRODUCTION_UP_INFLATION_DOWN", "PRODUCTION_DOWN_INFLATION_UP"]}
    }
}
