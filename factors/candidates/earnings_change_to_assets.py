"""Pre-registered asset-scaled earnings-change candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    return frame["net_income_yoy_change"] / assets


FACTOR = Factor(
    name="earnings_change_to_assets",
    family="quarterly_earnings_change",
    category="earnings",
    hypothesis=(
        "기업 규모 대비 전년동기 순이익 개선이 큰 기업은 영업 성과의 변화를 시장이 한 번에 "
        "반영하지 못해, 후속 공시 전까지 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    rebalance_months=3,
    needs=("net_income_yoy_change", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 전년동기 분기 순이익 변화액/총자산이 높은 종목은 낮은 종목보다 이후 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "같은 회계분기와 비교한 순이익 개선은 계절성을 줄인 이익 변화다. 절대 변화액을 총자산으로 "
        "나누면 단순 기업 규모 효과를 줄일 수 있다. 투자자가 개선의 지속성을 점진적으로 반영하면 "
        "공시 이후에도 상대가격 조정이 이어질 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성·커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성을 "
        "통과하지 못하면 가설을 기각한다. campaign BY 또는 봉인 OOS confirmation 실패도 최종 "
        "기각으로 본다."
    ),
    "expected_relationship": (
        "같은 원천 변화액을 과거 변동성으로 표준화하는 sue와 양의 관계가 예상되지만, 이 후보는 "
        "기업 규모 대비 변화 강도를 측정하므로 완전 중복은 아닐 것으로 예상한다. TTM 수익성 수준 "
        "및 operating_roa_change_12m과도 일부 관계가 있을 수 있다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT net_income_yoy_change와 total_assets를 "
        "사용한다. net_income_yoy_change는 최신 공개 분기 순이익에서 동일 회계분기의 전년 값을 "
        "뺀 금액이며 성장률이 아니다. 총자산이 양수인 관측에서만 정의하고 공시 사이에는 신호가 "
        "계단형으로 유지된다."
    ),
}
