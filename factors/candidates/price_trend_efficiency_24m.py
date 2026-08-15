"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    prior = grouped["adj_close"].shift(WINDOW_MONTHS)
    prior_month = grouped["ym"].shift(WINDOW_MONTHS)
    one_month = ordered["adj_close"] / grouped["adj_close"].shift(1) - 1.0
    absolute_monthly = one_month.where(one_month.gt(0), -one_month)
    path = absolute_monthly.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).mean().reset_index(level=0, drop=True) * WINDOW_MONTHS
    value = (ordered["adj_close"] / prior.where(prior > 0) - 1.0) / path.where(path > 0)
    return value.where(ordered["ym"].eq(prior_month + WINDOW_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name='price_trend_efficiency_24m',
    family='price_trend_efficiency_24m',
    category='momentum',
    exploration_domain='momentum_trend_reversal',
    hypothesis='24개월 가격경로 대비 방향효율이 높은 추세는 이후에도 지속된다.',
    predicted_sign=1,
    params={'window_months': WINDOW_MONTHS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '24개월 가격경로 대비 방향효율이 높은 추세는 이후에도 지속된다.',
    "mechanism": '왕복 잡음이 적은 장기 추세를 분리한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '12개월 효율성과 기간이 다르다.',
    "data_notes": 'adj_close의 연속 24개월 경로만 사용한다.',
}
