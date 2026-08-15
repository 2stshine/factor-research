"""Pre-registered nominal-capital intensity candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_assets"].where(frame["total_assets"] > 0)
    return frame["capital_stock"] / base

FACTOR = Factor(name="capital_stock_to_assets", family="nominal_capital_intensity", category="other",
    hypothesis="총자산 대비 자본금이 낮은 기업은 누적 자본효율이 높아 이후 상대수익이 높다.", predicted_sign=-1,
    params={}, rebalance_months=3, needs=("capital_stock", "total_assets"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT capital_stock/total_assets가 낮은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "명목 납입자본을 적게 사용하고 같은 자산기반을 유지하는 기업은 누적 내부성장과 자본효율이 높을 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자본구성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "paid_in_capital_ratio와 관련되지만 자기자본이 아닌 총자산 대비 명목자본을 측정한다.",
    "data_notes": "DART available_date PIT 자본금과 양의 총자산만 사용한다.",
}
