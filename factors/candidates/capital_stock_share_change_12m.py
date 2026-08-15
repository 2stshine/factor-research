"""Pre-registered annual change in legal capital share of equity."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    share = ordered["capital_stock"] / ordered["total_equity"].where(ordered["total_equity"] > 0)
    prior = share.groupby(ordered["asset_id"], sort=False).shift(LOOKBACK_MONTHS)
    prior_month = ordered.groupby("asset_id", sort=False)["ym"].shift(LOOKBACK_MONTHS)
    return (share - prior).where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="capital_stock_share_change_12m", family="contributed_capital_share_change",
    category="other", hypothesis="자기자본 중 자본금 비중이 증가한 기업은 외부자본 의존과 희석위험으로 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"lookback_months": LOOKBACK_MONTHS}, rebalance_months=3,
    needs=("capital_stock", "total_equity"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "자본금/자기자본 비중의 12개월 증가가 큰 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "누적이익보다 납입자본 비중이 빠르게 커지면 외부조달과 주식희석 가능성을 나타낸다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자본조달 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: paid_in_capital_ratio — 차이: 자본구성 수준이 아니라 12개월 외부자본 비중 변화를 측정한다.",
    "data_notes": "DART available_date PIT 자본금·양의 자기자본과 정확한 12개월 시차를 사용한다.",
}
