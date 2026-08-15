"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 6


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    source = ordered["trading_value"] / ordered["market_cap"].where(ordered["market_cap"] > 0)
    prior = source.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_month = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = source / prior.where(prior > 0) - 1.0
    return value.where(ordered["ym"].eq(prior_month + LOOKBACK_MONTHS)).reindex(frame.index)


FACTOR = Factor(
    name='trading_value_turnover_change_6m',
    family='trading_value_turnover_change_6m',
    category='other',
    exploration_domain='liquidity_trading',
    hypothesis='최근 6개월 trading_value_turnover 급증이 작은 종목은 과도한 관심과 투기수요를 피하여 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'lookback_months': LOOKBACK_MONTHS, 'source': 'trading_value_turnover'},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '최근 6개월 trading_value_turnover 급증이 작은 종목은 과도한 관심과 투기수요를 피하여 이후 상대수익이 높다.',
    "mechanism": '거래활동 수준 대신 기업가치 정규화 회전의 변화를 측정해 기존 Gold 유동성 수준과 구분한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '거래활동 수준과 일부 관계가 예상되지만 변화율이므로 0.70 Gold gate를 요구한다.',
    "data_notes": '월말 거래대금·ADV20·시가총액과 정확한 달력 시차만 사용한다.',
}
