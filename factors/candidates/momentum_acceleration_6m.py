"""Pre-registered acceleration of adjacent three-month price trends."""
from __future__ import annotations

from engine.factors import Factor

SEGMENT_MONTHS = 3
LOOKBACK_MONTHS = 6


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    middle = grouped["adj_close"].shift(SEGMENT_MONTHS)
    oldest = grouped["adj_close"].shift(LOOKBACK_MONTHS)
    middle_month = grouped["ym"].shift(SEGMENT_MONTHS)
    oldest_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    recent = ordered["adj_close"] / middle.where(middle > 0) - 1.0
    earlier = middle / oldest.where(oldest > 0) - 1.0
    exact = ordered["ym"].eq(middle_month + SEGMENT_MONTHS) & ordered["ym"].eq(oldest_month + LOOKBACK_MONTHS)
    return (recent - earlier).where(exact).reindex(frame.index)


FACTOR = Factor(
    name="momentum_acceleration_6m", family="price_momentum_acceleration",
    category="momentum", hypothesis="최근 3개월 추세가 직전 3개월보다 강화된 종목은 정보확산이 진행돼 이후 상대수익이 높다.",
    predicted_sign=1, params={"segment_months": SEGMENT_MONTHS, "lookback_months": LOOKBACK_MONTHS},
    rebalance_months=1, needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "최근 3개월 수익에서 직전 3개월 수익을 뺀 값이 큰 종목의 이후 순위가 높을 것이다.",
    "mechanism": "가격 추세의 가속은 정보 반영 속도가 아직 정점에 이르지 않았음을 나타낼 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 모멘텀 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: medium_term_momentum_6_2 — 차이: 6개월 누적 수준이 아니라 인접 3개월 추세의 변화만 측정한다.",
    "data_notes": "분할조정 adj_close와 정확한 3·6개월 달력 시차만 사용한다.",
}
