"""Pre-registered book-capital-scaled trading activity."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    equity = frame["total_equity"].where(frame["total_equity"] > 0)
    return frame["adv20"] / equity


FACTOR = Factor(
    name="adv20_to_book_equity", family="book_scaled_trading_activity",
    category="other",
    hypothesis="장부 자기자본 대비 거래대금이 높은 종목은 과도한 관심이 가격에 반영돼 이후 상대수익이 낮다.",
    predicted_sign=-1, params={}, rebalance_months=1,
    needs=("total_equity",), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "20일 평균 거래대금/장부 자기자본이 높은 종목의 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "기업의 누적 위험자본에 비해 거래가 과도하면 관심과 의견불일치가 현재 가격에 먼저 반영될 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 거래활동 계열 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: trading_turnover_20d — 차이: 시가총액 대신 PIT 장부 자기자본으로 거래활동을 정규화한다.",
    "data_notes": "동시점 Silver adv20과 DART available_date PIT 양의 자기자본만 사용한다.",
}
