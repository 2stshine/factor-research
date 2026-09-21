from copy import deepcopy
import hashlib
import json

import pandas as pd
import pytest

from engine.regime_inputs import VERSION, PIT_FLAGS, digest
from scripts.regime_readiness import audit_readiness, main


def write(path, value):
    path.write_text(json.dumps(value))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup(tmp_path, *, kind="macro_state", start="2020-01", end="2020-03", history="2020-01"):
    months = pd.period_range(history, end, freq="M")
    source = {"context_id": "test", "source_id": "SYNTHETIC", "kind": kind,
              "scope": {"start_month": start, "end_month": end},
              "rows": [{"month": str(m), "known_at": str(m.end_time.date()),
                        "state": "UP", "close": 100 + i} for i, m in enumerate(months)]}
    if kind == "macro_state":
        source.update(states=["UP", "DOWN"], classification_rules={"version": "SYNTHETIC_ONLY"})
    else:
        source.update(official_market_index=True, market_id="SYNTHETIC")
    proof = tmp_path / "proof.txt"
    proof.write_text("synthetic evidence, not real-data approval")
    manifest = {"schema_version": "regime-review-scope-v1", "period": {"start_month": start, "end_month": end},
                "requirements": [{"id": "required-test", "role": "market" if kind == "market_index" else "macro",
                    "context_id": "test", "blockers": [],
                    "evidence": [{"path": "proof.txt", "sha256": hashlib.sha256(proof.read_bytes()).hexdigest()}]}]}
    publish(tmp_path, source)
    write(tmp_path / "manifest.json", manifest)
    return source, manifest


def publish(tmp_path, source):
    approval = {"schema_version": "pit-regime-approval-v1", "status": "APPROVED", "source_layer": "SILVER",
                "purpose": "DIAGNOSTIC_ONLY", "source_id": source["source_id"], "source_sha256": digest(source),
                **{k: True for k in PIT_FLAGS}, "reviewer": "SYNTHETIC_TEST_ONLY", "reviewed_at": "2026-01-01T00:00:00Z",
                "evidence": [{"uri": "synthetic://proof", "sha256": "a" * 64}]}
    approval_sha = write(tmp_path / "approval.json", approval)
    context_sha = write(tmp_path / "context.json", {"schema_version": VERSION, "contexts": [
        {"source": source, "approval_file": "approval.json", "approval_sha256": approval_sha}]})
    write(tmp_path / "registry.json", {"schema_version": "diagnostic-regime-registry-v1", "contexts": [
        {"enabled": True, "file": "context.json", "sha256": context_sha}]})


def audit(tmp_path):
    return audit_readiness(tmp_path / "manifest.json", tmp_path / "registry.json")


def test_ready_contract_does_not_claim_historical_proof(tmp_path):
    setup(tmp_path)
    result = audit(tmp_path)
    assert result["complete"] and result["status"] == "COMPLETE"
    assert result["requirements"][0]["usable_months"] == 3
    assert not result["historical_truth_recertified"]
    assert not result["new_pit_approval_granted"]
    assert not result["diagnostic_analysis_executed"]


def test_blocked_requirement_cannot_disappear(tmp_path):
    _, manifest = setup(tmp_path)
    other = deepcopy(manifest["requirements"][0])
    other.update(id="unverified", context_id=None, blockers=["FIRST_VINTAGE_NOT_FOUND"])
    manifest["requirements"].append(other)
    write(tmp_path / "manifest.json", manifest)
    result = audit(tmp_path)
    assert result["status"] == "PARTIAL" and result["required_count"] == 2
    assert result["ready_count"] == 1 and not result["scope_was_reduced"]
    assert result["requirements"][1]["status"] == "EVIDENCE_INCOMPLETE"


@pytest.mark.parametrize("role,status", [
    ("CURRENT_RESEARCH_INPUT", "SEPARATE_RESEARCH_INPUT_GATE_REQUIRED"),
    ("MARKET_REGIME_CANDIDATE", "CONTEXT_ROLE_MISMATCH"),
])
def test_unrelated_macro_context_cannot_certify_other_input_role(tmp_path, role, status):
    _, manifest = setup(tmp_path)
    manifest["requirements"][0]["role"] = role
    write(tmp_path / "manifest.json", manifest)
    assert audit(tmp_path)["requirements"][0]["status"] == status


