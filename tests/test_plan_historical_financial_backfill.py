"""Pure synthetic existence/known-at tests: no DB, real panel or returns."""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from scripts import plan_historical_financial_backfill as plan


def row(date, label, value=400, available="2016-03-31", **kw):
    return {"asset_id": 1, "period_end": pd.Timestamp(date), "fiscal_period": label,
            "fs_type": "CFS", "available_date": pd.Timestamp(available),
            "metric": "revenue", "value": value, "revision_key": "1", **kw}


def state(*rows):
    return {(entry["period_end"], entry["fiscal_period"]): entry for entry in rows}


def frame():
    months = pd.period_range("2016-03", "2018-03", freq="M")
    result = pd.DataFrame({"asset_id": 1, "ym": months,
        "trade_date": months.to_timestamp("M"), "in_universe": True,
        "market_cap": 100.0, "adj_close": 1.0, "revenue_ttm": 400.0})
    result.loc[0, "revenue_ttm"] = np.nan
    return result


def test_symbolic_terms_cancel_but_original_quarter_evidence_remains_required():
    first = plan.Amount(0, (("x", 1),), frozenset({"x"}))
    result = plan.Amount(400).plus(first, -1).plus(first)
    assert result.constant == 400 and result.terms == ()
    assert result.required == frozenset({"x"})


def test_three_2015_quarters_make_fy_amount_known_without_imputing_amounts():
    original = state(row("2015-12-31", "FY"))
    before = deepcopy(original)
    audit = plan.symbolic_ttm(original)
    assert original == before
    assert audit["repairable_structure"]
    assert audit["ttm_amount_is_algebraically_known"]
    assert audit["known_ttm_positive"] is True
    assert audit["positive_denominator_still_unverified"] is False
    assert [(item["period_end"], item["fiscal_period"]) for item in audit["required_original_quarters"]] == [
        ("2015-03-31", "Q1"), ("2015-06-30", "Q2"), ("2015-09-30", "Q3")]


def test_rolling_ttm_is_only_conditional_on_unknown_positive_amount():
    audit = plan.symbolic_ttm(state(row("2015-12-31", "FY"), row("2016-03-31", "Q1", 120)))
    assert audit["repairable_structure"]
    assert audit["ttm_amount_is_algebraically_known"] is False
    assert audit["known_ttm_positive"] is None
    assert audit["positive_denominator_still_unverified"]


@pytest.mark.parametrize("value,positive", [(0, False), (-10, False), (400, True)])
def test_known_fy_sign_cannot_be_overridden(value, positive):
    audit = plan.symbolic_ttm(state(row("2015-12-31", "FY", value)))
    assert audit["known_ttm_positive"] is positive


def test_explicit_missing_quarter_is_not_repaired_by_symbolic_replacement():
    audit = plan.symbolic_ttm(state(row("2015-12-31", "FY"), row("2015-06-30", "Q2", np.nan)))
    assert audit["repairable_structure"] is False


def test_missing_fy_cannot_be_reconstructed_from_unknown_quarters():
    assert not plan.symbolic_ttm({})["repairable_structure"]


def test_nondecember_fy_requires_2014_quarter_outside_backfill_scope():
    audit = plan.symbolic_ttm(state(row("2015-09-30", "FY")))
    assert audit["repairable_structure"] is False


def test_nondecember_2016_fy_can_use_original_2015_quarters_if_current_q3_known():
    audit = plan.symbolic_ttm(state(
        row("2015-06-30", "FY", available="2015-09-30"),
        row("2016-03-31", "Q3", 100), row("2016-06-30", "FY", available="2016-09-30")))
    assert audit["repairable_structure"]
    assert audit["ttm_amount_is_algebraically_known"]
    assert [item["period_end"] for item in audit["required_original_quarters"]] == ["2015-09-30", "2015-12-31"]


def test_changed_fiscal_boundary_not_repaired():
    audit = plan.symbolic_ttm(state(row("2014-09-30", "FY"), row("2015-12-31", "FY")))
    assert audit["repairable_structure"] is False


def test_non_month_end_calendar_not_invented():
    assert plan.original_quarter_requirements(state(row("2015-12-26", "FY"))) == {}


def test_known_at_before_fy_filing_has_no_structural_repair():
    data = frame()
    raw = pd.DataFrame([row("2015-12-31", "FY", available="2016-04-01")])
    result = plan.analyze(data, raw)
    assert result["summary"]["current_overall_coverage"] == 0
    assert result["summary"]["structural_upper_bound_overall_coverage"] == 0


