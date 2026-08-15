"""Pre-registered long-lived-assets-to-market value candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    return frame["noncurrent_assets"] / market_cap


FACTOR = Factor(
    name="noncurrent_assets_yield", family="long_lived_asset_value", category="value",
    hypothesis="시장가치 대비 비유동자산이 큰 기업은 장기 생산기반이 저평가되어 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3, needs=("noncurrent_assets",), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "비유동자산/시가총액이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "설비·장기투자 등 생산기반이 가격에 비해 크면 대체원가와 수익잠재력이 저평가될 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 가치 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: asset_to_market — 차이: 총자산 중 장기 생산자산 가치만 가격과 비교한다.",
    "data_notes": "DART available_date PIT 비유동자산과 동시점 양의 시가총액을 사용한다.",
}
