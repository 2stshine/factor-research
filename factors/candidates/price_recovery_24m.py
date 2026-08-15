"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    anchor = grouped["adj_close"].rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).min().reset_index(level=0, drop=True)
    oldest = grouped["ym"].shift(WINDOW_MONTHS - 1)
    value = ordered["adj_close"] / anchor.where(anchor > 0) - 1.0
    return value.where(ordered["ym"].eq(oldest + WINDOW_MONTHS - 1)).reindex(frame.index)


FACTOR = Factor(
    name='price_recovery_24m',
    family='price_recovery_24m',
    category='momentum',
    exploration_domain='momentum_trend_reversal',
    hypothesis='24개월 저점에서 크게 회복한 종목의 개선이 이후에도 이어진다.',
    predicted_sign=1,
    params={'window_months': WINDOW_MONTHS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '24개월 저점에서 크게 회복한 종목의 개선이 이후에도 이어진다.',
    "mechanism": '장기 악재 해소의 지연반영을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '12개월 회복과 기간이 다르다.',
    "data_notes": 'adj_close 24개월 창만 사용한다.',
}
