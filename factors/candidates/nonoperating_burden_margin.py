"""Pre-registered non-operating burden relative to sales."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    sales = frame["revenue_ttm"].where(frame["revenue_ttm"] > 0)
    return (frame["operating_income_ttm"] - frame["net_income_ttm"]) / sales


FACTOR = Factor(
    name="nonoperating_burden_margin", family="nonoperating_sales_burden", category="quality",
    hypothesis="매출 대비 영업외·세금 부담이 큰 기업은 본업 성과의 주주귀속 전환이 약해 이후 상대수익이 낮다.",
    predicted_sign=-1, params={}, rebalance_months=3,
    needs=("operating_income_ttm", "net_income_ttm", "revenue_ttm"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "(영업이익-순이익)/TTM 매출이 높은 종목의 이후 수익률 순위가 낮을 것이다.",
    "mechanism": "금융비용·영업외손실·세금이 매출의 큰 몫을 소모하면 본업 이익이 주주가치로 전환되지 않는다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 이익전환 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: nonoperating_burden_to_assets — 차이: 자산이 아니라 매출 단위당 영업외 부담을 측정한다.",
    "data_notes": "DART available_date PIT 영업이익·순이익과 양의 TTM 매출만 사용한다.",
}
