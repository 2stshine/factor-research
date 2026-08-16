"""Pre-registered acceleration in 12-month sales growth."""
from __future__ import annotations
from engine.factors import Factor
LOOKBACK_MONTHS = 12

def compute(frame):
    x = frame.sort_values(["asset_id", "ym"]); g = x.groupby("asset_id")
    p1, p2 = g["revenue_ttm"].shift(12), g["revenue_ttm"].shift(24)
    y1, y2 = g["ym"].shift(12), g["ym"].shift(24)
    value = x["revenue_ttm"] / p1.where(p1 > 0) - p1 / p2.where(p2 > 0)
    return value.where(x["ym"].eq(y1 + 12) & x["ym"].eq(y2 + 24)).reindex(frame.index)

FACTOR = Factor(name="sales_growth_acceleration_12m", family="sales_growth_acceleration", category="earnings",
    hypothesis="12개월 매출성장률이 이전 12개월보다 가속한 기업은 수요 개선이 늦게 반영되어 이후 상대수익이 높다.",
    predicted_sign=1, params={"lookback_months": 12, "comparison_months": 24}, rebalance_months=3,
    needs=("revenue_ttm",), compute=compute)
RESEARCH_SPEC = {
    "thesis": "최근 전년동기 매출성장률에서 직전 전년동기 성장률을 뺀 값이 큰 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "성장 수준보다 성장의 가속은 수요·점유율 변화의 방향을 포착하며 후속 공시까지 점진 반영될 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 sales_growth_12m 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: sales_growth_12m — 차이: 성장률 수준이 아니라 성장률의 2차 차분만 측정한다.",
    "data_notes": "DART available_date PIT 매출과 정확한 12·24개월 전 양의 매출을 요구한다.",
}
