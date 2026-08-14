"""Trailing cash-dividend yield from certified canonical dividend events."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    price = frame["adj_close"].where(frame["adj_close"] > 0)
    cash_dividend = frame["dividend_cash_ttm"].where(
        frame["dividend_cash_ttm"] >= 0
    )
    return cash_dividend / price


FACTOR = Factor(
    name="dividend_yield_ttm",
    family="dividend_yield",
    category="value",
    hypothesis=(
        "현재 가격 대비 최근 12개월 현금배당이 큰 기업은 주주환원과 현금창출력이 가격에 "
        "충분히 반영되지 않아 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("dividend_cash_ttm",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "신호시점에 알려져 있고 실제 가격에 적용된 최근 12개월 주당 현금배당 합계를 월말 "
        "분할조정 가격으로 나눈 값이 높은 종목은 낮은 종목보다 이후 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "지속적인 현금배당은 주주환원과 현금창출의 관측 가능한 신호이며, 배당 대비 가격이 "
        "낮은 기업에는 가치·환원 프리미엄이 남을 수 있다."
    ),
    "falsification": (
        "배당 피드 커버리지·무결성, 전체·투자가능 IC, Rank ICIR, 기간 강건성, 기존 가치 "
        "신호와의 중복 및 정식 confirmation 기준을 통과하지 못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "value_bp·value_ep와 양의 관계를 예상하지만 공시 장부가나 이익이 아니라 실제 현금 "
        "주주환원을 사용하므로 완전한 중복은 아닐 것으로 예상한다."
    ),
    "data_notes": (
        "현재 CERTIFIED total-return run에 결합된 canonical DART ISSUER 현금배당만 사용한다. "
        "canonical latest terminal announcement_date 다음 날과 applied_trade_date 중 늦은 날부터 "
        "보이게 해 PIT를 지키며, "
        "adjusted_cash_amount와 adj_close를 같은 분할조정 기준으로 나눈다. 세전 gross 배당이고 "
        "적용 가능한 사건이 없는 인증기간 월은 0이다."
    ),
}
