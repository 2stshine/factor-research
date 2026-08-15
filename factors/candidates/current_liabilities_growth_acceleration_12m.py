"""Pre-registered acceleration in current-liability growth."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    x = frame.sort_values(["asset_id", "ym"]); g = x.groupby("asset_id")
    p1, p2 = g["current_liabilities"].shift(12), g["current_liabilities"].shift(24)
    y1, y2 = g["ym"].shift(12), g["ym"].shift(24)
    value = x["current_liabilities"] / p1.where(p1 > 0) - p1 / p2.where(p2 > 0)
    return value.where(x["ym"].eq(y1 + 12) & x["ym"].eq(y2 + 24)).reindex(frame.index)

FACTOR = Factor(name="current_liabilities_growth_acceleration_12m", family="short_term_debt_acceleration", category="other",
    hypothesis="유동부채 성장률이 가속한 기업은 단기 차환압력이 커 이후 상대수익이 낮다.", predicted_sign=-1,
    params={"lookback_months": 12, "comparison_months": 24}, rebalance_months=3, needs=("current_liabilities",), compute=compute)
RESEARCH_SPEC = {
    "thesis": "최근 유동부채 성장의 가속도가 높은 종목은 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "단기 의무 증가의 가속은 공급자금융·차입 의존과 가까운 만기 위험의 확대를 나타낼 수 있다.",
    "falsification": "음의 방향과 자동 gate, BY, 봉인 OOS, 귀무 또는 current_liabilities_growth_12m 직교성이 실패하면 기각한다.",
    "expected_relationship": "current_liabilities_growth_12m과 관련되지만 증가율 가속만 측정한다.",
    "data_notes": "DART available_date PIT 유동부채와 정확한 12·24개월 전 양의 값을 요구한다.",
}
