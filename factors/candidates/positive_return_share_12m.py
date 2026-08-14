"""Pre-registered return-consistency candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


WINDOW_MONTHS = 12
MIN_OBSERVATIONS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    monthly_return = ordered.groupby("asset_id")["adj_close"].pct_change(
        fill_method=None
    )
    positive = monthly_return.gt(0).where(monthly_return.notna()).astype(float)
    share = positive.groupby(asset).transform(
        lambda values: values.rolling(
            WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
        ).mean()
    )
    first_ym = ordered["ym"].groupby(asset).shift(WINDOW_MONTHS - 1)
    consecutive = ordered["ym"].eq(first_ym + WINDOW_MONTHS - 1)
    return share.where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="positive_return_share_12m",
    family="return_consistency",
    category="momentum",
    hypothesis=(
        "최근 12개월 중 상승한 달의 비중이 높은 종목은 정보가 여러 달에 걸쳐 안정적으로 "
        "반영되는 추세를 보여 이후에도 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
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
        "Silver 분할조정 가격으로 계산한 최근 12개월 양의 월 가격수익 비중이 높은 종목은 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "한 번의 급등보다 반복적인 양의 월수익은 긍정적 정보의 점진적 가격 반영과 추세의 "
        "폭을 나타낼 수 있다. 투자자의 과소반응이 지속되면 상승의 일관성이 미래수익을 예측한다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "mom_12_1 및 high_12m_proximity와 양의 관계가 가능하지만 시작·종점 수익률이나 고점 "
        "거리가 아니라 상승한 월의 비중만 측정하므로 정의상 다르다."
    ),
    "data_notes": (
        "Silver PIT 분할조정 가격 adj_close로 월 가격수익률을 계산한다. 정확히 연속된 "
        "12개월 모두가 있을 때만 정의하며 최초 12개월은 결측이다."
    ),
}
