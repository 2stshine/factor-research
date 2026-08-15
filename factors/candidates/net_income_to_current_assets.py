"""Pre-registered current-asset net-income productivity candidate."""
from __future__ import annotations
from engine.factors import Factor


def compute(frame):
    base = frame["current_assets"].where(frame["current_assets"] > 0)
    return frame["net_income_ttm"] / base


FACTOR = Factor(
    name="net_income_to_current_assets", family="current_asset_net_productivity", category="quality",
    hypothesis="유동자산 대비 순이익이 높은 기업은 운전자본을 최종 이익으로 전환하는 효율이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("net_income_ttm", "current_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "Silver PIT net_income_ttm/current_assets가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "현금·재고·채권 등 단기자산을 적게 묶고 최종 이익을 만드는 기업은 자본효율이 높다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 ROA·마진 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: net_roa — 차이: 총자산이 아니라 유동자산 생산성만 측정한다.",
    "data_notes": "DART available_date PIT 순이익과 양의 유동자산만 사용한다.",
}
