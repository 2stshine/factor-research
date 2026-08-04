"""Pre-registered balance-sheet-safe value composite; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


VALUE_WEIGHT = 0.5
SOLVENCY_WEIGHT = 0.5


def compute(frame):
    equity = frame["total_equity"]
    positive_equity = equity.where(equity > 0)
    book_to_price = equity / frame["market_cap"].where(frame["market_cap"] > 0)
    leverage = frame["total_liabilities"] / positive_equity
    value_rank = book_to_price.groupby(frame["ym"]).rank(pct=True)
    solvency_rank = (-leverage).groupby(frame["ym"]).rank(pct=True)
    return VALUE_WEIGHT * value_rank + SOLVENCY_WEIGHT * solvency_rank


FACTOR = Factor(
    name="solvent_value",
    family="defensive_value",
    category="value",
    hypothesis=(
        "장부가치 대비 저평가되면서 부채/자기자본 비율이 낮은 종목은 재무적 가치함정을 피하고 "
        "하방 손실을 줄여 이후 안정적인 롱온리 초과수익을 낸다."
    ),
    predicted_sign=1,
    params={"value_weight": VALUE_WEIGHT, "solvency_weight": SOLVENCY_WEIGHT},
    rebalance_months=3,
    needs=("total_equity", "total_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월별 장부가치/시가총액 순위와 저부채 순위를 동등 결합한 종목을 보유하면, 가격 변동성으로 "
        "가치함정을 거르는 방식보다 펀더멘털에 기반한 안정적인 비용 후 초과수익을 얻는다."
    ),
    "mechanism": (
        "가치 프리미엄에는 과잉반응 교정과 재무적 곤경 보상이 함께 섞인다. 낮은 레버리지는 값이 "
        "싼 이유가 지급능력 악화인 기업을 줄여, 회복 가능한 저평가와 구조적 부실을 구분한다."
    ),
    "falsification": (
        "투자가능 유니버스에서 IC가 유지되지 않거나, 비용 후 순알파와 IR이 충분하지 않거나, "
        "강건성·OOS·다중검정 또는 기존 Gold 직교성 검사를 통과하지 못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "value_bp 및 저부채 방향의 qual_lev와 높은 양의 관계를 예상한다. 가격 변동성을 쓰지 않으므로 "
        "low_vol_12m 및 defensive_value와는 중간 수준의 관계를 예상한다."
    ),
    "data_notes": (
        "Silver PIT total_equity, total_liabilities와 월말 market_cap을 사용한다. 부채비율이 정의되지 "
        "않는 자기자본 0 이하 기업은 신호가 결측이며 재무상태표 stock 값을 분기 차감하지 않는다."
    ),
}
