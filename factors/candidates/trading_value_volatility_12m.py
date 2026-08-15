"""Pre-registered instability of market-scaled trading activity."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    scaled = ordered["trading_value"] / ordered["market_cap"].where(ordered["market_cap"] > 0)
    grouped = scaled.groupby(ordered["asset_id"], sort=False)
    value = grouped.rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).std().reset_index(level=0, drop=True)
    oldest_month = ordered.groupby("asset_id", sort=False)["ym"].shift(WINDOW_MONTHS - 1)
    return value.where(ordered["ym"].eq(oldest_month + WINDOW_MONTHS - 1)).reindex(frame.index)


FACTOR = Factor(
    name="trading_value_volatility_12m", family="trading_attention_instability",
    category="other", hypothesis="기업가치 대비 거래활동이 불안정한 종목은 투자자 관심이 일시적이어서 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"window_months": WINDOW_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "12개월 거래대금/시가총액 표준편차가 높은 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "간헐적 거래 급증은 안정적 유동성보다 투기적 관심과 가격충격 위험을 나타낸다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 거래활동 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: turnover_volatility_12m — 차이: 주식회전율 대신 기업가치 대비 거래대금 변동성을 측정한다.",
    "data_notes": "동시점 trading_value·양의 market_cap의 정확한 12개월 달력창을 사용한다.",
}
