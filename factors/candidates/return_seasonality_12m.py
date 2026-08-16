"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 13
SEASONAL_LAG = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["adj_close"].shift(1)
    prior_month = grouped["ym"].shift(1)
    monthly = (ordered["adj_close"] / prior.where(prior > 0) - 1.0).where(
        ordered["ym"].eq(prior_month + 1)
    )
    seasonal = monthly.groupby(ordered["asset_id"], sort=False).shift(SEASONAL_LAG)
    seasonal_month = grouped["ym"].shift(SEASONAL_LAG)
    return seasonal.where(
        ordered["ym"].eq(seasonal_month + SEASONAL_LAG)
    ).reindex(frame.index)


FACTOR = Factor(
    name='return_seasonality_12m',
    family='return_seasonality_12m',
    category='momentum',
    exploration_domain='momentum_trend_reversal',
    hypothesis='같은 달의 12개월 전 월수익이 높은 종목은 반복되는 계절적 수요와 정보주기로 이후 상대수익이 높다.',
    predicted_sign=1,
    params={'lookback_months': LOOKBACK_MONTHS, 'seasonal_lag': SEASONAL_LAG},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '같은 달의 12개월 전 월수익이 높은 종목은 반복되는 계절적 수요와 정보주기로 이후 상대수익이 높다.',
    "mechanism": '연속 추세가 아니라 직전 연도의 동일 달력월 수익만 사용해 기업고유 계절성을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '일반 모멘텀과 입력은 공유하지만 불연속적인 12개월 시차의 한 달 수익만 사용해 구분한다.',
    "data_notes": 'adj_close로 계산한 과거 동일월 수익만 사용하며 미래 수익률과 OOS 결과를 사용하지 않는다.',
}
