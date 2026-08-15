"""Pre-registered current-asset operating productivity."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["current_assets"].where(frame["current_assets"] > 0)
    return frame["operating_income_ttm"] / base


FACTOR = Factor(
    name="operating_income_to_current_assets", family="current_asset_operating_productivity",
    category="quality", hypothesis="유동자산 대비 영업이익이 높은 기업은 운전자본 생산성이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("operating_income_ttm", "current_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "TTM 영업이익/유동자산이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "단기 운영자산을 적게 묶고 본업 이익을 만드는 기업은 자본효율이 높다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 수익성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: current_asset_turnover — 차이: 매출 회전이 아니라 본업 이익 생산성을 측정한다.",
    "data_notes": "DART available_date PIT 영업이익과 양의 유동자산만 사용한다.",
}
