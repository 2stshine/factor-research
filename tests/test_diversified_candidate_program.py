from __future__ import annotations

import numpy as np
import pandas as pd

from engine import research_policy
from scripts import run
from tools.generate_diversified_candidate_program import candidates


def test_diversified_program_is_exactly_ten_valid_ten_factor_batches():
    program = candidates()
    registry = run.load_registry()
    names = {candidate.name for candidate in program}
    existing = [factor for factor in registry if factor.name not in names]

    assert len(program) == 100
    assert len(names) == 100
    for batch in range(10):
        selected = [
            registry[candidate.name]
            for candidate in program[batch * 10:(batch + 1) * 10]
        ]
        artifact = research_policy.candidate_batch_policy(
            selected, existing_factors=existing,
        )
        research_policy.assert_candidate_batch_policy(artifact)
        assert artifact["exploration_domain_count"] == 7


def test_vectorized_market_beta_matches_calendar_reference():
    registry = run.load_registry()
    factor = registry["market_beta_12m"]
    months = pd.period_range("2018-01", periods=30, freq="M")
    rows = []
    for asset in range(40):
        market = "KOSPI" if asset < 20 else "KOSDAQ"
        for month_index, month in enumerate(months):
            rows.append({
                "asset_id": asset,
                "ym": month,
                "market": market,
                "market_cap": float(1_000 + asset * 17 + month_index * 3),
                "adj_close": float(
                    100 + asset * 2 + month_index * (1 + asset % 5)
                    + ((asset * month_index) % 7)
                ),
            })
    frame = pd.DataFrame(rows)
    observed = factor.compute(frame)

    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort").copy()
    asset = ordered["asset_id"]
    prior_close = ordered["adj_close"].groupby(asset).shift(1)
    prior_month = ordered["ym"].groupby(asset).shift(1)
    prior_market = ordered["market"].groupby(asset).shift(1)
    prior_cap = ordered["market_cap"].groupby(asset).shift(1)
    asset_return = (
        ordered["adj_close"] / prior_close.where(prior_close > 0) - 1.0
    ).where(ordered["ym"].eq(prior_month + 1))
    weight = prior_cap.where(prior_cap > 0)
    valid = asset_return.notna() & weight.notna() & prior_market.notna()
    groups = [ordered["ym"], prior_market]
    market_return = (
        (asset_return * weight).where(valid).groupby(groups).transform("sum")
        / weight.where(valid).groupby(groups).transform("sum").where(
            lambda value: value > 0
        )
    )
    ordered["_asset_return"] = asset_return
    ordered["_market_return"] = market_return
    expected = pd.Series(index=ordered.index, dtype=float)
    for _, group in ordered.groupby("asset_id", sort=False):
        calendar = pd.period_range(group["ym"].min(), group["ym"].max(), freq="M")
        local = group.set_index("ym")[["_asset_return", "_market_return"]].reindex(
            calendar
        )
        paired_asset = local["_asset_return"].where(local["_market_return"].notna())
        paired_market = local["_market_return"].where(local["_asset_return"].notna())
        covariance = paired_asset.rolling(12, min_periods=8).cov(paired_market)
        variance = paired_market.rolling(12, min_periods=8).var()
        value = covariance / variance.where(variance > 0)
        expected.loc[group.index] = value.reindex(group["ym"]).to_numpy()
    expected = expected.reindex(frame.index)
    oldest_month = ordered["ym"].groupby(ordered["asset_id"]).shift(12)
    expected = expected.where(ordered["ym"].eq(oldest_month + 12)).reindex(
        frame.index
    )

    assert observed.notna().equals(expected.notna())
    assert np.allclose(
        observed[observed.notna()], expected[expected.notna()],
        rtol=1e-10, atol=1e-12,
    )
