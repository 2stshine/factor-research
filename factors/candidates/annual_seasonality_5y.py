"""Pre-registered five-year annual return seasonality candidate."""
from __future__ import annotations

import pandas as pd

from engine.factors import Factor


MONTHS_PER_YEAR = 12
HISTORY_YEARS = 5
MIN_YEARS = 3


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    monthly_return = ordered.groupby("asset_id")["return_close"].pct_change(fill_method=None)
    seasonal_returns = [
        monthly_return.groupby(asset).shift(MONTHS_PER_YEAR * year)
        for year in range(1, HISTORY_YEARS + 1)
    ]
    history = pd.concat(seasonal_returns, axis=1)
    signal = history.mean(axis=1).where(history.count(axis=1) >= MIN_YEARS)
    return signal.reindex(frame.index)


FACTOR = Factor(
    name="annual_seasonality_5y",
    family="return_seasonality",
    category="momentum",
    hypothesis=(
        "개별 종목의 같은 달 수익률에는 반복되는 정보공시·수급·사업 계절성이 남아 있어, 최근 "
        "5년의 동일 월 평균수익률이 높은 종목이 해당 월 이후에도 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={
        "months_per_year": MONTHS_PER_YEAR,
        "history_years": HISTORY_YEARS,
        "min_years": MIN_YEARS,
    },
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT 총수익지수로 계산한 과거 1~5년 동일 월 수익률의 평균이 높은 종목은 낮은 "
        "종목보다 이후 한 달 수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "정기 공시, 배당·주주총회 일정, 업종별 수요와 기관 리밸런싱이 매년 비슷한 달에 반복되면 "
        "종목별 수익률에도 달력 기반 지속성이 생길 수 있다. 시장이 이 반복 패턴을 완전히 "
        "차익거래하지 못하면 과거 동일 월 성과가 다음 동일 월을 예측할 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "현재와 가까운 수익률을 쓰지 않으므로 mom_12_1·rev_1m과 낮은 관계를 예상한다. 회계 "
        "입력을 사용하지 않아 품질·가치 팩터와도 독립적일 것으로 예상한다."
    ),
    "data_notes": (
        "Silver total_return_close에 매핑된 return_close로 월수익률을 계산하고 12·24·36·48·60개월 "
        "전 동일 월 관측 중 최소 3개를 사용한다. 상장 이력이 짧은 종목은 결측이며, 거래일 수와 "
        "정확한 공시일을 직접 모델링하지 않는 월 단위 근사치다."
    ),
}
