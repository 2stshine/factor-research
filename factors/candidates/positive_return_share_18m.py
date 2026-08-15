"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 18


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
    name='positive_return_share_18m',
    family='positive_return_share_18m',
    category='momentum',
    exploration_domain='momentum_trend_reversal',
    hypothesis='18개월 상승월 비중이 높은 종목의 폭넓은 추세가 이후에도 지속된다.',
    predicted_sign=1,
    params={'window_months': WINDOW_MONTHS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '18개월 상승월 비중이 높은 종목의 폭넓은 추세가 이후에도 지속된다.',
    "mechanism": '누적수익보다 상승 참여 폭을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '12·24개월 비중과 기간이 다르다.',
    "data_notes": '연속 월 adj_close만 사용한다.',
}
