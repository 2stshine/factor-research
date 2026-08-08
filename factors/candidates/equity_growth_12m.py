"""Pre-registered total-equity growth candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    equity = ordered["total_equity"]
    prior_equity = equity.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_equity = prior_equity.where(prior_equity > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    consecutive = ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS)
    return (equity / prior_equity - 1).where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="equity_growth_12m",
    family="equity_growth",
    category="other",
    hypothesis=(
        "최근 12개월 자기자본이 빠르게 증가한 기업은 외부자금 조달이나 과도한 확장 가능성이 "
        "높고 성장 기대가 이미 가격에 반영되어 이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("total_equity",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 12개월 total_equity 성장률이 낮은 기업은 높은 기업보다 다음 달 총수익률 "
        "순위가 높을 것이다."
    ),
    "mechanism": (
        "자기자본의 빠른 팽창은 증자·주식보상·인수 또는 기대가 높은 확장을 포함할 수 있다. "
        "투자자가 조달과 확장의 희석·평균회귀 위험을 늦게 반영하면 낮은 성장 기업의 기대수익이 "
        "상대적으로 높을 수 있다."
    ),
    "falsification": (
        "사전등록한 음의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "shares 변화 기반 net_equity_issuance_12m 및 total-assets 기반 asset_growth_12m과 일부 "
        "관계가 가능하지만, 이 후보는 PIT 장부 자기자본 전체의 12개월 변화만 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 total_equity를 사용한다. 정확히 12개월 전 양의 "
        "자기자본이 있을 때만 정의하며 적자 누적에 따른 음의 자본 출발점은 비율에서 제외한다."
    ),
}
