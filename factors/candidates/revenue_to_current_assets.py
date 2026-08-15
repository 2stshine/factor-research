"""Pre-registered revenue productivity of current assets."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["current_assets"].where(frame["current_assets"] > 0)
    return frame["revenue_ttm"] / base


FACTOR = Factor(
    name="revenue_to_current_assets", family="working_asset_revenue_productivity",
    category="quality",
    hypothesis="유동자산 대비 매출이 높은 기업은 운전자본 효율이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("revenue_ttm", "current_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "PIT 매출/유동자산이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "같은 재고·매출채권·현금 기반에서 더 많은 매출을 내는 기업은 운전자본 회전이 효율적이다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자산회전 계열 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: asset_turnover — 차이: 총자산이 아니라 단기 영업자산의 매출 생산성만 측정한다.",
    "data_notes": "DART available_date PIT revenue_ttm과 양의 current_assets만 사용한다.",
}
