"""Pre-registered operating return-on-assets factor; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    return frame["operating_income_ttm"] / assets


FACTOR = Factor(
    name="operating_roa",
    family="operating_roa",
    category="quality",
    hypothesis=(
        "총자산 대비 최근 12개월 영업이익이 높은 기업은 자산을 지속적으로 효율적으로 활용하며, "
        "시장이 이 영업 수익성의 지속성을 과소평가해 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("operating_income_ttm", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 최근 12개월 영업이익을 총자산으로 나눈 단일 operating ROA가 높은 종목은 "
        "이후 수익률 순위도 높을 것이다."
    ),
    "mechanism": (
        "높은 operating ROA는 기업이 보유 자산에서 핵심 영업이익을 효율적으로 창출한다는 뜻이다. "
        "투자자가 이 수익성의 지속성을 충분히 반영하지 않으면 후속 실적 확인과 함께 점진적으로 "
        "재평가된다."
    ),
    "falsification": (
        "전체 및 투자 가능 IC 최소요건, 기간·중립화 강건성, 고정 OOS IC, 다중검정 또는 Gold 신호 "
        "직교성 중 하나라도 hard fail이면 operating ROA 가설을 기각한다."
    ),
    "expected_relationship": (
        "qual_opm·qual_roe와 양의 관계를 예상하고, 분모가 총자산이므로 asset_turnover와도 중간 정도의 "
        "관계를 예상한다. 가치·모멘텀 팩터와는 상대적으로 낮은 관계를 예상한다."
    ),
    "data_notes": (
        "Silver revision을 available_date 기준으로 재생한 operating_income_ttm과 total_assets만 사용한다. "
        "총자산이 0 이하인 관측은 비율이 정의되지 않아 결측으로 두며, 회계 데이터 가용성 때문에 "
        "가격 팩터보다 커버리지가 낮을 수 있다."
    ),
}
