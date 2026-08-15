"""Pre-registered post-tax-income debt coverage candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    liabilities = frame["total_liabilities"].where(frame["total_liabilities"] > 0)
    return frame["net_income_ttm"] / liabilities


FACTOR = Factor(
    name="net_income_to_liabilities",
    family="posttax_debt_coverage",
    category="quality",
    hypothesis="부채 대비 세후이익이 큰 기업은 실제 내부자본 축적 능력이 높아 이후 상대수익이 높다.",
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("net_income_ttm", "total_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT net_income_ttm/total_liabilities가 높은 종목이 낮은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "세금과 비영업비용을 지불한 뒤 남는 이익이 부채보다 충분하면 자기자본 축적과 부채 축소 여력이 크다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: pretax_income_to_liabilities — 차이: 세금·비지배 영향까지 반영한 최종 이익의 부채 커버리지다.",
    "data_notes": "DART available_date PIT TTM 순이익과 양의 총부채를 사용한다.",
}
