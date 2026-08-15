"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = ordered["current_assets"] - ordered["current_liabilities"]
    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_assets = ordered["total_assets"].groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (source - prior) / prior_assets.where(prior_assets > 0)
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name='working_capital_accruals_24m',
    family='working_capital_accruals_24m',
    category='earnings',
    exploration_domain='profitability_quality',
    hypothesis='working_capital_accrual 신호가 낮은 기업은 보고이익의 지속성과 현금전환이 높아 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'lookback_months': LOOKBACK_MONTHS, 'quality_measure': 'working_capital_accrual'},
    rebalance_months=3,
    needs=('current_assets', 'current_liabilities', 'total_assets'),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": 'working_capital_accrual 신호가 낮은 기업은 보고이익의 지속성과 현금전환이 높아 이후 상대수익이 높다.',
    "mechanism": 'PIT 이익·운전자본의 수준 변화 또는 변동성을 이용해 단순 수익성 수준과 다른 이익의 질을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '기존 수익성 또는 자산성장과 일부 관계가 예상되지만 측정 대상이 발생액·안정성이다.',
    "data_notes": 'DART available_date PIT 재무값과 고정 36개월 이하 달력창만 사용한다.',
}
