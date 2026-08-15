"""Pre-registered short-term-liabilities-to-market burden."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    return frame["current_liabilities"] / market_cap


FACTOR = Factor(
    name="current_liabilities_yield", family="market_short_debt_burden", category="value",
    hypothesis="시장가치 대비 유동부채가 큰 기업은 단기 재무위험이 커 이후 상대수익이 낮다.",
    predicted_sign=-1, params={}, rebalance_months=3, needs=("current_liabilities",), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "유동부채/시가총액이 높은 종목의 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "주주가치에 비해 1년 내 의무가 크면 차환과 희석 위험이 커진다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 시장레버리지 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: market_leverage — 차이: 총부채 중 단기 상환의무만 시장가치와 비교한다.",
    "data_notes": "DART available_date PIT 유동부채와 동시점 양의 시가총액을 사용한다.",
}
