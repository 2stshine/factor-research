"""Pre-registered acceleration in operating margin improvement."""
from __future__ import annotations

from engine.factors import Factor

STEP_MONTHS = 12
LOOKBACK_MONTHS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    margin = ordered["operating_income_ttm"] / ordered["revenue_ttm"].where(ordered["revenue_ttm"] > 0)
    grouped = margin.groupby(ordered["asset_id"], sort=False)
    prior = grouped.shift(STEP_MONTHS)
    oldest = grouped.shift(LOOKBACK_MONTHS)
    month_grouped = ordered.groupby("asset_id", sort=False)["ym"]
    prior_month = month_grouped.shift(STEP_MONTHS)
    oldest_month = month_grouped.shift(LOOKBACK_MONTHS)
    value = (margin - prior) - (prior - oldest)
    exact = ordered["ym"].eq(prior_month + STEP_MONTHS) & ordered["ym"].eq(oldest_month + LOOKBACK_MONTHS)
    return value.where(exact).reindex(frame.index)


FACTOR = Factor(
    name="operating_margin_acceleration_12m", family="operating_margin_acceleration",
    category="earnings", hypothesis="영업마진 개선 속도가 빨라진 기업은 본업 체질 개선이 늦게 반영되어 이후 상대수익이 높다.",
    predicted_sign=1, params={"step_months": STEP_MONTHS, "lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3, needs=("operating_income_ttm", "revenue_ttm"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "최근 12개월 영업마진 변화에서 직전 12개월 변화를 뺀 값이 큰 종목의 이후 순위가 높을 것이다.",
    "mechanism": "마진 개선의 가속은 가격결정력·원가구조 변화가 아직 이익전망에 완전히 반영되지 않았음을 나타낸다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 마진 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: operating_margin_change_12m — 차이: 마진 개선 수준이 아니라 두 연간 구간의 개선속도 차이를 측정한다.",
    "data_notes": "DART available_date PIT 영업이익·양의 매출과 정확한 12·24개월 시차를 사용한다.",
}
