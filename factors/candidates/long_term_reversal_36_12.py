"""Pre-registered 36-to-12-month long-term reversal candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 36
SKIP_MONTHS = 12


def compute(frame):
    grouped = frame.groupby("asset_id")["adj_close"]
    old_price = grouped.shift(LOOKBACK_MONTHS)
    recent_boundary = grouped.shift(SKIP_MONTHS)
    past_return = recent_boundary / old_price - 1
    return past_return


FACTOR = Factor(
    name="long_term_reversal_36_12",
    family="long_term_reversal",
    category="momentum",
    hypothesis=(
        "36개월 전부터 12개월 전까지 장기간 크게 하락한 종목은 투자자의 과잉반응과 장기 기대 "
        "오류가 교정되며 이후 상대적으로 높은 수익을 내고, 장기 승자는 반대로 평균회귀한다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS, "skip_months": SKIP_MONTHS},
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT 분할조정 가격으로 측정한 36~12개월 전 누적 가격수익률이 낮은 종목은 높은 종목보다 "
        "이후 수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "장기간의 나쁜 뉴스와 실적 부진에 투자자가 과도하게 반응하면 비관적 기대가 가격에 "
        "과잉 반영될 수 있다. 최근 12개월은 단기 모멘텀과 겹치지 않도록 제외하고, 더 오래된 "
        "가격 충격이 정상화되는 평균회귀를 포착한다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "최근 12개월을 제외하므로 mom_12_1 및 high_12m_proximity와 낮은 관계를 예상한다. 오래된 "
        "가격 하락 종목은 가치주가 되었을 수 있어 value 계열과 약한 양의 관계를 예상하지만, "
        "회계 입력을 사용하지 않으므로 동일 신호는 아닐 것으로 예상한다."
    ),
    "data_notes": (
        "Silver PIT 분할조정 가격 adj_close만 사용한다. 36개월 이력이 없는 관측은 "
        "결측이며, 12개월 skip은 사전 고정한다. 상장폐지 종착수익률 처리는 공통 게이트가 세 "
        "시나리오로 적용한다."
    ),
}
