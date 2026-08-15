"""Pre-registered current-asset share candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_assets"].where(frame["total_assets"] > 0)
    return frame["current_assets"] / base

FACTOR = Factor(name="current_assets_to_assets", family="asset_liquidity_share", category="quality",
    hypothesis="총자산 중 유동자산 비중이 높은 기업은 재무 유연성이 커 이후 상대수익이 높다.", predicted_sign=1,
    params={}, rebalance_months=3, needs=("current_assets", "total_assets"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT current_assets/total_assets가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "회수 가능한 단기자산 비중이 높으면 충격 시 차입·증자·강제매각 의존도가 낮아진다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 current_ratio·asset rigidity 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "noncurrent_asset_share의 보완적 구성비지만 직접 유동자산을 측정한다.",
    "data_notes": "DART available_date PIT 유동자산과 양의 총자산만 사용한다.",
}
