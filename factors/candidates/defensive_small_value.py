"""Pre-registered defensive small-value composite; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12
COMPONENT_WEIGHT = 1 / 3


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    market_cap = ordered["market_cap"].where(ordered["market_cap"] > 0)
    book_to_price = ordered["total_equity"] / market_cap
    monthly_return = ordered.groupby("asset_id")["adj_close"].pct_change()
    volatility = (
        monthly_return.groupby(ordered["asset_id"])
        .rolling(LOOKBACK_MONTHS, min_periods=LOOKBACK_MONTHS)
        .std()
        .reset_index(level=0, drop=True)
    )
    value_rank = book_to_price.groupby(ordered["ym"]).rank(pct=True)
    small_rank = (-market_cap).groupby(ordered["ym"]).rank(pct=True)
    stability_rank = (-volatility).groupby(ordered["ym"]).rank(pct=True)
    composite = COMPONENT_WEIGHT * (value_rank + small_rank + stability_rank)
    return composite.reindex(frame.index)


FACTOR = Factor(
    name="defensive_small_value",
    family="small_value",
    category="value",
    hypothesis=(
        "저평가·소형·저변동 특성이 동시에 있는 종목은 정보 비대칭에 따른 가격 오류를 보유하면서 "
        "취약하고 투자 불가능한 소형주를 줄여 이후 안정적인 롱온리 초과수익을 낸다."
    ),
    predicted_sign=1,
    params={
        "lookback_months": LOOKBACK_MONTHS,
        "component_weight": COMPONENT_WEIGHT,
    },
    rebalance_months=3,
    needs=("total_equity",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월별 가치·소형·12개월 저변동성 순위를 동등 결합한 종목을 보유하면, 소형가치의 높은 "
        "초과수익을 유지하면서 투자 가능 유니버스의 신호 보존성과 수익 안정성을 개선한다."
    ),
    "mechanism": (
        "저평가된 소형주는 정보 반영이 느리지만 일부 성과는 거래가 어렵고 취약한 종목에서 나온다. "
        "가격 안정성은 지속적인 악재 재평가와 복권형 변동이 큰 종목을 줄여, 거래 가능한 정보 "
        "비대칭 프리미엄을 분리한다."
    ),
    "falsification": (
        "투자가능 IC 유지율과 비용 후 성과가 충분하지 않거나, 리밸런싱·분위수·비용·기간·중립화 "
        "강건성, 고정 OOS, 다중검정 또는 Gold 직교성 중 하나라도 hard fail이면 가설을 기각한다."
    ),
    "expected_relationship": (
        "small_value와 가장 높은 양의 관계를 예상하고 value_bp, size, low_vol_12m과도 중간 이상의 "
        "양의 관계를 예상한다. 세 축 결합으로 단일 팩터와 완전히 같지는 않을 것으로 예상한다."
    ),
    "data_notes": (
        "Silver PIT total_equity, 월말 market_cap 및 분할조정 가격 adj_close를 사용한다. 각 구성요소는 월별 "
        "횡단면 순위이며 최초 12개월은 변동성 계산 때문에 의도적으로 결측이다."
    ),
}
