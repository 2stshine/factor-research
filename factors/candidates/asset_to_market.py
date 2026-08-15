"""Pre-registered total-assets-to-market value candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    return frame["total_assets"] / market_cap


FACTOR = Factor(
    name="asset_to_market", family="asset_backed_value", category="value",
    hypothesis="시장가치 대비 총자산이 큰 기업은 자산기반이 저평가되어 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3, needs=("total_assets",), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "총자산/시가총액이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "장부자본뿐 아니라 부채로 조달한 운영자산까지 가격 대비 싸게 거래되는 기업은 재평가 여지가 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 가치 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: value_bp — 차이: 순자산 대신 전체 운영자산의 시장가격 대비 크기를 측정한다.",
    "data_notes": "DART available_date PIT 총자산과 동시점 양의 시가총액을 사용한다.",
}
