"""Pre-registered 12-month current-asset growth candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    current_assets = ordered["current_assets"]
    prior = current_assets.groupby(asset).shift(LOOKBACK_MONTHS)
    prior = prior.where(prior > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    consecutive = ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS)
    return (current_assets / prior - 1).where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="current_assets_growth_12m",
    family="working_capital_investment_growth",
    category="other",
    hypothesis=(
        "최근 12개월 유동자산이 빠르게 증가한 기업은 재고·매출채권과 현금의 비효율적 축적 또는 "
        "과잉 확장 위험이 커 이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("current_assets",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 12개월 current_assets 성장률이 낮은 기업은 높은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "유동자산 팽창은 영업 성장의 준비일 수도 있지만 재고 체화와 매출채권 회수 지연을 포함할 "
        "수 있다. 시장이 외형 증가를 먼저 반영하고 운전자본의 낮은 생산성을 늦게 반영하면 낮은 "
        "유동자산 성장 기업의 기대수익이 상대적으로 높다."
    ),
    "falsification": (
        "음의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS, 귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: asset_growth_12m — 차이: 설비·투자자산을 제외하고 현금·재고·채권 "
        "등 단기 운전자본성 자산의 팽창만 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT current_assets를 사용한다. 정확히 12개월 전 "
        "유동자산이 양수인 관측에서 정의하며 M&A와 사업분할의 불연속은 별도 조정하지 않는다."
    ),
}
