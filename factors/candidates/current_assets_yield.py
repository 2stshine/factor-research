"""Pre-registered current-assets-to-market value candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    return frame["current_assets"] / market_cap


FACTOR = Factor(
    name="current_assets_yield", family="liquid_asset_value", category="value",
    hypothesis="시장가치 대비 유동자산이 큰 기업은 회수 가능한 자산가치가 저평가되어 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3, needs=("current_assets",), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "유동자산/시가총액이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "현금·채권·재고 등 단기 회수자산이 가격에 비해 크면 청산·재배치 선택권이 저평가될 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 가치 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: net_working_capital_yield — 차이: 유동부채를 차감하지 않은 총 유동자산 가치만 측정한다.",
    "data_notes": "DART available_date PIT 유동자산과 동시점 양의 시가총액을 사용한다.",
}
