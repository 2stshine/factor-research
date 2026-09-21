from copy import deepcopy

import pandas as pd
import pytest

from engine.assumed_macro_regimes import (
    classification_rules, completed_end_month, monthly_states, normalize_observation,
)
from scripts.build_assumed_fmp_regimes import COT_KNOWN_RELEASE_DATES


def raw(day, **fields):
    return {"payload": {"date": day, **fields}, "audit_received_at": "2026-09-20T00:00:00+00:00",
            "audit_source_uri": "synthetic://original", "source_row_index": 0}


def normalize(day, kind="macro", symbol="TEST", **fields):
    return normalize_observation(symbol, kind, raw(day, **fields), cot_release_dates=COT_KNOWN_RELEASE_DATES)


def test_receipt_preserved_and_macro_utc_moves_to_korean_release_month():
    row = normalize("2015-01-31 23:00:00", actual=3.0, previous=999, estimate=999)
    assert row["available_at_assumed"] == "2015-02-01T08:00:00+09:00"
    assert row["system_known_at"] == "2026-09-20T00:00:00+00:00"
    assert row["available_at_verified"] is None and row["value"] == 3
    months = monthly_states([row], "macro", start_month="2015-01", as_of="2015-03-01")
    assert months[0]["value"] is None and months[1]["value"] == 3


def test_price_month_end_close_not_known_in_same_korean_month():
    row = normalize("2015-01-31", kind="etf", close=100)
    assert row["available_at_assumed"].startswith("2015-02-01T14:00")
    months = monthly_states([row], "etf", start_month="2015-01", as_of="2015-02-01")
    assert months[0]["value"] is None


def test_cot_formula_and_regular_clock_obey_dst():
    winter = normalize("2015-01-06 00:00:00", kind="cot", noncommPositionsLongAll=60, noncommPositionsShortAll=10, openInterestAll=100)
    summer = normalize("2015-07-07 00:00:00", kind="cot", noncommPositionsLongAll=10, noncommPositionsShortAll=60, openInterestAll=100)
    assert winter["value"] == 0.5 and summer["value"] == -0.5
    assert winter["available_at_assumed"] == "2015-01-10T05:30:00+09:00"
    assert summer["available_at_assumed"] == "2015-07-11T04:30:00+09:00"


def test_known_cot_delay_not_plus_three_days_and_old_positions_are_stale():
    row = normalize("2025-09-30 00:00:00", kind="cot", noncommPositionsLongAll=60, noncommPositionsShortAll=10, openInterestAll=100)
    assert row["available_at_assumed"] == "2025-11-20T05:30:00+09:00"
    months = monthly_states([row], "cot", start_month="2025-10", as_of="2025-12-01")
    assert months[0]["reason"] == "NO_AVAILABLE_OBSERVATION"
    assert months[1]["reason"] == "STALE_OBSERVATION"


def test_known_unresolved_cot_outage_excluded_without_invented_clock():
    row = normalize("2019-01-15 00:00:00", kind="cot", noncommPositionsLongAll=1, noncommPositionsShortAll=0, openInterestAll=2)
    assert row["available_at_assumed"] is None
    assert row["excluded_reason"] == "KNOWN_COT_OUTAGE_RELEASE_DATE_UNRESOLVED"
    assert row["system_known_at"].startswith("2026-")


def test_macro_expanding_median_excludes_current_and_future():
    records = [normalize(str(m.start_time.date()), actual=i) for i, m in enumerate(pd.period_range("2015-01", "2017-02", freq="M"))]
    result = monthly_states(records, "macro", start_month="2015-01", as_of="2017-02-01")
    assert all(r["state"] == "UNKNOWN" for r in result[:24])
    assert result[24]["threshold"] == 11.5 and result[24]["state"] == "HIGH"
    changed = deepcopy(records)
    changed[-1]["value"] = -999999
    assert monthly_states(changed, "macro", start_month="2015-01", as_of="2017-02-01") == result


def test_macro_staleness_prevents_indefinite_fill():
    record = normalize("2015-01-01 00:00:00", actual=3)
    months = monthly_states([record], "macro", start_month="2015-01", as_of="2015-04-01")
    assert months[0]["value"] == 3 and months[1]["value"] == 3
    assert months[2]["value"] is None and months[2]["reason"] == "STALE_OBSERVATION"


def test_same_time_conflicts_are_unknown_null_duplicate_retains_numeric():
    first = normalize("2015-01-20 00:00:00", actual=3)
    conflict = normalize("2015-01-20 00:00:00", actual=4)
    null = normalize("2015-01-20 00:00:00", actual=None)
    unknown = monthly_states([first, conflict], "macro", start_month="2015-01", as_of="2015-02-01")[0]
    unambiguous = monthly_states([first, null], "macro", start_month="2015-01", as_of="2015-02-01")[0]
    assert unknown["reason"] == "CONFLICTING_SAME_TIME_VALUES"
    assert unambiguous["value"] == 3 and len(unambiguous["selected_observation_ids"]) == 2


def test_price_momentum_requires_all_four_monthly_observations():
    dates = ("2015-01-30", "2015-02-27", "2015-03-30", "2015-04-29")
    records = [normalize(day, kind="fx", close=100+i) for i, day in enumerate(dates)]
    rows = monthly_states(records, "fx", start_month="2015-01", as_of="2015-05-01")
    assert rows[-1]["state"] == "UP" and rows[-1]["effective_month"] == "2015-05"
    rows = monthly_states([records[0], *records[2:]], "fx", start_month="2015-01", as_of="2015-05-01")
    assert rows[-1]["state"] == "UNKNOWN"


def test_partial_current_month_excluded_and_rule_label_explicit():
    assert str(completed_end_month("2026-09-21")) == "2026-08"
    assert classification_rules("cot")["pit_status"] == "PIT_ASSUMED"
    assert classification_rules("macro")["economic_good_bad_interpretation"] is False
    with pytest.raises(ValueError):
        completed_end_month("2026-09-21T12:00:00")
