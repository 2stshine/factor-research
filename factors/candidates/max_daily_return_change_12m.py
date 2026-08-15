"""Pre-registered annual change in lottery-like maximum daily return."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["max_daily_return_1m"].shift(LOOKBACK_MONTHS)
    prior_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    value = ordered["max_daily_return_1m"] - prior
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name="max_daily_return_change_12m", family="lottery_demand_acceleration",
    category="other", hypothesis="월 최대 일수익이 과거보다 커진 종목은 복권형 수요가 강화돼 이후 상대수익이 낮다.",
    predicted_sign=-1, params={"lookback_months": LOOKBACK_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "월 최대 일수익의 12개월 변화가 큰 종목의 이후 순위가 낮을 것이다.",
    "mechanism": "극단적 상승일의 확대는 우측꼬리 선호 투자자 유입과 과대가격을 나타낼 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 MAX 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: max_daily_return_1m — 차이: 현재 극단값 수준이 아니라 12개월 확대폭을 측정한다.",
    "data_notes": "인증된 max_daily_return_1m과 정확한 12개월 전 값을 사용한다.",
}
