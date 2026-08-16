"""Pre-registered acceleration in 12-month pretax-income growth."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    x = frame.sort_values(["asset_id", "ym"]); g = x.groupby("asset_id")
    p1, p2 = g["pretax_income_ttm"].shift(12), g["pretax_income_ttm"].shift(24)
    y1, y2 = g["ym"].shift(12), g["ym"].shift(24)
    value = x["pretax_income_ttm"] / p1.where(p1 > 0) - p1 / p2.where(p2 > 0)
    return value.where(x["ym"].eq(y1 + 12) & x["ym"].eq(y2 + 24)).reindex(frame.index)

FACTOR = Factor(name="pretax_income_growth_acceleration_12m", family="pretax_earnings_acceleration", category="earnings",
    hypothesis="세전이익 성장률이 가속한 기업은 세율 잡음 전 이익 개선이 늦게 반영되어 이후 상대수익이 높다.", predicted_sign=1,
    params={"lookback_months": 12, "comparison_months": 24}, rebalance_months=3, needs=("pretax_income_ttm",), compute=compute)
RESEARCH_SPEC = {
    "thesis": "최근 세전이익 성장의 가속도가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "세전 이익 가속은 본업과 금융손익 개선을 묶어 포착하며 일회성 세율 변동의 잡음을 줄인다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 pretax_income_growth_12m 직교성이 실패하면 기각한다.",
    "expected_relationship": "pretax_income_growth_12m과 관련되지만 성장률의 2차 차분이다.",
    "data_notes": "DART available_date PIT 세전이익과 정확한 12·24개월 전 양의 세전이익을 요구한다.",
}
