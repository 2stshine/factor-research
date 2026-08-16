"""Pre-registered current-asset pretax-income productivity candidate."""
from __future__ import annotations
from engine.factors import Factor


def compute(frame):
    base = frame["current_assets"].where(frame["current_assets"] > 0)
    return frame["pretax_income_ttm"] / base


FACTOR = Factor(
    name="pretax_income_to_current_assets", family="current_asset_pretax_productivity", category="quality",
    hypothesis="유동자산 대비 세전이익이 높은 기업은 단기자산 운용 효율이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("pretax_income_ttm", "current_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "Silver PIT pretax_income_ttm/current_assets가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "세율 잡음 전 이익을 유동자산과 비교하면 운전자본의 전체 수익창출력을 포착한다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 인접 수익성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "net_income_to_current_assets와 관련되지만 세금 전 성과를 사용한다.",
    "data_notes": "DART available_date PIT 세전이익과 양의 유동자산만 사용한다.",
}