@pytest.mark.parametrize("change,expected", [
    ("missing_registry", "MISSING_REGISTRY"), ("bad_registry", "INVALID_REGISTRY"),
    ("changed_proof", "EVIDENCE_HASH_MISMATCH"), ("missing_proof", "MISSING_EVIDENCE"),
    ("no_context", "MISSING_APPROVED_CONTEXT"),
])
def test_fail_closed(tmp_path, change, expected):
    _, manifest = setup(tmp_path)
    if change == "missing_registry":
        (tmp_path / "registry.json").unlink()
    elif change == "bad_registry":
        (tmp_path / "context.json").write_text("{}")
    elif change == "changed_proof":
        (tmp_path / "proof.txt").write_text("changed")
    elif change == "missing_proof":
        (tmp_path / "proof.txt").unlink()
    else:
        manifest["requirements"][0].pop("context_id")
        write(tmp_path / "manifest.json", manifest)
    result = audit(tmp_path)
    assert not result["complete"] and result["requirements"][0]["status"] == expected


@pytest.mark.parametrize("mode", ["empty", "late", "unknown"])
def test_zero_usable_never_complete(tmp_path, mode):
    source, _ = setup(tmp_path)
    if mode == "empty":
        source["rows"] = []
    elif mode == "late":
        for row in source["rows"]:
            row["known_at"] = str((pd.Period(row["month"], freq="M") + 1).start_time.date())
    else:
        for row in source["rows"]:
            row["state"] = "UNKNOWN"
    publish(tmp_path, source)
    result = audit(tmp_path)
    assert result["requirements"][0]["status"] == "NO_USABLE_ROWS"
    assert not result["complete"]


def test_approved_scope_not_automatically_shrunk(tmp_path):
    _, manifest = setup(tmp_path)
    manifest["period"]["start_month"] = "2019-12"
    write(tmp_path / "manifest.json", manifest)
    assert audit(tmp_path)["requirements"][0]["status"] == "OUT_OF_APPROVED_SCOPE"


def test_missing_month_stays_missing(tmp_path):
    source, _ = setup(tmp_path)
    source["rows"].pop(1)
    publish(tmp_path, source)
    row = audit(tmp_path)["requirements"][0]
    assert row["status"] == "INCOMPLETE_PERIOD_COVERAGE" and row["missing_months"] == ["2020-02"]


def test_market_warmup_not_confused_with_price_coverage(tmp_path):
    source, _ = setup(tmp_path, kind="market_index")
    row = audit(tmp_path)["requirements"][0]
    assert row["status"] == "INSUFFICIENT_HISTORY" and row["usable_months"] == 3
    assert row["classified_months"] == 0
    source, _ = setup(tmp_path, kind="market_index", history="2016-01")
    row = audit(tmp_path)["requirements"][0]
    assert row["status"] == "READY" and row["classified_months"] == 3
    assert row["warmup_observations_before_period"] == 48


def test_boolean_market_prices_rejected(tmp_path):
    source, _ = setup(tmp_path, kind="market_index")
    source["rows"][0]["close"] = True
    publish(tmp_path, source)
    assert audit(tmp_path)["requirements"][0]["status"] == "INVALID_CONTEXT"


def test_duplicate_requirements_rejected(tmp_path):
    _, manifest = setup(tmp_path)
    manifest["requirements"].append(deepcopy(manifest["requirements"][0]))
    write(tmp_path / "manifest.json", manifest)
    with pytest.raises(ValueError, match="unique"):
        audit(tmp_path)


def test_cli_complete_gate_exit_and_no_overwrite(tmp_path):
    _, manifest = setup(tmp_path)
    manifest["requirements"][0]["blockers"] = ["NOT_VERIFIED"]
    write(tmp_path / "manifest.json", manifest)
    args = ["--manifest", str(tmp_path / "manifest.json"), "--registry", str(tmp_path / "registry.json"),
            "--output", str(tmp_path / "result.json"), "--require-complete"]
    assert main(args) == 2
    assert json.loads((tmp_path / "result.json").read_text())["status"] == "BLOCKED"
    with pytest.raises(FileExistsError):
        main(args)


@pytest.mark.parametrize("timestamp,expected", [
    ("2020-01-31T12:00:00", "INVALID_CONTEXT"),
    ("2020-01-31T23:59:59", "READY"),
])
def test_policy_day_bound_availability_matches_freeze_contract(tmp_path, timestamp, expected):
    from scripts.regime_readiness import _availability

    source, _ = setup(tmp_path, end="2020-01")
    source["rows"][0]["known_at"] = timestamp
    # Synthetic availability-only unit test, not a full approval artifact.
    item = {"source": source, "approval_sha256": "a" * 64,
            "approval": {"schema_version": "pit-regime-approval-v2"}}
    result = _availability(item, pd.period_range("2020-01", "2020-01", freq="M"))
    assert result["status"] == expected
