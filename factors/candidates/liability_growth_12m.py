"""Pre-registered 12-month liability-growth candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    liabilities = ordered["total_liabilities"].where(ordered["total_liabilities"] >= 0)
    prior_liabilities = liabilities.groupby(ordered["asset_id"]).shift(LOOKBACK_MONTHS)
    prior_liabilities = prior_liabilities.where(prior_liabilities > 0)
    growth = liabilities / prior_liabilities - 1
    return growth.reindex(frame.index)


FACTOR = Factor(
    name="liability_growth_12m",
    family="liability_growth",
    category="other",
    hypothesis=(
        "최근 12개월 부채가 빠르게 증가한 기업은 자금조달 압력과 미래 현금흐름 위험이 커지고, "
        "시장이 이 재무 팽창 위험을 충분히 반영하지 못해 이후 상대적으로 낮은 수익을 낸다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("total_liabilities",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 최근 12개월 총부채 증가율이 낮은 종목은 부채가 빠르게 증가한 종목보다 "
        "이후 수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "급격한 부채 증가는 투자와 운전자본을 위한 선제 조달일 수 있지만, 동시에 이자 부담과 "
        "차환 위험, 경영자의 과잉 확장을 높인다. 투자자가 외형 확장에 먼저 반응하고 재무 위험을 "
        "늦게 반영하면 저부채성장 기업이 이후 상대적으로 재평가될 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "재무 팽창을 측정하므로 asset_growth_12m과 양의 관계를 예상한다. 부채 수준을 측정하는 "
        "qual_lev와도 일부 관련되지만 변화율과 수준의 차이 때문에 완전한 중복은 아닐 것으로 "
        "예상한다. 수익성·모멘텀과의 관계는 낮을 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 정정공시를 재생한 Silver PIT total_liabilities를 사용한다. "
        "12개월 전 부채가 0 이하인 관측과 최초 12개월은 결측이다. 인수합병·사업분할과 리스 "
        "회계 변화로 생긴 구조적 부채 증가는 별도로 조정하지 않는다."
    ),
}
