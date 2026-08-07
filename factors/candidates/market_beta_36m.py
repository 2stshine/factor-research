"""Pre-registered 36-month market-beta candidate; do not edit after evaluation."""
from __future__ import annotations

import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 36
MIN_OBSERVATIONS = 24
BENCHMARK_POLICY = "lagged_market_cap_weighted_by_pit_market"
GAP_POLICY = "calendar_window_no_fill"


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort").copy()
    asset = ordered["asset_id"]
    prior_close = ordered["return_close"].groupby(asset).shift(1)
    prior_ym = ordered["ym"].groupby(asset).shift(1)
    prior_market = ordered["market"].groupby(asset).shift(1)
    prior_market_cap = ordered["market_cap"].groupby(asset).shift(1)
    asset_return = (ordered["return_close"] / prior_close - 1).where(
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
        paired_market = local["_market_return"].where(local["_asset_return"].notna())
        covariance = local["_asset_return"].rolling(
            window=WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
        ).cov(paired_market)
        market_variance = paired_market.rolling(
            window=WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
        ).var()
        beta = covariance / market_variance.where(market_variance > 0)
        output.loc[group.index] = beta.reindex(group["ym"]).to_numpy()
    return output.reindex(frame.index)


FACTOR = Factor(
    name="market_beta_36m",
    family="market_beta",
    category="other",
    hypothesis=(
        "레버리지·벤치마크 제약이 있는 투자자의 고베타 종목 선호로 고베타 주식이 상대적으로 "
        "고평가되고, 시장 민감도가 낮은 종목은 이후 더 높은 횡단면 수익을 낸다."
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
        "최근 36개월 시장 베타가 낮은 종목은 높은 종목보다 이후 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "일부 투자자는 직접 레버리지를 쓰는 대신 고베타 주식으로 목표 수익을 추구한다. 이 수요가 "
        "고베타 종목 가격을 높이면 저베타 종목은 상대적으로 낮게 평가되어 이후 더 높은 수익을 "
        "제공할 수 있다."
    ),
    "falsification": (
        "저베타 방향이 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성을 통과하지 못하거나 "
        "기존 저변동성 신호와 중복되면 독립적인 시장민감도 가설을 기각한다. campaign BY 또는 "
        "봉인 OOS confirmation 실패도 최종 기각으로 본다."
    ),
    "expected_relationship": (
        "low_vol_12m과 downside_vol_12m의 저위험 방향과 양의 관계가 예상되지만, 총변동성이 아니라 "
        "시장 공분산만 측정하므로 완전 중복은 아닐 것으로 예상한다. 회계 가치·수익성과의 관계는 "
        "제한적일 것으로 예상한다."
    ),
    "data_notes": (
        "Silver total_return_close로 연속 월 수익률을 만들고, 전월 PIT 시장구분과 전월 시가총액으로 "
        "각 월 KOSPI·KOSDAQ 수익률을 구성한다. 공식 지수수익률이 아니며 자기 종목 포함, "
        "비동시거래와 시장 이전의 영향을 받는다. 36개월 달력창에서 최소 24개 동일월 쌍이 있을 "
        "때만 계산하고 결측을 채우거나 내부 표본선택·중립화를 하지 않는다."
    ),
}
