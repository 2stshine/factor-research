"""Pre-registered operating-income obligation-coverage candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    liabilities = frame["total_liabilities"].where(
        frame["total_liabilities"] > 0
    )
    return frame["operating_income_ttm"] / liabilities


FACTOR = Factor(
    name="operating_income_to_liabilities",
    family="operating_obligation_coverage",
    category="quality",
    hypothesis=(
        "총부채 한 단위당 영업이익이 큰 기업은 영업에서 의무를 감당할 여력이 높아 "
        "재조달과 희석 위험이 작고 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("operating_income_ttm", "total_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "신호시점에 알려진 Silver PIT operating_income_ttm/total_liabilities가 높은 종목은 "
        "낮은 종목보다 다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "영업이익은 기업의 반복 영업이 채권자·거래상대방에 대한 총의무를 지탱하는 완충력이다. "
        "이 완충력이 높으면 불리한 차환, 강제 자산매각 또는 주식 희석 가능성이 낮고, 시장이 "
        "그 차이를 천천히 반영하면 횡단면 수익률을 예측할 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, 다중검정, Gold SQL parity 또는 일회성 OOS 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "operating_roa 및 operating_return_on_capital_employed와 양의 관계, qual_lev와 음의 관계를 "
        "예상한다. 다만 분모가 자산이나 자기자본이 아닌 총부채이므로 어느 하나의 단순 "
        "재표현으로 판정될 만큼 중복되면 독립 후보로 인정하지 않는다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 operating_income_ttm과 total_liabilities만 사용한다. "
        "총부채가 양수일 때 정의하며 적자 영업이익은 삭제하지 않는다. 이자비용이 없어 정식 "
        "이자보상배율이 아니라 총의무 대비 영업 완충력이다."
    ),
}
