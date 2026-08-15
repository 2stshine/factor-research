"""Pre-registered equity coverage of long-term liabilities."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    debt = frame["noncurrent_liabilities"].where(frame["noncurrent_liabilities"] > 0)
    return frame["total_equity"] / debt


FACTOR = Factor(
    name="equity_to_noncurrent_liabilities", family="long_term_equity_solvency",
    category="quality", hypothesis="장기부채 대비 자기자본이 큰 기업은 장기 지급능력이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("total_equity", "noncurrent_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "자기자본/비유동부채가 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "장기 채무를 흡수할 손실완충 자본이 크면 차환과 금리 충격에 견고하다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 레버리지 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: noncurrent_liabilities_to_equity — 차이: 부채 부담이 아니라 장기부채를 덮는 양의 자본 완충력으로 해석한다.",
    "data_notes": "DART available_date PIT 자기자본과 양의 비유동부채만 사용한다.",
}
