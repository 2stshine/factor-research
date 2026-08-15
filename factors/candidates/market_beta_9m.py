"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 9
MIN_OBSERVATIONS = 6


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort").copy()
    asset = ordered["asset_id"]
    prior_close = ordered["adj_close"].groupby(asset).shift(1)
    prior_month = ordered["ym"].groupby(asset).shift(1)
    prior_market = ordered["market"].groupby(asset).shift(1)
    prior_cap = ordered["market_cap"].groupby(asset).shift(1)
    asset_return = (ordered["adj_close"] / prior_close.where(prior_close > 0) - 1.0).where(
        ordered["ym"].eq(prior_month + 1)
    )
    weight = prior_cap.where(prior_cap > 0)
    valid = asset_return.notna() & weight.notna() & prior_market.notna()
    groups = [ordered["ym"], prior_market]
    weighted = (asset_return * weight).where(valid).groupby(groups).transform("sum")
    total = weight.where(valid).groupby(groups).transform("sum")
    market_return = weighted / total.where(total > 0)
    paired_asset = asset_return.where(market_return.notna())
    paired_market = market_return.where(asset_return.notna())
    product = paired_asset * paired_market
    asset_square = paired_asset.pow(2)
    market_square = paired_market.pow(2)
    rolling_asset = paired_asset.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    rolling_market = paired_market.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    rolling_product = product.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    rolling_asset_square = asset_square.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    rolling_market_square = market_square.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).mean().reset_index(level=0, drop=True)
    covariance = rolling_product - rolling_asset * rolling_market
    asset_variance = rolling_asset_square - rolling_asset.pow(2)
    market_variance = rolling_market_square - rolling_market.pow(2)
    value = covariance / market_variance.where(market_variance > 0)
    oldest_month = ordered["ym"].groupby(asset).shift(WINDOW_MONTHS)
    exact = ordered["ym"].eq(oldest_month + WINDOW_MONTHS)
    return value.where(exact).reindex(frame.index)


FACTOR = Factor(
    name='market_beta_9m',
    family='market_beta_9m',
    category='quality',
    exploration_domain='low_risk',
    hypothesis='최근 9개월 beta가 낮은 종목은 고위험 선호에 따른 과대가격을 피하여 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'window_months': WINDOW_MONTHS, 'min_observations': MIN_OBSERVATIONS, 'risk_measure': 'beta', 'benchmark': 'lagged_market_cap_weighted'},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '최근 9개월 beta가 낮은 종목은 고위험 선호에 따른 과대가격을 피하여 이후 상대수익이 높다.',
    "mechanism": '전월 시가총액 가중 시장수익과의 공분산 구조를 사용해 총변동성과 다른 시장위험을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '기존 24개월 고유변동성과 관련되지만 시장 공통성분의 민감도 또는 상관을 직접 측정한다.',
    "data_notes": 'adj_close, 전월 market·market_cap으로 내부 PIT 시장 벤치마크를 구성하고 결측을 채우지 않는다.',
}
