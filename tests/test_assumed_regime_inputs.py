"""Explicit user assumptions are diagnostic contracts, never PIT evidence.

Only synthetic contexts are used. No existing campaign, API, or database is read.
"""
from copy import deepcopy
import hashlib
import json

import pandas as pd
import pytest

from engine.regime_inputs import (
    ASSUMPTION_SCHEMA, ASSUMED_AVAILABILITY, VERSION, campaign_context, digest,
    freeze_context, make_assumption_acceptance, read_context,
)
from engine.mechanism_capture import capture_discovery
from tests.test_regime_inputs import bundle
from tests.test_mechanism_capture import fixture


def policy():
    return {"schema_version": "regime-assumption-policy-v1",
            "policy_id": "synthetic-user-acceptance-v1",
            "user_authorized": True,
            "authorization_text": "Synthetic test consent; not a real historical PIT review.",
            "new_campaigns_only": True, "diagnostics_only": True,
            "factor_feature_allowed": False, "promotion_gates_unchanged": True,
            "historical_pit_verified": False}


def accept(source, accepted_policy=None):
    return make_assumption_acceptance(source, accepted_policy or policy(),
        [{"uri": "synthetic://assumption-evidence", "sha256": "3" * 64}],
        accepted_at="2026-01-01T00:00:00Z")


def assumed_bundle(*, market=False):
    value = bundle()
    selected = value["contexts"] if market else value["contexts"][1:]
    for item in selected:
        source = item["source"]
        source.update(pit_status="PIT_ASSUMED", known_at_semantics=ASSUMED_AVAILABILITY,
                      assumptions=["Treat provider historical values as available by stated month end."],
                      scope={"start_month": "2014-01", "end_month": "2022-12"},
                      provenance={"provider": "SYNTHETIC", "raw_sha256": "a" * 64})
        item["approval"] = accept(source)
    return value


def campaign(value):
    *_, result = fixture()
    result["diagnostic_regimes"] = freeze_context(value,
        data_cutoff=result["discovery"]["data_cutoff"], oos_start=result["oos"]["start"])
    return result


def test_acceptance_explicitly_keeps_verification_flags_false():
    item = assumed_bundle()["contexts"][1]
    approval = item["approval"]
    assert approval["schema_version"] == ASSUMPTION_SCHEMA
    assert approval["status"] == "ASSUMPTION_ACCEPTED"
    assert approval["source_layer"] == "DERIVED_RESEARCH_CONTEXT"
    assert approval["historical_backtest_allowed"] is True
    for key in ("pit_approved", "publication_time_verified", "publication_date_verified",
                "historical_availability_verified", "revision_history_verified",
                "factor_feature_allowed", "intraday_allowed"):
        assert approval[key] is False
    assert approval["source_sha256"] == digest(item["source"])
    assert approval["assumption_policy"] == policy()
    assert approval["assumption_policy_sha256"] == digest(policy())


@pytest.mark.parametrize("field", ["user_authorized", "new_campaigns_only", "diagnostics_only",
                                  "promotion_gates_unchanged", "factor_feature_allowed", "historical_pit_verified"])
def test_acceptance_rejects_wrong_policy_flags(field):
    p = policy()
    p[field] = not p[field]
    with pytest.raises(ValueError):
        accept(assumed_bundle()["contexts"][1]["source"], p)


@pytest.mark.parametrize("field", ["policy_id", "authorization_text"])
def test_acceptance_requires_explicit_nonempty_policy_identity_and_authorization(field):
    p = policy()
    p[field] = "   "
    with pytest.raises(ValueError):
        accept(assumed_bundle()["contexts"][1]["source"], p)


@pytest.mark.parametrize("field,value", [
    ("pit_status", "PIT_VERIFIED"), ("known_at_semantics", "VERIFIED"),
    ("assumptions", []), ("assumptions", [""]), ("assumptions", [1]),
    ("scope", {"start_month": "2025-01", "end_month": "2024-01"}),
    ("scope", {"start_month": "2024-13", "end_month": "2025-01"}),
])
def test_acceptance_requires_source_assumptions_and_valid_scope(field, value):
    source = assumed_bundle()["contexts"][1]["source"]
    source[field] = value
    with pytest.raises(ValueError):
        accept(source)


