"""Append-only campaign invalidation for stale asset identity inputs."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

from engine import epochs


BEFORE_DIGEST = "1" * 64
AFTER_DIGEST = "2" * 64


def _start_campaign(
    root: Path,
    campaign_id: str = "campaign-identity",
    *,
    snapshot_asset_identity_digest: str | None = BEFORE_DIGEST,
    discovery_asset_identity_digest: str | None = "3" * 64,
    closure_asset_identity_digest: str | None = "4" * 64,
    closure_asset_identity_cutoff: str | None = "2026-08-31",
) -> Path:
    return epochs.start_campaign(
        root,
        campaign_id,
        discovery_data_cutoff="2023-06-30",
        snapshot_cutoff="2026-07-31",
        snapshot_digest="a" * 64,
        discovery_snapshot_digest="b" * 64,
        snapshot_asset_identity_digest=snapshot_asset_identity_digest,
        discovery_asset_identity_digest=discovery_asset_identity_digest,
        closure_asset_identity_digest=closure_asset_identity_digest,
        closure_asset_identity_cutoff=closure_asset_identity_cutoff,
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_campaign_requires_and_binds_both_asset_identity_digests(tmp_path):
    path = _start_campaign(
        tmp_path,
        snapshot_asset_identity_digest=BEFORE_DIGEST,
        discovery_asset_identity_digest="3" * 64,
    )
    campaign = json.loads(path.read_text(encoding="utf-8"))
    assert campaign["snapshot"]["asset_identity_digest"] == BEFORE_DIGEST
    assert campaign["snapshot"]["discovery_asset_identity_digest"] == "3" * 64

    with pytest.raises(ValueError, match="64자리"):
        _start_campaign(
            tmp_path / "missing-pair",
            snapshot_asset_identity_digest=BEFORE_DIGEST,
            discovery_asset_identity_digest=None,
        )
    with pytest.raises(ValueError, match="64자리"):
        _start_campaign(
            tmp_path / "invalid-digest",
            snapshot_asset_identity_digest="invalid",
            discovery_asset_identity_digest="3" * 64,
        )
    with pytest.raises(ValueError, match="closure asset identity"):
        _start_campaign(
            tmp_path / "missing-closure",
            closure_asset_identity_digest=None,
            closure_asset_identity_cutoff=None,
        )


def test_invalidation_authenticates_bound_before_identity_digest(tmp_path):
    manifest_path = _start_campaign(
        tmp_path,
        snapshot_asset_identity_digest=BEFORE_DIGEST,
        discovery_asset_identity_digest="3" * 64,
    )
    manifest_bytes = manifest_path.read_bytes()

    with pytest.raises(ValueError, match="snapshot 계약과 다릅니다"):
        epochs.invalidate_input_identity(
            tmp_path,
            "campaign-identity",
            migration_id="asset-rebuild-20260811",
            before_identity_digest="4" * 64,
            after_identity_digest=AFTER_DIGEST,
            reason="wrong prior digest",
        )
    assert manifest_path.read_bytes() == manifest_bytes
    assert not (manifest_path.parent / "identity-invalidations").exists()


def test_identity_invalidation_is_append_only_and_preserves_evidence(tmp_path):
    manifest_path = _start_campaign(tmp_path)
    campaign_dir = manifest_path.parent
    campaign = json.loads(manifest_path.read_text(encoding="utf-8"))
    campaign.update({
        "status": "AWAITING_IMPLEMENTATION",
        "epochs": [{"epoch_id": "epoch-001", "status": "CLOSED"}],
        "qualified_factors": [{
            "name": "candidate-a",
            "definition_hash": "c" * 64,
            "predicted_sign": 1,
        }],
        "discovery_results": "results/discovery.json",
        "implementation_verification": "implementation-verification.json",
    })
    _write_json(manifest_path, campaign)

    evidence = {
        "epochs/epoch-001/manifest.json": {"status": "CLOSED", "candidates": []},
        "results/discovery.json": {"verdict": "PROVISIONAL", "ic": 0.03},
        "implementation-attempts/attempt-001.json": {"status": "FAIL"},
        "implementation-verification.json": {"status": "PENDING"},
    }
    for relative, payload in evidence.items():
        _write_json(campaign_dir / relative, payload)
    existing_bytes = {
        relative: (campaign_dir / relative).read_bytes() for relative in evidence
    }
    before = copy.deepcopy(campaign)

    artifact_path = epochs.invalidate_input_identity(
        tmp_path,
        "campaign-identity",
        migration_id="asset-rebuild-20260811",
        before_identity_digest=BEFORE_DIGEST,
        after_identity_digest=AFTER_DIGEST,
        reason="RDS asset identity 재구축으로 asset_id와 종목코드 매핑이 변경됨",
    )

    after = epochs.load_campaign(tmp_path, "campaign-identity")
    assert after["status"] == epochs.INVALIDATED_INPUT_IDENTITY_STATUS
    assert after["oos"]["status"] == "NOT_USED"
    assert after["input_identity_invalidation"] == str(artifact_path)
    assert after["snapshot"] == before["snapshot"]
    assert after["epochs"] == before["epochs"]
    assert after["qualified_factors"] == before["qualified_factors"]
    assert after["discovery_results"] == before["discovery_results"]
    assert after["implementation_verification"] == before["implementation_verification"]
    expected_oos = dict(before["oos"], status="NOT_USED")
    assert after["oos"] == expected_oos

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["schema_version"] == epochs.IDENTITY_INVALIDATION_SCHEMA_VERSION
    assert artifact["prior_campaign_status"] == "AWAITING_IMPLEMENTATION"
    assert artifact["prior_oos_status"] == "SEALED"
    assert artifact["new_campaign_status"] == epochs.INVALIDATED_INPUT_IDENTITY_STATUS
    assert artifact["new_oos_status"] == "NOT_USED"
    assert artifact["before_identity_digest"] == BEFORE_DIGEST
    assert artifact["after_identity_digest"] == AFTER_DIGEST
    assert artifact["prior_manifest_digest"] == epochs._payload_digest(before)
    assert after["invalidated_at"] == artifact["invalidated_at"]
    assert after["input_identity_invalidation_digest"] == epochs._payload_digest(artifact)
    assert artifact["preserved_campaign_artifacts"] == {
        relative: hashlib.sha256(content).hexdigest()
        for relative, content in sorted(existing_bytes.items())
    }
    for relative, content in existing_bytes.items():
        assert (campaign_dir / relative).read_bytes() == content

    artifact_bytes = artifact_path.read_bytes()
    manifest_bytes = manifest_path.read_bytes()
    with pytest.raises(ValueError, match="비종료 campaign"):
        epochs.invalidate_input_identity(
            tmp_path,
            "campaign-identity",
            migration_id="asset-rebuild-20260811",
            before_identity_digest=BEFORE_DIGEST,
            after_identity_digest=AFTER_DIGEST,
            reason="같은 전이를 반복",
        )
    assert artifact_path.read_bytes() == artifact_bytes
    assert manifest_path.read_bytes() == manifest_bytes
    assert list((campaign_dir / "identity-invalidations").glob("*.json")) == [
        artifact_path,
    ]


def test_identity_invalidation_resumes_after_manifest_write_failure(
    monkeypatch, tmp_path,
):
    manifest_path = _start_campaign(tmp_path)
    original_manifest = manifest_path.read_bytes()
    real_write = epochs._write

    def fail_manifest_write(path, payload):
        if path == manifest_path:
            raise OSError("injected manifest write failure")
        real_write(path, payload)

    monkeypatch.setattr(epochs, "_write", fail_manifest_write)
    with pytest.raises(OSError, match="injected"):
        epochs.invalidate_input_identity(
            tmp_path,
            "campaign-identity",
            migration_id="asset-rebuild-20260811",
            before_identity_digest=BEFORE_DIGEST,
            after_identity_digest=AFTER_DIGEST,
            reason="RDS asset identity 변경",
        )

    artifact_path = (
        manifest_path.parent / "identity-invalidations"
        / "asset-rebuild-20260811.json"
    )
    artifact_bytes = artifact_path.read_bytes()
    assert manifest_path.read_bytes() == original_manifest

    monkeypatch.setattr(epochs, "_write", real_write)
    resumed = epochs.invalidate_input_identity(
        tmp_path,
        "campaign-identity",
        migration_id="asset-rebuild-20260811",
        before_identity_digest=BEFORE_DIGEST,
        after_identity_digest=AFTER_DIGEST,
        reason="RDS asset identity 변경",
    )
    assert resumed == artifact_path
    assert artifact_path.read_bytes() == artifact_bytes
    campaign = epochs.load_campaign(tmp_path, "campaign-identity")
    assert campaign["status"] == epochs.INVALIDATED_INPUT_IDENTITY_STATUS
    assert campaign["oos"]["status"] == "NOT_USED"


def test_identity_invalidation_resumes_after_atomic_replace_crash(
    monkeypatch, tmp_path,
):
    manifest_path = _start_campaign(tmp_path)
    real_write = epochs._write

    def fail_after_temporary_write(path, payload):
        if path == manifest_path:
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            raise OSError("injected crash before atomic replace")
        real_write(path, payload)

    monkeypatch.setattr(epochs, "_write", fail_after_temporary_write)
    with pytest.raises(OSError, match="before atomic replace"):
        epochs.invalidate_input_identity(
            tmp_path,
            "campaign-identity",
            migration_id="asset-rebuild-20260811",
            before_identity_digest=BEFORE_DIGEST,
            after_identity_digest=AFTER_DIGEST,
            reason="RDS asset identity 변경",
        )

    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    assert temporary.is_file()

    monkeypatch.setattr(epochs, "_write", real_write)
    epochs.invalidate_input_identity(
        tmp_path,
        "campaign-identity",
        migration_id="asset-rebuild-20260811",
        before_identity_digest=BEFORE_DIGEST,
        after_identity_digest=AFTER_DIGEST,
        reason="RDS asset identity 변경",
    )

    assert not temporary.exists()
    campaign = epochs.load_campaign(tmp_path, "campaign-identity")
    assert campaign["status"] == epochs.INVALIDATED_INPUT_IDENTITY_STATUS
    assert campaign["oos"]["status"] == "NOT_USED"


def test_identity_invalidation_journal_publish_is_atomic_and_retryable(
    monkeypatch, tmp_path,
):
    manifest_path = _start_campaign(tmp_path)
    original_manifest = manifest_path.read_bytes()
    artifact_path = (
        manifest_path.parent / "identity-invalidations"
        / "asset-rebuild-20260811.json"
    )
    real_link = os.link

    def fail_publish(_source, _destination):
        raise OSError("injected journal publish failure")

    monkeypatch.setattr(epochs.os, "link", fail_publish)
    with pytest.raises(OSError, match="journal publish failure"):
        epochs.invalidate_input_identity(
            tmp_path,
            "campaign-identity",
            migration_id="asset-rebuild-20260811",
            before_identity_digest=BEFORE_DIGEST,
            after_identity_digest=AFTER_DIGEST,
            reason="RDS asset identity 변경",
        )

    # The append-only name is either absent or complete; failed publication
    # must never expose an empty/partial JSON body at the final path.
    assert not artifact_path.exists()
    assert manifest_path.read_bytes() == original_manifest

    # Simulate a process-killed transport file. It is not research evidence
    # and must not change the authenticated pre-transition artifact set.
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    orphan = artifact_path.parent / f".{artifact_path.name}.orphan.tmp"
    orphan.write_text("{partial", encoding="utf-8")

    monkeypatch.setattr(epochs.os, "link", real_link)
    epochs.invalidate_input_identity(
        tmp_path,
        "campaign-identity",
        migration_id="asset-rebuild-20260811",
        before_identity_digest=BEFORE_DIGEST,
        after_identity_digest=AFTER_DIGEST,
        reason="RDS asset identity 변경",
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["schema_version"] == epochs.IDENTITY_INVALIDATION_SCHEMA_VERSION
    assert orphan.is_file()
    assert epochs.load_campaign(
        tmp_path, "campaign-identity",
    )["status"] == epochs.INVALIDATED_INPUT_IDENTITY_STATUS


@pytest.mark.parametrize(
    ("campaign_status", "oos_status", "message"),
    [
        ("CLOSED_NO_QUALIFIED", "SEALED", "비종료 campaign"),
        ("OPEN", "NOT_USED", "OOS가 SEALED"),
        ("UNKNOWN", "SEALED", "비종료 campaign"),
    ],
)
def test_identity_invalidation_rejects_invalid_state_without_mutation(
    tmp_path, campaign_status, oos_status, message,
):
    root = tmp_path / campaign_status.lower()
    manifest_path = _start_campaign(root)
    campaign = json.loads(manifest_path.read_text(encoding="utf-8"))
    campaign["status"] = campaign_status
    campaign["oos"]["status"] = oos_status
    _write_json(manifest_path, campaign)
    manifest_bytes = manifest_path.read_bytes()

    with pytest.raises(ValueError, match=message):
        epochs.invalidate_input_identity(
            root,
            "campaign-identity",
            migration_id="asset-rebuild-20260811",
            before_identity_digest=BEFORE_DIGEST,
            after_identity_digest=AFTER_DIGEST,
            reason="invalid state test",
        )

    assert manifest_path.read_bytes() == manifest_bytes
    assert not (manifest_path.parent / "identity-invalidations").exists()


def test_identity_invalidation_refuses_existing_artifact_and_unlocks_new_campaign(
    tmp_path,
):
    manifest_path = _start_campaign(tmp_path, "campaign-first")
    collision = (
        manifest_path.parent
        / "identity-invalidations"
        / "asset-rebuild-20260811.json"
    )
    _write_json(collision, {"existing": True})
    manifest_bytes = manifest_path.read_bytes()
    collision_bytes = collision.read_bytes()

    with pytest.raises(ValueError, match="append-only artifact가 이미 존재"):
        epochs.invalidate_input_identity(
            tmp_path,
            "campaign-first",
            migration_id="asset-rebuild-20260811",
            before_identity_digest=BEFORE_DIGEST,
            after_identity_digest=AFTER_DIGEST,
            reason="collision test",
        )
    assert manifest_path.read_bytes() == manifest_bytes
    assert collision.read_bytes() == collision_bytes

    collision.unlink()
    epochs.invalidate_input_identity(
        tmp_path,
        "campaign-first",
        migration_id="asset-rebuild-20260811",
        before_identity_digest=BEFORE_DIGEST,
        after_identity_digest=AFTER_DIGEST,
        reason="RDS asset identity 변경",
    )
    second = _start_campaign(tmp_path, "campaign-second")
    assert second.exists()
