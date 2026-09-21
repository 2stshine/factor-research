"""Synthetic source snapshots/readiness/lesson integration; no live research."""
from copy import deepcopy
import hashlib
import json

import pytest

from engine.lesson_evidence import build_packet
from engine.mechanism_capture import capture_discovery
from engine.regime_inputs import VERSION, digest
from engine import scientist_review
from scripts.regime_readiness import audit_readiness, main as readiness_main
from scripts.regime_snapshot import snapshot
from tests.test_assumed_regime_inputs import accept, assumed_bundle, campaign, policy
from tests.test_mechanism_capture import fixture
from tests.test_regime_inputs import bundle
from tests.test_regime_readiness import setup, write


def publish_bundle(tmp_path, value):
    contexts = []
    for i, item in enumerate(value["contexts"]):
        approval_path = tmp_path / f"acceptance-{i}.json"
        sha = write(approval_path, item["approval"])
        contexts.append({"source": item["source"], "approval_file": approval_path.name,
                         "approval_sha256": sha})
    context_sha = write(tmp_path / "context.json", {"schema_version": VERSION, "contexts": contexts})
    write(tmp_path / "registry.json", {"schema_version": "diagnostic-regime-registry-v1",
        "contexts": [{"enabled": True, "file": "context.json", "sha256": context_sha}]})
    return tmp_path / "registry.json"


def assume_source(tmp_path, source):
    source.update(pit_status="PIT_ASSUMED", known_at_semantics="ASSUMED_HISTORICAL_AVAILABILITY",
                  assumptions=["Synthetic user accepts timing and historical values as assumptions."])
    item = {"source": source, "approval": accept(source)}
    return publish_bundle(tmp_path, {"contexts": [item]})


def test_snapshot_distinguishes_verified_and_assumed_and_is_not_factor_run(tmp_path):
    registry = publish_bundle(tmp_path, assumed_bundle())
    result = snapshot(registry, as_of="2021-06-15")
    assert result["last_completed_month"] == "2021-05"
    assert result["verified_context_ids"] == ["test_market"]
    assert result["assumed_context_ids"] == ["test_macro"]
    assert result["configured_and_usable"]
    assert not result["historical_pit_verified_for_all_inputs"]
    for flag in ("factor_evaluation_executed", "campaign_created_or_modified", "promotion_gates_changed"):
        assert result[flag] is False
    macro = result["contexts"][1]
    assert macro["pit_status"] == "PIT_ASSUMED"
    assert macro["assumption_policy_sha256"] == digest(policy())
    assert macro["assumptions"]
    assert all(r["month"] <= "2021-05" for c in result["contexts"] for r in c["rows"])
    assert result["registry_sha256"] == hashlib.sha256(registry.read_bytes()).hexdigest()


def test_snapshot_verified_only_does_not_invent_assumptions(tmp_path):
    result = snapshot(publish_bundle(tmp_path, bundle()), as_of="2021-06-30")
    assert result["assumed_context_ids"] == []
    assert result["verified_context_ids"] == ["test_market", "test_macro"]
    assert result["historical_pit_verified_for_all_inputs"]


def test_snapshot_after_source_end_is_unknown_not_forward_filled(tmp_path):
    source, _ = setup(tmp_path)
    registry = assume_source(tmp_path, source)
    result = snapshot(registry, as_of="2020-05-15")
    context = result["contexts"][0]
    assert context["data_latest_month"] == "2020-03"
    assert result["last_completed_month"] == "2020-04"
    assert context["rows"][-1] == {"month": "2020-04", "effective_month": "2020-05",
                                    "state": "UNKNOWN", "status": "UNKNOWN"}
    assert context["latest_state"] == "UNKNOWN"


@pytest.mark.parametrize("kind", ["macro_state", "market_index"])
def test_snapshot_outputs_only_scoped_months_but_preserves_market_warmup(tmp_path, kind):
    source, _ = setup(tmp_path, kind=kind, start="2020-01", end="2020-03", history="2016-01")
    registry = assume_source(tmp_path, source)
    result = snapshot(registry, as_of="2020-03-31")
    context = result["contexts"][0]
    assert [r["month"] for r in context["rows"]] == ["2020-01", "2020-02", "2020-03"]
    assert context["total_months"] == 3
    assert sum(context["state_counts"].values()) == 3
    assert context["usable_months"] == 3
    assert context["first_usable_month"] == "2020-01"
    assert context["latest_usable_month"] == "2020-03"
    assert all(r["status"] == "READY" for r in context["rows"])
    # Index classification needs 37+ months for all axes. Three scoped months
    # alone cannot be READY, so this also proves pre-scope history was retained
    # for causal warmup rather than discarded before classification.
    if kind == "market_index":
        assert all(r["state"] != "UNKNOWN" for r in context["rows"])


