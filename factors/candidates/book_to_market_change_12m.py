"""Pre-registered twelve-month book-to-market change candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    current = ordered["total_equity"] / ordered["market_cap"].where(
        ordered["market_cap"] > 0
    )
    prior_equity = grouped["total_equity"].shift(LOOKBACK_MONTHS)
    prior_market_cap = grouped["market_cap"].shift(LOOKBACK_MONTHS)
    prior_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    prior = prior_equity / prior_market_cap.where(prior_market_cap > 0)
    return (current - prior).where(
        ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)
    ).reindex(frame.index)


FACTOR = Factor(
    name="book_to_market_change_12m",
    family="book_value_repricing",
    category="value",
    hypothesis=(
        "장부가치 대비 시장가치가 최근 12개월 동안 낮아진 기업은 과도한 가격 조정이 "
        "되돌려지며 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("total_equity",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "PIT 자기자본/시가총액 비율의 12개월 증가폭이 큰 종목은 다음 달 총수익률 "
        "순위가 높을 것이다."
    ),
    "mechanism": (
        "시장가격 하락 또는 장부가치 개선에 대한 과잉·지연 반응은 가치 괴리를 만들고 "
        "이후 재평가로 해소될 수 있다."
    ),
    "falsification": (
        "양의 방향, 투자 가능 IC, 강건성, BY, 기존 가치·반전 신호 직교성 또는 봉인 "
        "OOS가 실패하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: value_bp — 차이: 장부가치/시가총액의 절대 수준이 아니라 "
        "정확한 12개월 변화만 측정한다."
    ),
    "data_notes": (
        "DART available_date PIT 자기자본과 동월 Silver 시가총액을 사용한다. 현재·12개월 "
        "전 시가총액이 양수이고 정확한 달력 간격이 있을 때만 계산한다."
    ),
}
