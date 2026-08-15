"""Pre-registered operating working-capital buffer relative to sales."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    sales = frame["revenue_ttm"].where(frame["revenue_ttm"] > 0)
    return (frame["current_assets"] - frame["current_liabilities"]) / sales


FACTOR = Factor(
    name="working_capital_to_sales", family="working_capital_sales_buffer", category="quality",
    hypothesis="매출 대비 순운전자본 완충력이 높은 기업은 단기 자금충격을 견뎌 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("current_assets", "current_liabilities", "revenue_ttm"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "(유동자산-유동부채)/TTM 매출이 높은 종목의 이후 순위가 높을 것이다.",
    "mechanism": "매출 규모 대비 운전자본 여유는 재고·채권과 단기부채 충격의 흡수력을 나타낸다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 유동성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: net_working_capital_to_assets — 차이: 자산 규모가 아니라 영업 매출로 완충력을 정규화한다.",
    "data_notes": "DART available_date PIT 유동자산·유동부채와 양의 TTM 매출만 사용한다.",
}
