"""Pre-registered revenue productivity of legal capital."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["capital_stock"].where(frame["capital_stock"] > 0)
    return frame["revenue_ttm"] / base


FACTOR = Factor(
    name="revenue_to_capital_stock", family="legal_capital_revenue_productivity",
    category="quality", hypothesis="납입 자본금 대비 매출이 높은 기업은 법정자본 활용도가 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("revenue_ttm", "capital_stock"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "TTM 매출/자본금이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "작은 납입자본 기반으로 큰 영업규모를 유지하면 자본 확장 없이 성장할 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 생산성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: asset_turnover — 차이: 전체 자산 대신 납입 법정자본의 매출 생산성을 측정한다.",
    "data_notes": "DART available_date PIT 매출과 양의 자본금만 사용한다.",
}
