"""Pre-registered retained-earnings debt coverage candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    liabilities = frame["total_liabilities"].where(frame["total_liabilities"] > 0)
    return frame["retained_earnings"] / liabilities


FACTOR = Factor(
    name="retained_earnings_to_liabilities",
    family="earned_capital_debt_coverage",
    category="quality",
    hypothesis="부채 대비 누적 내부유보가 큰 기업은 재무 자립도가 높아 이후 상대수익이 높다.",
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("retained_earnings", "total_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT retained_earnings/total_liabilities가 높은 종목이 낮은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "누적 내부자본이 부채보다 충분하면 외부조달 의존과 파산비용이 낮고 이익의 역사적 지속성을 나타낼 수 있다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: retained_earnings_to_assets — 차이: 자산 내 유보 비중이 아니라 채권자 청구권을 덮는 누적 유보 규모다.",
    "data_notes": "DART available_date PIT 이익잉여금과 양의 총부채를 사용하며 음의 유보는 보존한다.",
}
