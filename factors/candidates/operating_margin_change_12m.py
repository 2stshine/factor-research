"""Pre-registered operating-margin expansion candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    revenue = ordered["revenue_ttm"].where(ordered["revenue_ttm"] > 0)
    margin = ordered["operating_income_ttm"] / revenue
    prior_margin = margin.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    consecutive = ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS)
    return (margin - prior_margin).where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="operating_margin_change_12m",
    family="operating_margin_expansion",
    category="earnings",
    hypothesis=(
        "최근 12개월 동안 영업이익률이 개선된 기업은 가격결정력과 비용 규율 개선이 "
        "점진적으로 반영되어 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("operating_income_ttm", "revenue_ttm"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 TTM 영업이익률이 정확히 12개월 전보다 많이 개선된 종목은 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "마진 확장은 단순 매출 성장과 달리 판매 한 단위에서 남기는 영업이익의 개선을 "
        "측정한다. 영업 레버리지, 구조조정 또는 가격결정력의 지속성을 투자자가 후속 공시에 "
        "걸쳐 반영하면 수익률 예측력이 생길 수 있다."
    ),
    "falsification": (
        "자동 gate의 양의 방향이 실패하거나 investable·기간·중립화 강건성이 없고, 또는 "
        "qual_opm·operating_roa_change_12m·asset_turnover_change_12m와 중복되면 기각한다."
    ),
    "expected_relationship": (
        "영업이익률 수준 및 operating_roa_change_12m와 양의 관계를 예상하지만, 매출 한 단위당 "
        "이익의 12개월 변화만 측정하므로 수준·자산효율 변화와 정의상 구별된다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 operating_income_ttm과 revenue_ttm을 사용한다. "
        "현재·과거 매출이 양수이고 정확히 12개월 전 관측이 있을 때 정의한다. 음의 영업마진은 "
        "보존하며 M&A·사업 재분류가 불연속을 만들 수 있다."
    ),
}
