"""Pre-registered asset-turnover change candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    turnover = ordered["revenue_ttm"] / assets
    prior_turnover = turnover.groupby(ordered["asset_id"]).shift(LOOKBACK_MONTHS)
    change = turnover - prior_turnover
    return change.reindex(frame.index)


FACTOR = Factor(
    name="asset_turnover_change_12m",
    family="asset_turnover_change",
    category="quality",
    hypothesis=(
        "최근 12개월 동안 총자산 대비 매출 창출력이 개선된 기업은 자산 활용 효율이 강화되고, "
        "시장이 이 운영 개선의 지속성을 늦게 반영해 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("revenue_ttm", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 revenue_ttm/total_assets가 12개월 전보다 많이 개선된 종목은 이후 수익률 "
        "순위도 높을 것이다."
    ),
    "mechanism": (
        "자산회전율 개선은 같은 자산 기반으로 더 많은 매출을 만들거나 비생산적 자산을 정리한 "
        "결과다. 투자자가 현재 효율 수준에는 반응해도 개선 추세의 지속성을 충분히 반영하지 "
        "못하면 후속 공시와 함께 가격이 점진적으로 조정될 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "자산 효율 수준인 asset_turnover와 약한 양의 관계, 매출 변화가 분자에 있으므로 "
        "sales_growth_12m과 중간 정도의 양의 관계를 예상한다. 수준이 아닌 변화량이므로 기존 "
        "수익성 팩터와의 중복은 제한적일 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT revenue_ttm과 total_assets를 사용한다. "
        "현재와 12개월 전 총자산이 양수인 관측만 정의되며 최초 12개월은 결측이다. 인수합병·"
        "사업분할에 따른 구조적 매출·자산 변화는 별도로 조정하지 않는다."
    ),
}
