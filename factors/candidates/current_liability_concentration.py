"""Pre-registered liability-maturity composition candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    liabilities = frame["total_liabilities"].where(frame["total_liabilities"] > 0)
    return frame["current_liabilities"] / liabilities


FACTOR = Factor(
    name="current_liability_concentration",
    family="liability_maturity_structure",
    category="quality",
    hypothesis=(
        "전체 부채 중 단기간에 결제해야 할 유동부채 비중이 높은 기업은 차환·운전자금 압박이 "
        "커서, 만기 집중도가 낮은 기업보다 이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    rebalance_months=3,
    needs=("current_liabilities", "total_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 유동부채/총부채 비율이 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "전체 의무 중 1년 안에 결제해야 할 몫이 크면 차환과 운전자금 충격에 취약해 불리한 증자나 "
        "자산매각 가능성이 커진다. 시장이 이 만기 집중 위험을 충분히 반영하지 않으면 낮은 집중도의 "
        "기업이 이후 상대적으로 재평가될 수 있다."
    ),
    "falsification": (
        "낮은 유동부채 집중 방향이 전체·투자 가능 IC, Rank ICIR, 기간·중립화 강건성을 통과하지 "
        "못하거나 current_ratio와 중복되면 별도의 부채 만기구조 가설을 기각한다. campaign BY "
        "또는 봉인 OOS confirmation 실패도 최종 기각으로 본다."
    ),
    "expected_relationship": (
        "current_ratio와 단기 재무위험이라는 개념을 공유하지만, 유동자산의 상환 능력이 아니라 "
        "총부채 안의 단기 의무 비중만 측정한다. qual_lev는 부채 총량, liability_growth_12m은 변화량을 "
        "보므로 구조적으로 구별된다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT current_liabilities와 total_liabilities를 "
        "사용하고 양의 총부채에서만 정의한다. 유동부채에는 단기차입금뿐 아니라 매입채무·선수금도 "
        "포함되므로 순수 차환위험으로 해석하지 않는다. PIT 업종 이력이 없어 업종별 정상구조를 "
        "통제하지 못하는 한계가 있다."
    ),
}
