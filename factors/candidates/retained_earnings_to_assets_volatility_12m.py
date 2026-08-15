"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 12
MIN_OBSERVATIONS = 9


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    ratio = ordered['retained_earnings'] / ordered['total_assets'].where(ordered['total_assets'] != 0)
    value = ratio.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).std().reset_index(level=0, drop=True)
    return value.reindex(frame.index)


FACTOR = Factor(
    name='retained_earnings_to_assets_volatility_12m',
    family='retained_earnings_to_assets_volatility_12m',
    category='earnings',
    exploration_domain='profitability_quality',
    hypothesis='최근 12개월 retained_earnings/total_assets 변동성이 낮은 기업은 이익의 질이 높아 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'window_months': WINDOW_MONTHS, 'min_observations': MIN_OBSERVATIONS, 'numerator': 'retained_earnings', 'denominator': 'total_assets'},
    rebalance_months=3,
    needs=('retained_earnings', 'total_assets'),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '최근 12개월 retained_earnings/total_assets 변동성이 낮은 기업은 이익의 질이 높아 이후 상대수익이 높다.',
    "mechanism": 'PIT 누적이익 비율의 안정성을 측정해 단일 시점 수익성 수준과 구분한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '수익성·자본축적 수준과 관련될 수 있으나 시계열 안정성은 별도 메커니즘이다.',
    "data_notes": 'DART available_date PIT 비율의 고정 달력창만 사용한다.',
}
