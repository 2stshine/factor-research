"""Trailing 252-observation realized volatility from daily total returns."""
from __future__ import annotations

from engine.factors import Factor


WINDOW_DAYS = 252
MIN_OBSERVATIONS = 126


def compute(frame):
    enough_history = frame["daily_return_observations_252d"] >= MIN_OBSERVATIONS
    return frame["daily_volatility_252d"].where(enough_history)


FACTOR = Factor(
    name="realized_volatility_252d",
    family="low_volatility",
    category="other",
    hypothesis=(
        "레버리지 제약과 고변동·복권형 종목 선호로 변동성이 높은 주식이 고평가되며, 최근 "
        "일별 실현변동성이 낮은 종목은 이후 상대수익이 높다."
    ),
    predicted_sign=-1,
    params={
        "window_days": WINDOW_DAYS,
        "min_observations": MIN_OBSERVATIONS,
    },
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "최근 252거래 관측의 일별 총수익률 표준편차가 낮은 종목은 높은 종목보다 이후 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "직접 레버리지가 어려운 투자자와 복권형 수익을 선호하는 투자자의 고변동 종목 수요가 "
        "저변동 종목에 상대적 기대수익 보상을 남길 수 있다."
    ),
    "falsification": (
        "현재 gate를 통과하지 못하거나 월별 low_vol_12m과의 중복이 허용 기준을 넘거나 정식 "
        "confirmation에 실패하면 일별 저변동성 후보를 기각한다."
    ),
    "expected_relationship": (
        "low_vol_12m 및 market_beta_36m과 양의 최종점수 관계가 예상된다. 다만 일별 충격을 "
        "사용하므로 월수익 표준편차보다 급격한 변동을 더 많이 반영한다."
    ),
    "data_notes": (
        "인증된 Silver 일별 total_return_close로 계산한 표준편차이며 최소 126개 유효 수익률을 "
        "요구한다. 시장요인을 회귀 제거한 idiosyncratic volatility는 아니다."
    ),
}
