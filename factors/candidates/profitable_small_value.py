"""Pre-registered profitable small-value composite; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


COMPONENT_WEIGHT = 1 / 3
NEUTRAL_RANK = 0.5


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    market_cap = ordered["market_cap"].where(ordered["market_cap"] > 0)
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    book_to_price = ordered["total_equity"] / market_cap
    operating_roa = ordered["operating_income_ttm"] / assets
    value_rank = book_to_price.groupby(ordered["ym"]).rank(pct=True)
    small_rank = (-market_cap).groupby(ordered["ym"]).rank(pct=True)
    profitability_rank = operating_roa.groupby(ordered["ym"]).rank(pct=True)
    profitability_rank = profitability_rank.fillna(NEUTRAL_RANK)
    composite = COMPONENT_WEIGHT * (value_rank + small_rank + profitability_rank)
    return composite.reindex(frame.index)


FACTOR = Factor(
    name="profitable_small_value",
    family="quality_small_value",
    category="quality",
    hypothesis=(
        "저평가된 소형주 중 총자산 대비 영업이익이 높은 기업은 가격 오류와 지속 가능한 영업성과를 "
        "동시에 보유해 이후에도 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={
        "component_weight": COMPONENT_WEIGHT,
        "neutral_rank": NEUTRAL_RANK,
    },
    rebalance_months=3,
    needs=("total_equity", "operating_income_ttm", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월별 장부가치/시가총액·소형주·영업ROA 순위를 동일 비중으로 결합하면, 단순 소형가치의 "
        "가격 오류 프리미엄을 유지하면서 영업 기반이 취약한 가치함정을 줄여 롱온리 초과수익을 얻는다."
    ),
    "mechanism": (
        "소형 저평가주는 정보 비대칭 때문에 천천히 재평가되지만 낮은 가격이 영업 부진을 정당하게 "
        "반영한 경우도 많다. 높은 영업ROA는 자산이 실제 영업이익을 창출한다는 지속적인 확인 신호로, "
        "가격 오류와 구조적 부실을 구분한다."
    ),
    "falsification": (
        "투자가능 IC 유지율과 비용 후 성과가 충분하지 않거나, 강건성·고정 OOS·다중검정·Gold "
        "직교성 중 하나라도 hard fail이면 수익성 소형가치 가설을 기각한다."
    ),
    "expected_relationship": (
        "small_value와 가장 높은 양의 관계를, qual_roe·qual_opm과 중간 정도의 양의 관계를 예상한다. "
        "수익성 축 때문에 단순 가치·규모 복합체와 완전히 같지는 않을 것으로 예상한다."
    ),
    "data_notes": (
        "Silver PIT total_equity, operating_income_ttm, total_assets와 월말 market_cap을 사용한다. 영업ROA가 "
        "없는 관측은 해당 축에만 중립 순위 0.5를 부여해 표본을 재정의하지 않는다."
    ),
}
