"""Pre-registered 12-month sales-growth candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    revenue = ordered["revenue_ttm"].where(ordered["revenue_ttm"] > 0)
    prior_revenue = revenue.groupby(ordered["asset_id"]).shift(LOOKBACK_MONTHS)
    growth = revenue / prior_revenue - 1
    return growth.reindex(frame.index)


FACTOR = Factor(
    name="sales_growth_12m",
    family="sales_growth",
    category="other",
    hypothesis=(
        "최근 12개월 매출 증가율이 지나치게 높은 기업은 투자자의 성장 외삽으로 기대가 가격에 "
        "과도하게 반영되는 반면, 낮은 매출 성장 기업은 낮은 기대가 정상화되며 이후 상대적으로 "
        "높은 수익을 낸다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("revenue_ttm",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 최근 12개월 매출 증가율이 낮은 종목은 높은 성장률을 기록한 종목보다 이후 "
        "수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "투자자는 최근의 높은 외형 성장을 장기간 지속될 것으로 외삽하고 성장 기업에 높은 "
        "기대를 부여할 수 있다. 경쟁과 기저효과로 매출 성장이 정상화되면 고성장 종목의 가격이 "
        "조정되고, 낮은 기대를 가진 저성장 종목은 작은 개선에도 재평가될 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "낮은 성장을 선호하므로 asset_growth_12m과 양의 관계, 성장 기대가 낮은 가치주를 일부 "
        "포착해 value_sp와 양의 관계를 예상한다. 매출 변화율이므로 수익성 수준 및 모멘텀과는 "
        "완전히 다른 신호일 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 정정공시를 재생한 Silver PIT revenue_ttm을 사용한다. 현재와 "
        "12개월 전 매출이 모두 양수인 관측만 정의되며 최초 12개월은 결측이다. 공시 간에는 같은 "
        "TTM 값이 유지될 수 있고, 인수합병·사업분할의 구조적 매출 변화는 별도로 조정하지 않는다."
    ),
}
