"""Pre-registered nominal-capital liability coverage candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_liabilities"].where(frame["total_liabilities"] > 0)
    return frame["capital_stock"] / base

FACTOR = Factor(name="capital_stock_to_liabilities", family="nominal_capital_debt_coverage", category="quality",
    hypothesis="총부채 대비 자본금이 높은 기업은 납입자본 완충력이 커 이후 상대수익이 높다.", predicted_sign=1,
    params={}, rebalance_months=3, needs=("capital_stock", "total_liabilities"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT capital_stock/total_liabilities가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "채무 한 단위당 명목 납입자본이 많으면 외부 충격을 흡수하는 장부 완충력이 클 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 레버리지 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "solvency 신호와 관련되지만 누적이익을 제외한 자본금만 사용한다.",
    "data_notes": "DART available_date PIT 자본금과 양의 총부채만 사용한다.",
}
