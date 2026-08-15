"""Pre-registered legal-capital yield."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    return frame["capital_stock"] / market_cap


FACTOR = Factor(
    name="capital_stock_yield", family="legal_capital_value", category="value",
    hypothesis="시장가치 대비 납입 법정자본이 큰 기업은 기초 자본가치가 저평가되어 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3, needs=("capital_stock",), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "자본금/시가총액이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "가격에 비해 납입된 법정자본이 크면 시장이 기초 자본기반을 낮게 평가했을 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 가치 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: capital_stock_to_assets — 차이: 자산구성이 아니라 시장가격 대비 법정자본 가치만 측정한다.",
    "data_notes": "DART available_date PIT 자본금과 동시점 양의 시가총액을 사용한다.",
}
