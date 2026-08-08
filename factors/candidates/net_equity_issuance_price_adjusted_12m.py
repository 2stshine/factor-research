"""Price-adjusted 12-month net equity issuance; pre-registration candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    market_cap = ordered["market_cap"].where(ordered["market_cap"] > 0)
    split_adjusted_price = ordered["adj_close"].where(ordered["adj_close"] > 0)
    adjusted_share_base = market_cap / split_adjusted_price
    prior_base = adjusted_share_base.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    consecutive = ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS)
    issuance = (adjusted_share_base / prior_base.where(prior_base > 0) - 1).where(
        consecutive
    )
    return issuance.reindex(frame.index)


FACTOR = Factor(
    name="net_equity_issuance_price_adjusted_12m",
    family="net_equity_issuance",
    category="other",
    hypothesis=(
        "최근 12개월 가격효과를 제거한 자기자본 발행이 큰 기업은 경영자의 고평가 활용 또는 "
        "외부자금 수요를 드러내며 이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "시가총액을 배당을 포함하지 않는 분할조정 가격으로 나눈 주식수 기반치의 정확한 "
        "12개월 증가율이 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "경영자는 주가가 내재가치보다 높거나 외부자금 수요가 클 때 주식을 발행할 유인이 "
        "있다. 시장이 이 발행 결정을 늦게 해석하면 발행기업의 상대가격이 이후 조정될 수 있다."
    ),
    "falsification": (
        "무결성·커버리지·IC·Rank ICIR·기간 강건성·중립화·다중검정 또는 정식 confirmation "
        "기준을 통과하지 못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "기업 확장과 자금조달이 함께 나타날 수 있어 asset_growth_12m과 일부 관계를 예상하지만, "
        "가격 모멘텀과 배당수익을 제거하므로 완전한 중복은 아닐 것으로 예상한다."
    ),
    "data_notes": (
        "Silver PIT market_cap과 분할조정 가격 adj_close를 사용한다. 기존 "
        "net_equity_issuance_12m은 배당 포함 total-return을 분모로 사용해 배당을 발행 감소처럼 "
        "섞으므로 보존하되 재사용하지 않는다. 정확히 12개월 전 관측이 없으면 결측이다."
    ),
}
