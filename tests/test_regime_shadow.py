"""Synthetic input-only checks. They do not certify any real market source."""
import json
import hashlib

import numpy as np
import pandas as pd
import pytest

from engine.regime_shadow import RULES, classify_daily_market
from scripts.research_regime_shadow import _completed_month, build


def sample():
    days = pd.bdate_range("2015-01-01", "2017-12-31")
    values = 100 * np.exp(np.cumsum(.0001 + .009 * np.sin(np.arange(len(days)) / 4)))
    return pd.DataFrame({"trade_date": days.strftime("%Y-%m-%d"), "close": values,
                         "known_at": [day.tz_localize("Asia/Seoul") + pd.Timedelta(hours=18) for day in days]})


def run(data, *, as_of="2017-12-31", calendar=None, coverage="2017-12-31", market="TEST"):
    return classify_daily_market(data, calendar_dates=list(sample().trade_date) if calendar is None else calendar,
        calendar_complete_through=coverage, as_of=as_of, market_id=market,
        source_id="synthetic-v1", start_month="2015-01")


def test_exact_formulas_reference_and_flags():
    data = sample()
    result = run(data)
    last = result["rows"][-1]
    assert last["status"] == "READY_SHADOW"
    rv63 = np.diff(np.log(data.close.iloc[-64:])).std(ddof=1) * np.sqrt(252)
    rv21 = np.diff(np.log(data.close.iloc[-22:])).std(ddof=1) * np.sqrt(252)
    assert last["rv63_annualized"] == pytest.approx(rv63)
    assert last["risk_change_21_over_63"] == pytest.approx(rv21 / rv63 - 1)
    previous = [row["rv63_annualized"] for row in result["rows"][-13:-1]]
    assert last["prior_12m_rv63_median"] == pytest.approx(np.median(previous))
    assert last["reference_values"] == previous
    prices = data.assign(month=data.trade_date.str[:7]).groupby("month").close.last()
    assert last["sma_10m"] == pytest.approx(prices.iloc[-10:].mean())
    assert last["trend_distance"] == pytest.approx(data.close.iloc[-1] / prices.iloc[-10:].mean() - 1)
    assert last["effective_month"] == "2018-01"
    assert result["pit_status"] == "PIT_UNKNOWN"
    assert result["approval_status"] == "NOT_APPROVED"
    assert result["factor_returns_accessed"] is False
    json.dumps(result, allow_nan=False)


def test_prefix_invariant_to_future_rows_and_modified_future_prices():
    data = sample()
    old = run(data[data.trade_date <= "2016-12-31"], as_of="2016-12-31")
    assert old["rows"] == run(data)["rows"][:24]
    changed = data.copy()
    changed.loc[changed.trade_date > "2016-12-31", "close"] *= 100
    assert old["rows"] == run(changed, as_of="2016-12-31")["rows"]


def test_threshold_excludes_current_month():
    data = sample()
    old = run(data)["rows"][-1]
    data.loc[data.index[-1], "close"] *= 2
    new = run(data)["rows"][-1]
    assert old["prior_12m_rv63_median"] == new["prior_12m_rv63_median"]
    assert old["rv63_annualized"] != new["rv63_annualized"]


def test_unfinished_month_and_unestablished_calendar_excluded():
    result = run(sample(), as_of="2017-12-15")
    assert result["rows"][-1]["month"] == "2017-11"
    last = run(sample(), coverage="2017-12-15")["rows"][-1]
    assert last["regime"] == "UNKNOWN"
    assert "CALENDAR_COVERAGE_NOT_ESTABLISHED" in last["reason"]


def test_late_input_never_repairs_old_snapshot():
    data = sample()
    index = data.index[data.trade_date == "2016-12-30"][0]
    data.loc[index, "known_at"] = pd.Timestamp("2017-02-01T00:00:00+09:00")
    rows = run(data)["rows"]
    assert rows[23]["regime"] == "UNKNOWN"
    assert "MISSING_OR_LATE_DAILY_OBSERVATION" in rows[23]["reason"]
    assert rows[24]["regime"] == "UNKNOWN"
    assert rows[25]["prior_reference_valid_months"] < 12
    assert rows[:24] == run(data, as_of="2016-12-31")["rows"]


def test_missing_session_breaks_risk_not_compressed_into_one_daily_return():
    data = sample()
    data = data[data.trade_date != "2017-11-01"]
    last = run(data)["rows"][-1]
    assert last["rv63_annualized"] is None
    assert last["regime"] == "UNKNOWN"


def test_missing_month_breaks_reference_and_empty_data_is_unknown():
    data = sample()
    data = data[~data.trade_date.str.startswith("2017-01")]
    result = run(data)
    assert result["rows"][-1]["prior_12m_rv63_median"] is None
    empty = run(data.iloc[:0])
    assert all(row["regime"] == "UNKNOWN" for row in empty["rows"])
    json.dumps(empty, allow_nan=False)


def test_empty_calendar_unknown_and_flat_market_defined():
    data = sample()
    empty = run(data.iloc[:0], calendar=[])
    assert all(row["status"] == "UNKNOWN" for row in empty["rows"])
    data["close"] = 100.0
    row = run(data)["rows"][-1]
    assert row["regime"] == "UP_LOW"
    assert row["rv63_prior_12m_percentile"] == 50
    assert row["risk_change_21_over_63"] is None


