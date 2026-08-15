"""Pre-registered short-term funding burden relative to sales."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    sales = frame["revenue_ttm"].where(frame["revenue_ttm"] > 0)
    return frame["current_liabilities"] / sales


FACTOR = Factor(
    name="current_liabilities_to_sales", family="short_term_funding_sales_burden",
    category="quality", hypothesis="매출 대비 유동부채가 큰 기업은 단기 자금압박으로 이후 상대수익이 낮다.",
    predicted_sign=-1, params={}, rebalance_months=3,
    needs=("current_liabilities", "revenue_ttm"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "유동부채/TTM 매출이 높은 종목의 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "영업 규모에 비해 단기 상환의무가 크면 차환과 운전자본 충격에 취약하다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 부채 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: current_liabilities_to_assets — 차이: 자산이 아니라 영업흐름 규모 대비 단기부채 부담을 측정한다.",
    "data_notes": "DART available_date PIT 유동부채와 양의 TTM 매출만 사용한다.",
}
