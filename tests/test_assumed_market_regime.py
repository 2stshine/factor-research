from copy import deepcopy
import json

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts.build_assumed_market_regime import collect_local, monthly_rows, build


def observations():
    dates = ["2015-01-02", "2015-01-30", "2015-02-02", "2015-02-27", "2015-03-02"]
    rows = [{"trade_date": d, "close": 100.0 + i} for i, d in enumerate(dates)]
    return rows, dates


def test_latest_raw_partial_month_excluded_and_actual_trade_day_preserved():
    daily, dates = observations()
    rows, checks = monthly_rows(daily, dates, as_of="2015-04-21")
    assert [r["month"] for r in rows] == ["2015-01", "2015-02"]
    assert rows[-1]["source_trade_date"] == "2015-02-27"
    assert rows[-1]["known_at"] == "2015-02-28T23:59:59"
    assert checks["excluded_latest_raw_month"] == "2015-03"
    assert checks["actual_publication_times_verified"] is False


def test_missing_target_day_relative_to_other_calendar_blocks():
    daily, dates = observations()
    with pytest.raises(ValueError, match="daily gap"):
        monthly_rows(daily[1:], dates, as_of="2015-04-21")


def test_missing_whole_middle_month_blocks():
    daily, dates = observations()
    daily = [r for r in daily if not r["trade_date"].startswith("2015-02")]
    dates = [d for d in dates if not d.startswith("2015-02")]
    with pytest.raises(ValueError, match="full calendar month"):
        monthly_rows(daily, dates, as_of="2015-04-21")


def test_conflicting_or_identical_duplicate_days_block():
    daily, dates = observations()
    for value in [daily[0], {**daily[0], "close": 999.0}]:
        with pytest.raises(ValueError, match="Duplicate index trade date"):
            monthly_rows(daily + [value], dates, as_of="2015-04-21")


def test_not_near_month_end_blocks_and_no_values_are_filled():
    daily = [{"trade_date": "2015-01-02", "close": 100.0},
             {"trade_date": "2015-02-02", "close": 101.0}]
    with pytest.raises(ValueError, match="near-month-end"):
        monthly_rows(daily, [r["trade_date"] for r in daily], as_of="2015-03-21")


def test_future_values_cannot_change_prior_monthly_observations():
    daily, dates = observations()
    before, _ = monthly_rows(daily, dates, as_of="2015-03-21")
    changed = deepcopy(daily) + [{"trade_date": "2099-01-01", "close": 999999.0}]
    after, _ = monthly_rows(changed, dates + ["2099-01-01"], as_of="2015-03-21")
    assert before == after


def test_collect_rejects_duplicate_index_and_partition_mismatch(tmp_path):
    path = tmp_path / "index/krxapi/date=2015-01-02/kospi.parquet"
    path.parent.mkdir(parents=True)
    row = {"BAS_DD": "20150102", "IDX_NM": "코스피", "CLSPRC_IDX": "1,000.00"}
    pq.write_table(pa.Table.from_pylist([row, row]), path)
    with pytest.raises(ValueError, match="exactly one"):
        collect_local(tmp_path, "KOSPI", "2015-02-01")
    pq.write_table(pa.Table.from_pylist([{**row, "BAS_DD": "20150105"}]), path)
    with pytest.raises(ValueError, match="differs from partition"):
        collect_local(tmp_path, "KOSPI", "2015-02-01")


def test_real_acceptance_wiring_and_warmup_without_claiming_verified_pit(tmp_path):
    data = tmp_path / "data"
    for i, month in enumerate(pd.period_range("2015-01", "2018-02", freq="M")):
        day = month.end_time.date()
        path = data / f"index/krxapi/date={day.isoformat()}/kospi.parquet"
        path.parent.mkdir(parents=True)
        pq.write_table(pa.Table.from_pylist([{"BAS_DD": day.strftime("%Y%m%d"),
            "IDX_NM": "코스피", "CLSPRC_IDX": str(100 + i)}]), path)
    policy = {"schema_version": "regime-assumption-policy-v1", "policy_id": "test-policy",
              "authorization_text": "Synthetic explicit assumption policy",
              "user_authorized": True, "new_campaigns_only": True,
              "diagnostics_only": True, "promotion_gates_unchanged": True,
              "factor_feature_allowed": False, "historical_pit_verified": False}
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy))
    output = tmp_path / "context"
    summary = build(data, output, policy_path, as_of="2018-03-21")
    assert summary["source_months"] == 37
    assert summary["first_all_four_axes_ready_month"] == "2018-01"
    assert summary["historical_pit_verified"] is False
    approval = json.loads((output / "approval.json").read_text())
    assert approval["status"] == "ASSUMPTION_ACCEPTED"
    assert approval["pit_approved"] is False
    with pytest.raises(FileExistsError):
        build(data, output, policy_path, as_of="2018-03-21")
