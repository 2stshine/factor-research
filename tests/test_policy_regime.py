"""PIT transformation and coarse-date approval contract, not factor outcomes."""
from copy import deepcopy
import hashlib
import json

import pytest

from engine.policy_regime import monthly_states, reconcile
from engine.regime_inputs import DAY_BOUND, digest, freeze_context, campaign_context, load_campaign_context
from scripts.prepare_bok_policy import parse_decision
from tests.test_regime_inputs import bundle


def decision(day, rate):
    return {"decision_date": day, "target_rate_pct": rate, "document_date_verified": True,
            "url": "https://official.example/" + day, "pdf_sha256": "a" * 64}


def fmp(day, rate):
    return {"series_id": "KR_POLICY_RATE", "received_at": "2026-09-20T00:00:00+00:00",
            "payload": {"date": day + " 19:00:00", "actual": rate, "country": "KR", "unit": "%"}}


def coarse_bundle():
    value = bundle()
    value["contexts"] = [value["contexts"][1]]
    item = value["contexts"][0]
    source = item["source"]
    source.update(macro_type="policy_rate", known_at_semantics=DAY_BOUND,
                  frequency="MONTH_END", value_semantics="ANNOUNCED_POLICY_TARGET")
    for row in source["rows"]:
        row["known_at"] += "T23:59:59"
    item["approval"].update(schema_version="pit-regime-approval-v2", source_sha256=digest(source),
        publication_date_verified=True, historical_availability_verified=True, publication_time_verified=False,
        intraday_allowed=False, factor_feature_allowed=False, availability_basis=DAY_BOUND,
        revision_basis="DATED_OFFICIAL_POLICY_DECISIONS")
    return value


def test_document_parser_excludes_percentage_point_change():
    text = "2015년 3월 12일 공보 한국은행 기준금리를 2.00%에서 1.75%로 0.25%p 하향조정하여 통화정책을 운용하기로 하였음"
    parsed = parse_decision(text, "2015-03-12")
    assert parsed["target_rate_pct"] == 1.75
    assert parsed["document_date_verified"] is True
    assert parse_decision(text, "2015-03-13")["document_date_verified"] is False


def test_reconciliation_uses_official_date_and_preserves_receipt_and_duplicates():
    rows = [fmp("2015-01-14", 2), fmp("2015-01-14", 2)]
    resolved = reconcile([decision("2015-01-15", 2)], rows)
    assert resolved[0]["available_at_upper_bound"] == "2015-01-15T23:59:59+09:00"
    assert resolved[0]["system_known_at"] == rows[0]["received_at"]
    assert resolved[0]["duplicate_excess"] == 1
    assert resolved[0]["provider_calendar_dates_corrected"] == 2
    assert len(resolved[0]["raw_fmp_rows"]) == 2


@pytest.mark.parametrize("mode", ["wrong_value", "wrong_unit", "missing_decision", "duplicate_official", "unverified_date"])
def test_unresolved_sources_cannot_be_curated(mode):
    official, rows = [decision("2015-01-15", 2)], [fmp("2015-01-15", 2)]
    if mode == "wrong_value":
        rows[0]["payload"]["actual"] = 1.75
    elif mode == "wrong_unit":
        rows[0]["payload"]["unit"] = "B"
    elif mode == "missing_decision":
        official.append(decision("2015-02-15", 2))
    elif mode == "duplicate_official":
        official.append(deepcopy(official[0]))
    else:
        official[0]["document_date_verified"] = False
    with pytest.raises(ValueError):
        reconcile(official, rows)


def test_month_end_release_included_but_next_month_release_cannot_leak():
    d = [decision("2014-10-01", 2), decision("2015-01-31", 1.75), decision("2015-02-01", 1.5)]
    jan = monthly_states(d, start="2015-01", end="2015-01")[0]
    assert jan["announced_target_rate_pct"] == 1.75
    assert jan["state"] == "EASING"
    assert jan["known_at"] == "2015-01-31T23:59:59"
    assert jan["latest_publication_date"] == "2015-01-31"


def test_missing_official_warmup_fails_not_filled():
    with pytest.raises(ValueError, match="warm-up"):
        monthly_states([decision("2015-01-02", 2)], start="2015-01", end="2015-01")


