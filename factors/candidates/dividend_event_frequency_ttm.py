"""Pre-registered trailing dividend-event frequency candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    return frame["dividend_event_count_ttm"].where(
        frame["dividend_event_count_ttm"] >= 0
    )


FACTOR = Factor(
    name="dividend_event_frequency_ttm",
    family="payout_frequency",
    category="quality",
    hypothesis=(
        "최근 12개월 동안 실제 현금배당을 더 자주 실시한 기업은 현금흐름 규율과 주주환원의 "
        "지속성이 높아 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("dividend_event_count_ttm",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "신호시점에 알려진 최근 12개월 canonical 현금배당 사건 수가 많은 종목은 적은 종목보다 "
        "다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "반복적인 현금배당은 배당액의 크기와 별개로 경영진의 현금흐름 규율과 주주환원 지속성을 "
        "보여준다. 이 질적 차이가 가격에 천천히 반영되면 배당 실시 빈도가 미래수익을 예측할 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, 다중검정, Gold SQL parity 또는 일회성 OOS 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "dividend_yield_ttm과 양의 관계를 예상하지만 현금배당의 금액이나 가격을 사용하지 않고 "
        "실시 횟수만 측정한다. 관계가 너무 높아 사실상 같은 신호라면 새 정보로 인정하지 않는다."
    ),
    "data_notes": (
        "현재 CERTIFIED total-return run에 결합된 canonical DART ISSUER 현금배당 사건만 센다. "
        "canonical latest terminal announcement_date 다음 날과 applied_trade_date 중 늦은 날부터 "
        "보이게 한 PIT 사건을 "
        "신호월 말 기준 최근 12개월로 집계하며, 사건이 없는 인증기간 월은 0이다."
    ),
}
