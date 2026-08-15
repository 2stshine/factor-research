"""Pre-registered operating return on legal capital."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["capital_stock"].where(frame["capital_stock"] > 0)
    return frame["operating_income_ttm"] / base


FACTOR = Factor(
    name="operating_income_to_capital_stock", family="legal_capital_operating_return",
    category="quality", hypothesis="법정자본 대비 영업이익이 높은 기업은 납입자본 생산성이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("operating_income_ttm", "capital_stock"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "TTM 영업이익/자본금이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "작은 납입자본으로 높은 본업 이익을 만들면 증자 없는 자본효율이 높다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 수익성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: operating_income_to_equity — 차이: 전체 자기자본이 아니라 납입 법정자본의 본업 수익률을 측정한다.",
    "data_notes": "DART available_date PIT 영업이익과 양의 자본금만 사용한다.",
}
