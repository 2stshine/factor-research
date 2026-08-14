"""Pre-registered 12-month net equity issuance proxy; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    market_cap = ordered["market_cap"].where(ordered["market_cap"] > 0)
    split_adjusted_price = ordered["adj_close"].where(ordered["adj_close"] > 0)
    market_cap_growth = market_cap / market_cap.groupby(asset).shift(LOOKBACK_MONTHS)
    price_growth = split_adjusted_price / split_adjusted_price.groupby(asset).shift(LOOKBACK_MONTHS)
    issuance = market_cap_growth / price_growth - 1
    return issuance.reindex(frame.index)


FACTOR = Factor(
    name="net_equity_issuance_12m",
    family="net_equity_issuance",
    category="other",
    hypothesis=(
        "최근 12개월 순주식 발행이 큰 기업은 고평가된 자기자본을 이용하거나 자금수요가 크다는 "
        "신호이고, 순환매·순배당 기업보다 이후 상대적으로 낮은 수익을 낸다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT에서 12개월 시가총액 성장률을 같은 기간 분할조정 가격 성장률로 나눈 순주식 발행 "
        "대용치가 낮은 종목은 높은 종목보다 이후 수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "경영자는 주가가 내재가치보다 높다고 판단하거나 외부자금 수요가 클 때 주식을 발행할 "
        "유인이 있다. 반대로 환매와 배당은 자본을 주주에게 반환한다. 투자자가 이러한 자금조달 "
        "선택의 정보를 늦게 반영하면 순발행이 낮은 기업이 이후 상대적으로 재평가될 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "주가 변화를 제거한 기업재무 신호이므로 mom_12_1과 낮은 관계를 예상한다. 주식 발행을 "
        "통해 자산을 확장한 기업에서는 asset_growth_12m과 양의 관계가 있을 수 있으나, 환매와 "
        "배당도 반영하므로 완전한 중복은 아닐 것으로 예상한다."
    ),
    "data_notes": (
        "Silver PIT market_cap과 분할조정 가격 adj_close를 사용한다. 12개월 이력이 "
        "없거나 값이 0 이하인 관측은 결측이다. 이 비율은 주식 수 변화를 직접 쓰지 않아 액면분할 "
        "영향을 줄이지만, 합병·분할·대규모 배당을 완벽히 분리하는 정밀 발행량 자료는 아니다."
    ),
}
