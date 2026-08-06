"""Pre-registered operating-ROA volatility candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


WINDOW_MONTHS = 36
MIN_OBSERVATIONS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    operating_roa = ordered["operating_income_ttm"] / assets
    volatility = operating_roa.groupby(ordered["asset_id"]).transform(
        lambda values: values.rolling(
            window=WINDOW_MONTHS,
            min_periods=MIN_OBSERVATIONS,
        ).std()
    )
    return volatility.reindex(frame.index)


FACTOR = Factor(
    name="operating_roa_volatility_36m",
    family="profitability_stability",
    category="quality",
    hypothesis=(
        "최근 36개월 영업 자산수익성의 변동성이 낮은 기업은 사업모델과 이익 창출력이 안정적이고, "
        "불확실성이 큰 기업에 대한 과도한 낙관이 교정되며 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=-1,
    params={"window_months": WINDOW_MONTHS, "min_observations": MIN_OBSERVATIONS},
    rebalance_months=3,
    needs=("operating_income_ttm", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT operating_income_ttm/total_assets의 최근 36개월 표준편차가 낮은 종목은 높은 "
        "종목보다 이후 수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "영업 ROA가 안정적이면 수요·원가 충격에도 자산에서 이익을 창출하는 능력이 지속된다는 "
        "뜻이다. 투자자가 변동성이 큰 기업의 상방 가능성을 과대평가하거나 안정적 기업을 지루한 "
        "종목으로 할인하면 낮은 수익성 변동성이 미래 수익을 예측할 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "수익성 수준인 operating_roa·qual_roe와는 약한 관계, 가격 안정성인 low_vol_12m과는 "
        "중간 정도의 양의 관계를 예상한다. 회계 수익성의 시계열 표준편차만 사용하므로 기존 "
        "복합 quality_stability와 동일한 정의는 아니다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 total_assets를 "
        "사용한다. 36개월 창에서 최소 24개 월 관측을 사전 고정한다. 회계 수치는 공시 사이에 "
        "반복되므로 실제로는 약 8개 이상 분기 정보의 변동성을 월 패널에서 측정하는 근사치다."
    ),
}
