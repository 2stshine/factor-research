"""Pre-registered legal-capital coverage of current liabilities."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    debt = frame["current_liabilities"].where(frame["current_liabilities"] > 0)
    return frame["capital_stock"] / debt


FACTOR = Factor(
    name="capital_stock_to_current_liabilities", family="legal_capital_short_debt_coverage",
    category="quality", hypothesis="유동부채 대비 납입 법정자본이 큰 기업은 단기 채무의 자본완충력이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("capital_stock", "current_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "자본금/유동부채가 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "회수 요구가 없는 납입자본이 단기부채보다 크면 지급위기 시 손실흡수 여력이 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자본구성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: capital_stock_to_liabilities — 차이: 전체부채가 아니라 단기부채에 대한 법정자본 완충력만 측정한다.",
    "data_notes": "DART available_date PIT 자본금과 양의 유동부채만 사용한다.",
}
