"""Pre-registered three-month price-reversal candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 3


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior_price = grouped["adj_close"].shift(LOOKBACK_MONTHS)
    prior_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    trailing_return = ordered["adj_close"] / prior_price.where(prior_price > 0) - 1.0
    return trailing_return.where(
        ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)
    ).reindex(frame.index)


FACTOR = Factor(
    name="short_term_reversal_3m",
    family="short_term_reversal_3m",
    category="momentum",
    hypothesis=(
        "최근 3개월의 가격 과잉반응과 유동성 충격이 되돌려지면 단기 패자는 이후 "
        "상대수익이 높다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver 분할조정 가격의 최근 3개월 누적수익률이 낮은 종목은 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "일시적 주문 불균형과 투자자 과잉반응은 수개월 내 평균회귀할 수 있으며, "
        "최근 패자에 유동성 공급 보상을 제공한다."
    ),
    "falsification": (
        "사전등록한 음의 방향, 투자 가능 IC, 종착수익 스트레스, 강건성, BY, 기존 "
        "반전·저위험 신호 직교성 또는 봉인 OOS가 실패하면 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: rev_1m — 차이: 한 달 미시구조 반전이 아니라 정확한 "
        "3개월 누적 과잉반응의 되돌림을 측정한다."
    ),
    "data_notes": (
        "Silver PIT adj_close만 사용하고 정확히 3개월 전 양의 가격과 달력 간격이 있는 "
        "관측에서만 누적 가격수익을 계산한다."
    ),
}
