"""Pre-registered long-lived-asset equity burden candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_equity"].where(frame["total_equity"] > 0)
    return frame["noncurrent_assets"] / base

FACTOR = Factor(name="noncurrent_assets_to_equity", family="equity_asset_rigidity", category="other",
    hypothesis="자기자본 대비 비유동자산이 낮은 기업은 자본 경직성과 외부조달 위험이 낮아 이후 상대수익이 높다.", predicted_sign=-1,
    params={}, rebalance_months=3, needs=("noncurrent_assets", "total_equity"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT noncurrent_assets/total_equity가 낮은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "자기자본을 장기 회수자산에 과도하게 묶지 않은 기업은 운전자본과 충격 대응 여력이 크다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자산경직성·레버리지 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "noncurrent_asset_share와 관련되지만 자기자본이 부담하는 장기자산 규모를 측정한다.",
    "data_notes": "DART available_date PIT 비유동자산과 양의 자기자본만 사용한다.",
}
