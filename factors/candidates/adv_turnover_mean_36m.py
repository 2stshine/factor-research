"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 36
MIN_OBSERVATIONS = 27


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    source = ordered["adv20"] / ordered["market_cap"].where(ordered["market_cap"] > 0)
    value = source.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    return value.reindex(frame.index)


FACTOR = Factor(
    name='adv_turnover_mean_36m',
    family='adv_turnover_mean_36m',
    category='other',
    exploration_domain='liquidity_trading',
    hypothesis='최근 36개월 ADV20/시가총액 거래회전의 mean가 낮은 종목은 유동성 보상 또는 과도한 관심 교정으로 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'window_months': WINDOW_MONTHS, 'min_observations': MIN_OBSERVATIONS, 'source': 'adv_turnover', 'reducer': 'mean'},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '최근 36개월 ADV20/시가총액 거래회전의 mean가 낮은 종목은 유동성 보상 또는 과도한 관심 교정으로 이후 상대수익이 높다.',
    "mechanism": '거래 규모를 기업가치로 정규화하거나 가격충격을 직접 측정해 단순 대형주 노출과 구분한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '기존 유동성 수준·변화 신호와 관련될 수 있어 Gold 상관 gate로 독립성을 확인한다.',
    "data_notes": '인증된 월말 거래·시가총액·Amihud 입력만 사용하며 결측을 채우지 않는다.',
}
