"""SQL input/safety contracts and raw fixtures; live PostgreSQL is separate.

The fixture expectations below are checked against the Python implementation,
but are never passed to PostgreSQL. These unit tests alone do NOT establish
PostgreSQL parity: callers must execute FLOW_TTM_SQL on a read-only connection.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from engine import fundamental_sql as sql
from engine import fundamentals as fu


def _rows(points, *, metric="revenue"):
    return [
        {"asset_id": 1, "period_end": period_end, "fiscal_period": label,
         "fs_type": "CFS", "metric": metric, "value": value,
         "available_date": (datetime.fromisoformat(period_end) + timedelta(days=45)).date().isoformat(),
         "revision_key": f"original-{index:02}"}
        for index, (period_end, label, value) in enumerate(points)
    ]


def synthetic_revision_cases():
    """Raw inputs/targets plus separate manual expectations for live runners."""
    calendar = [
        ("2021-03-31", "Q1", 10), ("2021-06-30", "Q2", 20),
        ("2021-09-30", "Q3", 30), ("2021-12-31", "Q4", 40),
    ]
    non_december = [
        ("2021-06-30", "Q1", 10), ("2021-09-30", "Q2", 20),
        ("2021-12-31", "Q3", 30), ("2022-03-31", "FY", 100),
    ]
    weekly = [
        ("2021-05-01", "Q1", 10), ("2021-07-31", "Q2", 20),
        ("2021-10-30", "Q3", 30), ("2022-02-05", "FY", 100),
    ]
    cases = []

    def add(name, rows, expected, *, dates=None, metric="revenue"):
        dates = dates or ["2023-05-31"]
        cases.append({"case": name, "rows": rows,
                      "targets": [{"asset_id": 1, "as_of_date": date, "metric": metric}
                                  for date in dates],
                      "expected_ttm": expected})

    add("consecutive_calendar", _rows(calendar), [100.0])
    add("missing_q3", _rows([
        calendar[0], calendar[1], calendar[3], ("2022-03-31", "Q1", 10),
    ]), [None])
    add("fy_residual", _rows([*calendar[:3], ("2021-12-31", "FY", 100)]), [100.0])
    add("fy_incomplete", _rows([calendar[0], calendar[2], ("2021-12-31", "FY", 100)]), [None])
    add("non_december_fy", _rows(non_december), [100.0])
    add("53_week_fy", _rows(weekly), [100.0])
    add("53_week_prior_boundary", _rows([("2021-01-30", "FY", 80), *weekly]), [100.0])
    add("conflicting_endpoint_labels", _rows([*calendar, ("2021-12-31", "Q3", 999)]), [None])
    add("unresolved_latest_fy", _rows([*calendar, ("2022-12-31", "FY", 100)]), [None])
    add("changed_fy_boundary", _rows([
        ("2021-01-31", "FY", 80), *calendar[:3], ("2021-12-31", "FY", 100),
    ]), [None])
    add("explicit_q4_preserved", _rows([*calendar, ("2021-12-31", "FY", 1000)]), [100.0])
    add("latest_null_quarter", _rows([*calendar, ("2022-03-31", "Q1", None)]), [None])
    add("unknown_period_label_barrier", _rows([*calendar, ("2022-03-31", "H1", 10)]), [None])
    add("empty_history", [], [None])

    cfs_rows = _rows(calendar)
    later_ofs = {**cfs_rows[2], "fs_type": "OFS", "value": 999,
                 "available_date": "2022-06-01", "revision_key": "late-ofs"}
    add("older_cfs_beats_later_ofs", [*cfs_rows, later_ofs], [100.0])
    later_cfs = {**cfs_rows[2], "value": 35,
                 "available_date": "2022-06-01", "revision_key": "late-cfs"}
    add("later_cfs_revision", [*cfs_rows, later_cfs], [100.0, 105.0],
        dates=["2022-05-31", "2022-06-30"])
    tie_low = {**later_cfs, "value": 31, "revision_key": "a"}
    tie_high = {**later_cfs, "value": 35, "revision_key": "z"}
    add("revision_key_tie_break", [*cfs_rows, tie_low, tie_high], [105.0])
    null_revision = {**later_cfs, "value": None}
    repaired = {**later_cfs, "available_date": "2022-07-01", "revision_key": "repaired"}
    add("null_revision_then_repair", [*cfs_rows, null_revision, repaired],
        [100.0, None, 105.0], dates=["2022-05-31", "2022-06-30", "2022-07-31"])
    late_missing = {**cfs_rows[2], "available_date": "2022-06-01", "revision_key": "late-q3"}
    add("late_missing_quarter", [cfs_rows[0], cfs_rows[1], cfs_rows[3], late_missing],
        [None, 100.0], dates=["2022-05-31", "2022-06-30"])
    for metric in sorted(fu.FLOW - {"revenue"}):
        add(f"flow_{metric}", _rows(calendar, metric=metric), [100.0], metric=metric)
    return cases


@pytest.mark.parametrize("case", synthetic_revision_cases(), ids=lambda case: case["case"])
def test_fixture_expectations_match_python_but_are_never_sql_parameters(case):
    raw = pd.DataFrame(case["rows"])
    snapshots = fu.materialize_pit(raw, verbose=False)
    for target, expected in zip(case["targets"], case["expected_ttm"], strict=True):
        matches = snapshots[
            snapshots["asset_id"].eq(target["asset_id"])
            & snapshots["available_date"].le(pd.Timestamp(target["as_of_date"]))
        ]
        actual = matches.iloc[-1][f"{target['metric']}_ttm"] if len(matches) else None
        if expected is None:
            assert actual is None or pd.isna(actual)
        else:
            assert actual == pytest.approx(expected)
    serialized = sql.flow_ttm_parameters(case["rows"], case["targets"])
    assert "expected_ttm" not in "".join(serialized)
    assert "ttm_value" not in "".join(serialized)
    assert len(json.loads(serialized[0])) == len(case["rows"])


def test_sql_text_is_query_only_and_contains_independent_replay():
    assert sql.FLOW_TTM_SQL.lstrip().startswith("WITH RECURSIVE")
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|CALL|COPY|TRUNCATE|DO)\b",
                         sql.FLOW_TTM_SQL, re.IGNORECASE)
    assert ";" not in sql.FLOW_TTM_SQL
    assert sql.FLOW_TTM_SQL.count("%s") == 2
    assert sql.CONTIGUITY_SQL.count("%s") == 1
    assert "row_number() OVER" in sql.FLOW_TTM_SQL
    assert "available_date <= target.as_of_date" in sql.FLOW_TTM_SQL
    assert "COLLATE \"C\" DESC" in sql.FLOW_TTM_SQL
    assert "fiscal_year.value - preceding.total" in sql.FLOW_TTM_SQL
    assert "FROM replay prior_state" in sql.FLOW_TTM_SQL
    assert "INVALID" in sql.FLOW_TTM_SQL
    assert sql.sql_sha256() == hashlib.sha256(sql.FLOW_TTM_SQL.encode()).hexdigest()


def test_parameter_builder_does_not_compute_financial_results(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("SQL parameters cannot contain Python-computed factor or TTM results")
    monkeypatch.setattr(fu, "_snapshot", forbidden)
    monkeypatch.setattr(fu, "_standalone_flow", forbidden)
    monkeypatch.setattr(fu, "is_contiguous_fiscal_quarters", forbidden)
    monkeypatch.setattr(fu, "materialize_pit", forbidden)
    case = synthetic_revision_cases()[0]
    before = copy.deepcopy(case)
    rows, targets = sql.flow_ttm_parameters(case["rows"], case["targets"])
    assert len(json.loads(rows)) == 4
    assert len(json.loads(targets)) == 1
    assert case == before


def test_explicit_null_is_not_dropped_or_replaced():
    case = next(case for case in synthetic_revision_cases() if case["case"] == "null_revision_then_repair")
    rows, _ = sql.flow_ttm_parameters(case["rows"], case["targets"])
    parsed = json.loads(rows)
    assert len(parsed) == 6
    assert parsed[4]["value"] is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True, "100"])
def test_invalid_json_values_fail_before_database(value):
    case = synthetic_revision_cases()[0]
    case["rows"][0]["value"] = value
    with pytest.raises(ValueError):
        sql.flow_ttm_parameters(case["rows"], case["targets"])


@pytest.mark.parametrize("field,value", [
    ("asset_id", True), ("asset_id", -1), ("asset_id", 1.5),
    ("asset_id", 2**63), ("period_end", "bad-date"),
    ("available_date", "2022-01-01T00:00:00+09:00"),
    ("metric", "total_assets"), ("revision_key", ""),
])
def test_invalid_raw_row_identity_is_rejected(field, value):
    case = synthetic_revision_cases()[0]
    case["rows"][0][field] = value
    with pytest.raises(ValueError):
        sql.flow_ttm_parameters(case["rows"], case["targets"])


def test_ambiguous_priority_and_target_duplicates_are_rejected():
    case = synthetic_revision_cases()[0]
    with pytest.raises(ValueError, match="identical-priority"):
        sql.flow_ttm_parameters([*case["rows"], case["rows"][0]], case["targets"])
    with pytest.raises(ValueError, match="Duplicate target"):
        sql.flow_ttm_parameters(case["rows"], case["targets"] * 2)


def test_contiguity_parameters_preserve_order_and_nulls():
    points = [{"period_end": "2021-06-30", "fiscal_period": "Q2", "value": None},
              {"period_end": "2021-03-31", "fiscal_period": "Q1", "value": 10}]
    serialized, = sql.continuity_parameters(points)
    assert [row["fiscal_period"] for row in json.loads(serialized)] == ["Q2", "Q1"]
    assert json.loads(serialized)[0]["value"] is None


def test_query_runner_requires_read_only_connection():
    for value in (False, None):
        with pytest.raises(ValueError, match="read-only"):
            sql.query_flow_ttm(SimpleNamespace(read_only=value), [], [])


def test_query_runner_sends_raw_parameters_and_returns_database_values_only():
    calls = []
    class Cursor:
        description = [SimpleNamespace(name="target_id"), SimpleNamespace(name="ttm_value")]
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def execute(self, query, params):
            calls.append((query, params))
        def fetchall(self):
            return [(0, 12345.0)]
    connection = SimpleNamespace(read_only=True, cursor=Cursor)
    case = synthetic_revision_cases()[0]
    assert sql.query_flow_ttm(connection, case["rows"], case["targets"]) == [
        {"target_id": 0, "ttm_value": 12345.0}
    ]
    assert calls == [(sql.FLOW_TTM_SQL, sql.flow_ttm_parameters(case["rows"], case["targets"]))]
