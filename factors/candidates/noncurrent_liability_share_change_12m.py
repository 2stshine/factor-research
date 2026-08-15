"""Pre-registered 12-month change in noncurrent-liability share."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    liabilities = ordered["total_liabilities"].where(ordered["total_liabilities"] > 0)
    current = ordered["noncurrent_liabilities"] / liabilities
    prior = current.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (current - prior).where(ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS))
    return value.reindex(frame.index)


FACTOR = Factor(
    name="noncurrent_liability_share_change_12m",
    family="liability_maturity_change",
    category="other",
    hypothesis="총부채 중 비유동부채 비중이 최근 12개월 높아진 기업은 단기 차환압력이 완화되어 이후 상대수익이 높다.",
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("noncurrent_liabilities", "total_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT noncurrent_liabilities/total_liabilities의 12개월 변화가 큰 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "부채 만기가 장기로 이동하면 가까운 시점의 차환·유동성 충격 노출이 줄어 재무 유연성이 개선될 수 있다.",
    "falsification": "양의 방향, 강건성, BY, 봉인 OOS, 귀무 또는 단기 지급능력·레버리지 신호와의 직교성이 실패하면 기각한다.",
    "expected_relationship": "noncurrent_liabilities_to_assets와 관련되지만 총부채 내 만기구성의 12개월 변화만 측정한다.",
    "data_notes": "DART available_date PIT 비유동부채와 양의 총부채를 사용하며 정확히 12개월 전 비율이 있을 때만 정의한다.",
}
