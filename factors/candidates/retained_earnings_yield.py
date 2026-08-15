"""Pre-registered retained-earnings yield."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    return frame["retained_earnings"] / market_cap


FACTOR = Factor(
    name="retained_earnings_yield", family="accumulated_earnings_value", category="value",
    hypothesis="시장가치 대비 누적 이익잉여금이 큰 기업은 내부 축적가치가 저평가되어 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3, needs=("retained_earnings",), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "이익잉여금/시가총액이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "과거 이익의 누적 내부자본이 가격에 비해 크면 외부조달 없이 투자할 선택권이 크다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 가치 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: value_bp — 차이: 전체 장부자본 중 누적 이익으로 조성된 부분만 가격과 비교한다.",
    "data_notes": "DART available_date PIT 이익잉여금과 동시점 양의 시가총액을 사용한다.",
}
