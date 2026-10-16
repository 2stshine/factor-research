"""Synthetic pre-registration contracts; no real panel, DB, returns or campaign."""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from engine import research_policy
from engine.research_production_evidence import validate_diagnostic_plan
from factors.candidates import sales_growth_acceleration_12m as candidate


def synthetic_frame(months=40):
    calendar = pd.period_range("2015-01", periods=months, freq="M")
    rows = [
        {"asset_id": asset, "ym": month, "revenue_ttm": 100.0 + asset * 200.0 + step * step,
         "instrument_type": "common_stock", "market": market}
        for asset, market in ((1, "KOSPI"), (2, "KOSDAQ"))
        for step, month in enumerate(calendar)
    ]
    return pd.DataFrame(rows).sample(frac=1, random_state=41)


def formula_from_exact_calendar(frame):
    values = frame.set_index(["asset_id", "ym"])["revenue_ttm"].to_dict()
    expected = pd.Series(np.nan, index=frame.index, dtype=float)
    for index, row in frame.iterrows():
        first = values.get((row.asset_id, row.ym - 12), np.nan)
        second = values.get((row.asset_id, row.ym - 24), np.nan)
        if first > 0 and second > 0:
            expected.loc[index] = row.revenue_ttm / first - first / second
    return expected


def test_formula_and_sign_remain_sales_growth_acceleration():
    frame = synthetic_frame()
    pd.testing.assert_series_equal(candidate.compute(frame), formula_from_exact_calendar(frame), check_names=False)
    assert candidate.FACTOR.predicted_sign == 1
    assert candidate.FACTOR.needs == ("revenue_ttm",)
    assert candidate.FACTOR.composite_evidence() == []
    assert candidate.FACTOR.undeclared_constants() == []


def test_monthly_rebalance_and_explicit_twenty_four_month_bound():
    factor = candidate.FACTOR
    assert factor.rebalance_months == 1
    assert factor.exploration_domain == "profitability_quality"
    assert research_policy.assert_allowed_lookback(name=factor.name, source=factor.source, params=factor.params) == 24


def test_exact_history_requires_current_and_twenty_four_prior_months():
    assert candidate.compute(synthetic_frame(months=24)).isna().all()
    frame = synthetic_frame(months=25)
    result = candidate.compute(frame)
    last = frame.ym.eq(pd.Period("2017-01", freq="M"))
    assert result.loc[~last].isna().all()
    assert result.loc[last].notna().all()
    pd.testing.assert_series_equal(result.loc[last], formula_from_exact_calendar(frame).loc[last], check_names=False)


def test_missing_calendar_month_is_not_compressed_or_filled():
    frame = synthetic_frame()
    gap = (frame.asset_id == 1) & frame.ym.eq(pd.Period("2016-04", freq="M"))
    frame = frame.loc[~gap].copy()
    result = candidate.compute(frame)
    anchor = frame.ym.eq(pd.Period("2018-01", freq="M"))
    assert result.loc[anchor & frame.asset_id.eq(1)].isna().all()
    assert result.loc[anchor & frame.asset_id.eq(2)].notna().all()


@pytest.mark.parametrize("lag", [12, 24])
@pytest.mark.parametrize("invalid", [0.0, -1.0, np.nan])
def test_both_historical_denominators_must_be_positive(lag, invalid):
    frame = synthetic_frame()
    anchor = pd.Period("2018-01", freq="M")
    frame.loc[frame.asset_id.eq(1) & frame.ym.eq(anchor - lag), "revenue_ttm"] = invalid
    result = candidate.compute(frame)
    assert result.loc[frame.asset_id.eq(1) & frame.ym.eq(anchor)].isna().all()
    assert result.loc[frame.asset_id.eq(2) & frame.ym.eq(anchor)].notna().all()


def test_future_rows_cannot_change_past_signals():
    frame = synthetic_frame()
    cutoff = pd.Period("2017-06", freq="M")
    prior = frame.ym.le(cutoff)
    expected = candidate.compute(frame).loc[prior]
    changed = frame.copy(deep=True)
    changed.loc[~prior, "revenue_ttm"] = -1e30
    pd.testing.assert_series_equal(candidate.compute(changed).loc[prior], expected)
    pd.testing.assert_series_equal(candidate.compute(frame.loc[prior]), expected)


def test_engine_causal_window_matches_unchanged_direct_formula():
    frame = synthetic_frame()
    actual = research_policy.compute_factor(candidate.FACTOR, frame)
    pd.testing.assert_series_equal(actual, candidate.compute(frame), check_names=False)


def test_diagnostic_controls_and_downstream_outcomes_do_not_change_score():
    frame = synthetic_frame()
    expected = candidate.compute(frame)
    augmented = frame.copy(deep=True)
    for column in ("operating_income_ttm", "total_assets", "economic_outcome", "fwd_mid", "total_return_close"):
        augmented[column] = np.arange(len(augmented), dtype=float) * -1000.0
    pd.testing.assert_series_equal(candidate.compute(augmented), expected)
    pd.testing.assert_series_equal(research_policy.compute_factor(candidate.FACTOR, augmented), expected, check_names=False)


def test_preregistered_diagnostics_are_valid_and_measure_snapshot_change():
    original = deepcopy(candidate.RESEARCH_SPEC["diagnostic_plan"])
    plan = validate_diagnostic_plan(candidate.RESEARCH_SPEC["diagnostic_plan"])
    assert candidate.RESEARCH_SPEC["diagnostic_plan"] == original
    assert plan["question_kind"] == "EXPLANATORY"
    assert plan["execution_cost"] is True
    assert plan["industry_control"] is None
    assert {control["name"] for control in plan["ratio_controls"]} == {"asset_turnover", "operating_margin"}
    outcome = plan["economic_outcome"]
    assert (outcome["numerator"], outcome["denominator"], outcome["measurement_kind"], outcome["horizon_months"]) == (
        "operating_income_ttm", "total_assets", "CHANGE", 12)
    assert outcome["available_at"] == "available_date"
    assert plan["input_history"]["revenue_ttm"]["source_history_months"] == 12
    assert plan["macro_axes"] == ["KR_PRODUCTION_INFLATION_DIRECTION"]
    assert plan["macro_contrasts"][plan["macro_axes"][0]] == [
        "PRODUCTION_UP_INFLATION_DOWN", "PRODUCTION_DOWN_INFLATION_UP"]
