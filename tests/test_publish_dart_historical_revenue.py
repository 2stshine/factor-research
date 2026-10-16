"""Bridge tests: synthetic sources only; database writer is mocked here."""
from __future__ import annotations

from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path

import pytest

from scripts import publish_dart_historical_revenue as bridge

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_dart_bridge_integration", ROOT / "tests/test_dart_historical_silver_integration.py")
integration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integration)
pub = integration.publisher


def files(tmp_path, monkeypatch):
    _, manifest, artifacts = integration.checked_bundle(tmp_path, monkeypatch)
    stage_dir, identity_dir = tmp_path / "stage", tmp_path / "identity"
    identity_dir.mkdir()
    identity_raw = artifacts[manifest["identity_sha256"]]
    identity = json.loads(identity_raw)
    mapping = identity["mappings"][0]
    listing = json.loads(artifacts[mapping["listing_snapshot_sha256"]])
    for filename, raw in (("identity.json", identity_raw),
                          ("fy-reference-scoped.json", artifacts[mapping["fy_reference_sha256"]]),
                          ("listing.json", artifacts[mapping["listing_snapshot_sha256"]]),
                          ("listing-source.json", artifacts[listing["identity_evidence_sha256"]])):
        (identity_dir / filename).write_bytes(raw)
    raw = artifacts[mapping["fy_issuer_sha256"]]
    (stage_dir / "synthetic-fy-list.json").write_bytes(raw)
    index_path = stage_dir / "artifact-index.json"
    index = json.loads(index_path.read_bytes())
    index["artifacts"][mapping["fy_issuer_sha256"]] = {"root": "output", "path": "synthetic-fy-list.json", "bytes": len(raw)}
    index_path.write_bytes(pub.canonical_bytes(index))
    return stage_dir, identity_dir


def draft(tmp_path, monkeypatch):
    stage_dir, identity_dir = files(tmp_path, monkeypatch)
    output = tmp_path / "draft.json"
    summary = bridge.plan(stage_dir, identity_dir, dataset_version="bridge-synthetic-v1", parser_version="v1", output=output)
    return stage_dir, identity_dir, output, summary


def accepted(tmp_path, monkeypatch):
    stage_dir, identity_dir, output, summary = draft(tmp_path, monkeypatch)
    value = json.loads(output.read_bytes())
    value["review"] = {"decision": "ACCEPT", "reviewer": "synthetic independent reviewer", "reviewed_at": "2026-10-02T12:00:00+09:00"}
    target = tmp_path / "accepted.json"
    target.write_bytes(pub.canonical_bytes(value))
    return stage_dir, identity_dir, target


def test_plan_is_only_draft_and_check_rejects_it(tmp_path, monkeypatch):
    stage_dir, identity_dir, output, summary = draft(tmp_path, monkeypatch)
    assert summary["decision"] == "DRAFT" and summary["pit_certified"] is False
    assert summary["proposed_current_quarter_rows"] == 2
    with pytest.raises(ValueError, match="DRAFT is not approval"):
        bridge.check_or_apply(stage_dir, identity_dir, output, parser_version="v1", output=tmp_path / "receipt.json")


def test_check_only_replays_accept_and_never_connects(tmp_path, monkeypatch):
    stage_dir, identity_dir, accepted_path = accepted(tmp_path, monkeypatch)
    monkeypatch.setattr(bridge.silver, "connect", lambda **kw: pytest.fail("check must not connect"))
    result = bridge.check_or_apply(stage_dir, identity_dir, accepted_path, parser_version="v1", output=tmp_path / "check.json")
    assert result["rows"] == 2 and result["committed"] is False
    assert result["database_writes"] is False and result["legacy_fundamental_writes"] is False


def test_identity_mismatch_becomes_explicit_draft_exclusion(tmp_path, monkeypatch):
    stage_dir, identity_dir = files(tmp_path, monkeypatch)
    path = identity_dir / "identity.json"
    value = json.loads(path.read_bytes())
    value["mappings"][0]["valid_from"] = "2016-01-01"
    path.write_bytes(pub.canonical_bytes(value))
    target = tmp_path / "draft.json"
    result = bridge.plan(stage_dir, identity_dir, dataset_version="bridge-synthetic-v1", parser_version="v1", output=target)
    assert result["proposed_current_quarter_rows"] == 0
    assert result["excluded_receipts"] == 1
    assert next(iter(json.loads(target.read_bytes())["plan"]["excluded_by_reason"])).startswith("HISTORICAL_IDENTITY_UNVERIFIED")


def test_source_contract_changed_requires_new_review(tmp_path, monkeypatch):
    stage_dir, identity_dir, path = accepted(tmp_path, monkeypatch)
    value = json.loads(path.read_bytes())
    value["bridge"]["publisher_source_sha256"] = "0" * 64
    path.write_bytes(pub.canonical_bytes(value))
    with pytest.raises(ValueError, match="source contract changed"):
        bridge.check_or_apply(stage_dir, identity_dir, path, parser_version="v1", output=tmp_path / "check.json")


def test_unsafe_lazy_index_path_is_rejected(tmp_path, monkeypatch):
    stage_dir, identity_dir = files(tmp_path, monkeypatch)
    path = stage_dir / "artifact-index.json"
    value = json.loads(path.read_bytes())
    next(iter(value["artifacts"].values()))["path"] = "../outside"
    path.write_bytes(pub.canonical_bytes(value))
    with pytest.raises(ValueError, match="Unsafe artifact-index"):
        bridge.Artifacts(stage_dir, identity_dir, pub)


def test_apply_explicit_rw_transaction_and_no_migration(tmp_path, monkeypatch):
    stage_dir, identity_dir, path = accepted(tmp_path, monkeypatch)
    calls = []
    class Conn:
        read_only, autocommit = False, False
        def transaction(self):
            calls.append("transaction")
            return nullcontext()
    def connect(**kw):
        assert kw == {"read_only": False}
        calls.append("connect_rw")
        return nullcontext(Conn())
    def publish(conn, **kw):
        assert kw["authorize_write"] is True
        calls.append("publish")
        return {"quality_run_id": "synthetic", "rows": 2, "inserted": 2, "committed": False}
    monkeypatch.setattr(pub, "publish", publish)
    result = bridge.check_or_apply(stage_dir, identity_dir, path, parser_version="v1", output=tmp_path / "apply.json", apply=True, connect=connect)
    assert calls == ["connect_rw", "transaction", "publish"]
    assert result["committed"] is True and result["migrations_executed"] is False


def test_hash_change_during_prepare_blocks_before_any_connection(tmp_path, monkeypatch):
    stage_dir, identity_dir, path = accepted(tmp_path, monkeypatch)
    original = pub.prepare
    def mutate(*args, **kw):
        value = original(*args, **kw)
        (identity_dir / "identity.json").write_bytes(b"changed during replay")
        return value
    monkeypatch.setattr(pub, "prepare", mutate)
    with pytest.raises(ValueError, match="changed during validation"):
        bridge.check_or_apply(stage_dir, identity_dir, path, parser_version="v1", output=tmp_path / "apply.json", apply=True,
                              connect=lambda **kw: pytest.fail("changed artifact must prevent DB connection"))


def test_apply_cli_requires_second_explicit_flag(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["publish_dart_historical_revenue", "apply", "--stage-dir", str(tmp_path),
                                     "--identity-dir", str(tmp_path), "--parser", "v1", "--checked-manifest", str(tmp_path / "accept.json"),
                                     "--output", str(tmp_path / "result.json")])
    with pytest.raises(SystemExit) as exc:
        bridge.main()
    assert exc.value.code == 2
