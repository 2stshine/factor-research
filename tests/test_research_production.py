"""Synthetic integration only: no actual factor, DB, OOS or model review."""
from copy import deepcopy
from types import SimpleNamespace

import pandas as pd
import pytest

from engine import research_production as production
from engine.adaptive_research import digest
from tests.test_research_real_diagnostics import fixture_frame, fixture_contract, regime_fixture


def prepared():
    frame = fixture_frame()
    contract = fixture_contract(frame)
    regimes = {}
    for market in ("KOSPI", "KOSDAQ"):
        child = frame.loc[frame.market.eq(market)].reset_index(drop=True)
        child, spec = regime_fixture(child)
        regimes[market] = {"frame": child, "contract": fixture_contract(child, regime=spec)}
    return {"status": "PREPARED", "frame": frame, "contract": contract,
            "regime_labs": regimes, "macro_labs": {}, "readiness": {"fixture": True},
            "input_history": {"fixture": True},
            "required_diagnostics": ["input_audit", "association", "controls", "regime_interaction"]}


def handoff(tmp_path, monkeypatch):
    import engine.research_production_evidence as evidence
    monkeypatch.setattr(evidence, "prepare_discovery_evidence", lambda *args, **kwargs: prepared())
    monkeypatch.setattr(production, "validate_campaign", lambda config: config["sha256"])
    config = {"code_sha256": production.code_bindings(), "regime": {}}
    config["sha256"] = digest(config)
    campaign = {"campaign_id": "synthetic-campaign", "research_v2": config,
                "snapshot": {"discovery_input_digest": "a" * 64}, "discovery": {"signal_end": "2021-12"}}
    candidate = {"definition_hash": "b" * 64, "strategy_sha256": "c" * 64, "diagnostic_plan": {}}
    epoch = {"epoch_id": "epoch-one", "research_v2_sha256": config["sha256"],
             "research_v2_plans": {"arbitrary_new_factor": candidate}}
    factor = SimpleNamespace(name="arbitrary_new_factor", definition_hash="b" * 64)
    receipt = production.handoff(tmp_path, campaign, epoch, None, None, factor, None)
    return production.ProductionBroker(receipt["path"]), campaign, epoch, factor


def action(diagnostic_id, evidence=()):
    return {"kind": "TEST", "reason": "Synthetic integration test only", "evidence_ids": list(evidence),
            "payload": {"diagnostic_id": diagnostic_id,
                "rivals": [{"explanation": "Fixture association", "expected_if_true": "Observed fixture relation"},
                           {"explanation": "Confounded fixture", "expected_if_true": "Control difference"}],
                "changes_mind_if": "Only returned synthetic evidence"}}


def test_general_factor_handoff_resume_and_actual_broker(tmp_path, monkeypatch):
    broker, campaign, epoch, factor = handoff(tmp_path, monkeypatch)
    receipt = production.handoff(tmp_path, campaign, epoch, None, None, factor, None)
    assert receipt["path"] == str(broker.root)
    assert receipt["new_factor_evaluations"] == receipt["oos_reads"] == receipt["gold_writes"] == 0
    assert not receipt["reviewed_lesson"]
    packet = broker.packet()
    result = broker.act(action("input_audit"), request_id="first", expected_revision=packet["state"]["revision"])
    assert result["status"] == "OBSERVED"
    assert broker.session().packet()["state"]["state"] == "ACTIVE"
    # Collection is not auto-authored or fake-reviewed.
    assert not (broker.root / "review-bundle.json").exists()


def test_regime_report_is_stratified_and_parent_bound(tmp_path, monkeypatch):
    broker, *_ = handoff(tmp_path, monkeypatch)
    report = broker.run("regime_interaction")
    assert set(report["metrics"]["stratified_markets"]) == {"KOSPI", "KOSDAQ"}
    assert not report["metrics"]["pooled_market_regime_estimate"]
    assert report["evidence_scope"]["contract_sha256"] == broker.manifest["data_contract_sha256"]
    assert not report["causal_identification"]


def test_tamper_and_changed_code_block_replay(tmp_path, monkeypatch):
    broker, *_ = handoff(tmp_path, monkeypatch)
    original = production.code_bindings()
    monkeypatch.setattr(production, "code_bindings", lambda: {**original, "NEW": "x"})
    with pytest.raises(ValueError, match="code changed"):
        production.ProductionBroker(broker.root)
    monkeypatch.setattr(production, "code_bindings", lambda: original)
    path = broker.root / "primary/frame.parquet"
    frame = pd.read_parquet(path)
    frame.loc[0, "signal"] += 1
    frame.to_parquet(path, index=False)
    with pytest.raises(ValueError, match="changed"):
        broker.run("association")


def test_wrong_epoch_definition_cannot_reuse(tmp_path, monkeypatch):
    broker, campaign, epoch, factor = handoff(tmp_path, monkeypatch)
    wrong = deepcopy(epoch)
    wrong["research_v2_plans"][factor.name]["definition_hash"] = "d" * 64
    with pytest.raises(ValueError, match="definition"):
        production.handoff(tmp_path, campaign, wrong, None, None, factor, None)


def test_pending_campaign_cannot_release_review(tmp_path, monkeypatch):
    from engine import epochs
    broker, *_ = handoff(tmp_path, monkeypatch)
    monkeypatch.setattr(epochs, "load_campaign", lambda *args: {"status": "OPEN"})
    with pytest.raises(ValueError, match="final campaign"):
        production.prepare_review(broker.root, tmp_path / "release")


def test_artifact_write_never_overwrites(tmp_path):
    path = tmp_path / "receipt.json"
    production.write(path, {"a": 1})
    production.write(path, {"a": 1})
    with pytest.raises(ValueError, match="Immutable"):
        production.write(path, {"a": 2})
