"""Pre-registered 12-month retained-earnings growth candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    retained = ordered["retained_earnings"]
    prior = retained.groupby(asset).shift(LOOKBACK_MONTHS)
    prior = prior.where(prior > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    consecutive = ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS)
    return (retained / prior - 1).where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="retained_earnings_growth_12m",
    family="internal_capital_accumulation",
    category="quality",
    hypothesis=(
        "최근 12개월 이익잉여금이 증가한 기업은 배당과 손실을 감당하고도 내부자본을 축적해 "
        "향후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("retained_earnings",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 12개월 retained_earnings 성장률이 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "이익잉여금 증가는 당기 이익에서 배당과 조정을 뺀 내부자본의 순축적이다. 지속적으로 "
        "내부자본을 늘리는 기업은 외부조달 의존과 재무곤경 위험이 낮고 시장이 그 복리 효과를 "
        "과소평가할 수 있다."
    ),
    "falsification": (
        "양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS, 귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: retained_earnings_to_equity — 차이: 자기자본 구성의 수준이 아니라 "
        "내부자본이 최근 12개월 동안 축적된 속도를 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT retained_earnings를 사용한다. 정확히 12개월 "
        "전 이익잉여금이 양수인 관측에서 정의하며 결손 기업의 기저 왜곡을 제외한다."
    ),
}
