"""Portable runtime closure only; no campaign/performance/OOS files are read."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from engine.regime_inputs import ASSUMED_AVAILABILITY, VERSION, make_assumption_acceptance
from scripts import check_regime_artifacts as checker


def write(path, value):
    body = json.dumps(value, sort_keys=True).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return hashlib.sha256(body).hexdigest()


def fixture(root, *, evidence=None):
    policy = {"schema_version": "regime-assumption-policy-v1", "policy_id": "test-v1",
              "authorization_text": "Synthetic diagnostic assumption, not an actual approval.",
              "user_authorized": True, "new_campaigns_only": True, "diagnostics_only": True,
              "promotion_gates_unchanged": True, "factor_feature_allowed": False,
              "historical_pit_verified": False}
    source = {"source_id": "TEST-v1", "context_id": "TEST", "kind": "macro_state",
              "states": ["UP", "DOWN"], "classification_rules": {"version": "test-v1"},
              "pit_status": "PIT_ASSUMED", "known_at_semantics": ASSUMED_AVAILABILITY,
              "assumptions": ["Synthetic historical availability assumption."],
              "scope": {"start_month": "2020-01", "end_month": "2020-01"},
              "rows": [{"month": "2020-01", "known_at": "2020-01-31T23:59:59", "state": "UP"}]}
    approval = make_assumption_acceptance(source, policy,
        evidence or [{"uri": "missing-raw.json", "sha256": "1" * 64}],
        accepted_at="2020-02-01T00:00:00Z")
    folder = root / "output/test"
    approval_sha = write(folder / "approval.json", approval)
    bundle = {"schema_version": VERSION, "contexts": [
        {"source": source, "approval_file": "approval.json", "approval_sha256": approval_sha}]}
    context_sha = write(folder / "context.json", bundle)
    registry = {"schema_version": "diagnostic-regime-registry-v1", "contexts": [
        {"context_id": "TEST", "enabled": True, "file": "../output/test/context.json", "sha256": context_sha}]}
    write(root / checker.REGISTRY, registry)
    return folder, bundle, registry


def test_missing_raw_evidence_is_not_a_runtime_failure(tmp_path):
    fixture(tmp_path)
    result = checker.check_artifacts(tmp_path)
    assert result["runtime_status"] == "PASS"
    assert result["runtime_file_count"] == 2
    assert result["reaudit"]["status"] == "INCOMPLETE_LOCAL_REFERENCES"
    assert result["reaudit"]["missing"] == 1
    assert result["reaudit"]["required_for_runtime"] is False
    assert result["reaudit"]["historical_pit_verified_by_this_check"] is False


def test_present_evidence_is_existence_only_no_content_read(tmp_path, monkeypatch):
    raw = tmp_path / "raw-secret.bin"
    raw.write_bytes(b"do not inspect this raw source")
    fixture(tmp_path, evidence=[{"uri": str(raw), "sha256": "1" * 64}])
    original = Path.read_bytes

    def read(path):
        assert path != raw
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    result = checker.check_artifacts(tmp_path)
    assert result["runtime_status"] == "PASS"
    assert result["reaudit"]["present"] == 1
    assert result["reaudit"]["evidence_hashes_rechecked"] is False


@pytest.mark.parametrize("target", ["context.json", "approval.json"])
def test_changed_artifact_fails_hash_binding(tmp_path, target):
    folder, _, _ = fixture(tmp_path)
    with (folder / target).open("ab") as handle:
        handle.write(b" ")
    assert checker.check_artifacts(tmp_path)["runtime_status"] == "FAIL"


def test_rehashed_changed_source_still_fails_approval_binding(tmp_path):
    folder, bundle, registry = fixture(tmp_path)
    bundle["contexts"][0]["source"]["rows"][0]["state"] = "DOWN"
    registry["contexts"][0]["sha256"] = write(folder / "context.json", bundle)
    write(tmp_path / checker.REGISTRY, registry)
    result = checker.check_artifacts(tmp_path)
    assert result["runtime_status"] == "FAIL"
    assert "source binding" in result["errors"][0]["error"]


def test_external_runtime_dependency_is_not_portable(tmp_path):
    folder, bundle, registry = fixture(tmp_path)
    bundle["contexts"][0]["approval_file"] = "../../../outside.json"
    registry["contexts"][0]["sha256"] = write(folder / "context.json", bundle)
    write(tmp_path / checker.REGISTRY, registry)
    result = checker.check_artifacts(tmp_path)
    assert result["runtime_status"] == "FAIL"
    assert "escapes repository" in result["errors"][0]["error"]


def test_index_check_requires_identical_indexed_bytes(tmp_path, monkeypatch):
    fixture(tmp_path)
    indexed = {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob("*.json")}
    monkeypatch.setattr(checker, "_index_bytes", lambda root, name: indexed.get(name))
    assert checker.check_artifacts(tmp_path, tracked_only=True)["runtime_status"] == "PASS"
    indexed.pop("output/test/approval.json")
    result = checker.check_artifacts(tmp_path, tracked_only=True)
    assert result["runtime_status"] == "FAIL"
    assert any(x["error"] == "Missing from Git index" for x in result["errors"])
    indexed["output/test/approval.json"] = b"different staged version"
    result = checker.check_artifacts(tmp_path, tracked_only=True)
    assert any(x["error"] == "Working bytes differ from Git index" for x in result["errors"])


def test_disabled_context_is_not_a_dependency(tmp_path):
    _, _, registry = fixture(tmp_path)
    registry["contexts"].append({"enabled": False, "file": "absent.json"})
    write(tmp_path / checker.REGISTRY, registry)
    assert checker.check_artifacts(tmp_path)["runtime_status"] == "PASS"


def test_real_release_loads_with_only_registry_and_runtime_files(tmp_path, monkeypatch):
    """Simulate a clean checkout with only the explicitly distributable inputs.

    Read only the default regime registry/context/approval files, never raw
    financials, performance, campaign data, or any evidence target's contents.
    """
    result = checker.check_artifacts(checker.ROOT)
    assert result["runtime_status"] == "PASS"
    paths = [checker.REGISTRY, *(x["path"] for x in result["runtime_files"])]
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(checker.ROOT / relative, target)
    original = Path.read_bytes

    def read(path):
        assert path.resolve().is_relative_to(tmp_path.resolve()), "Runtime read escaped clean checkout"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    clean = checker.check_artifacts(tmp_path)
    assert clean["runtime_status"] == "PASS"
    assert clean["contexts"] == result["contexts"] == 38
    assert clean["runtime_file_count"] == result["runtime_file_count"] == 41
    assert clean["runtime_bytes"] == result["runtime_bytes"]
    assert clean["reaudit"]["outside_checkout"] > 0
