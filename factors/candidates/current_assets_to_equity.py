"""Pre-registered current-assets-to-equity candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_equity"].where(frame["total_equity"] > 0)
    return frame["current_assets"] / base

FACTOR = Factor(name="current_assets_to_equity", family="equity_liquidity_capacity", category="quality",
    hypothesis="자기자본 대비 유동자산이 높은 기업은 주주자본의 유동성 완충력이 커 이후 상대수익이 높다.", predicted_sign=1,
    params={}, rebalance_months=3, needs=("current_assets", "total_equity"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT current_assets/total_equity가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "자기자본에 비해 회수 가능한 단기자산이 많으면 영업충격 때 외부조달 필요성이 낮다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 유동성·레버리지 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "current_assets_to_assets와 관련되지만 자기자본 대비 유동성 용량을 측정한다.",
    "data_notes": "DART available_date PIT 유동자산과 양의 자기자본만 사용한다.",
}
