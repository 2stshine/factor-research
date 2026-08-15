"""Pre-registered twelve-month directional price efficiency."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["adj_close"].shift(WINDOW_MONTHS)
    prior_month = grouped["ym"].shift(WINDOW_MONTHS)
    monthly = ordered["adj_close"] / grouped["adj_close"].shift(1) - 1.0
    absolute_monthly = monthly.where(monthly.gt(0), -monthly)
    path = (
        absolute_monthly.groupby(ordered["asset_id"], sort=False)
        .rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).mean()
        .reset_index(level=0, drop=True)
    ) * WINDOW_MONTHS
    value = (ordered["adj_close"] / prior.where(prior > 0) - 1.0) / path.where(path > 0)
    exact = ordered["ym"].eq(prior_month + WINDOW_MONTHS)
    return value.where(exact).reindex(frame.index)


FACTOR = Factor(
    name="price_trend_efficiency_12m", family="directional_price_efficiency",
    category="momentum", hypothesis="같은 12개월 수익도 왕복 잡음이 적은 상승 추세는 더 지속된다.",
    predicted_sign=1, params={"window_months": WINDOW_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "12개월 누적 분할조정수익/월별 절대수익 경로가 큰 종목의 이후 순위가 높을 것이다.",
    "mechanism": "정보가 일관되게 반영된 추세는 단기 반전 잡음보다 지속 가능성이 높다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 모멘텀 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: mom_12_1 — 차이: 누적수익 수준이 아니라 이동 경로 대비 방향 효율을 측정한다.",
    "data_notes": "분할조정 adj_close와 정확한 12개월 달력 경로만 사용한다.",
}
