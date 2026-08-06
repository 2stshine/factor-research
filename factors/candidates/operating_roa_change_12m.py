"""Pre-registered operating-ROA change candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    operating_roa = ordered["operating_income_ttm"] / assets
    prior_roa = operating_roa.groupby(ordered["asset_id"]).shift(LOOKBACK_MONTHS)
    change = operating_roa - prior_roa
    return change.reindex(frame.index)


FACTOR = Factor(
    name="operating_roa_change_12m",
    family="profitability_change",
    category="earnings",
    hypothesis=(
        "최근 12개월 동안 영업 자산수익성이 개선된 기업은 사업 효율과 이익 체력이 강화되고, "
        "시장이 이 개선의 지속성을 점진적으로 반영해 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("operating_income_ttm", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 operating_income_ttm/total_assets가 12개월 전보다 많이 개선된 종목은 이후 "
        "수익률 순위도 높을 것이다."
    ),
    "mechanism": (
        "영업 자산수익성 개선은 같은 자산 기반에서 더 많은 핵심 이익을 만들거나 비효율 자산을 "
        "정리하고 있다는 신호다. 투자자가 수익성 수준에는 반응해도 변화의 지속성을 한 번에 "
        "반영하지 못하면 후속 공시와 함께 가격이 점진적으로 조정될 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "수익성 수준을 쓰는 operating_roa와 약한 양의 관계, 이익 변화 정보를 담는 sue와 중간 "
        "정도의 양의 관계를 예상한다. 수준이 아닌 12개월 변화량이므로 qual_opm·qual_roe와의 "
        "중복은 제한적일 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 total_assets를 "
        "사용한다. 현재와 12개월 전 총자산이 양수인 관측만 정의되며 최초 12개월은 결측이다. "
        "공시 사이에는 신호가 계단형이고 인수합병·사업분할 효과는 별도로 조정하지 않는다."
    ),
}
