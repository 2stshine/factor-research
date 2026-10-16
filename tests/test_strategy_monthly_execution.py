"""Synthetic contracts/accounting only; no cache, database or historical returns."""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from strategies.monthly_execution import ExecutionCosts, VARIANTS, run_monthly_execution


def inputs(n=10, months=("2025-08", "2025-09")):
    periods = [pd.Period(month, freq="M") for month in months]
    session_months = pd.period_range(periods[0] + 1, periods[-1] + 2, freq="M")
    # Deliberately supplied special-time opens, never inferred weekdays/09:00.
    opens = {month: month.start_time.tz_localize("Asia/Seoul") + pd.Timedelta(days=2, hours=10)
             for month in session_months}
    scores, assets, market = [], [], []
    for month in periods:
        decision = month.end_time.floor("s").tz_localize("Asia/Seoul")
        for asset in range(1, n + 1):
            scores.append(dict(signal_month=month, asset_id=asset, signed_score=float(n - asset),
                               eligible=True, market_cap=100., available_at=decision))
            assets.append(dict(signal_month=month, asset_id=asset, entry_at=opens[month + 1],
                               exit_at=opens[month + 2], entry_open=100., gross_total_return_multiplier=1.,
                               return_available_at=opens[month + 2]))
        market.append(dict(signal_month=month, entry_at=opens[month + 1], exit_at=opens[month + 2],
                           gross_total_return_multiplier=1.02, return_available_at=opens[month + 2]))
    return dict(scores=pd.DataFrame(scores), sessions=pd.DataFrame([
                    dict(session_month=month, open_at=stamp) for month, stamp in opens.items()]),
                asset_windows=pd.DataFrame(assets), market_windows=pd.DataFrame(market),
                evidence=dict(schema_version="monthly-execution-evidence-v1", data_sha256="a" * 64,
                              as_of=max(opens.values()) + pd.Timedelta(days=3), calendar_verified=True,
                              asset_open_prices_verified=True, total_return_multipliers_verified=True,
                              market_total_return_verified=True, pit_inputs_verified=True),
                costs=ExecutionCosts(0., 0., {2025: 0., 2026: 0.}))


def result(args, variant="q20_equal"):
    return run_monthly_execution(**args)["variants"][variant]


def test_initial_purchase_is_self_financing_without_sale_tax():
    args = inputs(months=("2025-08",))
    args["costs"] = ExecutionCosts(.01, .02, {2025: .03})
    row = result(args)["monthly"].iloc[0]
    assert row.nav_after_cost == pytest.approx(1 / 1.01)
    assert row.buy_notional == pytest.approx(row.nav_after_cost)
    assert row.buy_cost == pytest.approx(row.buy_notional * .01)
    assert row.sell_notional == row.sell_cost == row.sell_tax == 0
    assert row.nav_exit + row.buy_cost == pytest.approx(1)
    assert row.net_return == pytest.approx(-.01 / 1.01)


def test_full_replacement_charges_costs_on_actual_sides_and_entry_year():
    args = inputs(months=("2025-11", "2025-12"))
    december = args["scores"].signal_month.eq(pd.Period("2025-12"))
    args["scores"].loc[december & args["scores"].asset_id.eq(2), "signed_score"] = 100.
    args["costs"] = ExecutionCosts(.01, .02, {2025: .03, 2026: .04})
    row = result(args, "q10_equal")["monthly"].iloc[1]
    assert row.entry_at.year == 2026
    assert row.sell_notional == pytest.approx(row.nav_before_rebalance)
    assert row.nav_after_cost == pytest.approx(row.nav_before_rebalance * (1 - .02 - .04) / 1.01)
    assert row.sell_tax == pytest.approx(row.sell_notional * .04)
    assert row.nav_after_cost + row.buy_cost + row.sell_cost + row.sell_tax == pytest.approx(row.nav_before_rebalance)


