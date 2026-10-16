import pytest

from engine.research_horizons import HypothesisHorizon, InputHistory, plan_horizons


def history(name="price", first="2015-01", lag=0, source=0):
    return InputHistory(name, first, lag, source, "fixture://verified-input", True)


def hypothesis(name="one", inputs=None, outcome=1, economic=None):
    return HypothesisHorizon(name, tuple(inputs or [history()]), outcome, economic)


def test_current_level_does_not_require_three_years():
    result = plan_horizons([hypothesis()], signal_end="2015-12")
    assert result["common_primary_start"] == "2015-01"
    assert result["common_calendar_months"] == 12
    assert result["active_policy_modified"] is False


def test_comparisons_share_a_common_start_and_not_just_own_warmup():
    result = plan_horizons([
        hypothesis("short", [history(lag=1)]),
        hypothesis("momentum", [history(lag=12)]),
    ], signal_end="2018-01")
    assert result["common_primary_start"] == "2016-01"
    assert result["hypotheses"][0]["first_formula_ready_month"] == "2015-02"
    assert "common_eligible_asset_sample" in result["remaining_checks"]


def test_ttm_source_history_is_reported_but_not_double_counted():
    result = plan_horizons([
        hypothesis(inputs=[history("ttm", "2016-01", lag=0, source=12)])
    ], signal_end="2018-01")
    assert result["common_primary_start"] == "2016-01"
    assert result["hypotheses"][0]["raw_history_upper_bound_months"] == 12


def test_ttm_year_over_year_reports_24_month_raw_dependency():
    result = plan_horizons([
        hypothesis(inputs=[history("ttm", "2016-01", lag=12, source=12)])
    ], signal_end="2018-01")
    row = result["hypotheses"][0]
    assert result["common_primary_start"] == "2017-01"
    assert row["raw_history_upper_bound_months"] == 24
    assert row["extended_history_rationale_required"] is True


def test_future_outcome_horizon_never_becomes_input_lookback():
    result = plan_horizons([hypothesis(economic=36)], signal_end="2018-01")
    assert result["common_primary_start"] == "2015-01"
    assert result["hypotheses"][0]["economic_label_horizon_months"] == 36


def test_declared_cohort_floor_is_preserved():
    result = plan_horizons([hypothesis()], signal_end="2020-01", minimum_primary_start="2018-03")
    assert result["common_primary_start"] == "2018-03"


def test_no_common_calendar_is_not_a_factor_rejection():
    result = plan_horizons([hypothesis(inputs=[history(lag=36)])], signal_end="2015-12")
    assert result["status"] == "NO_COMMON_CALENDAR"
    assert result["common_calendar_months"] == 0


@pytest.mark.parametrize("bad", ["2015-1", "2015-13", "2015-01-31", "0000-01", None])
def test_invalid_months_fail_closed(bad):
    with pytest.raises(ValueError):
        plan_horizons([hypothesis()], signal_end=bad)


@pytest.mark.parametrize("lag", [-1, 1.5, True])
def test_invalid_or_future_offsets_fail_closed(lag):
    with pytest.raises(ValueError):
        plan_horizons([hypothesis(inputs=[history(lag=lag)])], signal_end="2020-01")


def test_unverified_input_metadata_does_not_get_an_approved_plan():
    with pytest.raises(ValueError):
        plan_horizons([hypothesis(inputs=[
            InputHistory("price", "2015-01", 0, 0, "fixture://input", False)
        ])], signal_end="2020-01")


def test_duplicates_and_empty_hypotheses_are_rejected():
    with pytest.raises(ValueError):
        plan_horizons([], signal_end="2020-01")
    with pytest.raises(ValueError):
        plan_horizons([hypothesis(), hypothesis()], signal_end="2020-01")
    with pytest.raises(ValueError):
        plan_horizons([hypothesis(inputs=[history(), history()])], signal_end="2020-01")


def test_metadata_only_not_data_or_pit_certification():
    result = plan_horizons([hypothesis()], signal_end="2020-01")
    assert result["mode"] == "METADATA_ONLY_NOT_EXECUTION_AUTHORIZATION"
    assert result["source_metadata_verified_by_this_planner"] is False
