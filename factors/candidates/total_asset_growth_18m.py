"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 18


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = ordered['total_assets']
    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name='total_asset_growth_18m',
    family='total_asset_growth_18m',
    category='quality',
    exploration_domain='investment_capital_allocation',
    hypothesis='최근 18개월 total_assets 증가율이 낮은 기업은 과잉투자·자산팽창 위험이 작아 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'lookback_months': LOOKBACK_MONTHS, 'source_field': 'total_assets'},
    rebalance_months=3,
    needs=('total_assets',),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '최근 18개월 total_assets 증가율이 낮은 기업은 과잉투자·자산팽창 위험이 작아 이후 상대수익이 높다.',
    "mechanism": 'PIT 재무규모의 시간 변화를 이용해 경영자의 자본배분과 투자 확대를 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '기존 12개월 자산성장과 관련되지만 기간 또는 영업자산 범위가 다르다.',
    "data_notes": 'DART available_date PIT 값의 정확한 달력 시차와 양의 전기 분모만 사용한다.',
}
