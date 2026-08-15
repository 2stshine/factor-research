"""Pre-registered 12-month current-liability growth candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    current_liabilities = ordered["current_liabilities"]
    prior = current_liabilities.groupby(asset).shift(LOOKBACK_MONTHS)
    prior = prior.where(prior > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    consecutive = ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS)
    return (current_liabilities / prior - 1).where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="current_liabilities_growth_12m",
    family="short_term_financing_growth",
    category="other",
    hypothesis=(
        "최근 12개월 유동부채가 빠르게 증가한 기업은 단기 자금조달과 차환 압력이 커 이후 "
        "상대수익이 낮다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("current_liabilities",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 12개월 current_liabilities 성장률이 낮은 기업은 높은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "유동부채의 급증은 공급자신용 의존, 단기차입 확대 또는 만기 단축을 뜻할 수 있다. 시장이 "
        "성장 재원을 먼저 평가하고 가까운 만기의 차환 위험을 늦게 반영하면 낮은 단기부채 성장 "
        "기업이 상대적으로 재평가될 수 있다."
    ),
    "falsification": (
        "음의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS, 귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: liability_growth_12m — 차이: 장기부채 변화를 제외하고 1년 안에 "
        "상환·차환해야 하는 유동부채의 증가만 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT current_liabilities를 사용한다. 정확히 "
        "12개월 전 유동부채가 양수인 관측에서 정의한다."
    ),
}
