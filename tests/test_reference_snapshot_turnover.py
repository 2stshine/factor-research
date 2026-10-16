import copy

import pytest

from engine import reference_snapshot_turnover as t


def trade(nav, old, weights, rate=.0025):
    return t.rebalance(nav, old, weights, buy_rate=rate, sell_rate=rate)


def test_initial_buy_only_and_budget():
    values, row = trade(1., {}, {1: .5, 2: .5})
    assert sum(values.values()) == pytest.approx(1 / 1.0025)
    assert row["sell_cost"] == 0
    assert row["cost"] == pytest.approx(row["buy_notional"] * .0025)
    assert sum(values.values()) + row["cost"] == pytest.approx(1.)


def test_unchanged_holdings_cost_nothing():
    values, row = trade(1., {1: .5, 2: .5}, {1: .5, 2: .5})
    assert row["cost"] == pytest.approx(0, abs=1e-14)
    assert values == pytest.approx({1: .5, 2: .5})


def test_full_replacement_charges_both_sides():
    values, row = trade(1., {1: 1.}, {2: 1.})
    assert values[2] == pytest.approx(.9975 / 1.0025)
    assert row["sell_notional"] == 1.
    assert row["buy_notional"] == values[2]


def test_partial_replacement_does_not_charge_retained_notional():
    _, row = trade(1., {1: .5, 2: .5}, {1: .5, 3: .5})
    assert row["cost_fraction"] == pytest.approx(.0025)
    assert row["one_way_turnover"] == pytest.approx(.5)


def test_drift_requires_trade_even_when_targets_unchanged():
    targets = [("2020-01", {1: .5, 2: .5}), ("2020-02", {1: .5, 2: .5})]
    result = t.replay_path(targets, {("2020-01", 1): 1., ("2020-01", 2): 0.,
                                   ("2020-02", 1): 0., ("2020-02", 2): 0.},
                           assumption=t.ASSUMPTIONS[0], buy_bps=25, sell_bps=25)
    row = result["monthly"][1]
    assert row["one_way_turnover"] == pytest.approx(1 / 6)
    assert row["cost_fraction"] == pytest.approx(.005 / 6)
    assert row["net_return"] == pytest.approx(-row["cost_fraction"])


def test_missing_scenarios_preserve_targets_and_affect_trade_values():
    targets = [("2020-01", {1: .5, 2: .5}), ("2020-02", {2: .5, 3: .5})]
    original = copy.deepcopy(targets)
    lookup = {("2020-01", 2): 0., ("2020-02", 2): 0., ("2020-02", 3): 0.}
    flat, loss = [t.replay_path(targets, lookup, assumption=a, buy_bps=25, sell_bps=25) for a in t.ASSUMPTIONS]
    assert targets == original
    assert flat["monthly"][1]["assumed_prior_valuation_assets_at_trade"] == [1]
    assert loss["monthly"][1]["assumed_prior_valuation_assets_at_trade"] == []
    assert flat["monthly"][1]["sell_notional"] > loss["monthly"][1]["sell_notional"]
    assert not flat["summary"]["observed_complete_path"]
    assert not flat["final_liquidation_included"]


def test_no_cost_replay_matches_weighted_gross():
    result = t.replay_path([("2020-01", {1: .4, 2: .6})], {("2020-01", 1): .2, ("2020-01", 2): -.1},
                           assumption=t.ASSUMPTIONS[0], buy_bps=0, sell_bps=0)
    assert result["monthly"][0]["net_return"] == pytest.approx(.02)


@pytest.mark.parametrize("weights", [{1: .8}, {1: -.1, 2: 1.1}, {1: float("nan")}, {}])
def test_invalid_weights_fail(weights):
    with pytest.raises(ValueError, match="weights"):
        trade(1., {}, weights)


def test_nonconsecutive_months_fail():
    with pytest.raises(ValueError, match="Consecutive"):
        t.replay_path([("2020-01", {1: 1.}), ("2020-03", {1: 1.})], {},
                      assumption=t.ASSUMPTIONS[0], buy_bps=25, sell_bps=25)


def test_exhausted_nav_is_not_restarted():
    with pytest.raises(ValueError, match="Positive finite NAV"):
        t.replay_path([("2020-01", {1: 1.}), ("2020-02", {1: 1.})], {},
                      assumption=t.ASSUMPTIONS[1], buy_bps=25, sell_bps=25)


def test_duplicate_panel_keys_rejected():
    import pandas as pd
    panel = pd.DataFrame({"month": ["2020-01"] * 2, "asset_id": [1, 1], "outcome": [0., 0.]})
    with pytest.raises(ValueError, match="Duplicate"):
        t.evaluate(panel, [{}])
