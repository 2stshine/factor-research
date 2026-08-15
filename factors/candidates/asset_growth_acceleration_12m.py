"""Pre-registered acceleration in 12-month asset growth."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    x = frame.sort_values(["asset_id", "ym"]); g = x.groupby("asset_id")
    p1, p2 = g["total_assets"].shift(12), g["total_assets"].shift(24)
    y1, y2 = g["ym"].shift(12), g["ym"].shift(24)
    value = x["total_assets"] / p1.where(p1 > 0) - p1 / p2.where(p2 > 0)
    return value.where(x["ym"].eq(y1 + 12) & x["ym"].eq(y2 + 24)).reindex(frame.index)

FACTOR = Factor(name="asset_growth_acceleration_12m", family="investment_acceleration", category="other",
    hypothesis="자산성장률이 가속한 기업은 투자 과잉 위험이 커 이후 상대수익이 낮다.", predicted_sign=-1,
    params={"lookback_months": 12, "comparison_months": 24}, rebalance_months=3, needs=("total_assets",), compute=compute)
RESEARCH_SPEC = {
    "thesis": "최근 자산성장률의 직전 12개월 대비 가속도가 높은 종목은 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "급격히 가속하는 투자와 인수는 자본배분 규율 저하와 수익성 평균회귀를 동반할 수 있다.",
    "falsification": "음의 방향과 자동 gate, BY, 봉인 OOS, 귀무 또는 asset_growth_12m 직교성이 실패하면 기각한다.",
    "expected_relationship": "asset_growth_12m과 관련되지만 투자 성장의 가속만 측정한다.",
    "data_notes": "DART available_date PIT 총자산과 정확한 12·24개월 전 양의 총자산을 요구한다.",
}
