"""Pre-registered revenue-based total-liability turnover candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    liabilities = frame["total_liabilities"].where(frame["total_liabilities"] > 0)
    return frame["revenue_ttm"] / liabilities


FACTOR = Factor(
    name="revenue_to_total_liabilities",
    family="revenue_debt_turnover",
    category="quality",
    hypothesis=(
        "총부채 대비 매출이 높은 기업은 채무 한 단위로 더 큰 영업 규모를 유지해 부채 부담을 "
        "흡수하는 능력이 높으므로 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("revenue_ttm", "total_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 revenue_ttm/total_liabilities가 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "매출은 이익률 선택 이전의 사업 처리 규모이고 총부채는 단기·장기 자금조달 의무다. 같은 "
        "부채로 더 큰 매출 기반을 운영하는 기업은 수요 충격을 흡수하고 채무를 차환할 여력이 높다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: operating_income_to_liabilities — 차이: 이익률과 비용구조를 섞지 "
        "않고 총부채가 뒷받침하는 매출 규모의 회전만 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT revenue_ttm과 total_liabilities만 사용한다. "
        "총부채가 양수인 관측에서 정의하며 업종별 회전 차이는 공통 강건성 gate가 진단한다."
    ),
}
