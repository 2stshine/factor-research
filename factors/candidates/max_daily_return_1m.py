"""Maximum daily total return in the latest calendar month."""
from __future__ import annotations

from engine.factors import Factor


MIN_OBSERVATIONS = 10


def compute(frame):
    enough_history = frame["max_daily_return_observations_1m"] >= MIN_OBSERVATIONS
    return frame["max_daily_return_1m"].where(enough_history)


FACTOR = Factor(
    name="max_daily_return_1m",
    family="lottery_demand",
    category="other",
    hypothesis=(
        "최근 한 달에 극단적으로 큰 일수익을 보인 복권형 주식은 투자자 선호로 고평가되어 "
        "이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    params={"min_observations": MIN_OBSERVATIONS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "직전 월의 최대 일별 총수익률이 낮은 종목은 최대 일수익률이 높은 종목보다 이후 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "일부 투자자는 낮은 확률의 큰 보상을 선호해 최근 극단적 상승을 보인 주식에 과도한 "
        "가격을 지불할 수 있고, 이 고평가는 이후 평균수익을 낮춘다."
    ),
    "falsification": (
        "무결성·IC·Rank ICIR·기간 강건성·다중검정·confirmation을 통과하지 못하거나 다른 "
        "저위험 신호와 중복되면 독립적인 복권수요 가설을 기각한다."
    ),
    "expected_relationship": (
        "return_skewness_24m, return_kurtosis_24m 및 저변동성 신호와 관계가 예상되지만 최근 "
        "한 달의 단일 최대 일수익에만 반응한다."
    ),
    "data_notes": (
        "인증된 Silver total_return_close의 월중 일별 수익률 최대값이다. 기존 "
        "max_monthly_return_12m은 12개월 최대 월수익률 proxy이므로 보존하고 이 정의와 구분한다. "
        "월중 최소 10개 유효 관측이 필요하다."
    ),
}
