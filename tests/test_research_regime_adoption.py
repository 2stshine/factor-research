"""Assumed diagnostic adoption is not source certification or registry mutation."""
from copy import deepcopy
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from engine.regime_shadow import classify_daily_market
from engine.research_regime_adoption import (
    adopt_shadow_bundle, market_rows, validate_adoption,
)


def encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(",", ":")).encode()).hexdigest()


@pytest.fixture
def inputs(tmp_path):
    days = pd.bdate_range("2015-01-01", "2017-12-31")
    dates = list(days.strftime("%Y-%m-%d"))
    observations = pd.DataFrame({
        "trade_date": dates,
        "close": 100 * np.exp(np.cumsum(.0001 + .009 * np.sin(np.arange(len(days)) / 4))),
        "known_at": [day.tz_localize("Asia/Seoul") + pd.Timedelta(hours=23) for day in days],
    })
    expected = [day for day in dates if day.startswith("2017-12")]
    evidence = {
        "schema_version": "versioned-expected-market-sessions-v1", "month": "2017-12",
        "source_kind": "VERSIONED_CALENDAR_LIBRARY", "calendar_name": "XKRX",
        "package_version": "fixture-v1", "calendar_implementation_sha256": "e" * 64,
        "expected_sessions": expected,
    }
    evidence_path = tmp_path / "calendar.json"
    evidence_path.write_bytes(encode(evidence))
    completion = {
        "schema_version": "regime-shadow-month-completion-v1", "month": "2017-12",
        "market_ids": ["KOSPI", "KOSDAQ"], "complete_through": "2017-12-31",
        "calendar_evidence_file": evidence_path.name,
        "calendar_evidence_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
    }
    completion_path = tmp_path / "completion.json"
    completion_path.write_bytes(encode(completion))
    proof = {
        "contract_file": str(completion_path),
        "contract_sha256": hashlib.sha256(completion_path.read_bytes()).hexdigest(),
        "calendar_evidence_file": str(evidence_path),
        "calendar_evidence_sha256": completion["calendar_evidence_sha256"],
        "expected_sessions": expected, "complete_through": "2017-12-31",
    }
    bundle = {
        "schema_version": "local-krx-regime-shadow-bundle-v1",
        "created_at": "2018-01-01T10:00:00+09:00", "as_of": "2018-01-01",
        "status": "EXPERIMENTAL_SHADOW_NOT_APPROVED", "pit_status": "PIT_UNKNOWN",
        "factor_returns_accessed": False, "active_registry_changed": False,
        "db_accessed": False, "network_accessed": False,
        "compiler_sha256": "c" * 64, "engine_sha256": "e" * 64, "markets": {},
    }
    for market in ("KOSPI", "KOSDAQ"):
        data = classify_daily_market(
            observations, calendar_dates=dates, calendar_complete_through="2017-12-31",
            as_of="2018-01-01", market_id=market, source_id=f"fixture-{market}",
            start_month="2015-01", calendar_verified=False,
            known_at_semantics="ASSUMED_OBSERVATION_DAY_END_KST_NOT_RECEIPT")
        data["source_provenance"] = {
            "raw_files": [{"trade_date": day, "sha256": "a" * 64} for day in dates],
            "local_calendar": {"dates": dates, "semantics": "ASSUMED_UNION"},
            "last_complete_input_month": "2017-12", "explicit_month_completion": proof,
        }
        bundle["markets"][market] = data
    policy = {
        "schema_version": "regime-assumption-policy-v1", "policy_id": "fixture-policy",
        "user_authorized": True, "diagnostics_only": True, "new_campaigns_only": True,
        "historical_backtest_allowed_under_assumptions": True, "historical_pit_verified": False,
        "factor_feature_allowed": False, "intraday_allowed": False,
        "promotion_gates_unchanged": True, "raw_receipt_timestamps_must_be_preserved": True,
        "existing_approvals_must_not_be_relabelled": True,
        "automatic_gold_publication_allowed": False,
    }
    shadow_path, policy_path = tmp_path / "shadow.json", tmp_path / "policy.json"
    shadow_path.write_bytes(encode(bundle))
    policy_path.write_bytes(encode(policy))
    return shadow_path, policy_path, bundle, policy


def adopt(inputs, **kwargs):
    shadow, policy, *_rest = inputs
    options = dict(contract_id="new-real-diagnostic-v1", authorization_ref="user-request-20180101",
                   adopted_at="2018-01-01T11:00:00+09:00", start_month="2015-01", end_month="2017-12")
    options.update(kwargs)
    return adopt_shadow_bundle(shadow, policy, **options)


