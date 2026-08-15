"""Pre-registered internal-capital coverage of long liabilities."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["noncurrent_liabilities"].where(frame["noncurrent_liabilities"] > 0)
    return frame["retained_earnings"] / base


FACTOR = Factor(
    name="retained_earnings_to_noncurrent_liabilities",
    family="internal_capital_long_debt_coverage", category="quality",
    hypothesis="장기부채 대비 누적 내부이익이 높은 기업은 재조달 위험이 낮아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("retained_earnings", "noncurrent_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "PIT 이익잉여금/비유동부채가 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "누적 내부자본이 장기채무를 충분히 덮으면 외부조달 의존과 만기 재조달 위험이 낮다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 장기지급능력 계열 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: equity_to_noncurrent_liabilities — 차이: 전체 자기자본이 아니라 누적 내부이익만으로 장기채무 충당력을 측정한다.",
    "data_notes": "DART available_date PIT retained_earnings와 양의 noncurrent_liabilities만 사용한다.",
}
