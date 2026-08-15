"""Pre-registered pretax profit-margin candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    revenue = frame["revenue_ttm"].where(frame["revenue_ttm"] > 0)
    return frame["pretax_income_ttm"] / revenue


FACTOR = Factor(
    name="pretax_profit_margin",
    family="pretax_profitability_margin",
    category="quality",
    hypothesis=(
        "매출 대비 세전이익이 높은 기업은 영업성과와 비영업손익을 합친 가격결정력과 비용 "
        "통제력이 높아 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("pretax_income_ttm", "revenue_ttm"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 pretax_income_ttm/revenue_ttm이 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "세전 마진은 본업의 원가 구조뿐 아니라 금융비용과 비영업손익까지 매출 한 단위에 대해 "
        "얼마나 남기는지 측정한다. 시장이 이 종합 수익성의 지속성을 과소평가하면 이후 상대수익으로 "
        "이어질 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: net_profit_margin — 차이: 세후 순이익 대신 법인세 전 이익을 써 "
        "세율·세액공제 차이를 제거하면서 비영업손익은 포함한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT pretax_income_ttm과 revenue_ttm만 사용한다. "
        "매출이 양수인 관측에서 정의하고 세전손실은 음수로 유지한다."
    ),
}
