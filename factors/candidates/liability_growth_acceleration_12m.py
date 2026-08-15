"""Pre-registered acceleration in 12-month liability growth."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    x = frame.sort_values(["asset_id", "ym"]); g = x.groupby("asset_id")
    p1, p2 = g["total_liabilities"].shift(12), g["total_liabilities"].shift(24)
    y1, y2 = g["ym"].shift(12), g["ym"].shift(24)
    value = x["total_liabilities"] / p1.where(p1 > 0) - p1 / p2.where(p2 > 0)
    return value.where(x["ym"].eq(y1 + 12) & x["ym"].eq(y2 + 24)).reindex(frame.index)

FACTOR = Factor(name="liability_growth_acceleration_12m", family="debt_growth_acceleration", category="other",
    hypothesis="부채성장률이 가속한 기업은 재무위험과 자금수요가 커 이후 상대수익이 낮다.", predicted_sign=-1,
    params={"lookback_months": 12, "comparison_months": 24}, rebalance_months=3, needs=("total_liabilities",), compute=compute)
RESEARCH_SPEC = {
    "thesis": "최근 총부채 성장의 가속도가 높은 종목은 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "채무 증가의 가속은 차환 의존도나 공격적 투자 확대를 나타내며 하방 위험이 늦게 반영될 수 있다.",
    "falsification": "음의 방향과 자동 gate, BY, 봉인 OOS, 귀무 또는 liability_growth_12m 직교성이 실패하면 기각한다.",
    "expected_relationship": "liability_growth_12m과 관련되지만 부채 성장의 2차 차분이다.",
    "data_notes": "DART available_date PIT 총부채와 정확한 12·24개월 전 양의 총부채를 요구한다.",
}
