"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 6


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    denominator = ordered["market_cap"] + ordered["total_liabilities"]
    ratio = ordered['revenue_ttm'] / denominator.where(denominator > 0)
    prior = ratio.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = ratio - prior
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name='enterprise_sales_yield_change_6m',
    family='enterprise_sales_yield_change_6m',
    category='value',
    exploration_domain='value',
    hypothesis='revenue_ttm 대비 기업가치의 6개월 개선이 큰 기업은 영업규모가 가격에 덜 반영되어 이후 상대수익이 높다.',
    predicted_sign=1,
    params={'lookback_months': LOOKBACK_MONTHS, 'numerator': 'revenue_ttm', 'denominator': 'enterprise_value'},
    rebalance_months=3,
    needs=('revenue_ttm', 'total_liabilities'),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": 'revenue_ttm 대비 기업가치의 6개월 개선이 큰 기업은 영업규모가 가격에 덜 반영되어 이후 상대수익이 높다.',
    "mechanism": '매출과 부채를 포함한 기업가치를 결합해 장부자산/시가총액 변화와 다른 가치 재평가를 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '기존 가치 수준과 관련될 수 있으나 매출/기업가치의 변화로 Gold 0.70 사전검사를 요구한다.',
    "data_notes": 'PIT revenue_ttm·total_liabilities와 동시점 market_cap, 정확한 달력 시차만 사용한다.',
}
