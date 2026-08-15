"""Pre-registered long-term liability burden candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    return frame["noncurrent_liabilities"] / assets


FACTOR = Factor(
    name="noncurrent_liabilities_to_assets",
    family="long_term_liability_burden",
    category="quality",
    hypothesis="총자산 대비 장기부채가 낮은 기업은 재무 유연성이 높아 이후 상대수익이 높다.",
    predicted_sign=-1,
    params={},
    rebalance_months=3,
    needs=("noncurrent_liabilities", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT noncurrent_liabilities/total_assets가 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "장기 고정 청구권이 적으면 경기 충격과 금리 상승에 대응할 자본배분 유연성이 커진다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: qual_lev — 차이: 총부채/자본이 아니라 장기부채/총자산만 측정한다.",
    "data_notes": "DART available_date PIT 비유동부채와 양의 총자산을 사용한다.",
}
