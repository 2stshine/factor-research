"""Pre-registered earnings-confirmed small-value factor; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


COMPONENT_WEIGHT = 1 / 3
NEUTRAL_RANK = 0.5


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    market_cap = ordered["market_cap"].where(ordered["market_cap"] > 0)
    book_to_price = ordered["total_equity"] / market_cap
    value_rank = book_to_price.groupby(ordered["ym"]).rank(pct=True)
    small_rank = (-market_cap).groupby(ordered["ym"]).rank(pct=True)
    surprise_rank = ordered["sue_score"].groupby(ordered["ym"]).rank(pct=True)
    surprise_rank = surprise_rank.fillna(NEUTRAL_RANK)
    composite = COMPONENT_WEIGHT * (value_rank + small_rank + surprise_rank)
    return composite.reindex(frame.index)


FACTOR = Factor(
    name="earnings_confirmed_small_value",
    family="catalyst_small_value",
    category="earnings",
    hypothesis=(
        "저평가된 소형주 중 표준화 이익 서프라이즈가 높은 종목은 실적 촉매가 가격 오류의 교정을 "
        "촉진하여 이후에도 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={
        "component_weight": COMPONENT_WEIGHT,
        "neutral_rank": NEUTRAL_RANK,
    },
    rebalance_months=3,
    needs=("total_equity", "sue_score"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월별 가치·소형·표준화 이익 서프라이즈 순위를 동일 비중으로 결합하면, 단순 소형가치보다 "
        "가격 오류를 해소할 실적 촉매가 있는 종목을 식별해 투자 가능한 롱온리 초과수익을 얻는다."
    ),
    "mechanism": (
        "소형 저평가주는 정보 반영이 느리지만 가치함정일 수 있다. 예상 밖의 이익 개선은 저평가가 "
        "악화된 펀더멘털만 반영한 것이 아님을 확인하고, 제한된 애널리스트 커버리지 아래에서 후속 "
        "가격 조정을 유발한다."
    ),
    "falsification": (
        "투자가능 IC 유지율과 비용 후 성과가 충분하지 않거나, 강건성·고정 OOS·다중검정·Gold "
        "직교성 중 하나라도 hard fail이면 실적 촉매 소형가치 가설을 기각한다."
    ),
    "expected_relationship": (
        "small_value 및 value_bp와 양의 관계를 예상하지만 독립성이 높은 sue_score를 결합하므로 단순 "
        "가치·규모 복합체보다는 관계가 낮아질 것으로 예상한다."
    ),
    "data_notes": (
        "Silver PIT total_equity, market_cap, sue_score만 사용한다. SUE가 PIT로 제공되지 않는 과거 또는 "
        "종목에는 중립 순위 0.5를 부여해 표본을 재정의하거나 미래 가용성을 소급하지 않는다."
    ),
}
