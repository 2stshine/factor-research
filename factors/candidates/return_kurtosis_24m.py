"""Pre-registered return-tail concentration candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


WINDOW_MONTHS = 24
MIN_OBSERVATIONS = 18


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    monthly_return = ordered.groupby("asset_id")["adj_close"].pct_change(
        fill_method=None
    )
    kurtosis = monthly_return.groupby(asset).transform(
        lambda values: values.rolling(
            WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
        ).kurt()
    )
    first_ym = ordered["ym"].groupby(asset).shift(WINDOW_MONTHS - 1)
    consecutive = ordered["ym"].eq(first_ym + WINDOW_MONTHS - 1)
    return kurtosis.where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="return_kurtosis_24m",
    family="return_tail_concentration",
    category="other",
    hypothesis=(
        "최근 24개월 수익률의 꼬리 집중도가 큰 종목은 극단 수익을 선호하는 수요와 사건위험이 "
        "가격에 과도하게 반영되어 이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    params={
        "window_months": WINDOW_MONTHS,
        "min_observations": MIN_OBSERVATIONS,
    },
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver 분할조정 가격으로 계산한 최근 24개월 월 가격수익률 초과첨도가 낮은 종목은 높은 종목보다 "
        "다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "극단 수익이 자주 나타나는 종목은 복권형 상승 가능성에 대한 과잉수요나 집중된 사건위험을 "
        "포함할 수 있다. 이런 수요가 가격을 높이면 높은 꼬리 집중도의 미래 기대수익이 낮아진다."
    ),
    "falsification": (
        "사전등록한 음의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "return_skewness_24m, max_monthly_return_12m 및 변동성 계열과 일부 관계가 가능하지만, "
        "방향이나 분산이 아니라 분포 양쪽 꼬리의 집중도를 측정한다."
    ),
    "data_notes": (
        "Silver PIT 분할조정 가격 adj_close로 월 가격수익률을 계산한다. 연속 24개월 창에서 최소 18개 유효 "
        "관측을 요구하며 분산이 없어 첨도가 정의되지 않으면 결측으로 둔다."
    ),
}
