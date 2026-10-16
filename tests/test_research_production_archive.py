"""Synthetic-only production archive, exact delivery and incomplete release tests."""
from copy import deepcopy
import json
import sqlite3

import pytest

from engine import epochs, research_production as production
from engine.adaptive_research import digest
from tests.test_research_production import action, handoff


def submit(broker, value, key):
    packet = broker.packet()
    return broker.act(value, request_id=key, expected_revision=packet["state"]["revision"])


def audit(broker):
    response = submit(broker, action("input_audit"), "audit")
    assert response["status"] == "OBSERVED"
    return response["evidence"]["evidence_id"]


def stop(broker, *, complete=False):
    refs = [row["evidence_id"] for row in broker.session().packet()["state"]["evidence"]]
    return submit(broker, {"kind": "STOP", "reason": "Finish this synthetic inspection.",
        "evidence_ids": refs, "payload": {
            "conclusion": "EXPLANATION_COMPLETE_WITH_LIMITATIONS" if complete else "INCONCLUSIVE",
            "observations": [{"statement": "Only the returned synthetic evidence was observed.", "evidence_ids": refs}],
            "unresolved": ["Unperformed or insufficient evidence does not establish a mechanism."],
            "limitations": "Synthetic fixture, not an economic finding or independent OOS.",
            "mechanism_identified": False}}, "stop")


def closed_campaign(monkeypatch, campaign):
    frozen = deepcopy(campaign)
    frozen["status"] = "CLOSED_NO_QUALIFIED"
    monkeypatch.setattr(epochs, "load_campaign", lambda *_args: frozen)
    return frozen


def review_source(directory):
    bundle = production.read(directory / "review-bundle.json")
    case = next(iter(bundle["cases"].values()))
    return bundle, case, production.read(directory / case["sources"][0]["path"])


def test_delivered_packet_is_exactly_the_audited_whole_context(tmp_path, monkeypatch):
    broker, *_ = handoff(tmp_path, monkeypatch)
    packet = broker.packet()
    event = broker.session().events()[-1]
    assert packet == event["packet"]
    assert digest(packet) == event["packet_sha256"]
    context = packet["public_case"]["production_context"]
    assert context["readiness"] == broker.manifest["readiness"]
    assert context["input_history"] == broker.manifest["input_history"]
    assert context["input_profiles"] == broker.manifest["input_profiles"]
    assert broker.packet() == packet
    packet["public_case"]["production_context"]["readiness"] = {"forged": True}
    assert broker.packet() == event["packet"]


def test_archive_reads_original_after_code_drift_without_lab_or_writes(tmp_path, monkeypatch):
    broker, *_ = handoff(tmp_path, monkeypatch)
    audit(broker)
    stop(broker)
    original = broker.export()
    before = {str(path.relative_to(broker.root)): path.read_bytes()
              for path in broker.root.rglob("*") if path.is_file()}
    monkeypatch.setattr(production, "code_bindings", lambda: {"new": "synthetic-code"})
    with pytest.raises(ValueError, match="code changed"):
        production.ProductionBroker(broker.root)
    # A future implementation version must not relabel an original archive.
    import engine.research_real_runtime as runtime
    monkeypatch.setattr(production, "VERSION", "future-production-version")
    monkeypatch.setattr(runtime, "VERSION", "future-runtime-version")
    def forbidden(*_args, **_kwargs):
        pytest.fail("Archive inspection must never instantiate a lab or load a frame")
    monkeypatch.setattr(production, "RealDiagnosticLab", forbidden)
    monkeypatch.setattr(production.pd, "read_parquet", forbidden)
    archive = production.ProductionBroker(broker.root, read_only=True)
    assert archive.export() == original
    assert archive.status()["session_state"] == "STOPPED"
    with archive.session()._connect() as database:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            database.execute("DELETE FROM events")
    after = {str(path.relative_to(broker.root)): path.read_bytes()
             for path in broker.root.rglob("*") if path.is_file()}
    assert after == before


def test_archive_denies_every_action_and_initialization_path(tmp_path, monkeypatch):
    broker, *_ = handoff(tmp_path, monkeypatch)
    archive = production.ProductionBroker(broker.root, read_only=True)
    assert archive.status()["session_state"] == "ACTIVE"
    operations = [archive.packet, archive.initialize,
        lambda: archive.act({}, request_id="forbidden", expected_revision=0),
        lambda: archive.run("input_audit"), lambda: archive._lab(archive.manifest["primary"]),
        archive.session().request, lambda: archive.session().submit({}, request_id="x", expected_revision=0, execute=None)]
    for operation in operations:
        with pytest.raises(ValueError, match="Read-only production archive"):
            operation()


