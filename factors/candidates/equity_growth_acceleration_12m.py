"""Pre-registered acceleration in 12-month book-equity growth."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    x = frame.sort_values(["asset_id", "ym"]); g = x.groupby("asset_id")
    p1, p2 = g["total_equity"].shift(12), g["total_equity"].shift(24)
    y1, y2 = g["ym"].shift(12), g["ym"].shift(24)
    value = x["total_equity"] / p1.where(p1 > 0) - p1 / p2.where(p2 > 0)
    return value.where(x["ym"].eq(y1 + 12) & x["ym"].eq(y2 + 24)).reindex(frame.index)

FACTOR = Factor(name="equity_growth_acceleration_12m", family="equity_expansion_acceleration", category="other",
    hypothesis="장부자본 성장률이 가속한 기업은 신규 자본공급과 낮은 자본효율 위험으로 이후 상대수익이 낮다.", predicted_sign=-1,
    params={"lookback_months": 12, "comparison_months": 24}, rebalance_months=3, needs=("total_equity",), compute=compute)
RESEARCH_SPEC = {
    "thesis": "최근 장부자본 성장의 가속도가 높은 종목은 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "자기자본 확대의 가속은 외부자본 조달이나 이익 재투자의 한계수익 저하를 동반할 수 있다.",
    "falsification": "음의 방향과 자동 gate, BY, 봉인 OOS, 귀무 또는 equity_growth_12m 직교성이 실패하면 기각한다.",
    "expected_relationship": "equity_growth_12m과 관련되지만 자기자본 성장의 가속만 측정한다.",
    "data_notes": "DART available_date PIT 자기자본과 정확한 12·24개월 전 양의 자기자본을 요구한다.",
}
