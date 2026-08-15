"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["adj_close"].shift(1)
    prior_month = grouped["ym"].shift(1)
    monthly = (ordered["adj_close"] / prior.where(prior > 0) - 1.0).where(
        ordered["ym"].eq(prior_month + 1)
    )
    positive = monthly.gt(0).astype(float).where(monthly.notna())
    value = positive.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).mean().reset_index(level=0, drop=True)
    return value.reindex(frame.index)


FACTOR = Factor(
    name='positive_return_share_24m',
    family='positive_return_share_24m',
    category='momentum',
    exploration_domain='momentum_trend_reversal',
    hypothesis='24개월 상승월 비중이 높은 종목은 넓은 추세 참여로 이후 상대수익이 높다.',
    predicted_sign=1,
    params={'window_months': WINDOW_MONTHS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '24개월 상승월 비중이 높은 종목은 넓은 추세 참여로 이후 상대수익이 높다.',
    "mechanism": '소수 급등월이 아닌 추세의 폭을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '12개월 상승월 비중과 기간이 다르다.',
    "data_notes": '연속 월 adj_close 수익률만 사용한다.',
}