def test_coarse_official_publication_day_flows_through_real_adapter():
    frozen = freeze_context(coarse_bundle(), data_cutoff="2021-06-30", oos_start="2021-07")
    market, macro, _ = campaign_context({"diagnostic_regimes": frozen,
        "discovery": {"data_cutoff": "2021-06-30"}, "oos": {"start": "2021-07"}})
    assert market is None
    assert macro["test_macro"]["rows"][-1]["month"] == "2021-05"


@pytest.mark.parametrize("key,value", [
    ("publication_date_verified", False), ("historical_availability_verified", False),
    ("revision_history_verified", False), ("publication_time_verified", True),
    ("intraday_allowed", True), ("factor_feature_allowed", True),
    ("availability_basis", "ASSUMED_LAG"), ("revision_basis", "LATEST_PROVIDER_VALUES"),
])
def test_scoped_approval_cannot_be_replaced_by_generic_lag_or_missing_proof(key, value):
    b = coarse_bundle()
    b["contexts"][0]["approval"][key] = value
    with pytest.raises(ValueError, match="approved Silver"):
        freeze_context(b, data_cutoff="2021-06-30", oos_start="2021-07")


@pytest.mark.parametrize("key,value", [("macro_type", "fx"), ("frequency", "DAILY"),
    ("value_semantics", "ESTIMATED_ECONOMIC_STATISTIC"), ("known_at_semantics", "PROVIDER_DATE")])
def test_policy_approval_cannot_approve_other_data_types(key, value):
    b = coarse_bundle()
    item = b["contexts"][0]
    item["source"][key] = value
    item["approval"]["source_sha256"] = digest(item["source"])
    with pytest.raises(ValueError, match="approved Silver"):
        freeze_context(b, data_cutoff="2021-06-30", oos_start="2021-07")


def test_coarse_contract_rejects_backdated_clock():
    b = coarse_bundle()
    item = b["contexts"][0]
    item["source"]["rows"][0]["known_at"] = "2014-01-31T09:00:00"
    item["approval"]["source_sha256"] = digest(item["source"])
    with pytest.raises(ValueError, match="month-end decision bounds"):
        freeze_context(b, data_cutoff="2021-06-30", oos_start="2021-07")


def test_registered_context_loads_and_tampering_fails_closed(tmp_path):
    b = coarse_bundle()
    item = b["contexts"][0]
    approval = json.dumps(item["approval"]).encode()
    (tmp_path / "approval.json").write_bytes(approval)
    context = {"schema_version": b["schema_version"], "contexts": [{"source": item["source"],
        "approval_file": "approval.json", "approval_sha256": hashlib.sha256(approval).hexdigest()}]}
    body = json.dumps(context).encode()
    (tmp_path / "context.json").write_bytes(body)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"schema_version": "diagnostic-regime-registry-v1", "contexts": [
        {"enabled": True, "file": "context.json", "sha256": hashlib.sha256(body).hexdigest()}]}))
    assert load_campaign_context(registry_path=registry)["contexts"][0]["source"]["macro_type"] == "policy_rate"
    assert load_campaign_context(registry_path=registry, disabled=True) is None
    (tmp_path / "context.json").write_text("{}")
    with pytest.raises(ValueError, match="Registered regime context hash"):
        load_campaign_context(registry_path=registry)


def test_explicit_disable_and_explicit_context_conflict():
    with pytest.raises(ValueError, match="Cannot disable"):
        load_campaign_context(explicit_path="anything", disabled=True)


def test_v2_capture_delivers_macro_and_preserves_all_other_diagnostics():
    from engine.mechanism_capture import capture_discovery
    from tests.test_mechanism_capture import fixture
    panel, frame, factor, result, campaign = fixture()
    before = capture_discovery(panel, frame, factor, result, campaign, {})
    campaign["diagnostic_regimes"] = freeze_context(coarse_bundle(),
        data_cutoff=campaign["discovery"]["data_cutoff"], oos_start=campaign["oos"]["start"])
    after = capture_discovery(panel, frame, factor, result, campaign, {})
    for name in before["sections"]:
        if name != "regime_comparison":
            assert after["sections"][name] == before["sections"][name]
    section = after["sections"]["regime_comparison"]
    assert section["data"]["macro_views"]["test_macro"]["status"] == "AVAILABLE"
    assert section["status"] == "PARTIAL"  # Macro-only is not an official market-index regime.
