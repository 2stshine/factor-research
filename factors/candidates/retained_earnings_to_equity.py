"""Pre-registered retained-earnings-to-equity candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    equity = frame["total_equity"].where(frame["total_equity"] > 0)
    return frame["retained_earnings"] / equity


FACTOR = Factor(
    name="retained_earnings_to_equity",
    family="retained_earnings_equity_share",
    category="quality",
    hypothesis=(
        "자기자본 중 누적 이익잉여금 비중이 높은 기업은 외부 출자보다 내부 이익으로 자본을 "
        "형성한 성숙한 기업이어서 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("retained_earnings", "total_equity"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 retained_earnings/total_equity가 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "이익잉여금은 외부 출자 없이 누적한 내부자본이다. 자기자본에서 그 비중이 높으면 장기간 "
        "이익을 축적하고 희석성 자금조달 의존을 낮춘 기업일 가능성이 높으며, 시장이 이 자본의 "
        "질과 생존력을 과소평가하면 이후 상대수익이 높을 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: retained_earnings_to_assets — 차이: 자산 대비 누적 수익성이 아니라 "
        "자기자본이 내부이익과 외부출자 중 무엇으로 구성됐는지를 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT retained_earnings와 total_equity만 사용한다. "
        "자기자본이 양수인 관측에서 정의하고 결손 누적의 음수 이익잉여금은 유지한다. 자사주·기타 "
        "포괄손익누계액도 총자본에 포함되므로 순수한 존속연령 지표는 아니다."
    ),
}