@pytest.mark.parametrize("target", ["frame", "contract", "manifest", "audit"])
def test_archive_still_rejects_changed_source_bytes_and_event_chain(tmp_path, monkeypatch, target):
    broker, *_ = handoff(tmp_path, monkeypatch)
    if target == "audit":
        with sqlite3.connect(broker.root / "session.sqlite") as database:
            database.execute("UPDATE events SET sha='tampered' WHERE revision=0")
    else:
        path = broker.root / ("manifest.json" if target == "manifest" else broker.manifest["primary"][target])
        if target == "manifest":
            value = production.read(path)
            value["factor"] = "forged_factor"
            path.write_text(json.dumps(value))
        else:
            path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="changed|integrity|mismatch"):
        production.ProductionBroker(broker.root, read_only=True).export()


def test_request_data_terminal_releases_incomplete_evidence_without_resuming(tmp_path, monkeypatch):
    broker, campaign, *_ = handoff(tmp_path, monkeypatch)
    audit(broker)
    response = submit(broker, action("execution_cost"), "cost")
    assert response["status"] == "OBSERVED"
    evidence = response["evidence"]
    request = {"kind": "REQUEST_DATA", "reason": "Synthetic evidence is missing.",
        "evidence_ids": [evidence["evidence_id"]], "payload": {
            "dataset": evidence["response"]["missing_datasets"][0],
            "distinguishes": "Whether implementation is observable.",
            "expected_value": "Keep unmeasured implementation unresolved."}}
    assert submit(broker, request, "need-data")["status"] == "DATA_REQUESTED_NOT_ACQUIRED"
    with pytest.raises(ValueError, match="not active"):
        submit(broker, action("association"), "not-resumed")
    closed_campaign(monkeypatch, campaign)
    monkeypatch.setattr(production, "code_bindings", lambda: {"later": "unrelated-current-code"})
    result = production.prepare_review(broker.root, tmp_path / "release")
    assert result["terminal_status"] == "DATA_REQUESTED_NOT_ACQUIRED"
    assert result["explanation_complete"] is False
    assert set(result["unperformed_required_diagnostics"]) == {"association", "controls", "regime_interaction"}
    _bundle, case, source = review_source(tmp_path / "release")
    assert case["scope"] == broker.manifest["review_scope"]
    assert source["terminal_event"]["decision"] == request
    assert source["explanation_complete"] is False
    assert source["unperformed_required_diagnostics"] == result["unperformed_required_diagnostics"]
    assert case["unperformed_diagnostics"]["HOST_LLM"] == result["unperformed_required_diagnostics"]


@pytest.mark.parametrize("has_evidence", [False, True])
def test_proposal_terminal_requires_observed_evidence_for_review(tmp_path, monkeypatch, has_evidence):
    broker, campaign, *_ = handoff(tmp_path, monkeypatch)
    refs = [audit(broker)] if has_evidence else []
    proposal = {"kind": "PROPOSE_TEST", "reason": "Synthetic follow-up, never executed.",
        "evidence_ids": refs, "payload": {"question": "Which unavailable observation separates rivals?",
            "design": "Review the missing evidence source.", "distinguishes": "Measurement versus explanation."}}
    assert submit(broker, proposal, "proposal")["status"] == "NEW_TEST_PENDING_REVIEW"
    closed_campaign(monkeypatch, campaign)
    if not has_evidence:
        with pytest.raises(ValueError, match="without observed evidence"):
            production.prepare_review(broker.root, tmp_path / "release")
        assert not (tmp_path / "release").exists()
    else:
        result = production.prepare_review(broker.root, tmp_path / "release")
        assert result["terminal_status"] == "NEW_TEST_PENDING_REVIEW"
        assert result["explanation_complete"] is False
        assert result["unperformed_required_diagnostics"]


def test_explicit_complete_stop_keeps_existing_review_contract(tmp_path, monkeypatch):
    broker, campaign, *_ = handoff(tmp_path, monkeypatch)
    for diagnostic in broker.manifest["required_diagnostics"]:
        assert submit(broker, action(diagnostic), diagnostic)["status"] == "OBSERVED"
    assert stop(broker, complete=True)["status"] == "STOPPED"
    closed_campaign(monkeypatch, campaign)
    result = production.prepare_review(broker.root, tmp_path / "release")
    assert result["explanation_complete"] is True
    assert result["unperformed_required_diagnostics"] == []
    assert result["terminal_status"] == "STOPPED"


@pytest.mark.parametrize("command", ["status", "export", "prepare-review"])
def test_cli_consumers_select_read_only_broker(tmp_path, monkeypatch, command):
    from scripts import research_production as cli
    seen = []
    def capture(path, *, read_only=False):
        seen.append((path, read_only))
        raise RuntimeError("SYNTHETIC_STOP_BEFORE_FILE_ACCESS")
    monkeypatch.setattr(cli, "ProductionBroker", capture)
    with pytest.raises(RuntimeError, match="SYNTHETIC_STOP"):
        cli.main([command, "--handoff", str(tmp_path / "NOT_OPENED")])
    assert seen == [(tmp_path / "NOT_OPENED", True)]