def test_actual_wealth_drift_drives_next_rebalance_not_old_target_weights():
    args = inputs()
    first = args["asset_windows"].signal_month.eq(pd.Period("2025-08"))
    args["asset_windows"].loc[first & args["asset_windows"].asset_id.eq(1), "gross_total_return_multiplier"] = 2.
    data = result(args)
    first_positions = data["positions"].loc[data["positions"].signal_month.eq(pd.Period("2025-08"))].set_index("asset_id")
    assert first_positions.loc[1, "end_weight"] == pytest.approx(2 / 3)
    assert first_positions.loc[2, "end_weight"] == pytest.approx(1 / 3)
    row = data["monthly"].iloc[1]
    assert row.nav_before_rebalance == pytest.approx(1.5)
    assert row.buy_notional == row.sell_notional == pytest.approx(.25)
    assert row.turnover_buy == row.turnover_sell == pytest.approx(1 / 6)
    assert row.nav_exit == pytest.approx(1.5)


def test_four_fixed_variants_share_windows_benchmarks_and_use_both_weights():
    args = inputs(n=20)
    args["scores"].loc[args["scores"].asset_id.eq(1), "market_cap"] = 900.
    output = run_monthly_execution(**args)
    assert output["variant_order"] == [name for name, _, _ in VARIANTS]
    assert list(output["variants"]) == ["q20_equal", "q10_equal", "q20_sqrt_cap", "q10_sqrt_cap"]
    assert not output["actual_fill_verified"] and not output["orders_submitted"]
    assert not output["final_liquidation_included"]
    columns = ["signal_month", "entry_at", "exit_at", "n_eligible", "universe_ew_return", "market_total_return"]
    baseline = output["variants"]["q20_equal"]["monthly"]
    for variant in output["variants"].values():
        pd.testing.assert_frame_equal(variant["monthly"][columns], baseline[columns])
    assert output["variants"]["q20_equal"]["monthly"].n_selected.tolist() == [4, 4]
    assert output["variants"]["q10_equal"]["monthly"].n_selected.tolist() == [2, 2]
    positions = output["variants"]["q20_sqrt_cap"]["positions"].iloc[:4].set_index("asset_id")
    assert positions.loc[1, "target_weight"] == pytest.approx(.5)
    assert positions.loc[2, "target_weight"] == pytest.approx(1 / 6)
    assert baseline.entry_at.iloc[0].hour == 10
    assert baseline.exit_at.iloc[0] == baseline.entry_at.iloc[1]


def test_zero_scores_ties_and_input_order_have_deterministic_asset_order():
    args = inputs()
    args["scores"]["signed_score"] = 0.
    expected = result(args)
    for name in ("scores", "sessions", "asset_windows", "market_windows"):
        args[name] = args[name].sample(frac=1., random_state=10).reset_index(drop=True)
    actual = result(args)
    pd.testing.assert_frame_equal(actual["monthly"], expected["monthly"])
    pd.testing.assert_frame_equal(actual["trades"], expected["trades"])
    assert actual["positions"].asset_id.tolist() == [1, 2, 1, 2]


def test_missing_scores_do_not_shrink_benchmark_or_eligible_denominator():
    args = inputs()
    args["scores"].loc[args["scores"].asset_id.eq(10), "signed_score"] = np.nan
    args["asset_windows"].loc[args["asset_windows"].asset_id.eq(10), "gross_total_return_multiplier"] = 2.
    rows = result(args)["monthly"]
    assert rows.n_eligible.tolist() == [10, 10]
    assert rows.n_signal_available.tolist() == [9, 9]
    assert rows.n_selected.tolist() == [2, 2]
    assert rows.score_coverage.tolist() == [.9, .9]
    assert rows.universe_ew_return.tolist() == pytest.approx([.1, .1])
    assert rows.net_return.tolist() == pytest.approx([0., 0.])
    args["scores"].loc[args["scores"].asset_id.ne(1), "signed_score"] = np.nan
    with pytest.raises(ValueError, match="Insufficient available scores"):
        run_monthly_execution(**args)


def test_minimum_one_and_zero_total_return_multiplier_are_explicit():
    args = inputs(n=1, months=("2025-08",))
    args["asset_windows"]["gross_total_return_multiplier"] = 0.
    row = result(args)["monthly"].iloc[0]
    assert row.n_selected == 1 and row.net_return == -1 and row.nav_exit == 0


