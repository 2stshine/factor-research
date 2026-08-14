"""Pre-registered 24-month idiosyncratic-volatility candidate."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 24
MIN_OBSERVATIONS = 18
BENCHMARK_POLICY = "lagged_market_cap_weighted_by_pit_market"
GAP_POLICY = "calendar_window_no_fill"


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort").copy()
    asset = ordered["asset_id"]
    prior_close = ordered["adj_close"].groupby(asset).shift(1)
    prior_ym = ordered["ym"].groupby(asset).shift(1)
    prior_market = ordered["market"].groupby(asset).shift(1)
    prior_market_cap = ordered["market_cap"].groupby(asset).shift(1)
    asset_return = (ordered["adj_close"] / prior_close - 1).where(
        ordered["ym"].eq(prior_ym + 1) & (prior_close > 0)
    )
    weight = prior_market_cap.where(prior_market_cap > 0)
    valid = asset_return.notna() & weight.notna() & prior_market.notna()
    groups = [ordered["ym"], prior_market]
    weighted_sum = (asset_return * weight).where(valid).groupby(groups).transform("sum")
    total_weight = weight.where(valid).groupby(groups).transform("sum")
    ordered["_asset_return"] = asset_return
    ordered["_market_return"] = weighted_sum / total_weight.where(total_weight > 0)

    output = pd.Series(index=ordered.index, dtype=float)
    for _, group in ordered.groupby("asset_id", sort=False):
        calendar = pd.period_range(group["ym"].min(), group["ym"].max(), freq="M")
        local = group.set_index("ym")[["_asset_return", "_market_return"]].reindex(calendar)
        paired_asset = local["_asset_return"].where(local["_market_return"].notna())
        paired_market = local["_market_return"].where(local["_asset_return"].notna())
        asset_variance = paired_asset.rolling(
            window=WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
        ).var()
        market_variance = paired_market.rolling(
            window=WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
        ).var()
        covariance = paired_asset.rolling(
            window=WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
        ).cov(paired_market)
        residual_variance = asset_variance - covariance.pow(2) / market_variance.where(
            market_variance > 0
        )
        idiosyncratic_volatility = np.sqrt(residual_variance.clip(lower=0))
        output.loc[group.index] = idiosyncratic_volatility.reindex(group["ym"]).to_numpy()
    return output.reindex(frame.index)


FACTOR = Factor(
    name="idiosyncratic_volatility_24m",
    family="idiosyncratic_volatility",
    category="other",
    hypothesis=(
        "최근 24개월 시장수익으로 설명되지 않는 고유변동성이 큰 종목은 복권형 수요와 분산제약으로 "
        "과대평가되고, 고유변동성이 낮은 종목이 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=-1,
    params={
        "window_months": WINDOW_MONTHS,
        "min_observations": MIN_OBSERVATIONS,
        "benchmark_policy": BENCHMARK_POLICY,
        "gap_policy": GAP_POLICY,
    },
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT 분할조정 가격의 최근 24개월 월수익률에서 동월 시장수익으로 설명되지 않는 "
        "잔차변동성이 낮은 종목은 높은 종목보다 다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "분산되지 않은 투자자와 복권형 상승을 선호하는 투자자가 고유위험이 큰 종목에 높은 가격을 "
        "지불하면 그 종목의 기대수익률이 낮아질 수 있다. 시장 공통위험을 제거한 잔차분산은 이 "
        "수요를 총변동성과 분리해 측정한다."
    ),
    "falsification": (
        "사전등록한 음의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하거나 기존 저변동성 신호와 중복되면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: realized_volatility_252d — 차이: 총 일별 변동성이 아니라 PIT "
        "시장별 월수익 요인을 제거한 24개월 고유변동성만 측정한다. market_beta_36m은 공분산의 "
        "기울기를 측정하므로 잔차분산과 다르다."
    ),
    "data_notes": (
        "Silver PIT adj_close로 연속 월 가격수익률을 만들고 전월 market과 전월 market_cap으로 "
        "KOSPI·KOSDAQ별 동월 가치가중 수익률을 구성한다. 24개월 달력창에서 최소 18개 동일월 "
        "관측을 요구하고 결측을 채우지 않는다. 공식 지수나 일별 잔차변동성이 아니라 월별 내부 "
        "벤치마크를 사용한다는 한계가 있다."
    ),
}
