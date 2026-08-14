"""Pre-registered downside-volatility candidate; do not edit after evaluation."""
from __future__ import annotations

import numpy as np

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    monthly_return = ordered.groupby("asset_id")["adj_close"].pct_change()
    downside_squared = monthly_return.clip(upper=0).pow(2)
    downside_variance = (
        downside_squared.groupby(ordered["asset_id"])
        .rolling(LOOKBACK_MONTHS, min_periods=LOOKBACK_MONTHS)
        .mean()
        .reset_index(level=0, drop=True)
    )
    return np.sqrt(downside_variance).reindex(frame.index)


FACTOR = Factor(
    name="downside_vol_12m",
    family="low_volatility",
    category="other",
    hypothesis=(
        "최근 12개월 손실 구간의 하방 변동성이 낮은 종목은 재무적 취약성과 복권형 하락위험이 "
        "과대평가된 종목을 피하면서 상승 변동성은 보존해 이후 롱온리 초과수익을 낸다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월별 분할조정 가격수익률의 최근 12개월 하방 준편차가 낮은 종목을 보유하면, 전체 변동성이 낮은 "
        "종목을 고르는 것보다 상승 잠재력을 덜 훼손하면서 비용 후 양의 초과수익을 얻는다."
    ),
    "mechanism": (
        "투자자는 복권형 종목과 극단적 반등 가능성을 선호하고 하락위험을 충분히 가격에 반영하지 "
        "않을 수 있다. 전체 변동성과 달리 하방 준편차는 좋은 상승 변동성을 벌하지 않고 반복적인 "
        "손실과 취약성에 집중한다."
    ),
    "falsification": (
        "상폐 종착수익률 세 시나리오에서 방향이 유지되지 않거나, 투자가능 유니버스에서 IC가 "
        "유지되지 않거나, 비용 후 순알파와 OOS 성과가 양수가 아니거나, 중립화 후 성과가 사라지면 "
        "가설을 기각한다."
    ),
    "expected_relationship": (
        "low_vol_12m과 높은 양의 관계를 예상하지만 상승 변동성을 제외하므로 완전한 중복은 아닐 "
        "것으로 예상한다. 가치·수익성 팩터와는 낮거나 중간 수준의 관계를 예상한다."
    ),
    "data_notes": (
        "Silver PIT 분할조정 가격 adj_close에서 계산한 월 가격수익률의 음수 부분만 사용한다. 최초 12개월은 "
        "의도적으로 결측이며 일별 꼬리위험이 아니라 월별 하방 준편차를 측정한다."
    ),
}