@pytest.mark.parametrize("field", ["pit_approved", "publication_time_verified", "publication_date_verified",
                                  "historical_availability_verified", "revision_history_verified",
                                  "factor_feature_allowed", "intraday_allowed"])
def test_assumption_cannot_claim_verification_or_feature_permission(field):
    value = assumed_bundle()
    value["contexts"][1]["approval"][field] = True
    with pytest.raises(ValueError):
        campaign(value)


def test_source_policy_and_evidence_tamper_fail_closed():
    for change in ("source", "policy", "evidence", "reviewer"):
        value = assumed_bundle()
        item = value["contexts"][1]
        if change == "source":
            item["source"]["assumptions"].append("Different assumption")
        elif change == "policy":
            item["approval"]["assumption_policy"]["authorization_text"] += " Changed"
        elif change == "evidence":
            item["approval"]["evidence"] = []
        else:
            item["approval"]["reviewer"] = ""
        with pytest.raises(ValueError):
            campaign(value)


def test_scope_is_enforced_on_retained_input_rows():
    value = assumed_bundle()
    item = value["contexts"][1]
    item["source"]["scope"]["start_month"] = "2015-01"
    item["approval"] = accept(item["source"])
    with pytest.raises(ValueError, match="outside accepted scope"):
        campaign(value)


def test_mixed_context_metadata_preserves_verified_and_assumed_distinction():
    c = campaign(assumed_bundle())
    frozen = c["diagnostic_regimes"]
    assert frozen["pit_status"] == "PIT_ASSUMED"
    assert frozen["assumed_context_ids"] == ["test_macro"]
    assert frozen["verified_context_ids"] == ["test_market"]
    assert frozen["contexts"][1]["provenance"]["provider"] == "SYNTHETIC"
    market, macro, metadata = campaign_context(c)
    assert metadata["status"] == "FROZEN_ASSUMED_INPUT"
    assert metadata["assumption_policy_sha256s"] == [digest(policy())]
    assert "pit_status" not in market.columns
    assert macro["test_macro"]["pit_status"] == "PIT_ASSUMED"
    assert macro["test_macro"]["assumptions"]


def test_assumed_market_is_labeled_without_changing_classification_math():
    normal, _, _ = campaign_context(campaign(bundle()))
    assumed, _, metadata = campaign_context(campaign(assumed_bundle(market=True)))
    assert (assumed["pit_status"] == "PIT_ASSUMED").all()
    pd.testing.assert_frame_equal(normal, assumed.drop(columns="pit_status"), check_flags=False)
    assert metadata["verified_context_ids"] == []


def test_assumption_policy_hash_changes_lesson_input_contract_identity():
    first = assumed_bundle()
    second = deepcopy(first)
    item = second["contexts"][1]
    different = policy()
    different["authorization_text"] += " Additional timing assumption."
    item["approval"] = accept(item["source"], different)
    before = campaign_context(campaign(first))[2]
    after = campaign_context(campaign(second))[2]
    assert before["input_contract_sha256"] != after["input_contract_sha256"]
    assert before["sha256"] != after["sha256"]


def test_assumed_late_missing_and_oos_are_still_guarded_and_propagated():
    value = assumed_bundle()
    item = value["contexts"][1]
    item["source"]["rows"] = [r for r in item["source"]["rows"] if r["month"] != "2021-04"]
    next(r for r in item["source"]["rows"] if r["month"] == "2021-05")["known_at"] = "2021-06-01"
    # These future values must be excluded before validation, not inspected as diagnostics.
    next(r for r in item["source"]["rows"] if r["month"] == "2021-07").update(state="INVALID", known_at="INVALID")
    item["approval"] = accept(item["source"])
    c = campaign(value)
    assert all(max(r["month"] for r in s["rows"]) == "2021-05" for s in c["diagnostic_regimes"]["contexts"])
    panel, frame, factor, result, _ = fixture()
    study = capture_discovery(panel, frame, factor, result, c, {})
    section = study["sections"]["regime_comparison"]
    view = section["data"]["macro_views"]["test_macro"]
    assert [r["state"] for r in view["monthly"][-2:]] == ["UNKNOWN", "UNKNOWN"]
    assert view["pit_status"] == "PIT_ASSUMED"
    assert view["assumption_policy_sha256"] == digest(policy())
    assert any("PIT_ASSUMED" in s for s in section["limitations"])
    frame.loc[frame.ym.ge(pd.Period("2021-06")), ["f_test", "fwd_mid", "net_income_ttm"]] = -999999
    assert capture_discovery(panel, frame, factor, result, c, {}) == study