def test_scope_provenance_and_source_immutability(inputs):
    before = [path.read_bytes() for path in inputs[:2]]
    result = adopt(inputs, start_month="2016-04")
    assert result["pit_status"] == "PIT_ASSUMED"
    assert result["source_original_pit_status"] == "PIT_UNKNOWN"
    assert result["adoption_time_is_historical_availability"] is False
    assert result["factor_feature_allowed"] is False
    assert result["trading_allowed"] is False
    assert result["active_registry_changed"] is False
    assert result["raw_bytes_reverified"] is False
    assert result["source"]["sha256"] == hashlib.sha256(before[0]).hexdigest()
    assert before == [path.read_bytes() for path in inputs[:2]]
    for market in ("KOSPI", "KOSDAQ"):
        rows = market_rows(result, market)
        assert rows[0]["month"] == "2016-04"
        assert len(rows) == 21
        assert rows[-1]["effective_month"] == "2018-01"
        assert rows[-1]["original_pit_status"] == "PIT_UNKNOWN"
        assert rows[-1]["rv63_annualized"] == inputs[2]["markets"][market]["rows"][-1]["rv63_annualized"]
        rows[-1]["regime"] = "MUTATED_COPY"
        assert market_rows(result, market)[-1]["regime"] != "MUTATED_COPY"
    validate_adoption(result)


def test_unknown_preserved_and_conservative_completion_allowed(inputs):
    shadow, _policy, bundle, _ = inputs
    for market in bundle["markets"].values():
        market["source_provenance"]["explicit_month_completion"] = None
    shadow.write_bytes(encode(bundle))
    result = adopt(inputs)
    for market in ("KOSPI", "KOSDAQ"):
        first = market_rows(result, market)[0]
        assert first["status"] == first["regime"] == "UNKNOWN"
        assert first["pit_status"] == "PIT_ASSUMED"
        assert first["reason"]
        assert result["markets"][market]["completion_evidence"] is None


@pytest.mark.parametrize("change", ["unauthorized", "factor", "vintage", "old_campaign"])
def test_policy_cannot_broaden_authority(inputs, change):
    _shadow, policy_path, _bundle, policy = inputs
    key, value = {"unauthorized": ("user_authorized", False),
                  "factor": ("factor_feature_allowed", True),
                  "vintage": ("historical_pit_verified", True),
                  "old_campaign": ("new_campaigns_only", False)}[change]
    policy[key] = value
    policy_path.write_bytes(encode(policy))
    with pytest.raises(ValueError):
        adopt(inputs)


@pytest.mark.parametrize("kwargs", [
    {"adopted_at": "2018-01-01"}, {"adopted_at": "2017-12-31T23:59:00+09:00"},
    {"start_month": "2017-1"}, {"start_month": "2014-12"},
    {"start_month": "2018-01", "end_month": "2017-12"}, {"end_month": "2018-01"},
    {"authorization_ref": ""},
])
def test_timing_scope_and_authorization(inputs, kwargs):
    with pytest.raises(ValueError):
        adopt(inputs, **kwargs)


@pytest.mark.parametrize("change", ["market", "mapping", "clock", "current_reference", "label",
                                    "pit", "calendar", "duplicate", "missing", "rule", "performance", "extra_outcome"])
def test_source_semantic_corruption_rejected(inputs, change):
    shadow, _policy, bundle, _ = inputs
    market = bundle["markets"]["KOSPI"]
    row = market["rows"][-1]
    if change == "market":
        row["market_id"] = "KOSDAQ"
    elif change == "mapping":
        row["effective_month"] = row["month"]
    elif change == "clock":
        row["decision_at"] = "2017-12-01T00:00:00+09:00"
    elif change == "current_reference":
        row["prior_reference_months"][-1] = row["month"]
    elif change == "label":
        row["regime"] = "UP_UNKNOWN"
    elif change == "pit":
        row["pit_status"] = "PIT_VERIFIED"
    elif change == "calendar":
        row["calendar_verified"] = True
    elif change == "duplicate":
        market["rows"].append(deepcopy(row))
    elif change == "missing":
        market["rows"].pop(20)
    elif change == "rule":
        market["rules"]["reference_months"] = 6
    elif change == "extra_outcome":
        row["hidden_factor_return"] = "FORBIDDEN_CANARY"
    else:
        bundle["factor_returns_accessed"] = True
    shadow.write_bytes(encode(bundle))
    with pytest.raises(ValueError):
        adopt(inputs)


@pytest.mark.parametrize("change", ["hash", "calendar_gap", "observed_gap", "path_escape"])
def test_calendar_completion_checked(inputs, change):
    shadow, _policy, bundle, _ = inputs
    source = bundle["markets"]["KOSPI"]["source_provenance"]
    if change == "hash":
        (shadow.parent / "calendar.json").write_text("{}")
    elif change == "calendar_gap":
        source["local_calendar"]["dates"].pop()
    elif change == "observed_gap":
        source["raw_files"].pop()
    else:
        source["explicit_month_completion"]["contract_file"] = str(shadow.parent.parent / "outside.json")
    shadow.write_bytes(encode(bundle))
    with pytest.raises(ValueError):
        adopt(inputs)


def test_frozen_contract_tamper_and_rehashed_authority_escalation(inputs):
    result = adopt(inputs)
    result["markets"]["KOSPI"]["rows"][-1]["regime"] = "CORRUPTED"
    with pytest.raises(ValueError, match="hash"):
        validate_adoption(result)
    result = adopt(inputs)
    result["factor_feature_allowed"] = True
    result.pop("contract_sha256")
    result["contract_sha256"] = digest(result)
    with pytest.raises(ValueError, match="boundary"):
        validate_adoption(result)


def test_unknown_market_is_not_implicitly_pooled(inputs):
    with pytest.raises(ValueError):
        market_rows(adopt(inputs), "TOTAL")
