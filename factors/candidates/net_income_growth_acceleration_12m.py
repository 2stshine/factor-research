"""Pre-registered acceleration in 12-month net-income growth."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    x = frame.sort_values(["asset_id", "ym"]); g = x.groupby("asset_id")
    p1, p2 = g["net_income_ttm"].shift(12), g["net_income_ttm"].shift(24)
    y1, y2 = g["ym"].shift(12), g["ym"].shift(24)
    value = x["net_income_ttm"] / p1.where(p1 > 0) - p1 / p2.where(p2 > 0)
    return value.where(x["ym"].eq(y1 + 12) & x["ym"].eq(y2 + 24)).reindex(frame.index)

FACTOR = Factor(name="net_income_growth_acceleration_12m", family="net_earnings_acceleration", category="earnings",
    hypothesis="순이익 성장률이 가속한 기업은 최종 이익 개선이 늦게 반영되어 이후 상대수익이 높다.", predicted_sign=1,
    params={"lookback_months": 12, "comparison_months": 24}, rebalance_months=3, needs=("net_income_ttm",), compute=compute)
RESEARCH_SPEC = {
    "thesis": "최근 순이익 성장의 가속도가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "최종 이익 가속은 영업·금융·세후 성과의 동시 개선을 포착해 기대치가 후행 조정될 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 net_income_growth_12m 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: net_income_growth_12m — 차이: 성장률 수준이 아니라 성장률 가속만 측정한다.",
    "data_notes": "DART available_date PIT 순이익과 정확한 12·24개월 전 양의 순이익을 요구한다.",
}