def test_snapshot_late_macro_value_is_unknown(tmp_path):
    source, _ = setup(tmp_path)
    source["rows"][-1]["known_at"] = "2020-04-01"
    result = snapshot(assume_source(tmp_path, source), as_of="2020-03-31")
    context = result["contexts"][0]
    assert context["rows"][-1]["state"] == "UNKNOWN"
    assert context["usable_months"] == 2
    assert context["latest_status"] == "UNKNOWN"


def test_snapshot_no_completed_rows_is_not_usable(tmp_path):
    source, _ = setup(tmp_path)
    result = snapshot(assume_source(tmp_path, source), as_of="2019-12-31")
    assert result["contexts"][0]["status"] == "NO_COMPLETED_ROWS"
    assert not result["configured_and_usable"]


def test_snapshot_ignores_incomplete_month_values_before_parsing(tmp_path):
    source, _ = setup(tmp_path)
    source["rows"][-1].update(known_at="INVALID_INCOMPLETE_MONTH", state="INVALID")
    result = snapshot(assume_source(tmp_path, source), as_of="2020-03-15")
    assert result["last_completed_month"] == "2020-02"
    assert result["contexts"][0]["usable_months"] == 2


@pytest.mark.parametrize("mode", ["empty", "disabled"])
def test_snapshot_empty_registry_cannot_report_success(tmp_path, mode):
    contexts = [] if mode == "empty" else [{"enabled": False}]
    path = tmp_path / "registry.json"
    write(path, {"schema_version": "diagnostic-regime-registry-v1", "contexts": contexts})
    with pytest.raises(ValueError, match="No registered"):
        snapshot(path, as_of="2020-03-31")


@pytest.mark.parametrize("mode,match", [("duplicate_context", "Duplicate registered"),
                                       ("duplicate_month", "Unresolved monthly"),
                                       ("two_markets", "Only one primary")])
def test_snapshot_rejects_duplicate_contracts(tmp_path, mode, match):
    value = bundle()
    if mode == "duplicate_context":
        value["contexts"].append(deepcopy(value["contexts"][0]))
    elif mode == "duplicate_month":
        item = value["contexts"][1]
        item["source"]["rows"].append(deepcopy(item["source"]["rows"][0]))
        item["approval"]["source_sha256"] = digest(item["source"])
    else:
        item = deepcopy(value["contexts"][0])
        item["source"]["context_id"] = "other_market"
        item["approval"]["source_sha256"] = digest(item["source"])
        value["contexts"].append(item)
    with pytest.raises(ValueError, match=match):
        snapshot(publish_bundle(tmp_path, value), as_of="2020-03-31")


def test_readiness_strict_default_blocks_but_opt_in_is_not_pit_verification(tmp_path):
    source, _ = setup(tmp_path)
    registry = assume_source(tmp_path, source)
    strict = audit_readiness(tmp_path / "manifest.json", registry)
    assert strict["requirements"][0]["status"] == "ASSUMPTION_NOT_HISTORICAL_VERIFICATION"
    assert strict["requirements"][0]["availability_status"] == "READY"
    assert strict["status"] == "BLOCKED" and not strict["complete"]
    allowed = audit_readiness(tmp_path / "manifest.json", registry, allow_assumed=True)
    assert allowed["requirements"][0]["status"] == "READY_ASSUMED"
    assert allowed["status"] == "COMPLETE_UNDER_ASSUMPTIONS" and allowed["complete"]
    assert allowed["assumed_ready_count"] == 1
    assert allowed["requirements"][0]["pit_status"] == "PIT_ASSUMED"
    for flag in ("historical_truth_recertified", "new_pit_approval_granted", "diagnostic_analysis_executed",
                 "campaign_or_registry_modified", "database_accessed", "scope_was_reduced"):
        assert allowed[flag] is False


