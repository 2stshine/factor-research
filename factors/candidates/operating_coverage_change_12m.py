"""Pre-registered annual change in short-term operating coverage."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    current = ordered["operating_income_ttm"] / ordered["current_liabilities"].where(ordered["current_liabilities"] > 0)
    prior = current.groupby(ordered["asset_id"], sort=False).shift(LOOKBACK_MONTHS)
    prior_month = ordered.groupby("asset_id", sort=False)["ym"].shift(LOOKBACK_MONTHS)
    return (current - prior).where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="operating_coverage_change_12m", family="short_term_operating_coverage_improvement",
    category="earnings", hypothesis="영업이익의 단기부채 충당력이 개선된 기업은 신용위험 감소가 늦게 반영되어 이후 상대수익이 높다.",
    predicted_sign=1, params={"lookback_months": LOOKBACK_MONTHS}, rebalance_months=3,
    needs=("operating_income_ttm", "current_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "영업이익/유동부채의 12개월 변화가 큰 종목의 이후 순위가 높을 것이다.",
    "mechanism": "본업 현금창출력에 가까운 이익이 단기 의무보다 빨리 개선되면 차환위험이 줄어든다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 이익개선 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: operating_income_to_current_liabilities — 차이: 충당력 수준이 아니라 12개월 개선폭을 측정한다.",
    "data_notes": "DART available_date PIT 영업이익·양의 유동부채와 정확한 12개월 시차를 사용한다.",
}
