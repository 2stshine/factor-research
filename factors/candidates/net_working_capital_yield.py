"""Pre-registered net-working-capital valuation candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    net_working_capital = frame["current_assets"] - frame["current_liabilities"]
    return net_working_capital / frame["market_cap"].where(frame["market_cap"] > 0)


FACTOR = Factor(
    name="net_working_capital_yield",
    family="liquid_asset_value",
    category="value",
    hypothesis=(
        "순운전자본이 시장가치에 비해 큰 기업은 유동자산 완충력과 청산가치가 "
        "과소평가되어 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("current_assets", "current_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "PIT 유동자산에서 유동부채를 뺀 순운전자본/시가총액 비율이 높은 종목은 "
        "다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "단기 의무를 차감한 유동자산 완충력은 하방 위험을 제한하며, 시장이 이를 낮게 "
        "평가한 기업에는 가치 재평가 여지가 있다."
    ),
    "falsification": (
        "양의 방향, 입력·표본 무결성, 투자 가능 IC, 강건성, BY, 기존 가치 신호 "
        "직교성 또는 봉인 OOS가 실패하면 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: net_working_capital_to_assets — 차이: 자산 내 운전자본 "
        "구성이 아니라 시장가치 대비 유동 청산가치의 가격 괴리를 측정한다."
    ),
    "data_notes": (
        "DART available_date PIT 유동자산·유동부채와 동월 Silver 시가총액을 사용하며 "
        "시가총액이 양수일 때만 계산한다."
    ),
}
