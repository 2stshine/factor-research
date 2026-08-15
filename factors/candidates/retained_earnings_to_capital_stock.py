"""Pre-registered internally-earned-capital candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    capital_stock = frame["capital_stock"].where(frame["capital_stock"] > 0)
    return frame["retained_earnings"] / capital_stock


FACTOR = Factor(
    name="retained_earnings_to_capital_stock",
    family="earned_to_contributed_capital",
    category="quality",
    hypothesis=(
        "납입자본 대비 이익잉여금이 높은 기업은 외부 출자보다 누적 이익으로 성장해 희석과 "
        "자금조달 의존이 낮으므로 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("retained_earnings", "capital_stock"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 retained_earnings/capital_stock이 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "자본금은 주주의 납입 기반이고 이익잉여금은 사업에서 누적한 내부자본이다. 내부자본이 "
        "납입자본보다 큰 기업은 장기간 이익을 재투자해 성장했을 가능성이 높고, 시장이 그 존속성과 "
        "자금조달 자립도를 과소평가할 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: retained_earnings_to_equity — 차이: 기타포괄손익과 자본잉여금을 "
        "포함한 총자본 비중이 아니라 법정 납입자본 대비 누적 내부이익의 배율을 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT retained_earnings와 capital_stock만 사용한다. "
        "자본금이 양수인 관측에서 정의하고 누적결손의 음수 이익잉여금은 유지한다."
    ),
}
