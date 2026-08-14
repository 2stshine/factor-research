"""Pre-registered current-asset-turnover candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    current_assets = frame["current_assets"].where(frame["current_assets"] > 0)
    return frame["revenue_ttm"] / current_assets


FACTOR = Factor(
    name="current_asset_turnover",
    family="current_asset_turnover",
    category="quality",
    hypothesis=(
        "유동자산 대비 매출이 높은 기업은 재고·매출채권·현금 등 단기 운전자본을 효율적으로 "
        "활용해 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("revenue_ttm", "current_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 revenue_ttm/current_assets가 높은 기업은 낮은 기업보다 다음 달 총수익률 "
        "순위가 높을 것이다."
    ),
    "mechanism": (
        "같은 유동자산 기반에서 더 많은 매출을 만드는 기업은 재고와 매출채권의 회전, 현금의 "
        "배치와 단기 운영규율이 우수할 수 있다. 시장이 운전자본 효율의 지속성을 늦게 반영하면 "
        "높은 회전율이 이후 상대수익을 예측할 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: asset_turnover — 차이: 전체 자산 효율이 아니라 재고·채권·현금 등 "
        "단기 영업자산의 회전효율에만 초점을 둔다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT revenue_ttm과 current_assets만 사용한다. "
        "유동자산이 양수인 관측에서 정의하며 업종별 운전자본 구조 차이는 공통 시장·규모·업종 "
        "강건성 검사에서 진단한다."
    ),
}