def test_assumption_artifact_file_hash_contract_is_unchanged(tmp_path):
    prepared = assumed_bundle()
    items = []
    for i, item in enumerate(prepared["contexts"]):
        path = tmp_path / f"approval-{i}.json"
        body = json.dumps(item["approval"]).encode()
        path.write_bytes(body)
        items.append({"source": item["source"], "approval_file": path.name,
                      "approval_sha256": hashlib.sha256(body).hexdigest()})
    context = tmp_path / "context.json"
    context.write_text(json.dumps({"schema_version": VERSION, "contexts": items}))
    assert len(read_context(context)["contexts"]) == 2
    path.write_text("{}")
    with pytest.raises(ValueError, match="file hash mismatch"):
        read_context(context)


def test_verified_schema_cannot_disguise_an_assumed_source():
    value = bundle()
    item = value["contexts"][1]
    item["source"]["pit_status"] = "PIT_ASSUMED"
    item["approval"]["source_sha256"] = digest(item["source"])
    with pytest.raises(ValueError):
        campaign(value)


def test_strict_only_identity_and_schema_unchanged():
    c = campaign(bundle())
    frozen = c["diagnostic_regimes"]
    assert set(frozen) == {"schema_version", "data_cutoff", "last_signal_month",
                           "market_rules_version", "contexts", "purpose", "sha256"}
    _, macro, metadata = campaign_context(c)
    identity = [{k: s[k] for k in ("context_id", "source_id", "kind", "market_id",
                "states", "classification_rules") if k in s} for s in frozen["contexts"]]
    assert metadata == {"status": "FROZEN_PIT_INPUT", "sha256": frozen["sha256"],
                        "input_contract_sha256": digest(identity), "last_signal_month": "2021-05",
                        "context_ids": ["test_market", "test_macro"]}
    assert "pit_status" not in macro["test_macro"]


def test_assumption_contract_is_bound_into_actual_lesson_evidence_identity():
    from engine.lesson_evidence import build_packet
    from scripts.candidate_lessons import _regime_rules

    panel, frame, factor, result, _ = fixture()
    c = campaign(assumed_bundle())
    study = capture_discovery(panel, frame, factor, result, c, {})
    packet = build_packet({"visibility": "RELEASED_QUALITATIVE", "record_id": "synthetic",
                           "hypothesis_and_calculation": {}, "evidence": {}},
                          {"factor": {"definition_hash": "d"}, "mechanism_study": study}, None)
    section = packet["diagnostics"]["regime_comparison"]["data"]
    assert section["macro_views"]["test_macro"]["pit_status"] == "PIT_ASSUMED"
    assert {"version": "regime-input-contract-v1",
            "sha256": section["input_status"]["input_contract_sha256"]} in _regime_rules(packet)


def test_rehashed_frozen_policy_still_cannot_break_acceptance_binding():
    c = campaign(assumed_bundle())
    frozen = c["diagnostic_regimes"]
    frozen["contexts"][1]["approval"]["assumption_policy"]["authorization_text"] += " Changed"
    frozen["sha256"] = digest({k: v for k, v in frozen.items() if k != "sha256"})
    with pytest.raises(ValueError, match="Frozen PIT approval mismatch"):
        campaign_context(c)


def test_acceptance_cannot_claim_future_or_undated_authorization():
    source = assumed_bundle()["contexts"][1]["source"]
    for accepted_at in ("2099-01-01T00:00:00Z", "2026-01-01"):
        with pytest.raises(ValueError, match="review time"):
            make_assumption_acceptance(source, policy(),
                [{"uri": "synthetic://proof", "sha256": "3" * 64}], accepted_at=accepted_at)
