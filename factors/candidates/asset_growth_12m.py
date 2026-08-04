"""Pre-registered asset-growth candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    prior_assets = assets.groupby(ordered["asset_id"]).shift(LOOKBACK_MONTHS)
    growth = assets / prior_assets - 1
    return growth.reindex(frame.index)


FACTOR = Factor(
    name="asset_growth_12m",
    family="asset_growth",
    category="other",
    hypothesis=(
        "최근 12개월 총자산 증가율이 낮은 기업은 과잉투자와 제국 확장에 따른 가치 훼손을 "
        "덜 겪어 이후 롱온리 초과수익을 낸다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("total_assets",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "공시 시점에 알 수 있는 총자산의 12개월 증가율이 낮은 종목을 보유하면, 공격적으로 "
        "자산을 확장한 종목보다 비용 후 양의 초과수익을 얻는다."
    ),
    "mechanism": (
        "경영자의 과잉투자와 제국 확장은 자본수익률을 낮출 수 있고, 투자자는 최근 성장률을 "
        "과도하게 외삽해 공격적 투자 기업을 고평가할 수 있다. 낮은 자산 증가는 이러한 "
        "대리인 비용과 기대 과잉의 반대편을 포착한다."
    ),
    "falsification": (
        "상폐 종착수익률 세 시나리오에서 방향이 유지되지 않거나, 투자가능 유니버스의 IC가 "
        "유지되지 않거나, 거래비용 후 순알파가 양수가 아니거나, 규모·시장·유동성 중립화 후 "
        "성과가 사라지면 가설을 기각한다."
    ),
    "expected_relationship": (
        "성숙한 저성장 기업을 선호하므로 value_bp와 약한 양의 관계를 예상한다. 자산을 빠르게 "
        "늘리지 않고 매출을 만드는 기업과 겹칠 수 있어 asset_turnover와도 일부 양의 관계를 "
        "예상하지만, 성장 변화율을 사용하므로 두 팩터와 완전히 같지는 않을 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 정정공시를 재생한 Silver PIT total_assets를 사용한다. "
        "재무상태표 stock 항목이므로 분기 차감 없이 당시 최신 잔액을 사용하며 최초 12개월은 "
        "의도적으로 결측이다. 공시 사이에는 같은 잔액이 유지되어 신호가 계단형일 수 있다."
    ),
}
