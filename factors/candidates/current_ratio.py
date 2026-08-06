"""Pre-registered current-ratio candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    current_liabilities = frame["current_liabilities"].where(
        frame["current_liabilities"] > 0
    )
    return frame["current_assets"] / current_liabilities


FACTOR = Factor(
    name="current_ratio",
    family="short_term_solvency",
    category="quality",
    hypothesis=(
        "유동부채 대비 유동자산이 많은 기업은 단기 자금압박과 강제조달 위험이 낮아, 이후 "
        "상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    rebalance_months=3,
    needs=("current_assets", "current_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 current_assets/current_liabilities가 높은 종목은 낮은 종목보다 이후 수익률 "
        "순위가 높을 것이다."
    ),
    "mechanism": (
        "유동비율이 높으면 가까운 만기의 의무를 내부 유동자산으로 감당할 여력이 크다. 신용경색이나 "
        "영업 충격 때 불리한 조건의 차입·증자·자산매각 가능성이 낮아 손실 꼬리가 줄 수 있고, "
        "시장이 이 재무 유연성을 충분히 보상하지 않으면 횡단면 수익률을 예측할 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "장기 레버리지를 보는 qual_lev·solvent_value와 중간 정도 관계를 예상하지만, 만기 1년 내 "
        "지급능력에 집중하므로 수익성·가치 팩터와의 관계는 낮을 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT current_assets와 current_liabilities만 "
        "사용한다. 유동부채가 양수인 관측에서 정의한다. 금융업은 유동·비유동 분류의 경제적 의미가 "
        "일반 기업과 다를 수 있으나 섹터 정보를 결과에 맞춰 사후 제외하지 않는다."
    ),
}
