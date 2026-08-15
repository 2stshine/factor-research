"""Pre-registered legal-capital intensity of current assets."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["current_assets"].where(frame["current_assets"] > 0)
    return frame["capital_stock"] / base


FACTOR = Factor(
    name="capital_stock_to_current_assets", family="legal_capital_current_asset_intensity",
    category="other", hypothesis="유동자산 대비 법정자본 비중이 큰 기업은 단기자산 운영의 자본 경직성이 커 이후 상대수익이 낮다.",
    predicted_sign=-1, params={}, rebalance_months=3,
    needs=("capital_stock", "current_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "자본금/유동자산이 높은 종목의 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "단기 운영자산에 비해 고정된 법정자본이 크면 자본 재배치 효율이 낮을 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자본구성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: capital_stock_to_assets — 차이: 전체 자산이 아니라 유동자산에 묶인 법정자본 강도를 측정한다.",
    "data_notes": "DART available_date PIT 자본금과 양의 유동자산만 사용한다.",
}
