"""Pre-registered paid-in-capital composition candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    equity = frame["total_equity"].where(frame["total_equity"] > 0)
    return frame["capital_stock"] / equity


FACTOR = Factor(
    name="paid_in_capital_ratio",
    family="equity_composition",
    category="quality",
    hypothesis=(
        "자기자본 중 법정 자본금 비중이 높은 기업은 누적 이익과 기타 내부 축적 자본의 완충력이 "
        "상대적으로 약해, 자본금 비중이 낮은 기업보다 이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    rebalance_months=3,
    needs=("capital_stock", "total_equity"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 자본금/자기자본 비율이 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "자기자본에서 명목 자본금이 차지하는 비중이 낮으면 이익잉여금·자본잉여 등 사업을 통해 "
        "축적되거나 명목 자본금 밖에서 형성된 완충력이 상대적으로 크다는 뜻일 수 있다. 시장이 "
        "이 자본 구성의 질을 충분히 구분하지 않으면 이후 재평가가 나타날 수 있다."
    ),
    "falsification": (
        "낮은 자본금 비중 방향이 전체·투자 가능 IC, Rank ICIR, 기간·중립화 강건성을 통과하지 "
        "못하거나 기존 내부금융 신호와 중복되면 가설을 기각한다. campaign BY 또는 봉인 OOS "
        "confirmation 실패도 최종 기각으로 본다."
    ),
    "expected_relationship": (
        "retained_earnings_to_assets의 내부축적 방향과 일부 관계가 예상되지만, 본 후보는 총자산이 "
        "아니라 자기자본 내부의 명목 자본금 구성만 본다. net_equity_issuance_12m은 최근 조달 "
        "변화량이므로 현재 구성 수준인 본 후보와 구별된다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT capital_stock과 total_equity를 사용하고 양의 "
        "자기자본에서만 정의한다. capital_stock은 총 외부조달액이 아니라 법정 명목 자본금이며, "
        "주식발행초과금·기타자본은 포함하지 않는다. 감자·증자·합병으로 구조적 단절이 생길 수 있다."
    ),
}