@pytest.mark.parametrize("change,status", [("blocker", "EVIDENCE_INCOMPLETE"),
                                         ("late", "INCOMPLETE_PERIOD_COVERAGE"),
                                         ("scope", "OUT_OF_APPROVED_SCOPE"),
                                         ("factor_input", "SEPARATE_RESEARCH_INPUT_GATE_REQUIRED")])
def test_allow_assumed_never_waives_other_requirements(tmp_path, change, status):
    source, manifest = setup(tmp_path)
    if change == "blocker":
        manifest["requirements"][0]["blockers"] = ["Unresolved source-specific issue"]
    elif change == "late":
        source["rows"][-1]["known_at"] = "2020-04-01"
    elif change == "scope":
        manifest["period"]["end_month"] = "2020-04"
    else:
        manifest["requirements"][0]["role"] = "CURRENT_RESEARCH_INPUT"
    write(tmp_path / "manifest.json", manifest)
    result = audit_readiness(tmp_path / "manifest.json", assume_source(tmp_path, source), allow_assumed=True)
    assert result["requirements"][0]["status"] == status
    assert not result["complete"]


def test_readiness_cli_requires_explicit_allow_assumed(tmp_path):
    source, _ = setup(tmp_path)
    registry = assume_source(tmp_path, source)
    args = ["--manifest", str(tmp_path / "manifest.json"), "--registry", str(registry), "--require-complete"]
    assert readiness_main(args + ["--output", str(tmp_path / "strict.json")]) == 2
    assert readiness_main(args + ["--output", str(tmp_path / "allowed.json"), "--allow-assumed"]) == 0
    assert json.loads((tmp_path / "allowed.json").read_text())["status"] == "COMPLETE_UNDER_ASSUMPTIONS"


def test_capture_to_packet_carries_assumption_warning_and_policy_identity():
    panel, frame, factor, result, _ = fixture()
    study = capture_discovery(panel, frame, factor, result, campaign(assumed_bundle()), {})
    section = study["sections"]["regime_comparison"]
    assert any("accepted PIT assumptions" in limitation for limitation in section["limitations"])
    packet = build_packet({"visibility": "RELEASED_QUALITATIVE", "record_id": "synthetic",
                           "hypothesis_and_calculation": {}, "evidence": {}},
                          {"factor": {"definition_hash": "d"}, "mechanism_study": study}, None)
    basis = packet["scientist"]["study_context"]["regime_input_basis"]
    assert basis["pit_status"] == "PIT_ASSUMED"
    assert basis["assumed_context_ids"] == ["test_macro"]
    assert basis["verified_context_ids"] == ["test_market"]
    assert basis["assumption_policy_sha256s"] == [digest(policy())]
    warnings = packet["scientist"]["interpretation_warnings"]
    warning = next(w for w in warnings if w["code"] == "REGIME_PIT_ASSUMPTIONS_ACCEPTED")
    assert warning["evidence_ids"] == ["diagnostic.discovery.regime_comparison"]
    assert "do not claim first-vintage verification" in warning["meaning"]


def test_verified_packet_does_not_receive_assumed_warning():
    panel, frame, factor, result, _ = fixture()
    study = capture_discovery(panel, frame, factor, result, campaign(bundle()), {})
    packet = build_packet({"visibility": "RELEASED_QUALITATIVE", "record_id": "synthetic",
                           "hypothesis_and_calculation": {}, "evidence": {}},
                          {"factor": {"definition_hash": "d"}, "mechanism_study": study}, None)
    assert "regime_input_basis" not in packet["scientist"]["study_context"]
    assert not any(w["code"] == "REGIME_PIT_ASSUMPTIONS_ACCEPTED"
                   for w in packet["scientist"]["interpretation_warnings"])


def test_interpreter_and_critic_prompts_preserve_assumption_boundary():
    # The fixed instructions must label assumptions without requesting new impact analysis.
    strings = [v for k, v in vars(scientist_review).items() if k.isupper() and isinstance(v, str)]
    prompts = [s for s in strings if "PIT_ASSUMED" in s]
    assert len(prompts) >= 2
    assert any("승격 gate" in s for s in prompts)
    assert any("영향 측정" in s or "영향측정" in s for s in prompts)
