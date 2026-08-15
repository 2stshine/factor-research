"""Pre-registered equity revenue productivity candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_equity"].where(frame["total_equity"] > 0)
    return frame["revenue_ttm"] / base

FACTOR = Factor(name="revenue_to_equity", family="equity_revenue_productivity", category="quality",
    hypothesis="자기자본 대비 매출이 높은 기업은 주주자본의 사업 활용도가 높아 이후 상대수익이 높다.", predicted_sign=1,
    params={}, rebalance_months=3, needs=("revenue_ttm", "total_equity"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT revenue_ttm/total_equity가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "주주가 제공한 장부자본 한 단위가 만드는 사업규모가 크면 자본효율과 운영 레버리지가 높을 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자산회전·가치 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "asset turnover와 관련되지만 주주자본의 매출 생산성을 측정한다.",
    "data_notes": "DART available_date PIT 매출과 양의 자기자본만 사용한다.",
}
