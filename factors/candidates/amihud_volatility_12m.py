"""Pre-registered instability of monthly Amihud illiquidity."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    value = grouped["amihud_illiquidity_1m"].rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).std().reset_index(level=0, drop=True)
    oldest_month = grouped["ym"].shift(WINDOW_MONTHS - 1)
    return value.where(ordered["ym"].eq(oldest_month + WINDOW_MONTHS - 1)).reindex(frame.index)


FACTOR = Factor(
    name="amihud_volatility_12m", family="liquidity_instability", category="other",
    hypothesis="월별 가격충격 유동성이 불안정한 종목은 거래환경 위험이 커 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"window_months": WINDOW_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "12개월 Amihud 비유동성 표준편차가 높은 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "거래비용의 불안정성은 평시 유동성 수준보다 자금회수 불확실성을 크게 만든다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 유동성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: amihud_illiquidity_1m — 차이: 수준이 아니라 12개월 유동성 환경의 불안정성을 측정한다.",
    "data_notes": "인증된 월별 Amihud 값의 정확한 12개월 달력창을 사용한다.",
}
