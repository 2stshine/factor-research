"""Pre-registered post-tax income conversion candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    pretax_income = frame["pretax_income_ttm"].where(
        frame["pretax_income_ttm"] > 0
    )
    return frame["net_income_ttm"] / pretax_income


FACTOR = Factor(
    name="posttax_income_conversion",
    family="tax_conversion_efficiency",
    category="quality",
    hypothesis=(
        "양의 세전이익 중 순이익으로 남는 비율이 높은 기업은 세금·세후 조정 누수가 작고 "
        "이익 실현 품질이 높아 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("pretax_income_ttm", "net_income_ttm"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 net_income_ttm/pretax_income_ttm이 높은 기업은 다음 달 총수익률 순위가 "
        "높을 것이다."
    ),
    "mechanism": (
        "낮은 전환율은 높은 세부담이나 세후 비경상 누수를 나타낸다. 시장이 headline 세전성과를 "
        "먼저 반영하고 이 누수를 늦게 평가하면 이후 가격 조정이 발생할 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "operating_income과 net_income의 차이를 보는 nonoperating_burden_to_assets와 일부 관계가 "
        "가능하지만, 이 후보는 세전 이후 구간의 전환율만 분리하므로 정의상 다르다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 pretax_income_ttm과 net_income_ttm을 사용한다. 양의 "
        "세전이익만 분모로 인정하며 적자와 결측을 다른 값으로 대체하지 않는다."
    ),
}
