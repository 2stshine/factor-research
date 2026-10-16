"""Only synthetic registration artifacts; no panel, DB, returns, or OOS reads."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine import epochs, gate, research_policy
from engine.factors import Factor, Registry
from scripts import research as cli, run


@pytest.fixture
def probe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    factor = Factor(name="checkpoint_probe", category="other",
                    hypothesis="synthetic input only", predicted_sign=1,
                    compute=lambda frame: frame["input"])
    registry = Registry()
    registry.add(factor)
    campaign = {
        "campaign_id": "campaign-probe", "protocol_version": "frozen-protocol",
        "ruleset_version": "frozen-rules", "status": "OPEN",
        "snapshot": {"discovery_input_digest": "a" * 64},
    }
    specs = {factor.name: {"strategy_sha256": "b" * 64,
                           "strategy_file": "synthetic/checkpoint_probe.py"}}
    feasibility = research_policy.input_feasibility_artifact(
        [factor], snapshot_digest="a" * 64, signal_start="2015-01", signal_end="2020-01",
        metrics={factor.name: {"coverage": 1., "monthly_coverage_p10": 1.}},
        minimum_coverage=gate.TH["coverage"],
        minimum_monthly_p10=gate.TH["monthly_coverage_p10"],
    )
    gold = _gold(factor)
    monkeypatch.setattr(cli.F, "REGISTRY", registry)
    monkeypatch.setattr(cli, "RESEARCH_SPECS", specs)
    monkeypatch.setattr(run, "load_registry", lambda: None)
    monkeypatch.setattr(epochs, "load_campaign", lambda *_: deepcopy(campaign))
    monkeypatch.setattr(run.trials, "TrialLedger", lambda *_: SimpleNamespace(definition_hashes=lambda: set()))
    monkeypatch.setattr(cli.research, "attempted_factor_names", lambda *_: set())
    monkeypatch.setattr(cli.research, "assert_new_candidate", lambda *_, **__: None)
    monkeypatch.setattr(run, "_load", lambda: object())
    monkeypatch.setattr(run, "preflight_candidate_registration", lambda *_: (feasibility, gold))
    monkeypatch.setattr(run.silver, "connect", _forbidden)
    monkeypatch.setattr(run, "_evaluate", _forbidden)
    monkeypatch.setattr(epochs, "start_epoch", _forbidden)
    return SimpleNamespace(root=tmp_path / "research", campaign=campaign, factor=factor,
                           specs=specs, feasibility=feasibility, gold=gold,
                           args=SimpleNamespace(campaign="campaign-probe", epoch="epoch-probe",
                                                factors=[factor.name]))


def _forbidden(*_, **__):
    pytest.fail("No real DB, return evaluation, or unintended registration allowed")


def _gold(factor, *, failed=False):
    return research_policy.gold_signal_preflight_artifact(
        [factor], snapshot_digest="a" * 64, gold_family_digest="c" * 64,
        approved_factors=["synthetic_gold"] if failed else [],
        relationships=[{
            "factor": factor.name, "status": "FAIL" if failed else "PASS",
            "max_gold_signal_corr": None if failed else 0.,
            "comparisons": [{"gold_factor": "synthetic_gold", "status": "INSUFFICIENT_MONTHS",
                             "comparison_months": 2, "correlation": None}] if failed else [],
        }], threshold=gate.TH["max_gold_corr"],
        minimum_comparison_months=gate.TH["min_gold_corr_months"],
    )


def _receipts(probe):
    return sorted(probe.root.glob("campaigns/*/registration-preflight/*/*.json"))


def _save(probe, **kwargs):
    return cli._checkpoint_registration_preflight(
        probe.campaign, "epoch-probe", [probe.factor], probe.specs,
        probe.feasibility, probe.gold, root=probe.root, **kwargs,
    )


def test_success_preserves_original_artifacts_before_registration(probe, monkeypatch, capsys):
    calls = []

    def register(*_, **kwargs):
        receipts = _receipts(probe)
        assert len(receipts) == 1
        receipt = json.loads(receipts[0].read_text())
        assert receipt["input_feasibility"] == kwargs["input_feasibility"] == probe.feasibility
        assert receipt["gold_signal_preflight"] == kwargs["gold_signal_preflight"] == probe.gold
        calls.append("register_after_checkpoint")
        return Path("synthetic-epoch.json")

    monkeypatch.setattr(epochs, "start_epoch", register)
    cli.cmd_epoch_start(probe.args)
    path, = _receipts(probe)
    receipt = json.loads(path.read_text())
    digest = receipt.pop("checkpoint_sha256")
    assert epochs._payload_digest(receipt) == digest == path.stem
    assert receipt["campaign_manifest_sha256"] == epochs._payload_digest(probe.campaign)
    assert receipt["protocol_version"] == "frozen-protocol"
    assert receipt["ruleset_version"] == "frozen-rules"
    assert receipt["candidates"] == [{"name": probe.factor.name,
            "definition_hash": probe.factor.definition_hash, **probe.specs[probe.factor.name]}]
    assert receipt["registration_authorized"] is False
    assert (receipt["return_evaluations"], receipt["oos_reads"], receipt["gold_writes"]) == (0, 0, 0)
    for source, sha in receipt["source_sha256"].items():
        assert hashlib.sha256((cli.REPO_ROOT / source).read_bytes()).hexdigest() == sha
    assert set(receipt["source_sha256"]) == {"scripts/research.py", "scripts/run.py",
        "engine/research_policy.py", "engine/gate.py", "engine/silver.py"}
    assert str(path) in capsys.readouterr().out
    assert calls == ["register_after_checkpoint"]


def test_gold_fail_retains_reason_without_inventing_threshold_exceedance(probe, monkeypatch):
    failed = _gold(probe.factor, failed=True)
    monkeypatch.setattr(run, "preflight_candidate_registration", lambda *_: (probe.feasibility, failed))
    with pytest.raises(SystemExit, match="상관 사전검사 실패"):
        cli.cmd_epoch_start(probe.args)
    path, = _receipts(probe)
    receipt = json.loads(path.read_text())
    assert receipt["input_feasibility"] == probe.feasibility
    assert receipt["gold_signal_preflight"] == failed
    assert receipt["gold_signal_preflight"]["candidates"][0]["comparisons"][0]["status"] == "INSUFFICIENT_MONTHS"
    assert "임계초과" not in path.read_text()


def test_input_rejection_preserves_artifact_and_explicit_gold_not_run(probe, monkeypatch):
    failed = research_policy.input_feasibility_artifact(
        [probe.factor], snapshot_digest="a" * 64, signal_start="2015-01", signal_end="2020-01",
        metrics={probe.factor.name: {"coverage": .1, "monthly_coverage_p10": 0.}},
        minimum_coverage=gate.TH["coverage"], minimum_monthly_p10=gate.TH["monthly_coverage_p10"],
    )
    sentinel = "postgres://secret@example.invalid/not-persisted"

    def reject(*_):
        raise run.CandidateInputPreflightError(failed, ValueError(sentinel))

    monkeypatch.setattr(run, "preflight_candidate_registration", reject)
    with pytest.raises(SystemExit):
        cli.cmd_epoch_start(probe.args)
    path, = _receipts(probe)
    receipt = json.loads(path.read_text())
    assert receipt["stage"] == "INPUT_ASSERTION_REJECTED_BEFORE_LIVE_GOLD"
    assert receipt["input_feasibility"] == failed
    assert receipt["gold_signal_preflight"] == {"status": "NOT_RUN",
        "reason": "INPUT_FEASIBILITY_ASSERTION_REJECTED", "gold_queried": False,
        "live_identity_checked": False}
    assert sentinel not in path.read_text()
    assert "traceback" not in path.read_text()


def test_input_exception_copies_evidence_without_relabeling_corrupt_artifact(probe):
    corrupt = deepcopy(probe.feasibility)
    corrupt["snapshot_digest"] = "wrong"
    error = run.CandidateInputPreflightError(corrupt, ValueError("artifact가 손상"))
    corrupt["status"] = "CHANGED_LATER"
    assert error.input_feasibility["status"] == "PASS"
    assert error.input_feasibility["snapshot_digest"] == "wrong"
    assert str(error) == "artifact가 손상"


def test_immutable_receipt_cannot_be_overwritten_and_new_capture_appends(probe, monkeypatch):
    monkeypatch.setattr(epochs, "_now", lambda: "2026-10-02T00:00:00+00:00")
    first = _save(probe)
    before = first.read_bytes()
    assert _save(probe) == first
    assert first.read_bytes() == before
    first.write_text("{}")  # Simulate tampering; production writer must not repair/overwrite.
    with pytest.raises(ValueError, match="Immutable registration checkpoint changed"):
        _save(probe)
    assert first.read_text() == "{}"
    monkeypatch.setattr(epochs, "_now", lambda: "2026-10-02T00:00:01+00:00")
    second = _save(probe)
    assert second != first
    assert len(_receipts(probe)) == 2
    assert first.read_text() == "{}"


@pytest.mark.parametrize("field,unsafe", [("epoch", "../../.."), ("campaign", "../../escape"),
                                         ("epoch", "/tmp/escape"), ("campaign", "a/../escape")])
def test_shared_id_validation_prevents_checkpoint_path_escape(probe, field, unsafe):
    epoch = "epoch-probe"
    if field == "campaign":
        probe.campaign["campaign_id"] = unsafe
    else:
        epoch = unsafe
    with pytest.raises(ValueError, match="소문자"):
        cli._checkpoint_registration_preflight(probe.campaign, epoch, [probe.factor],
            probe.specs, probe.feasibility, probe.gold, root=probe.root)
    assert not probe.root.exists()


def test_symlink_directory_cannot_escape_research_root(probe, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (probe.root / "campaigns").mkdir(parents=True)
    (probe.root / "campaigns" / "campaign-probe").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes research root"):
        _save(probe)
    assert not list(outside.iterdir())
