"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 6


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    ratio = ordered['pretax_income_ttm'] / ordered["market_cap"].where(ordered["market_cap"] > 0)
    prior = ratio.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = ratio - prior
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name='pretax_yield_change_6m',
    family='pretax_yield_change_6m',
    category='value',
    exploration_domain='value',
    hypothesis='pretax_income_ttm 대비 시장가치의 6개월 개선이 큰 기업은 펀더멘털 대비 가격이 덜 반영되어 이후 상대수익이 높다.',
    predicted_sign=1,
    params={'lookback_months': LOOKBACK_MONTHS, 'numerator': 'pretax_income_ttm', 'denominator': 'market_cap'},
    rebalance_months=3,
    needs=('pretax_income_ttm',),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": 'pretax_income_ttm 대비 시장가치의 6개월 개선이 큰 기업은 펀더멘털 대비 가격이 덜 반영되어 이후 상대수익이 높다.',
    "mechanism": '가치비율의 현재 수준 대신 사전 고정 기간의 개선을 측정해 기존 Gold 가치 수준 신호와 구분한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '가치 수준과 관련될 수 있으나 변화율이므로 Gold 0.70 사전검사를 요구한다.',
    "data_notes": 'PIT 재무 분자와 동시점 양의 market_cap 또는 enterprise value, 정확한 달력 시차만 사용한다.',
}
