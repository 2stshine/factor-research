"""Pre-registered operating-earnings-yield candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    return frame["operating_income_ttm"] / market_cap


FACTOR = Factor(
    name="operating_earnings_yield",
    family="operating_earnings_yield",
    category="value",
    hypothesis=(
        "시가총액 대비 영업이익이 큰 기업은 핵심 영업현금창출력에 비해 낮게 평가되어 이후 "
        "상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("operating_income_ttm",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 operating_income_ttm/market_cap이 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "순이익에는 자본구조, 세율과 비경상손익이 섞인다. 핵심 영업이익을 현재 자기자본 시장가치와 "
        "직접 비교하면 영업사업의 수익창출력에 비해 주가가 낮은 기업을 포착할 수 있고, 이 가격 "
        "괴리가 해소되면서 초과수익이 발생할 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: value_ep — 차이: 세후 순이익 대신 핵심 영업이익을 사용해 "
        "자본구조·세금·비경상손익 이전의 영업가치 저평가를 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 동월 양의 market_cap을 "
        "사용한다. 음의 영업이익은 그대로 유지하며 기업가치 대신 자기자본 시가총액을 분모로 써 "
        "부채가 큰 기업의 값이 높아질 수 있는 한계는 leverage 중립화 gate로 진단한다."
    ),
}