def test_same_day_fy_available_allows_structural_bound_not_actual_gate_pass():
    data = frame()
    result = plan.analyze(data, pd.DataFrame([row("2015-12-31", "FY")]))
    assert result["summary"]["structural_upper_bound_overall_coverage"] == 1
    assert result["summary"]["candidate_input_gate_passed"] is False
    assert result["monthly"][0]["newly_structurally_repairable_asset_ids"] == [1]


def test_asset_specific_trade_date_not_calendar_month_end_controls_known_at():
    data = frame()
    data.loc[0, "trade_date"] = pd.Timestamp("2016-03-30")
    result = plan.analyze(data, pd.DataFrame([row("2015-12-31", "FY")]))
    assert result["summary"]["structural_upper_bound_overall_coverage"] == 0


def test_exact_lag_calendar_missing_month_is_not_compressed():
    data = frame().drop(index=6)
    result = plan.analyze(data, pd.DataFrame([row("2015-12-31", "FY")]))
    assert result["summary"]["structural_upper_bound_overall_coverage"] == 0
    assert result["monthly"][0]["blocking_reason_counts_nonexclusive"]["EXACT_12_24_MONTH_CALENDAR_ALIGNMENT_MISSING"] == 1


def test_existing_nonpositive_denominator_is_not_filled():
    data = frame()
    data.loc[12, "revenue_ttm"] = 0
    result = plan.analyze(data, pd.DataFrame([row("2015-12-31", "FY")]))
    assert result["summary"]["structural_upper_bound_overall_coverage"] == 0


def test_nonpositive_algebraic_fy_denominator_blocks_upper_bound():
    result = plan.analyze(frame(), pd.DataFrame([row("2015-12-31", "FY", -10)]))
    assert result["summary"]["structural_upper_bound_overall_coverage"] == 0


def test_future_revision_does_not_change_past_structural_decision():
    raw = pd.DataFrame([row("2015-12-31", "FY")])
    future = row("2015-12-31", "FY", -100, available="2016-04-01", revision_key="2")
    a = plan.analyze(frame(), raw)
    b = plan.analyze(frame(), pd.concat([raw, pd.DataFrame([future])], ignore_index=True))
    assert a["monthly"] == b["monthly"]
    assert a["repairable_input_slots"] == b["repairable_input_slots"]


def test_cfs_dominates_later_ofs_and_higher_revision_wins_same_day():
    raw = pd.DataFrame([row("2015-12-31", "FY", -10, available="2016-03-01"),
        row("2015-12-31", "FY", 400, available="2016-03-30", fs_type="OFS"),
        row("2015-12-31", "FY", 300, available="2016-03-01", revision_key="2")])
    result = plan.analyze(frame(), raw)
    assert result["summary"]["structural_upper_bound_overall_coverage"] == 1


def test_equal_priority_ambiguity_fails_closed():
    raw = pd.DataFrame([row("2015-12-31", "FY"), row("2015-12-31", "FY", 500)])
    with pytest.raises(ValueError, match="Ambiguous"):
        plan.analyze(frame(), raw)


def test_beyond_cutoff_raw_rows_not_in_availability_distribution():
    raw = pd.DataFrame([row("2015-12-31", "FY"), row("2015-12-31", "FY", 500, available="2023-08-01")])
    result = plan.analyze(frame(), raw)
    assert result["source_2015_available_date_distribution"] == [
        {"fiscal_period": "FY", "available_month": "2016-03", "revision_rows": 1}]


def test_extra_label_columns_not_inspected_and_inputs_unchanged():
    data = frame()
    data["fwd_return"] = object()
    before = data.copy(deep=True)
    plan.analyze(data, pd.DataFrame([row("2015-12-31", "FY")]))
    pd.testing.assert_frame_equal(data, before)


def test_duplicate_month_key_fails_closed():
    data = frame()
    with pytest.raises(ValueError, match="Duplicate asset-month"):
        plan.analyze(pd.concat([data, data.iloc[:1]]), pd.DataFrame([row("2015-12-31", "FY")]))


def test_cli_requires_explicit_paths_and_does_not_change_window(monkeypatch):
    calls = []
    monkeypatch.setattr(plan, "run", lambda source, output: calls.append((source, output)))
    plan.main(["--source", "some-source", "--output", "new-audit.json"])
    assert tuple(map(str, calls[0])) == ("some-source", "new-audit.json")
    assert (plan.START, plan.END, plan.RAW_END) == ("2018-03", "2023-06", "2023-07-31")
