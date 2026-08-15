"""Pre-registered annual change in Amihud illiquidity."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["amihud_illiquidity_1m"].shift(LOOKBACK_MONTHS)
    prior_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    value = ordered["amihud_illiquidity_1m"] / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="amihud_change_12m", family="liquidity_deterioration", category="other",
    hypothesis="가격충격 비유동성이 빠르게 악화된 종목은 거래기반 위축으로 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"lookback_months": LOOKBACK_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "Amihud 비유동성의 12개월 증가율이 높은 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "유동성의 급격한 악화는 투자자 이탈과 정보비대칭 확대를 나타낼 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 유동성 수준 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: amihud_illiquidity_1m — 차이: 현재 수준이 아니라 12개월 악화 속도를 측정한다.",
    "data_notes": "인증된 월별 Amihud 값과 정확한 12개월 전 양의 값만 사용한다.",
}
