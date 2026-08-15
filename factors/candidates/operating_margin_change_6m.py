"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 6


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    ratio = ordered['operating_income_ttm'] / ordered['revenue_ttm'].where(ordered['revenue_ttm'] != 0)
    prior = ratio.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = ratio - prior
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name='operating_margin_change_6m',
    family='operating_margin_change_6m',
    category='earnings',
    exploration_domain='profitability_quality',
    hypothesis='최근 6개월 operating_income_ttm/revenue_ttm 개선이 큰 기업은 이익의 질과 지속성이 높아 이후 상대수익이 높다.',
    predicted_sign=1,
    params={'lookback_months': LOOKBACK_MONTHS, 'numerator': 'operating_income_ttm', 'denominator': 'revenue_ttm'},
    rebalance_months=3,
    needs=('operating_income_ttm', 'revenue_ttm'),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '최근 6개월 operating_income_ttm/revenue_ttm 개선이 큰 기업은 이익의 질과 지속성이 높아 이후 상대수익이 높다.',
    "mechanism": '수익성 수준이 아니라 동일 PIT 비율의 개선을 측정해 기존 Gold 수준 신호와 구분한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '관련 수익성 수준 신호와 일부 관계가 예상되지만 변화율은 별도 메커니즘이다.',
    "data_notes": 'DART available_date PIT 값과 정확한 달력 시차, 0이 아닌 분모만 사용한다.',
}
