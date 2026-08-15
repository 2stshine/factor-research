"""Pre-registered revenue coverage of short-term liabilities."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    debt = frame["current_liabilities"].where(frame["current_liabilities"] > 0)
    return frame["revenue_ttm"] / debt


FACTOR = Factor(
    name="revenue_to_current_liabilities", family="short_term_revenue_coverage",
    category="quality", hypothesis="단기부채 대비 매출이 높은 기업은 영업규모로 상환의무를 지탱해 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("revenue_ttm", "current_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "TTM 매출/유동부채가 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "단기 의무 한 단위당 매출 기반이 크면 운전자본과 차환 충격을 흡수하기 쉽다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 매출생산성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: revenue_to_total_liabilities — 차이: 전체부채가 아니라 1년 내 상환의무만 분모로 사용한다.",
    "data_notes": "DART available_date PIT 매출과 양의 유동부채만 사용한다.",
}
