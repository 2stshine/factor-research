"""Pre-registered acceleration in retained-earnings growth."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    x = frame.sort_values(["asset_id", "ym"]); g = x.groupby("asset_id")
    p1, p2 = g["retained_earnings"].shift(12), g["retained_earnings"].shift(24)
    y1, y2 = g["ym"].shift(12), g["ym"].shift(24)
    value = x["retained_earnings"] / p1.where(p1 > 0) - p1 / p2.where(p2 > 0)
    return value.where(x["ym"].eq(y1 + 12) & x["ym"].eq(y2 + 24)).reindex(frame.index)

FACTOR = Factor(name="retained_earnings_growth_acceleration_12m", family="internal_capital_acceleration", category="quality",
    hypothesis="이익잉여금 성장률이 가속한 기업은 내부자본 축적이 강화되어 이후 상대수익이 높다.", predicted_sign=1,
    params={"lookback_months": 12, "comparison_months": 24}, rebalance_months=3, needs=("retained_earnings",), compute=compute)
RESEARCH_SPEC = {
    "thesis": "최근 이익잉여금 성장의 가속도가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "내부자본 축적의 가속은 외부조달 의존도 감소와 누적 수익력 개선을 나타낼 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 retained_earnings_growth_12m 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: retained_earnings_growth_12m — 차이: 성장률 수준이 아니라 성장의 가속만 측정한다.",
    "data_notes": "DART available_date PIT 이익잉여금과 정확한 12·24개월 전 양의 값을 요구한다.",
}
