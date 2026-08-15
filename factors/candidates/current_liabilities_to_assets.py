"""Pre-registered short-term liability burden candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    return frame["current_liabilities"] / assets


FACTOR = Factor(
    name="current_liabilities_to_assets",
    family="short_term_liability_burden",
    category="quality",
    hypothesis="총자산 대비 단기부채가 낮은 기업은 유동성 압력이 작아 이후 상대수익이 높다.",
    predicted_sign=-1,
    params={},
    rebalance_months=3,
    needs=("current_liabilities", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT current_liabilities/total_assets가 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "단기 만기 부채가 적으면 불리한 시점의 차환·자산매각 위험이 줄어 하방 위험이 낮아진다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: current_liability_concentration — 차이: 부채 내 만기구조가 아니라 총자산 대비 단기청구권 규모다.",
    "data_notes": "DART available_date PIT 유동부채와 양의 총자산을 사용한다.",
}
