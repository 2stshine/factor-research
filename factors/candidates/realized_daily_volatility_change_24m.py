"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = ordered['daily_volatility_252d']
    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name='realized_daily_volatility_change_24m',
    family='realized_daily_volatility_change_24m',
    category='quality',
    exploration_domain='low_risk',
    hypothesis='최근 24개월 daily_volatility_252d 악화가 작은 종목은 위험수요의 과대가격을 피하여 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'lookback_months': LOOKBACK_MONTHS, 'source_field': 'daily_volatility_252d'},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '최근 24개월 daily_volatility_252d 악화가 작은 종목은 위험수요의 과대가격을 피하여 이후 상대수익이 높다.',
    "mechanism": '위험 수준이 아니라 사전 고정 기간의 변화를 측정해 기존 Gold 저위험 수준 신호와 구분한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '저위험 수준과 관련될 수 있으나 변화율이므로 Gold 0.70 사전검사를 요구한다.',
    "data_notes": 'Silver 월말 위험 요약과 정확한 달력 시차만 사용한다.',
}
