"""Pre-registered retained-earnings-to-assets candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    return frame["retained_earnings"] / assets


FACTOR = Factor(
    name="retained_earnings_to_assets",
    family="internal_financing",
    category="quality",
    hypothesis=(
        "총자산 대비 누적 이익잉여금이 큰 기업은 외부자금 의존도가 낮고 장기간 수익을 축적한 "
        "기업이어서, 재무곤경 위험이 낮고 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    rebalance_months=3,
    needs=("retained_earnings", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 retained_earnings/total_assets가 높은 종목은 낮은 종목보다 이후 수익률 "
        "순위가 높을 것이다."
    ),
    "mechanism": (
        "이익잉여금은 과거 이익 중 배당하지 않고 내부에 축적한 자본이다. 자산 대비 비중이 높으면 "
        "손실과 외부조달에 의존해 성장한 기업보다 누적 수익성과 자금 자립도가 높아, 재무곤경과 "
        "비싼 증자 위험이 작을 수 있다. 시장이 이 장기 생존력 차이를 충분히 가격에 반영하지 "
        "않으면 미래 횡단면 수익률을 예측한다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "현재 이익 수준을 쓰는 qual_roe·net_roa와 양의 관계가 예상되지만, 장기간 누적된 내부자금 "
        "재원을 측정하므로 완전한 중복은 아닐 것으로 예상한다. 부채비율 qual_lev와는 음의 관계, "
        "net_equity_issuance_12m과는 약한 양의 관계를 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT retained_earnings와 total_assets만 사용한다. "
        "총자산이 양수인 관측에서 정의하며, 결손 누적으로 이익잉여금이 음수인 값도 그대로 "
        "유지한다. 회사 연령과 과거 배당정책이 함께 반영될 수 있다."
    ),
}