@pytest.mark.parametrize("change", ["naive", "early", "zero", "duplicate", "calendar_duplicate"])
def test_invalid_inputs_rejected(change):
    data = sample()
    calendar = list(data.trade_date)
    if change == "naive":
        data["known_at"] = data.known_at.dt.tz_localize(None)
    elif change == "early":
        data.loc[0, "known_at"] = pd.Timestamp("2014-12-31T23:00:00+09:00")
    elif change == "zero":
        data.loc[0, "close"] = 0
    elif change == "duplicate":
        data = pd.concat([data, data.iloc[:1]])
    else:
        calendar.append(calendar[0])
    with pytest.raises(ValueError):
        run(data, calendar=calendar)


def test_market_isolation_extra_labels_not_read_and_immutable_rules():
    data = sample()
    first = run(data, market="KOSPI")
    data["fwd_return"] = 999.0
    data["result"] = "forbidden-extra-column"
    assert first == run(data, market="KOSPI")
    second = run(data, market="KOSDAQ")
    assert first["rows"][-1]["input_sha256"] != second["rows"][-1]["input_sha256"]
    first["rules"]["risk_return_sessions"] = 5
    assert RULES["risk_return_sessions"] == 63


def completion_fixture(tmp_path, *, evidence_change=None, contract_change=None):
    expected = list(pd.bdate_range("2017-12-01", "2017-12-31").strftime("%Y-%m-%d"))
    evidence = {
        "schema_version": "versioned-expected-market-sessions-v1",
        "source_kind": "VERSIONED_CALENDAR_LIBRARY", "month": "2017-12",
        "calendar_name": "XKRX", "package_version": "synthetic-fixture",
        "calendar_implementation_sha256": "a" * 64,
        "expected_sessions": expected,
    }
    evidence.update(evidence_change or {})
    body = json.dumps(evidence).encode()
    (tmp_path / "calendar.json").write_bytes(body)
    contract = {
        "schema_version": "regime-shadow-month-completion-v1",
        "market_ids": ["KOSPI", "KOSDAQ"], "month": "2017-12",
        "complete_through": "2017-12-31", "calendar_evidence_file": "calendar.json",
        "calendar_evidence_sha256": hashlib.sha256(body).hexdigest(),
    }
    contract.update(contract_change or {})
    path = tmp_path / "completion.json"
    path.write_text(json.dumps(contract))
    return path, expected


def test_completion_is_opt_in_and_source_bound(tmp_path):
    path, expected = completion_fixture(tmp_path)
    daily = [{"trade_date": day} for day in expected]
    arguments = dict(market="KOSPI", daily=daily, calendar_dates=expected,
                     conservative_month="2017-11", as_of="2018-01-01")
    assert _completed_month(None, **arguments) == ("2017-11", None)
    month, proof = _completed_month(path, **arguments)
    assert month == "2017-12"
    assert proof["calendar_verified"] is False
    assert proof["historical_calendar_before_month_recertified"] is False
    assert proof["contract_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("problem", ["missing", "unexpected", "calendar_gap", "tamper",
                                     "partial_month", "different_market", "price_derived",
                                     "skip_month", "duplicate_expected"])
def test_completion_rejects_unestablished_coverage(tmp_path, problem):
    evidence_change = {"source_kind": "PRICE_DATE_UNION"} if problem == "price_derived" else {}
    if problem == "duplicate_expected":
        evidence_change["expected_sessions"] = ["2017-12-01", "2017-12-01"]
    contract_change = {"market_ids": ["KOSPI"]} if problem == "different_market" else {}
    path, expected = completion_fixture(tmp_path, evidence_change=evidence_change,
                                        contract_change=contract_change)
    daily = [{"trade_date": day} for day in expected]
    calendar = list(expected)
    if problem == "missing":
        daily.pop()
    if problem == "unexpected":
        daily.append({"trade_date": "2017-12-30"})
    if problem == "calendar_gap":
        calendar.pop()
    if problem == "tamper":
        (tmp_path / "calendar.json").write_text("{}")
    with pytest.raises(ValueError):
        _completed_month(path, market="KOSPI", daily=daily, calendar_dates=calendar,
                         conservative_month="2017-10" if problem == "skip_month" else "2017-11",
                         as_of="2017-12-15" if problem == "partial_month" else "2018-01-01")


def test_compiler_completion_extends_only_last_month_without_approval(tmp_path, monkeypatch):
    path, _expected = completion_fixture(tmp_path)
    data = sample()
    daily = data[["trade_date", "close"]].to_dict("records")
    calendar = {"dates": list(data.trade_date)}
    monkeypatch.setattr("scripts.research_regime_shadow.collect_local",
                        lambda *_args: (daily, [], calendar))
    plain_path, opted_path = tmp_path / "plain.json", tmp_path / "opted.json"
    build(data_dir=tmp_path, output=plain_path, as_of="2018-01-01")
    build(data_dir=tmp_path, output=opted_path, as_of="2018-01-01", completion_contract=path)
    plain, opted = json.loads(plain_path.read_bytes()), json.loads(opted_path.read_bytes())
    for market in ("KOSPI", "KOSDAQ"):
        assert plain["markets"][market]["rows"][:-1] == opted["markets"][market]["rows"][:-1]
        assert plain["markets"][market]["rows"][-1]["status"] == "UNKNOWN"
        assert opted["markets"][market]["rows"][-1]["status"] == "READY_SHADOW"
        assert opted["markets"][market]["rows"][-1]["pit_status"] == "PIT_UNKNOWN"
        assert opted["markets"][market]["rows"][-1]["calendar_verified"] is False
        assert opted["markets"][market]["source_provenance"]["explicit_month_completion"]
    assert opted["status"] == "EXPERIMENTAL_SHADOW_NOT_APPROVED"
    assert opted["active_registry_changed"] is False
    assert opted["factor_returns_accessed"] is False
    with pytest.raises(FileExistsError):
        build(data_dir=tmp_path, output=opted_path, as_of="2018-01-01", completion_contract=path)
