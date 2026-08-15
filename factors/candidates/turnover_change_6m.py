"""Pre-registered six-month change in market-scaled turnover."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 6


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    scaled = ordered["adv20"] / ordered["market_cap"].where(ordered["market_cap"] > 0)
    grouped = scaled.groupby(ordered["asset_id"], sort=False)
    prior = grouped.shift(LOOKBACK_MONTHS)
    prior_month = ordered.groupby("asset_id", sort=False)["ym"].shift(LOOKBACK_MONTHS)
    value = scaled / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="turnover_change_6m", family="trading_attention_change", category="other",
    hypothesis="시가총액 대비 거래활동이 급증한 종목은 투자자 과잉관심으로 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"lookback_months": LOOKBACK_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "시가총액 대비 20일 평균 거래대금의 6개월 증가율이 높은 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "단기간 거래관심 급증은 일시적 주목과 과잉수요를 반영할 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 거래활동 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: adv20_to_market_cap — 차이: 유동성 수준이 아니라 6개월 투자자 관심 변화만 측정한다.",
    "data_notes": "동시점 adv20·양의 market_cap과 정확한 6개월 시차를 사용한다.",
}
