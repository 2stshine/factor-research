"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor





def compute(frame):
    denominator = frame['operating_income_ttm']
    return frame['net_income_ttm'] / denominator.where(denominator != 0)


FACTOR = Factor(
    name='net_to_operating_income_conversion',
    family='net_to_operating_income_conversion',
    category='earnings',
    exploration_domain='profitability_quality',
    hypothesis='PIT net_income_ttm/operating_income_ttm 비율이 높은 기업은 이익의 질과 지속성이 높아 이후 상대수익이 높다.',
    predicted_sign=1,
    params={'numerator': 'net_income_ttm', 'denominator': 'operating_income_ttm'},
    rebalance_months=3,
    needs=('net_income_ttm', 'operating_income_ttm'),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": 'PIT net_income_ttm/operating_income_ttm 비율이 높은 기업은 이익의 질과 지속성이 높아 이후 상대수익이 높다.',
    "mechanism": '서로 다른 포괄·영업·세전 이익 단계의 변환 또는 자본 효율성을 하나의 경제 비율로 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '기존 수익성 신호와 관련될 수 있으나 분자·분모 단계가 다르다.',
    "data_notes": '동일 available_date PIT 재무값과 0이 아닌 분모만 사용한다.',
}
