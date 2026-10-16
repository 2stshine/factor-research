"""Production binding regressions using synthetic inputs and temporary files only.

No real memory store, campaign artifact, market data, network, or OOS is opened.
The memory verifier double checks its caller's exact arguments; the underlying
receipt authentication is separately exercised by test_research_memory_transfer.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from engine import epochs, research_production as production
from engine.adaptive_research import digest
from tests.test_research_production import prepared
from tests.test_research_real_diagnostics import fixture_contract


def configuration(monkeypatch):
    import engine.research_regime_production as regimes

    monkeypatch.setattr(regimes, "validate_frozen_context", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(regimes, "macro_catalog", lambda _frozen: {
        "synthetic-policy-axis": {"states": ["LOW", "HIGH"]},
    })
    config = {"version": production.VERSION, "regime": {"synthetic": True},
              "policy": {"memory_pointer": "synthetic-pointer.json"},
              "code_sha256": production.code_bindings()}
    config["sha256"] = digest(config)
    return config


@pytest.fixture
def registration(tmp_path, monkeypatch):
    import engine.research_memory_transfer as memory

    campaign = {"campaign_id": "synthetic-campaign", "research_v2": configuration(monkeypatch),
                "snapshot": {"discovery_input_digest": "a" * 64},
                "discovery": {"signal_end": "2021-12"}}
    factor = SimpleNamespace(name="synthetic_factor", definition_hash="b" * 64)
    specs = {factor.name: {"strategy_sha256": "c" * 64, "diagnostic_plan": {}}}
    context = {"synthetic": "recorded context fixture"}
    path = tmp_path / "context.json"
    file_sha = production.write(path, context)
    proof = {"status": "MEMORY_USAGE_VERIFIED", "context_sha256": digest(context),
             "usage_sha256": "d" * 64}
    calls = []

    def authenticate(pointer, supplied, *, expected_scope, task_id, repo_root):
        calls.append(task_id)
        assert pointer == tmp_path / "synthetic-pointer.json"
        assert supplied == context
        assert expected_scope == production.target_scope(campaign, "c" * 64)
        assert task_id == "synthetic-campaign/epoch-one/synthetic_factor"
        assert repo_root == tmp_path
        return deepcopy(proof)

    monkeypatch.setattr(memory, "require_campaign_memory_usage", authenticate)
    binding = {**proof, "context_path": str(path), "context_file_sha256": file_sha}
    return SimpleNamespace(campaign=campaign, factor=factor, specs=specs,
        bindings={factor.name: binding}, root=tmp_path, context_path=path, calls=calls)


def freeze(fixture):
    return production.freeze_candidate_plans(fixture.campaign, [fixture.factor], fixture.specs,
        memory_bindings=fixture.bindings, epoch_id="epoch-one",
        strategy_digests={fixture.factor.name: "c" * 64}, repo_root=fixture.root)


def test_strategy_sha_mismatch_rejected_before_memory_or_registration(registration):
    registration.specs[registration.factor.name]["strategy_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="candidate source SHA"):
        freeze(registration)
    assert not registration.calls


def test_memory_binding_must_match_actual_revalidated_usage(registration):
    assert freeze(registration)[registration.factor.name]["memory"]["status"] == "MEMORY_USAGE_VERIFIED"
    registration.bindings[registration.factor.name]["usage_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="audited usage"):
        freeze(registration)
    assert len(registration.calls) == 2


def test_context_file_tamper_rejected_before_memory_verifier(registration):
    registration.context_path.write_text('{"synthetic": "tampered fixture"}\n')
    with pytest.raises(ValueError, match="context file changed"):
        freeze(registration)
    assert not registration.calls


def test_macro_axis_and_contrast_must_exist_before_registration(registration):
    for axis, contrast in (("missing-axis", ["LOW", "HIGH"]),
                           ("synthetic-policy-axis", ["LOW", "UNDECLARED"])):
        registration.specs[registration.factor.name]["diagnostic_plan"] = {
            "macro_axes": [axis], "macro_contrasts": {axis: contrast},
        }
        with pytest.raises(ValueError, match="frozen source"):
            freeze(registration)
    assert not registration.calls


def test_live_code_drift_stops_candidate_readiness_before_other_checks(monkeypatch):
    config = configuration(monkeypatch)
    campaign = {"research_v2": config}
    monkeypatch.setattr(epochs, "load_campaign", lambda *_args: campaign)
    monkeypatch.setattr(epochs, "load_epoch", lambda *_args: {})
    monkeypatch.setattr(production, "code_bindings", lambda: {"synthetic-code": "changed"})
    monkeypatch.setattr(epochs, "validate_manifest", lambda *_args, **_kwargs: pytest.fail(
        "Must stop at live-code precheck before validating or evaluating a candidate"))
    with pytest.raises(ValueError, match="stop before candidate evaluation"):
        epochs.assert_candidate_ready("NOT_OPENED", "synthetic", "epoch-one",
            SimpleNamespace(name="synthetic_factor"), strategy_sha256="c" * 64)


def test_epoch_plan_hash_detects_changed_plan_and_preserves_legacy(monkeypatch):
    config = configuration(monkeypatch)
    campaign = {"research_v2": config, "protocol_version": epochs.PROTOCOL_VERSION,
                "ruleset_version": epochs.RULESET_VERSION}
    plans = {"synthetic_factor": {"memory": {"usage_sha256": "a" * 64}}}
    epoch = {"protocol_version": epochs.PROTOCOL_VERSION, "ruleset_version": epochs.RULESET_VERSION,
             "research_v2_sha256": config["sha256"], "research_v2_plans": plans,
             "research_v2_plans_sha256": digest(plans)}
    epochs._assert_current_state(campaign, epoch)
    plans["synthetic_factor"]["memory"]["usage_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="진단 계획·기억 결합"):
        epochs._assert_current_state(campaign, epoch)
    epochs._assert_current_state({key: value for key, value in campaign.items() if key != "research_v2"},
        {key: value for key, value in epoch.items() if not key.startswith("research_v2")})


def diagnostic_args(monkeypatch, *, evidence=None):
    import engine.research_production_evidence as adapter

    monkeypatch.setattr(adapter, "prepare_discovery_evidence", lambda *_args, **_kwargs: evidence or prepared())
    monkeypatch.setattr(production, "validate_campaign", lambda _config, **_kwargs: "a" * 64)
    campaign = {"campaign_id": "synthetic-campaign", "research_v2": {
        "sha256": "a" * 64, "code_sha256": production.code_bindings(), "regime": {}},
        "snapshot": {"discovery_input_digest": "a" * 64}, "discovery": {"signal_end": "2021-12"}}
    candidate = {"definition_hash": "b" * 64, "strategy_sha256": "c" * 64, "diagnostic_plan": {}}
    epoch = {"epoch_id": "epoch-one", "research_v2_sha256": "a" * 64,
             "research_v2_plans": {"synthetic_factor": candidate}}
    factor = SimpleNamespace(name="synthetic_factor", definition_hash="b" * 64)
    return campaign, epoch, None, None, factor, None


def test_committed_handoff_resumes_missing_session_without_reprojection(tmp_path, monkeypatch):
    import engine.research_production_evidence as adapter

    args = diagnostic_args(monkeypatch)
    initialize = production.ProductionBroker.initialize
    monkeypatch.setattr(production.ProductionBroker, "initialize", lambda _self: (_ for _ in ()).throw(
        RuntimeError("Synthetic interruption after directory publication")))
    with pytest.raises(RuntimeError, match="Synthetic interruption"):
        production.handoff(tmp_path, *args)
    destination = tmp_path / "campaigns/synthetic-campaign/v2/epoch-one/synthetic_factor"
    manifest_before = (destination / "manifest.json").read_bytes()
    assert not (destination / "session.sqlite").exists()
    monkeypatch.setattr(production.ProductionBroker, "initialize", initialize)
    monkeypatch.setattr(adapter, "prepare_discovery_evidence", lambda *_args, **_kwargs: pytest.fail(
        "A persisted handoff must not reconstruct or reevaluate the factor"))
    receipt = production.handoff(tmp_path, *args)
    assert receipt["status"] == "READY_FOR_HOST_DIAGNOSTICS"
    assert production.ProductionBroker(destination).session().packet()["state"]["state"] == "ACTIVE"
    assert (destination / "manifest.json").read_bytes() == manifest_before


def test_insufficient_market_support_is_propagated_not_hidden_by_other_market(tmp_path, monkeypatch):
    data = prepared()
    child = data["regime_labs"]["KOSDAQ"]
    frame = child["frame"]
    midpoint = sorted(frame.ym.unique())[frame.ym.nunique() // 2]
    frame["state"] = frame.ym.map(lambda month: "LOW" if month < midpoint else "HIGH")
    child["contract"] = fixture_contract(frame, regime=child["contract"]["regime"])
    receipt = production.handoff(tmp_path, *diagnostic_args(monkeypatch, evidence=data))
    report = production.ProductionBroker(receipt["path"]).run("regime_interaction")
    strata = report["metrics"]["stratified_markets"]
    assert strata["KOSPI"]["status"] == "COMPUTED"
    assert strata["KOSDAQ"]["status"] == "INSUFFICIENT_SUPPORT"
    assert strata["KOSDAQ"]["metrics"]["interaction"]["ci95"] is None
    assert report["status"] == "INSUFFICIENT_SUPPORT"
    assert report["metrics"]["status_by_stratum"]["regime_labs:KOSDAQ"] == "INSUFFICIENT_SUPPORT"
