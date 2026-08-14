"""Pre-registered defensive-value composite; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12
VALUE_WEIGHT = 0.5
STABILITY_WEIGHT = 0.5


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    book_to_price = ordered["total_equity"] / ordered["market_cap"].where(
        ordered["market_cap"] > 0
    )
    monthly_return = ordered.groupby("asset_id")["adj_close"].pct_change()
    volatility = (
        monthly_return.groupby(ordered["asset_id"])
        .rolling(LOOKBACK_MONTHS, min_periods=LOOKBACK_MONTHS)
        .std()
        .reset_index(level=0, drop=True)
    )
    value_rank = book_to_price.groupby(ordered["ym"]).rank(pct=True)
    stability_rank = (-volatility).groupby(ordered["ym"]).rank(pct=True)
    composite = VALUE_WEIGHT * value_rank + STABILITY_WEIGHT * stability_rank
    return composite.reindex(frame.index)


FACTOR = Factor(
    name="defensive_value",
    family="defensive_value",
    category="value",
    hypothesis=(
        "장부가치 대비 저평가되면서 최근 12개월 가격 변동성이 낮은 종목은 고변동 가치함정을 "
        "피하면서 가치 프리미엄을 보존해 이후 롱온리 초과수익을 낸다."
    ),
    predicted_sign=1,
    params={
        "lookback_months": LOOKBACK_MONTHS,
        "value_weight": VALUE_WEIGHT,
        "stability_weight": STABILITY_WEIGHT,
    },
    rebalance_months=3,
    needs=("total_equity",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월별 장부가치/시가총액 순위와 12개월 저변동성 순위를 동등 결합한 종목을 보유하면, "
        "단순 가치 또는 단순 저변동성보다 비용 후 안정적인 초과수익을 얻는다."
    ),
    "mechanism": (
        "가치주는 과잉반응 교정의 수익원을 제공하지만 일부는 사업 악화와 재무적 취약성으로 싼 "
        "가치함정이다. 낮은 가격 변동성 조건은 시장이 지속적으로 재평가하는 취약 종목을 줄여 "
        "가치 프리미엄의 질을 높인다."
    ),
    "falsification": (
        "상폐 종착수익률 세 시나리오에서 방향이 유지되지 않거나, 투자가능 유니버스 IC와 비용 후 "
        "순알파가 기준을 충족하지 않거나, 강건성·OOS·다중검정 또는 기존 Gold 직교성 검사를 "
        "통과하지 못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "value_bp와 low_vol_12m 모두에 중간 이상의 양의 관계를 예상한다. 두 신호를 동등 결합하므로 "
        "어느 하나와 완전히 동일하지 않고, 수익성 팩터와는 낮거나 중간 수준의 관계를 예상한다."
    ),
    "data_notes": (
        "Silver PIT total_equity와 월말 분할조정 가격 adj_close를 사용한다. 각 월의 횡단면 백분위 순위로 "
        "단위 차이를 제거하며 최초 12개월은 변동성 계산 때문에 의도적으로 결측이다."
    ),
}
