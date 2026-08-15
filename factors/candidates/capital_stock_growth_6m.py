"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 6


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = ordered["capital_stock"]
    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name='capital_stock_growth_6m',
    family='capital_stock_growth_6m',
    category='other',
    exploration_domain='financing_issuance',
    hypothesis='최근 6개월 capital_stock 확대가 큰 기업은 외부자금 수요나 고평가 활용 가능성이 높아 이후 상대수익이 낮다.',
    predicted_sign=-1,
    params={'lookback_months': LOOKBACK_MONTHS, 'financing_measure': 'capital_stock'},
    rebalance_months=3,
    needs=('capital_stock',),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '최근 6개월 capital_stock 확대가 큰 기업은 외부자금 수요나 고평가 활용 가능성이 높아 이후 상대수익이 낮다.',
    "mechanism": '발행·부채조달·자본금 변화 중 하나를 PIT 시점에서 분리하여 경영자의 자금조달 결정을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '자산성장과 일부 관계가 예상되지만 조달 측면만 측정한다.',
    "data_notes": '정확한 달력 시차와 양의 분모만 사용하며 기업행사 후행 라벨은 사용하지 않는다.',
}
