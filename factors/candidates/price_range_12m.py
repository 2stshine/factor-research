"""Pre-registered twelve-month split-adjusted price range."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    high = grouped["adj_close"].rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).max().reset_index(level=0, drop=True)
    low = grouped["adj_close"].rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).min().reset_index(level=0, drop=True)
    oldest_month = grouped["ym"].shift(WINDOW_MONTHS - 1)
    value = high / low.where(low > 0) - 1.0
    exact = ordered["ym"].eq(oldest_month + WINDOW_MONTHS - 1)
    return value.where(exact).reindex(frame.index)


FACTOR = Factor(
    name="price_range_12m", family="price_range_risk", category="other",
    hypothesis="12개월 가격 범위가 넓은 종목은 불확실성과 투기수요가 커 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"window_months": WINDOW_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "12개월 최고/최저 분할조정가격 비율이 큰 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "넓은 거래범위는 가치 불확실성과 상태의존적 투자자 수요를 반영한다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 저위험 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: realized_volatility_252d — 차이: 일별 분산이 아니라 연간 극값 범위를 측정한다.",
    "data_notes": "분할조정 adj_close의 정확한 12개 달력월만 사용한다.",
}
