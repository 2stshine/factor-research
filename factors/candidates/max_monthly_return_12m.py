"""Pre-registered maximum monthly return candidate."""
from __future__ import annotations

from engine.factors import Factor


WINDOW_MONTHS = 12
MIN_OBSERVATIONS = 9


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    monthly_return = ordered.groupby("asset_id")["adj_close"].pct_change(
        fill_method=None
    )
    maximum_return = monthly_return.groupby(asset).transform(
        lambda series: series.rolling(
            WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
        ).max()
    )
    return maximum_return.reindex(frame.index)


FACTOR = Factor(
    name="max_monthly_return_12m",
    family="lottery_demand",
    category="other",
    hypothesis=(
        "최근 12개월 중 한 달의 극단적 급등폭이 큰 종목은 복권형 수익을 선호하는 투자자의 "
        "수요로 과대평가되어 이후 상대적으로 낮은 수익을 낸다."
    ),
    predicted_sign=-1,
    params={
        "window_months": WINDOW_MONTHS,
        "min_observations": MIN_OBSERVATIONS,
    },
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT 분할조정 가격으로 계산한 최근 12개월 최대 월 가격수익률이 낮은 종목은 높은 종목보다 "
        "이후 수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "일부 투자자가 작은 확률의 큰 이익을 과도하게 선호하면 최근 극단적 급등을 경험한 종목에 "
        "수요가 몰려 가격이 펀더멘털보다 높아질 수 있다. 이 복권형 수요가 되돌려질 때 높은 과거 "
        "최대수익률은 낮은 미래 횡단면 수익률로 이어질 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "극단 수익의 비대칭을 측정하는 return_skewness_24m와 양의 관계, 변동성 계열과 양의 관계가 "
        "예상된다. 다만 분포 전체가 아니라 단 하나의 최대 월수익만 사용하므로 완전한 중복은 아닐 "
        "것으로 예상한다."
    ),
    "data_notes": (
        "Silver PIT 분할조정 가격 adj_close로 월 가격수익률을 계산한다. 최근 12개월 중 최소 "
        "9개월이 있을 때 최대값을 사용한다. 일중 최대수익률이 아니라 월 단위 근사이며, 극단값을 "
        "사후 절단하거나 윈도 길이를 바꾸지 않는다."
    ),
}
