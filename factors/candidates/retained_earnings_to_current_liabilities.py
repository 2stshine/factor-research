"""Pre-registered retained-earnings coverage of current liabilities."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    debt = frame["current_liabilities"].where(frame["current_liabilities"] > 0)
    return frame["retained_earnings"] / debt


FACTOR = Factor(
    name="retained_earnings_to_current_liabilities", family="internal_capital_short_debt_coverage",
    category="quality", hypothesis="유동부채 대비 누적 이익잉여금이 큰 기업은 내부자본 완충력이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("retained_earnings", "current_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "이익잉여금/유동부채가 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "누적 내부이익이 단기 의무를 충분히 덮으면 외부 차환과 증자 의존도가 낮다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 내부자본 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: retained_earnings_to_liabilities — 차이: 전체 의무가 아니라 단기 상환부채의 내부자본 충당력을 측정한다.",
    "data_notes": "DART available_date PIT 이익잉여금과 양의 유동부채만 사용한다.",
}
