"""Pre-registered liquid-balance-sheet coverage candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    liabilities = frame["total_liabilities"].where(frame["total_liabilities"] > 0)
    return frame["current_assets"] / liabilities


FACTOR = Factor(
    name="current_assets_to_total_liabilities",
    family="liquid_asset_debt_coverage",
    category="quality",
    hypothesis=(
        "총부채 대비 유동자산이 높은 기업은 가까운 시일에 현금화할 자원으로 전체 채무를 더 잘 "
        "완충해 재무곤경 위험이 낮으므로 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("current_assets", "total_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 current_assets/total_liabilities가 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "유동자산은 영업주기 안에 현금화 가능한 완충재이고 총부채는 단기·장기 채무를 모두 담는다. "
        "이 비율이 높으면 차환시장 경색에도 대응할 수 있어 부실 확률과 강제 자산매각 위험이 낮다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: current_ratio — 차이: 유동부채만의 단기 지급능력이 아니라 "
        "유동자산이 장기부채까지 포함한 전체 채무를 얼마나 덮는지 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT current_assets와 total_liabilities만 사용한다. "
        "총부채가 양수인 관측에서 정의하며 자산 유동성의 업종 차이는 공통 강건성 gate가 진단한다."
    ),
}