def test_net_return_uses_compounded_cost_drag_not_gross_minus_fee_fraction():
    args = inputs(months=("2025-08",))
    args["asset_windows"]["gross_total_return_multiplier"] = 1.5
    args["costs"] = ExecutionCosts(.01, 0., {2025: 0.})
    row = result(args)["monthly"].iloc[0]
    assert row.net_return == pytest.approx((1 - row.cost_fraction) * (1 + row.gross_return) - 1)
    assert row.cost_drag_return == pytest.approx(row.gross_return - row.net_return)
    assert row.net_return != pytest.approx(row.gross_return - row.cost_fraction)


@pytest.mark.parametrize("failure", ["missing_asset", "missing_held_exit", "missing_market", "missing_session",
                                     "wrong_benchmark_dates", "late_input", "naive_time", "early_return",
                                     "not_yet_available_return", "unverified", "bad_digest", "duplicate",
                                     "zero_price", "zero_cap", "nan_return", "infinite_score", "tax_year"])
def test_invalid_inputs_fail_closed_without_skips_or_renormalization(failure):
    args = inputs()
    if failure == "missing_asset":
        args["asset_windows"] = args["asset_windows"].iloc[1:]
    elif failure == "missing_held_exit":
        match = args["scores"].signal_month.eq(pd.Period("2025-09")) & args["scores"].asset_id.eq(1)
        args["scores"].loc[match, "eligible"] = False
        match = args["asset_windows"].signal_month.eq(pd.Period("2025-09")) & args["asset_windows"].asset_id.eq(1)
        args["asset_windows"] = args["asset_windows"].loc[~match]
    elif failure == "missing_market":
        args["market_windows"] = args["market_windows"].iloc[1:]
    elif failure == "missing_session":
        args["sessions"] = args["sessions"].iloc[:-1]
    elif failure == "wrong_benchmark_dates":
        args["market_windows"].loc[0, "exit_at"] += pd.Timedelta(hours=1)
    elif failure == "late_input":
        args["scores"].loc[0, "available_at"] += pd.Timedelta(seconds=1)
    elif failure == "naive_time":
        args["evidence"]["as_of"] = "2026-01-01"
    elif failure == "early_return":
        args["asset_windows"].loc[0, "return_available_at"] -= pd.Timedelta(days=1)
    elif failure == "not_yet_available_return":
        args["evidence"]["as_of"] -= pd.Timedelta(days=20)
    elif failure == "unverified":
        args["evidence"]["calendar_verified"] = False
    elif failure == "bad_digest":
        args["evidence"]["data_sha256"] = "not-a-hash"
    elif failure == "duplicate":
        args["scores"] = pd.concat([args["scores"], args["scores"].iloc[:1]], ignore_index=True)
    elif failure == "zero_price":
        args["asset_windows"].loc[0, "entry_open"] = 0.
    elif failure == "zero_cap":
        args["scores"].loc[0, "market_cap"] = 0.
    elif failure == "nan_return":
        args["asset_windows"].loc[0, "gross_total_return_multiplier"] = np.nan
    elif failure == "infinite_score":
        args["scores"].loc[0, "signed_score"] = np.inf
    elif failure == "tax_year":
        args["costs"] = ExecutionCosts(0., 0., {})
    with pytest.raises(ValueError):
        run_monthly_execution(**args)


def test_gap_in_signal_months_is_rejected_and_inputs_are_not_mutated():
    args = inputs()
    original = deepcopy(args)
    run_monthly_execution(**args)
    for name in ("scores", "sessions", "asset_windows", "market_windows"):
        pd.testing.assert_frame_equal(args[name], original[name])
    assert args["evidence"] == original["evidence"]
    gap = inputs(months=("2025-08", "2025-10"))
    with pytest.raises(ValueError, match="consecutive"):
        run_monthly_execution(**gap)


def test_finite_input_multipliers_cannot_overflow_into_reported_wealth():
    args = inputs(n=1)
    args["asset_windows"]["gross_total_return_multiplier"] = 1e308
    with pytest.raises(ValueError, match="Non-finite"):
        run_monthly_execution(**args)
