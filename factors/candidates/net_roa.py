"""Pre-registered net return-on-assets candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    return frame["net_income_ttm"] / assets


FACTOR = Factor(
    name="net_roa",
    family="net_roa",
    category="quality",
    hypothesis=(
        "총자산 대비 최종 순이익이 높은 기업은 자산을 효율적으로 운용하면서 금융비용과 세금까지 "
        "감당하는 수익성이 높고, 시장이 이 전사적 효율의 지속성을 과소평가해 이후 상대적으로 "
        "높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("net_income_ttm", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 최근 12개월 순이익을 총자산으로 나눈 단일 net ROA가 높은 종목은 이후 "
        "수익률 순위도 높을 것이다."
    ),
    "mechanism": (
        "net ROA는 보유 자산이 최종 주주이익으로 전환되는 정도를 측정한다. 높은 값은 영업 "
        "효율뿐 아니라 부채비용·세금·비영업손익까지 관리한다는 뜻이며, 이 효율이 지속되면 "
        "후속 공시를 통해 점진적으로 가격에 반영될 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, 고정 OOS, "
        "다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "분자가 순이익인 qual_roe, 분모가 총자산인 operating_roa와 강한 양의 관계를 예상한다. "
        "net_profit_margin과도 관련되지만 매출 대신 자산을 분모로 사용하므로 자산회전율 차이가 "
        "남을 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 정정공시를 재생한 Silver PIT net_income_ttm과 total_assets만 "
        "사용한다. 총자산이 0 이하인 관측은 결측으로 두며, 순이익에는 일회성 비영업손익과 "
        "세금 효과가 포함될 수 있다."
    ),
}
