"""Pre-registered long-lived-asset revenue productivity candidate."""
from __future__ import annotations
from engine.factors import Factor


def compute(frame):
    base = frame["noncurrent_assets"].where(frame["noncurrent_assets"] > 0)
    return frame["revenue_ttm"] / base


FACTOR = Factor(
    name="revenue_to_noncurrent_assets", family="long_lived_asset_revenue_productivity", category="quality",
    hypothesis="비유동자산 대비 매출이 높은 기업은 장기자본의 영업 활용도가 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("revenue_ttm", "noncurrent_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "Silver PIT revenue_ttm/noncurrent_assets가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "회수기간이 긴 자산 한 단위가 만드는 매출이 많으면 고정비와 자본집약 위험을 흡수할 여력이 크다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자산회전·수익성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "operating_income_to_noncurrent_assets와 관련되지만 이익률을 섞지 않은 매출 생산성이다.",
    "data_notes": "DART available_date PIT 매출과 양의 비유동자산만 사용한다.",
}
