"""Pre-registered net-income return on legal capital."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["capital_stock"].where(frame["capital_stock"] > 0)
    return frame["net_income_ttm"] / base


FACTOR = Factor(
    name="net_income_to_capital_stock", family="legal_capital_net_return",
    category="quality",
    hypothesis="법정 납입자본 대비 순이익이 높은 기업은 주주자본 활용 효율이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("net_income_ttm", "capital_stock"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "PIT 순이익/자본금이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "같은 법정 납입자본에서 더 많은 최종이익을 만드는 기업은 주주자본의 경제적 생산성이 높다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 수익성 계열 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: operating_income_to_capital_stock — 차이: 영업이익 대신 금융손익과 세금을 반영한 순이익을 사용한다.",
    "data_notes": "DART available_date PIT net_income_ttm과 양의 capital_stock만 사용한다.",
}
