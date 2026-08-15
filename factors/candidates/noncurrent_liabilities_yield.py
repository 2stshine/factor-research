"""Pre-registered long-term-liabilities-to-market burden."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    return frame["noncurrent_liabilities"] / market_cap


FACTOR = Factor(
    name="noncurrent_liabilities_yield", family="market_long_debt_burden", category="value",
    hypothesis="시장가치 대비 장기부채가 큰 기업은 구조적 재무위험이 커 이후 상대수익이 낮다.",
    predicted_sign=-1, params={}, rebalance_months=3, needs=("noncurrent_liabilities",), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "비유동부채/시가총액이 높은 종목의 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "주주가치에 비해 장기 채무가 크면 금리상승과 장기 차환 부담이 지속된다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 시장레버리지 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: market_leverage — 차이: 총부채 중 장기 만기 의무만 시장가치와 비교한다.",
    "data_notes": "DART available_date PIT 비유동부채와 동시점 양의 시가총액을 사용한다.",
}
