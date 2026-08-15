"""Pre-registered long-lived-asset operating productivity candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    noncurrent_assets = frame["noncurrent_assets"].where(
        frame["noncurrent_assets"] > 0
    )
    return frame["operating_income_ttm"] / noncurrent_assets


FACTOR = Factor(
    name="operating_income_to_noncurrent_assets",
    family="long_lived_asset_operating_productivity",
    category="quality",
    hypothesis=(
        "비유동자산 대비 영업이익이 높은 기업은 장기 설비와 투자자산을 본업 이익으로 전환하는 "
        "효율이 높아 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("operating_income_ttm", "noncurrent_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 operating_income_ttm/noncurrent_assets가 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "비유동자산은 장기간 자본을 묶는 생산설비·투자자산의 기반이다. 같은 장기자산으로 더 많은 "
        "영업이익을 만드는 기업은 자본집약 위험을 덜 부담하며 시장이 이 효율의 지속성을 "
        "과소평가할 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: operating_roa — 차이: 유동자산을 포함한 총자산 수익성이 아니라 "
        "회수기간이 긴 비유동자산의 본업 생산성만 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT operating_income_ttm과 noncurrent_assets만 "
        "사용한다. 비유동자산이 양수인 관측에서 정의하고 영업손실은 유지한다."
    ),
}
