"""Pre-registered annual change in average trading value."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["adv20"].shift(LOOKBACK_MONTHS)
    prior_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    value = ordered["adv20"] / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="adv20_change_12m", family="trading_liquidity_growth", category="other",
    hypothesis="평균 거래대금이 빠르게 증가한 종목은 유동성 프리미엄이 축소돼 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"lookback_months": LOOKBACK_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "20일 평균 거래대금의 12개월 증가율이 높은 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "지속적인 거래 접근성 개선은 투자자의 요구 비유동성 보상을 낮춘다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 거래유동성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: trading_turnover_20d — 차이: 현재 회전 수준이 아니라 절대 거래유동성의 12개월 성장률을 측정한다.",
    "data_notes": "동시점 adv20과 정확한 12개월 전 양의 값만 사용한다.",
}
