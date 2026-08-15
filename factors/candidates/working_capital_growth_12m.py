"""Pre-registered annual net working-capital investment growth."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    working_capital = ordered["current_assets"] - ordered["current_liabilities"]
    prior = working_capital.groupby(ordered["asset_id"], sort=False).shift(LOOKBACK_MONTHS)
    prior_month = ordered.groupby("asset_id", sort=False)["ym"].shift(LOOKBACK_MONTHS)
    value = working_capital / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="working_capital_growth_12m", family="working_capital_investment",
    category="other", hypothesis="순운전자본이 빠르게 증가한 기업은 자금이 영업자산에 묶여 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"lookback_months": LOOKBACK_MONTHS}, rebalance_months=3,
    needs=("current_assets", "current_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "양의 순운전자본의 12개월 증가율이 높은 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "재고·매출채권 등 단기자산 투자는 현금을 흡수하고 과잉확장 위험을 높인다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 투자 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: working_capital_accruals_12m — 차이: 총자산 스케일 발생액이 아니라 양의 순운전자본 자체의 연간 성장률을 측정한다.",
    "data_notes": "DART available_date PIT 유동자산·유동부채와 정확한 12개월 전 양의 순운전자본을 요구한다.",
}
