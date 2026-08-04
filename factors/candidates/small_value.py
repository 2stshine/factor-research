"""Pre-registered small-value interaction; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


VALUE_WEIGHT = 0.5
SIZE_WEIGHT = 0.5


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    book_to_price = frame["total_equity"] / market_cap
    value_rank = book_to_price.groupby(frame["ym"]).rank(pct=True)
    small_rank = (-market_cap).groupby(frame["ym"]).rank(pct=True)
    return VALUE_WEIGHT * value_rank + SIZE_WEIGHT * small_rank


FACTOR = Factor(
    name="small_value",
    family="small_value",
    category="value",
    hypothesis=(
        "장부가치 대비 저평가된 소형주는 기관 미커버와 높은 정보비대칭 때문에 가격 오류가 더 "
        "천천히 교정되어 투자 가능한 범위에서도 이후 롱온리 초과수익을 낸다."
    ),
    predicted_sign=1,
    params={"value_weight": VALUE_WEIGHT, "size_weight": SIZE_WEIGHT},
    rebalance_months=3,
    needs=("total_equity",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월별 장부가치/시가총액 순위와 소형주 순위를 동등 결합한 종목을 보유하면, 단독 가치나 "
        "단독 규모 신호보다 비용 후 안정적인 초과수익을 얻는다."
    ),
    "mechanism": (
        "소형주는 애널리스트와 기관의 관심이 적어 공시 정보가 가격에 늦게 반영되고, 저평가까지 "
        "겹치면 과도한 비관이 교정되는 폭이 커질 수 있다. 고정 유동성 유니버스는 체결 불가능한 "
        "초소형주 효과와 이 메커니즘을 구분한다."
    ),
    "falsification": (
        "투자가능 유니버스에서 IC가 유지되지 않거나, 비용·회전율 반영 후 성과가 부족하거나, "
        "중립화·기간분할·OOS·다중검정 또는 Gold 직교성 검사를 통과하지 못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "value_bp와 size 모두에 중간 이상의 양의 관계를 예상한다. 동등 결합으로 어느 하나와 완전히 "
        "같지 않으며 수익성·SUE 팩터와는 낮은 관계를 예상한다."
    ),
    "data_notes": (
        "Silver PIT total_equity와 월말 market_cap을 사용한다. 팩터 내부에서 유니버스를 자르지 않고 "
        "월별 횡단면 순위만 결합하며, 실제 투자 가능성은 공통 게이트가 판정한다."
    ),
}
