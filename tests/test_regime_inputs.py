"""Synthetic wiring checks, not real-data PIT approvals or factor evaluations."""
from copy import deepcopy
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from engine import epochs
from engine.regime_inputs import (
    VERSION, PIT_FLAGS, digest, read_context, freeze_context, campaign_context,
)
from engine.mechanism_capture import capture_discovery
from tests.test_mechanism_capture import fixture


def bundle():
    months = pd.period_range("2014-01", "2022-12", freq="M")
    market = {"context_id": "test_market", "source_id": "synthetic-index-v1",
              "kind": "market_index", "market_id": "TEST", "official_market_index": True,
              "rows": [{"month": str(m), "known_at": str(m.end_time.date()),
                        "close": float(100 * np.exp(.004 * i + .05 * np.sin(i)))}
                       for i, m in enumerate(months)]}
    macro = {"context_id": "test_macro", "source_id": "synthetic-macro-v1", "kind": "macro_state",
             "states": ["TIGHT", "LOOSE"],
             "classification_rules": {"version": "synthetic-only-v1", "method": "test-fixture"},
             "rows": [{"month": str(m), "known_at": str(m.end_time.date()),
                       "state": "TIGHT" if i % 6 < 3 else "LOOSE"} for i, m in enumerate(months)]}
    contexts = []
    for source in (market, macro):
        approval = {"schema_version": "pit-regime-approval-v1", "status": "APPROVED",
                    "source_layer": "SILVER", "purpose": "DIAGNOSTIC_ONLY",
                    "source_id": source["source_id"], "source_sha256": digest(source),
                    **{k: True for k in PIT_FLAGS}, "reviewer": "SYNTHETIC_TEST_ONLY",
                    "reviewed_at": "2026-01-01T00:00:00Z",
                    "evidence": [{"uri": "synthetic://fixture", "sha256": "1" * 64}]}
        contexts.append({"source": source, "approval": approval, "approval_sha256": "2" * 64})
    return {"schema_version": VERSION, "contexts": contexts}


def frozen_campaign():
    *_, campaign = fixture()
    campaign["diagnostic_regimes"] = freeze_context(bundle(),
        data_cutoff=campaign["discovery"]["data_cutoff"], oos_start=campaign["oos"]["start"])
    return campaign


def test_actual_capture_delivers_market_and_macro_without_changing_other_diagnostics():
    panel, frame, factor, result, campaign = fixture()
    before = capture_discovery(panel, frame, factor, result, campaign, {})
    campaign = frozen_campaign()
    after = capture_discovery(panel, frame, factor, result, campaign, {})
    for key in before["sections"]:
        if key != "regime_comparison":
            assert before["sections"][key] == after["sections"][key]
    section = after["sections"]["regime_comparison"]
    assert section["status"] == "AVAILABLE"
    assert section["data"]["input_status"]["status"] == "FROZEN_PIT_INPUT"
    assert section["data"]["monthly"][-1]["month"] == "2021-05"
    assert section["data"]["macro_views"]["test_macro"]["status"] == "AVAILABLE"
    assert {x["state"] for x in section["data"]["macro_views"]["test_macro"]["states"]} == {"TIGHT", "LOOSE", "UNKNOWN"}


@pytest.mark.parametrize("flag", PIT_FLAGS)
def test_unapproved_pit_is_not_passed(flag):
    value = bundle()
    value["contexts"][0]["approval"][flag] = False
    with pytest.raises(ValueError, match="approved Silver"):
        freeze_context(value, data_cutoff="2021-06-30", oos_start="2021-07")


@pytest.mark.parametrize("change", ["source", "layer", "evidence", "reviewer"])
def test_source_proof_is_required(change):
    value = bundle()
    item = value["contexts"][0]
    if change == "source":
        item["source"]["rows"][0]["close"] += 1
    elif change == "layer":
        item["approval"]["source_layer"] = "BRONZE"
    elif change == "evidence":
        item["approval"]["evidence"] = []
    else:
        item["approval"]["reviewer"] = ""
    with pytest.raises(ValueError):
        freeze_context(value, data_cutoff="2021-06-30", oos_start="2021-07")


def test_context_file_checks_separate_approval_hash(tmp_path):
    prepared = bundle()
    external = {"schema_version": VERSION, "contexts": []}
    for i, item in enumerate(prepared["contexts"]):
        path = tmp_path / f"approval-{i}.json"
        body = json.dumps(item["approval"]).encode()
        path.write_bytes(body)
        external["contexts"].append({"source": item["source"], "approval_file": path.name,
                                     "approval_sha256": hashlib.sha256(body).hexdigest()})
    context = tmp_path / "context.json"
    context.write_text(json.dumps(external))
    assert len(read_context(context)["contexts"]) == 2
    path.write_text("{}")
    with pytest.raises(ValueError, match="approval file hash"):
        read_context(context)


