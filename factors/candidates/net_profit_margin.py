"""Pre-registered net profit margin candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    revenue = frame["revenue_ttm"].where(frame["revenue_ttm"] > 0)
    return frame["net_income_ttm"] / revenue


FACTOR = Factor(
    name="net_profit_margin",
    family="net_profit_margin",
    category="quality",
    hypothesis=(
        "매출액 대비 최종 순이익이 높은 기업은 영업 효율뿐 아니라 금융비용·세금·비영업손익까지 "
        "관리하는 전사적 수익성이 높고, 시장이 이 수익성의 지속성을 과소평가해 이후 상대적으로 "
        "높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("net_income_ttm", "revenue_ttm"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 최근 12개월 순이익을 같은 기간 매출액으로 나눈 단일 순이익률이 높은 "
        "종목은 이후 수익률 순위도 높을 것이다."
    ),
    "mechanism": (
        "높은 순이익률은 가격결정력과 비용 통제뿐 아니라 이자·세금·비영업 항목까지 통과한 "
        "최종 수익성을 뜻한다. 투자자가 일시적 비용 충격과 지속 가능한 전사적 효율을 충분히 "
        "구분하지 못하면 높은 최종 마진 기업이 점진적으로 재평가될 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, 고정 OOS, "
        "다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "영업이익률인 qual_opm 및 자기자본 수익성인 qual_roe와 양의 관계를 예상한다. 다만 "
        "분모가 매출이고 이자·세금·비영업손익을 포함하므로 두 팩터와 완전히 같지는 않을 것으로 "
        "예상한다. 가치·모멘텀 팩터와의 관계는 상대적으로 낮을 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 정정공시를 재생한 Silver PIT net_income_ttm과 revenue_ttm만 "
        "사용한다. 매출액이 0 이하인 관측은 비율이 정의되지 않아 결측으로 두며, 금융업처럼 "
        "매출 정의가 일반 제조업과 다른 업종에서는 경제적 의미가 달라질 수 있다."
    ),
}
