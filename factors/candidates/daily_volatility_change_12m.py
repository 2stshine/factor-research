"""Pre-registered annual change in daily realized volatility."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["daily_volatility_252d"].shift(LOOKBACK_MONTHS)
    prior_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    value = ordered["daily_volatility_252d"] / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="daily_volatility_change_12m", family="risk_deterioration", category="other",
    hypothesis="실현 변동성이 빠르게 상승한 종목은 위험상태가 악화되어 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"lookback_months": LOOKBACK_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "252일 일별 변동성의 12개월 증가율이 높은 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "위험의 급증은 사업·정보환경 변화와 강제 포지션 축소를 나타낼 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 저변동성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: realized_volatility_252d — 차이: 현재 위험수준이 아니라 12개월 위험 악화율을 측정한다.",
    "data_notes": "인증된 daily_volatility_252d와 정확한 12개월 전 양의 값만 사용한다.",
}