def test_late_macro_is_unknown_and_missing_month_is_not_filled():
    value = bundle()
    item = value["contexts"][1]
    item["source"]["rows"] = [r for r in item["source"]["rows"] if r["month"] != "2021-04"]
    next(r for r in item["source"]["rows"] if r["month"] == "2021-05")["known_at"] = "2021-06-01"
    item["approval"]["source_sha256"] = digest(item["source"])
    panel, frame, factor, result, campaign = fixture()
    campaign["diagnostic_regimes"] = freeze_context(value, data_cutoff="2021-06-30", oos_start="2021-07")
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    view = study["sections"]["regime_comparison"]["data"]["macro_views"]["test_macro"]
    assert view["status"] == "PARTIAL"
    assert [r["state"] for r in view["monthly"][-2:]] == ["UNKNOWN", "UNKNOWN"]


def test_frozen_input_and_boundary_tampering_fails():
    campaign = frozen_campaign()
    changed = deepcopy(campaign)
    changed["diagnostic_regimes"]["contexts"][0]["rows"][0]["close"] += 1
    with pytest.raises(ValueError, match="hash mismatch"):
        campaign_context(changed)
    campaign["discovery"]["data_cutoff"] = "2021-05-31"
    with pytest.raises(ValueError, match="boundary mismatch"):
        campaign_context(campaign)


def test_oos_and_embargo_rows_are_not_frozen_or_used():
    campaign = frozen_campaign()
    for source in campaign["diagnostic_regimes"]["contexts"]:
        assert max(r["month"] for r in source["rows"]) == "2021-05"
    panel, frame, factor, result, _ = fixture()
    original = capture_discovery(panel, frame, factor, result, campaign, {})
    frame.loc[frame.ym.ge(pd.Period("2021-06")), ["f_test", "fwd_mid", "net_income_ttm"]] = -999999
    assert capture_discovery(panel, frame, factor, result, campaign, {}) == original


def test_campaign_start_freezes_optional_context(tmp_path):
    path = epochs.start_campaign(tmp_path, "campaign-context", discovery_data_cutoff="2023-06-30",
        snapshot_cutoff="2026-07-31", snapshot_digest="a" * 64, discovery_snapshot_digest="b" * 64,
        snapshot_asset_identity_digest="c" * 64, discovery_asset_identity_digest="d" * 64,
        closure_asset_identity_digest="e" * 64, closure_asset_identity_cutoff="2026-08-31",
        diagnostic_regimes=bundle())
    campaign = json.loads(path.read_bytes())
    assert campaign["diagnostic_regimes"]["sha256"]
    assert campaign_context(campaign)[0] is not None


def test_packet_and_lesson_identity_receive_real_capture_not_manual_injection():
    from engine.lesson_evidence import build_packet
    from scripts.candidate_lessons import _regime_rules
    panel, frame, factor, result, _ = fixture()
    study = capture_discovery(panel, frame, factor, result, frozen_campaign(), {})
    packet = build_packet({"visibility": "RELEASED_QUALITATIVE", "record_id": "synthetic",
                           "hypothesis_and_calculation": {}, "evidence": {}},
                          {"factor": {"definition_hash": "d"}, "mechanism_study": study}, None)
    assert "test_macro" in packet["diagnostics"]["regime_comparison"]["data"]["macro_views"]
    assert any(x["id"] == "diagnostic.discovery.regime_comparison" for x in packet["evidence"])
    assert any(x["version"] == "regime-input-contract-v1" for x in _regime_rules(packet))


def test_bronze_report_passed_is_not_a_pit_approval(tmp_path):
    from scripts.regime_inputs import audit_bronze
    path = tmp_path / "verified.json"
    path.write_text(json.dumps({"status": "passed", "rows_by_series": {"TEST": 2},
        "rows": 2, "manifest_uri": "s3://synthetic/manifest.json", "pit_approved": False}))
    report = audit_bronze([path])
    assert report["bronze_rows"] == 2 and report["approved_regime_series"] == 0
    assert report["pit_approval_granted"] is False


def test_epoch_binding_rejects_rehashed_context_replacement():
    campaign = frozen_campaign()
    campaign.update(protocol_version=epochs.PROTOCOL_VERSION, ruleset_version=epochs.RULESET_VERSION)
    epoch = {"protocol_version": epochs.PROTOCOL_VERSION, "ruleset_version": epochs.RULESET_VERSION,
             "diagnostic_regimes_sha256": campaign["diagnostic_regimes"]["sha256"]}
    epochs._assert_current_state(campaign, epoch)
    frozen = campaign["diagnostic_regimes"]
    frozen["contexts"][0]["rows"][0]["close"] += 1
    frozen["sha256"] = digest({k: v for k, v in frozen.items() if k != "sha256"})
    with pytest.raises(ValueError, match="레짐 입력이 변경"):
        epochs._assert_current_state(campaign, epoch)


def test_old_campaign_does_not_automatically_read_new_files():
    *_, campaign = fixture()
    market, macro, status = campaign_context(campaign)
    assert market is None and macro == {} and status["status"] == "NOT_CONFIGURED"
