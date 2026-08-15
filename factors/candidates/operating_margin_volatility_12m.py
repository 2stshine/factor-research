"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 12
MIN_OBSERVATIONS = 9


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = ordered['operating_income_ttm'] / ordered["revenue_ttm"].where(ordered["revenue_ttm"] != 0)
    value = source.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).std().reset_index(level=0, drop=True)
    return value.reindex(frame.index)


FACTOR = Factor(
    name='operating_margin_volatility_12m',
    family='operating_margin_volatility_12m',
    category='earnings',
    exploration_domain='profitability_quality',
    hypothesis='operating_margin_volatility 신호가 낮은 기업은 보고이익의 지속성과 현금전환이 높아 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'window_months': WINDOW_MONTHS, 'min_observations': MIN_OBSERVATIONS, 'quality_measure': 'operating_margin_volatility'},
    rebalance_months=3,
    needs=('operating_income_ttm', 'revenue_ttm'),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": 'operating_margin_volatility 신호가 낮은 기업은 보고이익의 지속성과 현금전환이 높아 이후 상대수익이 높다.',
    "mechanism": 'PIT 이익·운전자본의 수준 변화 또는 변동성을 이용해 단순 수익성 수준과 다른 이익의 질을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '기존 수익성 또는 자산성장과 일부 관계가 예상되지만 측정 대상이 발생액·안정성이다.',
    "data_notes": 'DART available_date PIT 재무값과 고정 36개월 이하 달력창만 사용한다.',
}
