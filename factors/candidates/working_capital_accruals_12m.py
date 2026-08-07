"""Pre-registered working-capital accrual candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    net_working_capital = ordered["current_assets"] - ordered["current_liabilities"]
    prior_working_capital = net_working_capital.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_assets = ordered["total_assets"].groupby(asset).shift(LOOKBACK_MONTHS)
    prior_assets = prior_assets.where(prior_assets > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    consecutive = ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS)
    accruals = ((net_working_capital - prior_working_capital) / prior_assets).where(consecutive)
    return accruals.reindex(frame.index)


FACTOR = Factor(
    name="working_capital_accruals_12m",
    family="working_capital_accruals",
    category="quality",
    hypothesis=(
        "총자산 대비 운전자본이 빠르게 늘어난 기업은 현금화되지 않은 재고·매출채권 또는 "
        "과잉투자가 축적됐을 가능성이 높아 이익 지속성이 낮고, 이후 상대수익도 낮다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("current_assets", "current_liabilities", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT에서 12개월 순운전자본 증가액을 전기 총자산으로 나눈 값이 낮은 종목은 높은 "
        "종목보다 이후 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "유동자산 증가가 유동부채 증가보다 크면 기업의 운전자본에 현금이 묶인다. 이 증가가 "
        "매출채권·재고 축적이나 공격적인 수익 인식에서 왔다면 보고이익의 현금 전환과 지속성이 "
        "낮을 수 있고, 투자자가 이를 늦게 반영하면 이후 가격이 조정될 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성·커버리지, 전체·투자 가능 IC와 Rank ICIR, 네 기간 및 중립화 "
        "강건성을 통과하지 못하면 가설을 기각한다. campaign BY 또는 봉인 OOS confirmation "
        "실패도 최종 기각으로 본다."
    ),
    "expected_relationship": (
        "자산 확장 정보를 일부 포함하므로 asset_growth_12m의 저성장 방향과 관계가 있을 수 있다. "
        "current_ratio는 단기 지급능력의 수준이고 이 후보는 운전자본의 12개월 변화이므로 정의상 "
        "구별되며, 수익성·모멘텀과의 관계는 낮을 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT current_assets, current_liabilities, "
        "total_assets를 사용한다. 정확히 12개월 전 관측과 양의 전기 총자산이 있을 때만 정의한다. "
        "현금·단기차입금 분리가 없어 순수 영업 accrual이 아닌 넓은 근사치이며 M&A·분할·계정 "
        "재분류 효과가 섞일 수 있다."
    ),
}
