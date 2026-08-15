"""Pre-registered annual change in book equity debt coverage."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    coverage = ordered["total_equity"] / ordered["total_liabilities"].where(ordered["total_liabilities"] > 0)
    prior = coverage.groupby(ordered["asset_id"], sort=False).shift(LOOKBACK_MONTHS)
    prior_month = ordered.groupby("asset_id", sort=False)["ym"].shift(LOOKBACK_MONTHS)
    return (coverage - prior).where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="equity_debt_coverage_change_12m", family="book_solvency_improvement",
    category="quality", hypothesis="자기자본의 부채 충당력이 개선된 기업은 재무위험 감소가 늦게 반영되어 이후 상대수익이 높다.",
    predicted_sign=1, params={"lookback_months": LOOKBACK_MONTHS}, rebalance_months=3,
    needs=("total_equity", "total_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "자기자본/총부채의 12개월 변화가 큰 종목의 이후 순위가 높을 것이다.",
    "mechanism": "부채 대비 손실흡수자본의 증가는 파산·차환위험을 낮추지만 신용평가와 가격은 후행할 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 레버리지 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: qual_lev — 차이: 레버리지 수준이 아니라 장부 지급능력의 12개월 개선폭을 측정한다.",
    "data_notes": "DART available_date PIT 자기자본·양의 총부채와 정확한 12개월 시차를 사용한다.",
}
