"""Unit contracts for the newly added common single-signal candidates."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factors.candidates import amihud_illiquidity_1m
from factors.candidates import dividend_yield_ttm
from factors.candidates import high_52w_price_proximity
from factors.candidates import max_daily_return_1m
from factors.candidates import net_equity_issuance_price_adjusted_12m
from factors.candidates import realized_volatility_252d


@pytest.mark.parametrize(
    ("module", "predicted_sign", "needs"),
    [
        (amihud_illiquidity_1m, 1, ()),
        (dividend_yield_ttm, 1, ("dividend_cash_ttm",)),
        (high_52w_price_proximity, 1, ()),
        (max_daily_return_1m, -1, ()),
        (net_equity_issuance_price_adjusted_12m, -1, ()),
        (realized_volatility_252d, -1, ()),
    ],
)
def test_factor_direction_and_declared_input_contract(
    module, predicted_sign: int, needs: tuple[str, ...],
):
    factor = module.FACTOR

    assert factor.predicted_sign == predicted_sign
    assert factor.needs == needs
    assert factor.composite_evidence() == []
    assert factor.undeclared_constants() == []


def test_amihud_illiquidity_keeps_raw_value_at_minimum_observation_count():
    frame = pd.DataFrame(
        {
            "amihud_illiquidity_1m": [1.25e-12, 2.50e-12, np.nan],
            "amihud_observations_1m": [10, 9, 20],
        },
        index=[17, 3, 91],
    )

    result = amihud_illiquidity_1m.compute(frame)
    expected = pd.Series([1.25e-12, np.nan, np.nan], index=frame.index)

    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_realized_volatility_keeps_raw_value_at_minimum_observation_count():
    frame = pd.DataFrame(
        {
            "daily_volatility_252d": [0.018, 0.031, np.nan],
            "daily_return_observations_252d": [126, 125, 252],
        },
        index=[8, 5, 2],
    )

    result = realized_volatility_252d.compute(frame)
    expected = pd.Series([0.018, np.nan, np.nan], index=frame.index)

    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_max_daily_return_keeps_raw_value_at_minimum_observation_count():
    frame = pd.DataFrame(
        {
            "max_daily_return_1m": [0.071, -0.012, np.nan],
            "max_daily_return_observations_1m": [10, 9, 20],
        },
        index=[44, 11, 27],
    )

    result = max_daily_return_1m.compute(frame)
    expected = pd.Series([0.071, np.nan, np.nan], index=frame.index)

    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_52_week_high_proximity_uses_split_adjusted_price_and_valid_history():
    frame = pd.DataFrame(
        {
            "adj_close": [90.0, 90.0, 0.0, 100.0, 100.0],
            "price_high_252d": [100.0, 100.0, 100.0, 0.0, -100.0],
            "price_high_observations_252d": [200, 199, 252, 252, 252],
        },
        index=[50, 10, 40, 20, 30],
    )

    result = high_52w_price_proximity.compute(frame)
    expected = pd.Series([0.9, np.nan, np.nan, np.nan, np.nan], index=frame.index)

    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_dividend_yield_is_trailing_cash_per_split_adjusted_price():
    frame = pd.DataFrame(
        {
            "adj_close": [100.0, 50.0, 0.0, -20.0, 100.0, np.nan],
            "dividend_cash_ttm": [5.0, 0.0, 5.0, 5.0, -1.0, 5.0],
        },
        index=[6, 1, 5, 2, 4, 3],
    )

    result = dividend_yield_ttm.compute(frame)
    expected = pd.Series([0.05, 0.0, np.nan, np.nan, np.nan, np.nan], index=frame.index)

    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_net_equity_issuance_uses_exact_12_month_price_adjusted_share_growth():
    rows: list[dict] = []

    # Asset 1 has an exact 12-month comparison.  Market cap grows 150%, but the
    # split-adjusted share base only grows from 100 to 125, so issuance is 25%.
    for offset, ym in enumerate(pd.period_range("2022-01", "2023-01", freq="M")):
        price = 10.0 if offset < 12 else 20.0
        share_base = 100.0 if offset < 12 else 125.0
        rows.append({
            "asset_id": 1,
            "ym": ym,
            "market_cap": price * share_base,
            "adj_close": price,
        })

    # Asset 2 has 13 rows, but its last row is 13 calendar months after the
    # first.  A row-count shift must not turn that gap into a 12-month signal.
    gapped_months = list(pd.period_range("2022-01", "2022-12", freq="M"))
    gapped_months.append(pd.Period("2023-02", freq="M"))
    for offset, ym in enumerate(gapped_months):
        share_base = 200.0 if offset < 12 else 300.0
        rows.append({
            "asset_id": 2,
            "ym": ym,
            "market_cap": 10.0 * share_base,
            "adj_close": 10.0,
        })

    # Asset 3 has an invalid prior split-adjusted price, so its base cannot be
    # used as a denominator even though the calendar months are consecutive.
    for offset, ym in enumerate(pd.period_range("2022-01", "2023-01", freq="M")):
        rows.append({
            "asset_id": 3,
            "ym": ym,
            "market_cap": 1_000.0,
            "adj_close": 0.0 if offset == 0 else 10.0,
        })

    ordered = pd.DataFrame(rows)
    ordered.index = pd.Index(range(1000, 1000 + len(ordered)), name="source_row")
    frame = ordered.sample(frac=1.0, random_state=20260808)
    target_index = frame.index[
        (frame["asset_id"] == 1) & (frame["ym"] == pd.Period("2023-01", freq="M"))
    ].item()
    gapped_index = frame.index[
        (frame["asset_id"] == 2) & (frame["ym"] == pd.Period("2023-02", freq="M"))
    ].item()
    invalid_prior_index = frame.index[
        (frame["asset_id"] == 3) & (frame["ym"] == pd.Period("2023-01", freq="M"))
    ].item()

    result = net_equity_issuance_price_adjusted_12m.compute(frame)

    assert result.index.equals(frame.index)
    assert result.loc[target_index] == pytest.approx(0.25)
    assert pd.isna(result.loc[gapped_index])
    assert pd.isna(result.loc[invalid_prior_index])
    assert result.notna().sum() == 1
