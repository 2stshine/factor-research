"""Pre-registered first-order monthly return persistence."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 12
LOOKBACK_MONTHS = 13


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    monthly = ordered["adj_close"] / grouped["adj_close"].shift(1) - 1.0
    lagged = monthly.groupby(ordered["asset_id"], sort=False).shift(1)
    products = monthly * lagged
    value = products.groupby(ordered["asset_id"], sort=False).rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).mean().reset_index(level=0, drop=True)
    oldest_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    return value.where(ordered["ym"].eq(oldest_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="return_persistence_12m", family="monthly_return_persistence", category="momentum",
    hypothesis="월별 수익의 연속성이 높은 종목은 정보가 점진적으로 반영되어 이후 상대수익이 높다.",
    predicted_sign=1, params={"window_months": WINDOW_MONTHS, "lookback_months": LOOKBACK_MONTHS},
    rebalance_months=1, needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "최근 12개 월수익과 직전 월수익 곱의 평균이 큰 종목의 이후 순위가 높을 것이다.",
    "mechanism": "연속된 같은 방향 움직임은 단일 누적수익보다 정보확산의 지속성을 직접 나타낸다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 모멘텀 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: positive_return_share_12m — 차이: 상승월 비중이 아니라 인접 월수익의 방향·크기 연속성을 측정한다.",
    "data_notes": "분할조정 adj_close의 정확한 13개월 달력 이력만 사용한다.",
}
