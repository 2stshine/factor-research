"""Unit contracts for the pre-registered common-factor candidates."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factors.candidates import intermediate_momentum_12_7
from factors.candidates import market_leverage


@pytest.mark.parametrize(
    ("module", "predicted_sign", "needs"),
    [
        (intermediate_momentum_12_7, 1, ()),
        (market_leverage, 1, ("total_liabilities",)),
    ],
)
def test_direction_and_single_signal_contract(module, predicted_sign, needs):
    factor = module.FACTOR

    assert factor.predicted_sign == predicted_sign
    assert factor.needs == needs
    assert factor.composite_evidence() == []
    assert factor.undeclared_constants() == []


def _monthly_price_frame(*, missing_month=None):
    months = pd.period_range("2020-01", "2021-03", freq="M")
    if missing_month is not None:
        months = months[months != pd.Period(missing_month, freq="M")]
    prices = pd.Series(
        [100.0 * (1.0 + 0.01) ** offset for offset in range(len(months))]
    )
    return pd.DataFrame(
        {
            "asset_id": ["A"] * len(months),
            "ym": months,
            "return_close": prices.to_numpy(),
        },
        index=np.arange(len(months))[::-1] + 10,
    )


def test_intermediate_momentum_uses_exact_six_returns_twelve_to_seven():
    frame = _monthly_price_frame()

    result = intermediate_momentum_12_7.compute(frame)
    target_index = frame.index[frame["ym"].eq(pd.Period("2021-02", freq="M"))][0]

    assert result.index.equals(frame.index)
    assert result.loc[target_index] == pytest.approx((1.0 + 0.01) ** 6 - 1.0)


def test_intermediate_momentum_does_not_fill_missing_calendar_month():
    frame = _monthly_price_frame(missing_month="2020-08")

    result = intermediate_momentum_12_7.compute(frame)
    target_index = frame.index[frame["ym"].eq(pd.Period("2021-02", freq="M"))][0]

    assert np.isnan(result.loc[target_index])


def test_intermediate_momentum_is_order_and_index_safe():
    frame = pd.concat(
        [
            _monthly_price_frame().assign(asset_id="A"),
            _monthly_price_frame().assign(asset_id="B", return_close=lambda d: d["return_close"] * 2),
        ]
    )
    frame.index = np.arange(len(frame)) * 3 + 5
    shuffled = frame.sample(frac=1.0, random_state=7)

    expected = intermediate_momentum_12_7.compute(frame)
    actual = intermediate_momentum_12_7.compute(shuffled).reindex(frame.index)

    pd.testing.assert_series_equal(actual, expected)


def test_market_leverage_keeps_zero_debt_and_guards_invalid_values():
    frame = pd.DataFrame(
        {
            "total_liabilities": [50.0, 0.0, -1.0, 20.0, np.nan],
            "market_cap": [100.0, 80.0, 50.0, 0.0, 40.0],
        },
        index=[8, 2, 9, 4, 7],
    )

    result = market_leverage.compute(frame)
    expected = pd.Series([0.5, 0.0, np.nan, np.nan, np.nan], index=frame.index)

    pd.testing.assert_series_equal(result, expected, check_names=False)
