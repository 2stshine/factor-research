"""Pre-registered revenue coverage of long-term liabilities."""
from __future__ import annotations
from engine.factors import Factor


def compute(frame):
    base = frame["noncurrent_liabilities"].where(frame["noncurrent_liabilities"] > 0)
    return frame["revenue_ttm"] / base


FACTOR = Factor(
    name="revenue_to_noncurrent_liabilities", family="long_term_revenue_coverage", category="quality",
    hypothesis="비유동부채 대비 매출이 높은 기업은 장기 채무를 지탱하는 사업 규모가 커 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("revenue_ttm", "noncurrent_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "Silver PIT revenue_ttm/noncurrent_liabilities가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "장기부채 한 단위가 뒷받침하는 매출 기반이 크면 수요 충격과 차환 부담을 흡수할 여지가 크다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 revenue_to_total_liabilities 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: revenue_to_total_liabilities — 차이: 총부채가 아니라 장기부채 만기구조만 측정한다.",
    "data_notes": "DART available_date PIT 매출과 양의 비유동부채만 사용한다.",
}
