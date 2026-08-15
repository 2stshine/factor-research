"""Pre-registered 12-month change in current ratio."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    liabilities = ordered["current_liabilities"].where(
        ordered["current_liabilities"] > 0
    )
    current = ordered["current_assets"] / liabilities
    prior = current.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (current - prior).where(ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS))
    return value.reindex(frame.index)


FACTOR = Factor(
    name="current_ratio_change_12m",
    family="short_term_solvency_change",
    category="quality",
    hypothesis="최근 12개월 유동비율이 개선된 기업은 단기 자금압박이 낮아져 이후 상대수익이 높다.",
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("current_assets", "current_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT current_assets/current_liabilities의 12개월 변화가 큰 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "단기 지급능력의 개선은 불리한 차환·증자 위험을 낮추며, 공시 후 점진적으로 가격에 반영될 수 있다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "current_ratio 수준과 양의 관계를 예상하지만, 최근 12개월 개선폭만 측정하므로 정의상 구별된다.",
    "data_notes": "DART available_date PIT 유동자산과 양의 유동부채를 쓰며 정확히 12개월 전 비율이 있을 때만 정의한다.",
}
