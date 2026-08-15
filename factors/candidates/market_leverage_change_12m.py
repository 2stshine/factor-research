"""Pre-registered 12-month change in market leverage."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    liabilities = ordered["total_liabilities"].where(ordered["total_liabilities"] >= 0)
    market_cap = ordered["market_cap"].where(ordered["market_cap"] > 0)
    current = liabilities / market_cap
    prior = current.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (current - prior).where(ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS))
    return value.reindex(frame.index)


FACTOR = Factor(
    name="market_leverage_change_12m",
    family="market_leverage_change",
    category="other",
    hypothesis="최근 12개월 시장 레버리지가 낮아진 기업은 재무위험 완화가 지연 반영되어 이후 상대수익이 높다.",
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("total_liabilities",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "총부채/월말 시가총액의 12개월 변화가 낮은 종목은 높은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "부채 축소 또는 주주가치 회복으로 낮아진 잔여청구권 위험이 신용·주식시장에 점진적으로 반영될 수 있다.",
    "falsification": "음의 방향, 강건성, BY, 봉인 OOS, 귀무 또는 market_leverage·size·value 직교성 gate가 실패하면 기각한다.",
    "expected_relationship": "market_leverage 수준과 관련되지만 레버리지의 최근 변화만 측정한다.",
    "data_notes": "DART available_date PIT 비음수 총부채와 양의 월말 시가총액을 사용하며 정확히 12개월 전 관측을 요구한다.",
}
