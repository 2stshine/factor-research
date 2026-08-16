"""Pre-registered acceleration in asset-turnover improvement."""
from __future__ import annotations

from engine.factors import Factor

STEP_MONTHS = 12
LOOKBACK_MONTHS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    turnover = ordered["revenue_ttm"] / ordered["total_assets"].where(ordered["total_assets"] > 0)
    grouped = turnover.groupby(ordered["asset_id"], sort=False)
    prior = grouped.shift(STEP_MONTHS)
    oldest = grouped.shift(LOOKBACK_MONTHS)
    month_grouped = ordered.groupby("asset_id", sort=False)["ym"]
    prior_month = month_grouped.shift(STEP_MONTHS)
    oldest_month = month_grouped.shift(LOOKBACK_MONTHS)
    value = (turnover - prior) - (prior - oldest)
    exact = ordered["ym"].eq(prior_month + STEP_MONTHS) & ordered["ym"].eq(oldest_month + LOOKBACK_MONTHS)
    return value.where(exact).reindex(frame.index)


FACTOR = Factor(
    name="asset_turnover_acceleration_12m", family="asset_efficiency_acceleration",
    category="quality", hypothesis="자산회전 개선이 가속한 기업은 자산효율 전환이 늦게 반영되어 이후 상대수익이 높다.",
    predicted_sign=1, params={"step_months": STEP_MONTHS, "lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3, needs=("revenue_ttm", "total_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "최근 12개월 자산회전 변화에서 직전 12개월 변화를 뺀 값이 큰 종목의 이후 순위가 높을 것이다.",
    "mechanism": "매출이 자산보다 점점 빠르게 성장하면 유휴자산 축소와 운영 레버리지 개선이 진행 중일 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자산효율 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: asset_turnover_change_12m — 차이: 회전율 변화가 아니라 변화의 2차 차분을 측정한다.",
    "data_notes": "DART available_date PIT 매출·양의 총자산과 정확한 12·24개월 시차를 사용한다.",
}
