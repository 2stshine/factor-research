"""Pre-registered 12-month operating-income growth candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    income = ordered["operating_income_ttm"]
    prior_income = income.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_income = prior_income.where(prior_income > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    consecutive = ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS)
    return (income / prior_income - 1).where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="operating_income_growth_12m",
    family="operating_income_growth",
    category="earnings",
    hypothesis=(
        "최근 12개월 영업이익이 증가한 기업은 본업 개선이 후속 공시에 걸쳐 점진적으로 가격에 "
        "반영되어 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("operating_income_ttm",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 12개월 operating_income_ttm 성장률이 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "본업 이익의 증가는 수요·가격결정력·원가규율 개선을 함께 반영한다. 투자자가 개선의 "
        "지속성을 여러 분기 공시에 걸쳐 반영하면 영업이익 성장 기업에 지연된 재평가가 생길 수 있다."
    ),
    "falsification": (
        "양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS, 귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: operating_roa_change_12m — 차이: 자산 분모의 변화와 무관하게 "
        "본업 이익 자체의 12개월 성장률만 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT operating_income_ttm을 사용한다. 정확히 "
        "12개월 전 영업이익이 양수인 관측에서 정의하며 현재 영업손실 전환은 음수로 유지한다."
    ),
}
