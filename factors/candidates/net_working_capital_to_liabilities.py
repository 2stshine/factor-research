"""Pre-registered net-working-capital liability coverage candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_liabilities"].where(frame["total_liabilities"] > 0)
    return (frame["current_assets"] - frame["current_liabilities"]) / base

FACTOR = Factor(name="net_working_capital_to_liabilities", family="working_capital_debt_coverage", category="quality",
    hypothesis="총부채 대비 순운전자본이 높은 기업은 단기 유동성 완충력이 커 이후 상대수익이 높다.", predicted_sign=1,
    params={}, rebalance_months=3, needs=("current_assets", "current_liabilities", "total_liabilities"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT (current_assets-current_liabilities)/total_liabilities가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "유동자산에서 단기 의무를 뺀 잔여 완충력이 전체 채무 대비 크면 차환 충격의 하방이 줄어든다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 current_ratio·solvency 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "net_working_capital_to_assets와 관련되지만 채무 상환범위에 초점을 둔다.",
    "data_notes": "DART available_date PIT 유동자산·유동부채·양의 총부채만 사용한다.",
}
