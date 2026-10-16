"""Only consecutive fiscal quarters may form newly materialized PIT TTM."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import fundamentals as fu


def _records(dates, labels=("Q1", "Q2", "Q3", "Q4"), values=None):
    values = values if values is not None else range(10, 10 * (len(dates) + 1), 10)
    return [(pd.Timestamp(date), label, float(value))
            for date, label, value in zip(dates, labels, values, strict=True)]


def _state(records, metric="revenue"):
    return {(date, label, metric): {"value": value}
            for date, label, value in records}


def _ttm(records, metric="revenue"):
    return fu._snapshot(_state(records, metric), 1, pd.Timestamp("2025-05-16"))[
        f"{metric}_ttm"
    ]


def _filing_rows(records, metric="revenue"):
    return pd.DataFrame([
        {"asset_id": 1, "period_end": date, "fiscal_period": label,
         "fs_type": "CFS", "available_date": date + pd.Timedelta(days=45),
         "metric": metric, "value": value, "revision_key": f"filing-{index}"}
        for index, (date, label, value) in enumerate(records)
    ])


def test_methodology_and_whole_file_source_hash_are_explicit():
    assert fu.FUNDAMENTAL_METHODOLOGY_VERSION == "dart-pit-contiguous-fiscal-quarters-v2"
    assert fu.source_sha256() == hashlib.sha256(Path(fu.__file__).read_bytes()).hexdigest()


@pytest.mark.parametrize("dates", [
    ("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"),
    ("2021-06-30", "2021-09-30", "2021-12-31", "2022-03-31"),
    ("2021-08-31", "2021-11-30", "2022-02-28", "2022-05-31"),
    ("2023-08-31", "2023-11-30", "2024-02-29", "2024-05-31"),
    ("2021-05-15", "2021-08-15", "2021-11-15", "2022-02-15"),
])
def test_calendar_schedules_support_non_december_years_and_leap_years(dates):
    records = _records(dates)
    assert fu.is_contiguous_fiscal_quarters(records)
    assert _ttm(records) == 100.0


@pytest.mark.parametrize("labels", [
    ("Q1", "Q2", "Q3", "Q4"),
    ("Q2", "Q3", "Q4", "Q1"),
    ("Q3", "Q4", "Q1", "Q2"),
    ("Q4", "Q1", "Q2", "Q3"),
])
def test_rolling_ttm_accepts_every_fiscal_quarter_rotation(labels):
    records = _records(("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"), labels)
    assert _ttm(records) == 100.0


@pytest.mark.parametrize("week_gaps", [(13, 13, 13), (14, 13, 13), (13, 14, 13), (13, 13, 14)])
def test_week_based_schedules_accept_one_extra_week_without_calendar_certification(week_gaps):
    dates = [pd.Timestamp("2021-04-03")]
    for gap in week_gaps:
        dates.append(dates[-1] + pd.Timedelta(weeks=gap))
    records = _records(dates)
    assert fu.is_contiguous_fiscal_quarters(records)
    assert _ttm(records) == 100.0


@pytest.mark.parametrize("metric", sorted(fu.FLOW))
def test_reproduced_missing_q3_never_sums_older_q1_into_ttm(metric):
    records = _records(
        ("2021-03-31", "2021-06-30", "2021-12-31", "2022-03-31"),
        ("Q1", "Q2", "Q4", "Q1"), (10, 20, 40, 10),
    )
    assert not fu.is_contiguous_fiscal_quarters(records)
    assert pd.isna(_ttm(records, metric))


@pytest.mark.parametrize("dates,labels", [
    (("2021-03-31", "2021-06-30", "2021-09-30", "2022-03-31"), ("Q1", "Q2", "Q3", "Q4")),
    (("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"), ("Q1", "Q2", "Q2", "Q4")),
    (("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"), ("Q1", "Q3", "Q2", "Q4")),
    (("2021-03-31", "2021-06-30", "2021-09-30", "2022-01-31"), ("Q1", "Q2", "Q3", "Q4")),
    (("2021-03-31", "2021-06-30", "2021-08-31", "2021-11-30"), ("Q1", "Q2", "Q3", "Q4")),
])
def test_gaps_duplicate_labels_and_changed_year_ends_fail_closed(dates, labels):
    records = _records(dates, labels)
    assert not fu.is_contiguous_fiscal_quarters(records)
    assert pd.isna(_ttm(records))


def test_two_extra_weeks_in_one_year_fail_closed():
    dates = [pd.Timestamp("2021-04-03")]
    for weeks in (14, 13, 14):
        dates.append(dates[-1] + pd.Timedelta(weeks=weeks))
    assert pd.isna(_ttm(_records(dates)))


def test_same_endpoint_with_conflicting_labels_is_a_barrier_not_priority_selection():
    records = _records(("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"))
    records.append((pd.Timestamp("2021-12-31"), "Q3", 999.0))
    series = fu._standalone_flow(_state(records), "revenue")
    assert series[-1][1] == "INVALID"
    assert pd.isna(series[-1][2])
    assert pd.isna(_ttm(records))


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_current_quarter_cannot_reuse_previous_complete_ttm(value):
    records = _records(("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"))
    records.append((pd.Timestamp("2022-03-31"), "Q1", value))
    assert pd.isna(_ttm(records))


@pytest.mark.parametrize("dates", [
    ("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"),
    ("2021-06-30", "2021-09-30", "2021-12-31", "2022-03-31"),
    ("2021-05-01", "2021-07-31", "2021-10-30", "2022-02-05"),
])
def test_fy_derives_q4_only_from_same_year_consecutive_quarters(dates):
    records = _records(dates, ("Q1", "Q2", "Q3", "FY"), (10, 20, 30, 100))
    series = fu._standalone_flow(_state(records), "revenue")
    assert series[-1] == (pd.Timestamp(dates[-1]), "Q4", 40.0)
    assert _ttm(records) == 100.0


@pytest.mark.parametrize("invalid", ["missing_q2", "old_q1", "conflicting_label", "missing_fy_value"])
def test_fy_cannot_repair_incomplete_or_ambiguous_quarter_history(invalid):
    records = _records(
        ("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"),
        ("Q1", "Q2", "Q3", "FY"), (10, 20, 30, 100),
    )
    if invalid == "missing_q2":
        records.pop(1)
    elif invalid == "old_q1":
        records[0] = (pd.Timestamp("2020-03-31"), "Q1", 10.0)
    elif invalid == "conflicting_label":
        records.append((pd.Timestamp("2021-06-30"), "Q1", 999.0))
    else:
        records[-1] = (records[-1][0], "FY", np.nan)
    assert pd.isna(_ttm(records))
    assert fu._standalone_flow(_state(records), "revenue")[-1][1] == "INVALID"


def test_observed_shortened_fiscal_year_blocks_fy_derivation():
    records = _records(
        ("2021-01-31", "2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"),
        ("FY", "Q1", "Q2", "Q3", "FY"), (100, 10, 20, 30, 100),
    )
    assert pd.isna(_ttm(records))


def test_unobserved_intervening_fy_does_not_certify_residual_year_length():
    records = _records(
        ("2019-12-31", "2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"),
        ("FY", "Q1", "Q2", "Q3", "FY"), (100, 10, 20, 30, 100),
    )
    assert pd.isna(_ttm(records))


def test_previous_fy_boundary_allows_53_week_year():
    records = _records(
        ("2021-01-30", "2021-05-01", "2021-07-31", "2021-10-30", "2022-02-05"),
        ("FY", "Q1", "Q2", "Q3", "FY"), (80, 10, 20, 30, 100),
    )
    assert _ttm(records) == 100.0


def test_explicit_q4_keeps_source_value_instead_of_using_fy_residual():
    records = _records(("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"))
    records.append((pd.Timestamp("2021-12-31"), "FY", 1000.0))
    assert _ttm(records) == 100.0
    assert fu._standalone_flow(_state(records), "revenue")[-1][2] == 40.0


def test_unresolved_latest_fy_is_not_silently_skipped():
    records = _records(("2020-03-31", "2020-06-30", "2020-09-30", "2020-12-31"))
    records.append((pd.Timestamp("2021-12-31"), "FY", 100.0))
    assert pd.isna(_ttm(records))


def test_future_filing_addition_never_repairs_older_pit_snapshots():
    records = _records(("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"))
    base = _filing_rows(records)
    expected = fu.materialize_pit(base, verbose=False)
    revision = base.iloc[[2]].copy()
    revision["available_date"] = pd.Timestamp("2022-06-01")
    revision["revision_key"] = "late-revision"
    revision["value"] = 999.0
    observed = fu.materialize_pit(pd.concat([base, revision], ignore_index=True), verbose=False)
    pd.testing.assert_frame_equal(expected, observed.loc[:len(expected) - 1].reset_index(drop=True))
    assert observed.iloc[-1]["revenue_ttm"] == 1069.0


def test_missing_revision_is_retained_as_barrier_and_later_repair_is_causal():
    base = _filing_rows(_records(("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31")))
    retraction = base.iloc[[2]].copy()
    retraction["available_date"] = pd.Timestamp("2022-06-01")
    retraction["revision_key"] = "retracted"
    retraction["value"] = np.nan
    repair = retraction.copy()
    repair["available_date"] = pd.Timestamp("2022-07-01")
    repair["revision_key"] = "repaired"
    repair["value"] = 35.0
    output = fu.materialize_pit(pd.concat([base, retraction, repair], ignore_index=True), verbose=False)
    assert output.iloc[-3]["revenue_ttm"] == 100.0
    assert pd.isna(output.iloc[-2]["revenue_ttm"])
    assert output.iloc[-1]["revenue_ttm"] == 105.0


def test_nan_barrier_remains_until_four_new_valid_quarters_exist():
    records = _records(
        ("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31",
         "2022-03-31", "2022-06-30", "2022-09-30", "2022-12-31"),
        ("Q1", "Q2", "Q3", "Q4", "Q1", "Q2", "Q3", "Q4"),
        (10, 20, 30, np.nan, 10, 20, 30, 40),
    )
    assert pd.isna(_ttm(records[:-1]))
    assert _ttm(records) == 100.0


def test_materialization_preserves_input_and_revision_order_invariance():
    rows = _filing_rows(_records(("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31")))
    unchanged = rows.copy(deep=True)
    expected = fu.materialize_pit(rows, verbose=False)
    actual = fu.materialize_pit(rows.sample(frac=1.0, random_state=42), verbose=False)
    pd.testing.assert_frame_equal(rows, unchanged)
    pd.testing.assert_frame_equal(actual, expected)


def test_missing_stock_revision_keeps_existing_stock_fallback_policy():
    base = _filing_rows(
        _records(("2021-12-31",), ("FY",), (100.0,)), metric="total_assets",
    )
    missing = base.copy()
    missing["available_date"] = pd.Timestamp("2022-06-01")
    missing["revision_key"] = "missing-stock-revision"
    missing["value"] = np.nan
    original = fu.materialize_pit(base, verbose=False)
    observed = fu.materialize_pit(pd.concat([base, missing], ignore_index=True), verbose=False)
    pd.testing.assert_frame_equal(original, observed)


def test_late_missing_quarter_filing_repairs_only_future_snapshots():
    records = _records(("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"))
    complete = _filing_rows(records)
    base = complete.drop(index=2).reset_index(drop=True)
    expected = fu.materialize_pit(base, verbose=False)
    late = complete.iloc[[2]].copy()
    late["available_date"] = pd.Timestamp("2022-06-01")
    late["revision_key"] = "late-q3"
    observed = fu.materialize_pit(pd.concat([base, late], ignore_index=True), verbose=False)
    pd.testing.assert_frame_equal(expected, observed.loc[:len(expected) - 1].reset_index(drop=True))
    assert expected["revenue_ttm"].isna().all()
    assert observed.iloc[-1]["revenue_ttm"] == 100.0


def test_structure_cache_never_caches_values_or_allows_missing_value_reuse():
    records = _records(("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31"))
    fu._quarter_structure_is_contiguous.cache_clear()
    assert _ttm(records) == 100.0
    initial = fu._quarter_structure_is_contiguous.cache_info()
    assert initial.misses == 1
    updated = [*records[:-1], (*records[-1][:2], 45.0)]
    assert _ttm(updated) == 105.0
    assert fu._quarter_structure_is_contiguous.cache_info().hits == initial.hits + 1
    missing = [*records[:-1], (*records[-1][:2], np.nan)]
    assert pd.isna(_ttm(missing))
    assert fu._quarter_structure_is_contiguous.cache_info().hits == initial.hits + 1
    assert fu._quarter_structure_is_contiguous.cache_info().maxsize == 8192
