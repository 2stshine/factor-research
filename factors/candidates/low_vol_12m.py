"""Pre-registered low-volatility candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    monthly_return = ordered.groupby("asset_id")["return_close"].pct_change()
    volatility = (
        monthly_return.groupby(ordered["asset_id"])
        .rolling(LOOKBACK_MONTHS, min_periods=LOOKBACK_MONTHS)
        .std()
        .reset_index(level=0, drop=True)
    )
    return volatility.reindex(frame.index)


FACTOR = Factor(
    name="low_vol_12m",
    family="low_volatility",
    category="other",
    hypothesis=(
        "최근 12개월 변동성이 낮은 종목은 레버리지 제약과 투자자의 복권형 고변동 주식 "
        "선호 때문에 과소평가되어 이후 롱온리 초과수익을 낸다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월별 총수익률의 최근 12개월 변동성이 낮은 종목을 보유하면 고변동 종목 선호의 "
        "가격 왜곡이 교정되며 비용 후 양의 초과수익을 얻는다."
    ),
    "mechanism": (
        "벤치마크 추종과 레버리지 제약을 받는 투자자는 목표 수익을 높이기 위해 고베타·고변동 "
        "종목을 과도하게 매수하고, 복권형 수익 분포 선호도 같은 방향으로 작용한다."
    ),
    "falsification": (
        "투자가능 유니버스에서 IC가 유지되지 않거나 비용 후 순알파가 양수가 아니거나, "
        "규모·시장·유동성 중립화 후 성과가 사라지면 가설을 기각한다."
    ),
    "expected_relationship": (
        "소형주가 고변동인 경향 때문에 size와 양의 최종점수 상관을 예상하지만, 가격 변동성 자체를 "
        "사용하므로 기존 가치·수익성 팩터와의 상관은 낮을 것으로 예상한다."
    ),
    "data_notes": (
        "Silver total_return_close로 만든 월별 수익률만 사용한다. 최초 12개월은 의도적으로 결측이며 "
        "분모·재무 정정공시 의존성은 없다."
    ),
}
