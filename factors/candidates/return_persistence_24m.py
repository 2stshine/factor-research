"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    monthly = ordered["adj_close"] / grouped["adj_close"].shift(1) - 1.0
    lagged = monthly.groupby(ordered["asset_id"], sort=False).shift(1)
    products = monthly * lagged
    value = products.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).mean().reset_index(level=0, drop=True)
    oldest = grouped["ym"].shift(WINDOW_MONTHS + 1)
    return value.where(ordered["ym"].eq(oldest + WINDOW_MONTHS + 1)).reindex(frame.index)


FACTOR = Factor(
    name='return_persistence_24m',
    family='return_persistence_24m',
    category='momentum',
    exploration_domain='momentum_trend_reversal',
    hypothesis='24개월 인접 월수익 연속성이 높은 종목의 정보 반영이 이후에도 이어진다.',
    predicted_sign=1,
    params={'window_months': WINDOW_MONTHS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '24개월 인접 월수익 연속성이 높은 종목의 정보 반영이 이후에도 이어진다.',
    "mechanism": '월수익 자기공분산으로 추세 지속성을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '12개월 지속성과 기간이 다르다.',
    "data_notes": 'adj_close의 25개월 경로만 사용한다.',
}
