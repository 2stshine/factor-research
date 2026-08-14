"""Pre-registered operating-income-to-current-liabilities candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    current_liabilities = frame["current_liabilities"].where(
        frame["current_liabilities"] > 0
    )
    return frame["operating_income_ttm"] / current_liabilities


FACTOR = Factor(
    name="operating_income_to_current_liabilities",
    family="short_term_operating_coverage",
    category="quality",
    hypothesis=(
        "단기부채 대비 영업이익이 높은 기업은 가까운 만기의 지급의무를 핵심 영업성과로 감당할 "
        "여력이 커 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("operating_income_ttm", "current_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 operating_income_ttm/current_liabilities가 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "유동부채는 영업주기 안에 상환하거나 차환해야 하는 의무다. 핵심 영업이익으로 이를 충분히 "
        "덮는 기업은 단기 유동성 충격과 비싼 차환에 덜 노출되며, 시장이 이 회복력을 과소평가하면 "
        "향후 상대수익이 높을 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: operating_income_to_liabilities — 차이: 전체 부채의 장기 상환능력이 "
        "아니라 1년 안에 도래하는 유동부채에 대한 단기 영업 커버리지만 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 current_liabilities만 "
        "사용한다. 유동부채가 양수인 관측에서 정의하고 음의 영업이익은 유지한다. 금융업과 "
        "비금융업의 유동부채 성격 차이는 공통 강건성 gate에서 진단한다."
    ),
}
