"""Pre-registered trading-activity instability candidate; immutable after evaluation."""
from __future__ import annotations

import numpy as np

from engine.factors import Factor


WINDOW_MONTHS = 12
MIN_OBSERVATIONS = 9


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    adv = ordered["adv20"].where(ordered["adv20"] > 0)
    market_cap = ordered["market_cap"].where(ordered["market_cap"] > 0)
    log_turnover = np.log(adv / market_cap)
    volatility = log_turnover.groupby(asset).transform(
        lambda values: values.rolling(
            WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
        ).std()
    )
    first_ym = ordered["ym"].groupby(asset).shift(WINDOW_MONTHS - 1)
    consecutive = ordered["ym"].eq(first_ym + WINDOW_MONTHS - 1)
    return volatility.where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="turnover_volatility_12m",
    family="trading_activity_instability",
    category="other",
    hypothesis=(
        "시가총액 대비 거래활동이 최근 12개월 동안 불안정한 종목은 관심 충격과 투자자 의견 "
        "불일치가 커 과대평가되기 쉬우며 이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    params={
        "window_months": WINDOW_MONTHS,
        "min_observations": MIN_OBSERVATIONS,
    },
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 log(ADV20/market_cap) 12개월 변동성이 낮은 종목은 높은 종목보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "거래활동의 급격한 증감은 일시적 관심, 투기 수요와 의견 불일치를 반영할 수 있다. 이런 "
        "수요 충격이 가격을 펀더멘털보다 높인 뒤 정상화되면 활동이 안정적인 종목의 기대수익이 "
        "상대적으로 높을 수 있다."
    ),
    "falsification": (
        "사전등록한 음의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "trading_turnover_20d의 거래활동 수준 및 변동성 계열과 일부 관계는 가능하지만, 이 후보는 "
        "수준이 아니라 12개월 동안의 log turnover 불안정성만 측정한다."
    ),
    "data_notes": (
        "Silver의 양의 ADV20과 market_cap만 사용한다. 12개월 창에서 최소 9개 관측과 정확한 달력 "
        "연속성을 요구한다. 체결가격 충격이나 Amihud 비율을 사용하지 않으며 최초 11개월은 결측이다."
    ),
}
