"""Pre-registered ratio of cumulative monthly gains to losses."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    monthly = ordered["adj_close"] / grouped["adj_close"].shift(1) - 1.0
    gains = monthly.clip(lower=0).groupby(ordered["asset_id"], sort=False).rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).mean().reset_index(level=0, drop=True)
    losses = (-monthly.clip(upper=0)).groupby(ordered["asset_id"], sort=False).rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).mean().reset_index(level=0, drop=True)
    oldest_month = grouped["ym"].shift(WINDOW_MONTHS)
    value = gains / losses.where(losses > 0)
    return value.where(ordered["ym"].eq(oldest_month + WINDOW_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="return_gain_loss_ratio_12m", family="return_magnitude_asymmetry", category="momentum",
    hypothesis="월별 상승폭이 하락폭보다 큰 종목은 우호적 정보의 지속성이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={"window_months": WINDOW_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "12개월 월별 양의 수익 합/음의 수익 절대합이 높은 종목의 이후 순위가 높을 것이다.",
    "mechanism": "상승월의 크기가 하락월 손실을 지속적으로 압도하면 단순 상승 빈도보다 강한 정보 우위를 나타낸다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 수익일관성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: positive_return_share_12m — 차이: 상승월 개수가 아니라 상승·하락 월수익의 누적 크기 비율을 측정한다.",
    "data_notes": "분할조정 adj_close의 정확한 12개월 월수익만 사용한다.",
}
