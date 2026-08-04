"""Pre-registered 12-month high-proximity factor; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    rolling_high = (
        ordered.groupby("asset_id")["return_close"]
        .rolling(LOOKBACK_MONTHS, min_periods=LOOKBACK_MONTHS)
        .max()
        .reset_index(level=0, drop=True)
    )
    proximity = ordered["return_close"] / rolling_high.where(rolling_high > 0)
    return proximity.reindex(frame.index)


FACTOR = Factor(
    name="high_12m_proximity",
    family="price_anchoring",
    category="momentum",
    hypothesis=(
        "최근 12개월 월말 고점에 가까운 종목은 투자자의 고점 앵커링으로 긍정적 정보가 "
        "천천히 반영되어 이후에도 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "현재 총수익지수가 최근 12개월 월말 최고치에 가까운 종목을 보유하면, 단순 시작점-종점 "
        "모멘텀과 다른 고점 기준점 효과로 이후 롱온리 초과수익을 얻는다."
    ),
    "mechanism": (
        "투자자는 이전 고점을 매도 또는 가치판단의 기준점으로 삼아 호재를 한 번에 가격에 반영하지 "
        "않는다. 고점에 가까운 가격은 누적된 긍정적 정보와 매도 저항의 소진을 나타내므로 가격 발견이 "
        "계속될 수 있다."
    ),
    "falsification": (
        "투자가능 IC와 비용 후 성과가 충분하지 않거나, 강건성·고정 OOS·다중검정·Gold 직교성 중 "
        "하나라도 hard fail이면 고점 앵커링 가설을 기각한다."
    ),
    "expected_relationship": (
        "mom_12_1과는 양의 관계를 예상하지만, 12개월 시작점 대비 수익률이 아니라 기간 중 최고점과의 "
        "거리이므로 완전히 같지는 않을 것으로 예상한다. 가치·품질 팩터와는 낮은 관계를 예상한다."
    ),
    "data_notes": (
        "Silver PIT total_return_close의 월말 관측치로 12개월 이동 최고치를 계산한다. 일별 52주 고가가 "
        "아니며, 최초 11개월은 의도적으로 결측이다."
    ),
}
