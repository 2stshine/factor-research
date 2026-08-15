"""Pre-registered six-to-two-month price-momentum candidate."""
from __future__ import annotations

from engine.factors import Factor


FARTHEST_RETURN_LAG = 6
NEAREST_RETURN_LAG = 2
LOOKBACK_MONTHS = 6
SKIP_MONTHS = 1
GAP_POLICY = "calendar_months_no_fill"


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    recent = grouped["adj_close"].shift(SKIP_MONTHS)
    distant = grouped["adj_close"].shift(LOOKBACK_MONTHS)
    recent_month = grouped["ym"].shift(SKIP_MONTHS)
    distant_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    signal = recent / distant.where(distant > 0) - 1.0
    exact_calendar = (
        ordered["ym"].eq(recent_month + SKIP_MONTHS)
        & ordered["ym"].eq(distant_month + LOOKBACK_MONTHS)
    )
    return signal.where(exact_calendar).reindex(frame.index)


FACTOR = Factor(
    name="medium_term_momentum_6_2",
    family="medium_term_momentum",
    category="momentum",
    hypothesis=(
        "최근 한 달을 제외한 6개월 전부터 2개월 전까지의 가격 정보가 천천히 "
        "반영되면 해당 구간의 승자는 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={
        "farthest_return_lag": FARTHEST_RETURN_LAG,
        "nearest_return_lag": NEAREST_RETURN_LAG,
        "lookback_months": LOOKBACK_MONTHS,
        "skip_months": SKIP_MONTHS,
        "gap_policy": GAP_POLICY,
    },
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver 분할조정 가격으로 측정한 t-6부터 t-2까지 다섯 월수익의 복리 "
        "누적값이 높은 종목은 다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "기업 정보의 점진적 확산과 투자자 과소반응은 수개월 동안 가격 추세를 만들 수 "
        "있으며, 가장 최근 한 달을 제외하면 단기 반전과 미시구조 잡음을 줄일 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성·입력 커버리지·투자가능 IC·Rank ICIR·기간 및 "
        "중립화 강건성·campaign BY를 통과하지 못하거나 기존 신호와 중복되면 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: intermediate_momentum_12_7 — 차이: 더 최근인 "
        "t-6~t-2 구간만 사용하며 t-12~t-7의 오래된 정보확산과 구별한다. mom_12_1과 "
        "양의 관계는 예상하지만 정확한 형성 구간은 겹치지 않는다."
    ),
    "data_notes": (
        "Silver PIT adj_close로 월 가격수익을 만들고 종목별 달력월을 재색인한다. 결측 "
        "월은 채우지 않으며 정확한 다섯 월수익이 모두 있을 때만 신호를 낸다."
    ),
}
