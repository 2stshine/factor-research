"""Pre-registered quality-and-stability composite; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12
COMPONENT_WEIGHT = 1 / 4
NEUTRAL_RANK = 0.5


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    operating_roa = ordered["operating_income_ttm"] / assets
    asset_turnover = ordered["revenue_ttm"] / assets
    equity_ratio = ordered["total_equity"] / assets
    monthly_return = ordered.groupby("asset_id")["return_close"].pct_change()
    volatility = (
        monthly_return.groupby(ordered["asset_id"])
        .rolling(LOOKBACK_MONTHS, min_periods=LOOKBACK_MONTHS)
        .std()
        .reset_index(level=0, drop=True)
    )
    operating_rank = operating_roa.groupby(ordered["ym"]).rank(pct=True)
    efficiency_rank = asset_turnover.groupby(ordered["ym"]).rank(pct=True)
    solvency_rank = equity_ratio.groupby(ordered["ym"]).rank(pct=True)
    stability_rank = (-volatility).groupby(ordered["ym"]).rank(pct=True)
    quality_sum = (
        operating_rank.fillna(NEUTRAL_RANK)
        + efficiency_rank.fillna(NEUTRAL_RANK)
        + solvency_rank.fillna(NEUTRAL_RANK)
        + stability_rank
    )
    return (COMPONENT_WEIGHT * quality_sum).reindex(frame.index)


FACTOR = Factor(
    name="quality_stability",
    family="quality_stability",
    category="quality",
    hypothesis=(
        "영업수익성·자산효율·자기자본 완충력이 높고 가격 변동성이 낮은 기업은 지속 가능한 사업 "
        "품질이 과소평가되어 이후에도 안정적인 초과수익을 낸다."
    ),
    predicted_sign=1,
    params={
        "lookback_months": LOOKBACK_MONTHS,
        "component_weight": COMPONENT_WEIGHT,
        "neutral_rank": NEUTRAL_RANK,
    },
    rebalance_months=3,
    needs=(
        "operating_income_ttm",
        "revenue_ttm",
        "total_assets",
        "total_equity",
    ),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월별 영업ROA·자산회전율·자기자본비율·12개월 저변동성 순위를 동일 비중으로 결합하면, "
        "단일 회계비율의 잡음을 줄이고 지속 가능한 품질을 가진 종목에서 롱온리 초과수익을 얻는다."
    ),
    "mechanism": (
        "높은 수익성과 효율성은 경쟁우위를, 높은 자기자본비율은 재무 충격 흡수력을, 낮은 가격 "
        "변동성은 취약성과 복권형 수요의 부재를 나타낸다. 네 신호가 함께 높은 기업의 이익 지속성을 "
        "시장이 보수적으로 평가하면 점진적인 재평가가 발생한다."
    ),
    "falsification": (
        "투자가능 IC와 비용 후 성과가 충분하지 않거나, 리밸런싱·비용·기간·중립화 강건성, 고정 "
        "OOS, 다중검정 또는 Gold 직교성 중 하나라도 hard fail이면 안정적 품질 가설을 기각한다."
    ),
    "expected_relationship": (
        "qual_opm, asset_turnover, qual_lev 및 low_vol_12m과 양의 관계를 예상하지만 네 축의 동등 "
        "결합이므로 어느 단일 팩터와도 완전히 같지는 않을 것으로 예상한다. 가치·소형 팩터와는 낮은 "
        "관계를 예상한다."
    ),
    "data_notes": (
        "Silver PIT operating_income_ttm, revenue_ttm, total_assets, total_equity와 total_return_close를 "
        "사용한다. 회계항목이 없는 관측은 해당 회계축만 중립 순위 0.5로 두며, 최초 12개월은 가격 "
        "안정성 계산 때문에 의도적으로 결측이다."
    ),
}
