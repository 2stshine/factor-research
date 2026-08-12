"""Unit contracts for the candidates frozen before the next OOS reveal."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factors.candidates import dividend_event_frequency_ttm
from factors.candidates import noncurrent_asset_share
from factors.candidates import operating_income_to_liabilities


@pytest.mark.parametrize(
    ("module", "predicted_sign", "needs"),
    [
        (
            operating_income_to_liabilities,
            1,
            ("operating_income_ttm", "total_liabilities"),
        ),
        (noncurrent_asset_share, -1, ("noncurrent_assets", "total_assets")),
        (dividend_event_frequency_ttm, 1, ("dividend_event_count_ttm",)),
    ],
)
def test_direction_and_single_signal_contract(module, predicted_sign, needs):
    factor = module.FACTOR

    assert factor.predicted_sign == predicted_sign
    assert factor.needs == needs
    assert factor.composite_evidence() == []
    assert factor.undeclared_constants() == []


def test_operating_income_to_liabilities_keeps_losses_and_requires_debt():
    frame = pd.DataFrame(
        {
            "operating_income_ttm": [20.0, -5.0, 8.0, 4.0],
            "total_liabilities": [100.0, 50.0, 0.0, -10.0],
        },
        index=[7, 2, 9, 1],
    )

    result = operating_income_to_liabilities.compute(frame)
    expected = pd.Series([0.2, -0.1, np.nan, np.nan], index=frame.index)

    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_noncurrent_asset_share_requires_valid_asset_values():
    frame = pd.DataFrame(
        {
            "noncurrent_assets": [60.0, 0.0, -5.0, 10.0],
            "total_assets": [100.0, 80.0, 100.0, 0.0],
        },
        index=[4, 8, 3, 6],
    )

    result = noncurrent_asset_share.compute(frame)
    expected = pd.Series([0.6, 0.0, np.nan, np.nan], index=frame.index)

    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_dividend_event_frequency_keeps_zero_and_rejects_negative_counts():
    frame = pd.DataFrame(
        {"dividend_event_count_ttm": [4.0, 1.0, 0.0, -1.0, np.nan]},
        index=[12, 5, 7, 2, 9],
    )

    result = dividend_event_frequency_ttm.compute(frame)
    expected = pd.Series([4.0, 1.0, 0.0, np.nan, np.nan], index=frame.index)

    pd.testing.assert_series_equal(result, expected, check_names=False)
