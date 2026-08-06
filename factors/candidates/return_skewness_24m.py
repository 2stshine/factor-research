"""Pre-registered 24-month return-skewness candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


WINDOW_MONTHS = 24
MIN_OBSERVATIONS = 18


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    monthly_return = ordered.groupby("asset_id")["return_close"].pct_change(fill_method=None)
    skewness = monthly_return.groupby(ordered["asset_id"]).transform(
        lambda values: values.rolling(
            window=WINDOW_MONTHS,
            min_periods=MIN_OBSERVATIONS,
        ).skew()
    )
    return skewness.reindex(frame.index)


FACTOR = Factor(
    name="return_skewness_24m",
    family="return_skewness",
    category="other",
    hypothesis=(
        "최근 24개월 수익률 분포의 양의 왜도가 큰 복권형 종목은 극단적 상승 가능성을 선호하는 "
        "투자자에게 과대평가되고, 왜도가 낮은 종목이 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=-1,
    params={"window_months": WINDOW_MONTHS, "min_observations": MIN_OBSERVATIONS},
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT 총수익지수로 계산한 최근 24개월 월수익률 왜도가 낮은 종목은 양의 왜도가 큰 "
        "종목보다 이후 수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "일부 투자자는 낮은 확률의 큰 상승을 제공하는 복권형 주식에 높은 가격을 지불할 수 있다. "
        "과거 수익률 분포의 큰 양의 꼬리는 이러한 선호의 관측 가능한 대리변수이며, 과대수요가 "
        "미래 기대수익률을 낮출 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "양의 왜도 종목이 고변동인 경우가 많아 low_vol_12m 및 downside_vol_12m과 양의 관계를 "
        "예상한다. 그러나 분산이 아니라 분포의 비대칭을 측정하므로 완전한 중복은 아니며, 회계 "
        "품질·가치 팩터와의 관계는 낮을 것으로 예상한다."
    ),
    "data_notes": (
        "Silver total_return_close에 매핑된 return_close로 월수익률을 계산한다. 24개월 창에서 최소 "
        "18개 관측을 사전 고정하며, 이력이 부족하거나 수익률 분산이 없어 왜도가 정의되지 않는 "
        "관측은 결측으로 둔다. 일별 왜도가 아닌 월별 왜도라는 한계가 있다."
    ),
}
