"""Synthetic-only contracts; no Silver panel or research outcomes are read."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from factors.candidate_loader import (
    _load_module,
    _validate_active_history_semantics,
    _validate_spec,
)
from factors.candidates import return_trading_activity_correlation_12m as candidate


def _frame(months=28, *, asset_id=101, start="2020-01", phase=0.0):
    position = np.arange(months, dtype=float)
    returns = 0.03 * np.sin(position * 0.9 + phase) + 0.02 * np.cos(position * 0.37)
    return pd.DataFrame({
        "asset_id": asset_id,
        "ticker": "REUSED",
        "ym": pd.period_range(start, periods=months, freq="M"),
        "adj_close": 100.0 * np.cumprod(1.0 + returns),
        "adv20": np.exp(18.0 + 0.5 * np.cos(position * 0.7 + phase)
                        + 0.3 * np.sin(position * 0.23)),
    })


def _reference(frame):
    """Independent, explicit 13-row calendar windows and NumPy Pearson."""
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, asset_frame in frame.groupby("asset_id"):
        ordered = asset_frame.sort_values("ym")
        for end in range(12, len(ordered)):
            window = ordered.iloc[end - 12:end + 1]
            expected_months = pd.period_range(window["ym"].iloc[0], periods=13, freq="M")
            if not np.array_equal(window["ym"].to_numpy(), expected_months.to_numpy()):
                continue
            prices = window["adj_close"].to_numpy(dtype=float)
            activity = window["adv20"].iloc[1:].to_numpy(dtype=float)
            if not (np.isfinite(prices).all() and (prices > 0).all()
                    and np.isfinite(activity).all() and (activity > 0).all()):
                continue
            returns = prices[1:] / prices[:-1] - 1.0
            logged = np.log(activity)
            if np.ptp(returns) == 0 or np.ptp(logged) == 0:
                continue
            result.loc[window.index[-1]] = np.corrcoef(returns, logged)[0, 1]
    return result


def test_targeted_loader_and_single_signal_contract():
    path = Path(candidate.__file__)
    module, digest, source = _load_module(path)
    _validate_active_history_semantics(path, source)
    spec = _validate_spec(path, module.FACTOR, module.RESEARCH_SPEC, source_digest=digest)

    assert spec["strategy_sha256"] == digest
    assert module.FACTOR.definition_hash == candidate.FACTOR.definition_hash
    assert candidate.FACTOR.predicted_sign == -1
    assert candidate.FACTOR.params["lookback_months"] == 12
    assert candidate.FACTOR.params["min_observations"] == 12
    assert candidate.FACTOR.composite_evidence() == []
    assert candidate.FACTOR.undeclared_constants() == []


def test_exact_trailing_pearson_matches_independent_reference_and_preserves_input():
    frame = _frame()
    before = frame.copy(deep=True)

    result = candidate.compute(frame)

    pd.testing.assert_series_equal(result, _reference(frame), check_names=False,
                                   rtol=1e-10, atol=1e-11)
    assert result.iloc[:12].isna().all()
    assert result.iloc[12:].notna().all()
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("initial_activity", [np.nan, 0.0, -1.0, np.inf])
def test_oldest_price_does_not_require_a_thirteenth_activity_value(initial_activity):
    frame = _frame(13)
    frame.loc[0, "adv20"] = initial_activity

    result = candidate.compute(frame)

    assert result.iloc[-1] == pytest.approx(_reference(frame).iloc[-1], abs=1e-11)
    assert result.notna().sum() == 1


@pytest.mark.parametrize("column,position", [
    ("adj_close", 0), ("adj_close", 6), ("adj_close", 12),
    ("adv20", 1), ("adv20", 6), ("adv20", 12),
])
@pytest.mark.parametrize("invalid", [np.nan, 0.0, -1.0, np.inf, -np.inf])
def test_invalid_required_price_or_activity_invalidates_window(column, position, invalid):
    frame = _frame(13)
    frame.loc[position, column] = invalid

    assert candidate.compute(frame).isna().all()


@pytest.mark.parametrize("column", ["adj_close", "adv20"])
def test_missing_input_recovers_only_after_it_leaves_required_window(column):
    frame = _frame(28)
    frame.loc[5, column] = np.nan

    result = candidate.compute(frame)

    pd.testing.assert_series_equal(result, _reference(frame), check_names=False,
                                   rtol=1e-10, atol=1e-11)
    first_valid_position = 18 if column == "adj_close" else 17
    assert result.iloc[:first_valid_position].isna().all()
    assert result.iloc[first_valid_position:].notna().all()


@pytest.mark.parametrize("missing_position", [1, 6, 12])
def test_calendar_gap_rejects_row_count_window_and_recovers(missing_position):
    frame = _frame(30).drop(index=missing_position)

    result = candidate.compute(frame)

    pd.testing.assert_series_equal(result, _reference(frame), check_names=False,
                                   rtol=1e-10, atol=1e-11)
    assert result.loc[result.index <= missing_position + 12].isna().all()
    assert result.loc[missing_position + 13:].notna().all()


@pytest.mark.parametrize("index_kind", ["integer", "string"])
def test_shuffled_assets_and_nontrivial_index_preserve_alignment(index_kind):
    frame = pd.concat([_frame(28), _frame(22, asset_id=707, phase=1.3)], ignore_index=True)
    labels = np.arange(len(frame)) * 11 + 97
    if index_kind == "string":
        labels = [f"source-row-{label}" for label in labels]
    frame.index = pd.Index(labels, name="source_row")
    frame = frame.sample(frac=1.0, random_state=73)

    result = candidate.compute(frame)

    assert result.index.equals(frame.index)
    pd.testing.assert_series_equal(result, _reference(frame), check_names=False,
                                   rtol=1e-10, atol=1e-11)
    for _, asset_frame in frame.groupby("asset_id"):
        pd.testing.assert_series_equal(result.loc[asset_frame.index],
                                       candidate.compute(asset_frame), check_names=False)


def test_reused_ticker_does_not_supply_another_assets_price_history():
    frame = pd.concat([
        _frame(13, asset_id=101, start="2020-01"),
        _frame(13, asset_id=909, start="2021-02", phase=2.1),
    ], ignore_index=True).sample(frac=1.0, random_state=53)

    result = candidate.compute(frame)
    new_asset = frame.loc[frame["asset_id"].eq(909)].sort_values("ym")

    assert result.loc[new_asset.index[:12]].isna().all()
    assert result.loc[new_asset.index[-1]] == pytest.approx(
        _reference(new_asset).iloc[-1], abs=1e-11,
    )
    pd.testing.assert_series_equal(result, _reference(frame), check_names=False,
                                   rtol=1e-10, atol=1e-11)


@pytest.mark.parametrize("constant_input", ["price", "return", "activity"])
def test_zero_variance_is_missing(constant_input):
    frame = _frame(28)
    if constant_input == "price":
        frame["adj_close"] = 100.0
    elif constant_input == "return":
        # Powers of two give exactly constant, nonzero binary returns.
        frame["adj_close"] = 2.0 ** np.arange(len(frame))
    else:
        frame["adv20"] = 1e8

    assert candidate.compute(frame).isna().all()


def test_appending_and_mutating_future_rows_cannot_change_past_signals():
    frame = pd.concat([_frame(32), _frame(32, asset_id=707, phase=0.8)], ignore_index=True)
    cutoff = pd.Period("2021-08", freq="M")
    prefix = frame.loc[frame["ym"] <= cutoff].sample(frac=1.0, random_state=13)
    expected = candidate.compute(prefix)

    extended = frame.copy()
    future = extended["ym"] > cutoff
    extended.loc[future, "adj_close"] *= np.linspace(0.1, 10.0, future.sum())
    extended.loc[future, "adv20"] *= np.linspace(0.01, 100.0, future.sum())
    extended = extended.sample(frac=1.0, random_state=17)

    pd.testing.assert_series_equal(candidate.compute(extended).loc[prefix.index],
                                   expected, check_names=False)


def test_output_ignores_forward_labels_ex_post_prices_and_other_assets():
    frame = _frame()
    baseline = candidate.compute(frame)
    frame["fwd_1m"] = np.linspace(-1.0, 1000.0, len(frame))
    frame["total_return_close"] = np.linspace(1e9, 1.0, len(frame))
    other = _frame(asset_id=909, phase=2.2)
    other.index += len(frame)
    other["adj_close"] *= 1e7
    other["adv20"] *= 1e-7
    extended = pd.concat([frame, other]).sample(frac=1.0, random_state=19)

    pd.testing.assert_series_equal(candidate.compute(extended).loc[frame.index],
                                   baseline, check_names=False)
