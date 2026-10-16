from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess

import pytest

from engine import research_generation as g


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "legacy"
    root.mkdir()
    git(root, "init", "-q")
    (root / "engine").mkdir()
    (root / "engine/old.py").write_text("old_code = 1\n")
    (root / ".gitignore").write_text("ignored.bin\n")
    git(root, "add", ".")
    git(root, "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid", "commit", "-qm", "synthetic only")
    (root / "engine/old.py").write_text("dirty_code = 2\n")
    (root / "research/campaigns/old").mkdir(parents=True)
    (root / "research/campaigns/old/opaque.json").write_bytes(b'{"synthetic_record":"preserve bytes without interpreting"}\n')
    return root


def test_capture_dirty_untracked_opaque_records_idempotent_and_preserves_originals(repository):
    original = (repository / "engine/old.py").read_bytes()
    destination = repository / "research/archives/legacy"
    receipt = g.capture_legacy_snapshot({"research": repository}, archive_root=destination)
    again = g.capture_legacy_snapshot({"research": repository}, archive_root=destination)
    assert receipt == again
    assert (repository / "engine/old.py").read_bytes() == original
    manifest = json.loads(Path(receipt["manifest_path"]).read_bytes())
    paths = {row["path"]: row for row in manifest["entries"]}
    assert paths["engine/old.py"]["sha256"] == g.file_digest(repository / "engine/old.py")
    assert paths["research/campaigns/old/opaque.json"]["tracked"] is False
    assert paths["engine/old.py"]["original_path"] == str(repository / "engine/old.py")
    assert g.verify_legacy_snapshot(receipt["manifest_path"])["archive_id"] == receipt["archive_id"]


def test_secrets_cache_output_new_v3_and_ignored_files_excluded(repository):
    for name, data in {".env": b"secret=yes", "output/returns.bin": b"do-not-copy", ".cache/cache.pkl": b"do-not-copy",
                       "ignored.bin": b"git ignored", "engine/research_generation.py": b"new tool",
                       "engine/research_transition_guard.py": b"new guard", "engine/reference_portfolio.py": b"new model",
                       "source-secret.txt": b'api_key = "synthetic-private-key-not-to-preserve"'}.items():
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    receipt = g.capture_legacy_snapshot({"research": repository}, archive_root=repository / "research/archives/legacy")
    manifest = json.loads(Path(receipt["manifest_path"]).read_bytes())
    copied = {r["path"] for r in manifest["entries"]}
    assert not ({".env", "output/returns.bin", ".cache/cache.pkl", "ignored.bin", "source-secret.txt",
                 "engine/research_generation.py", "engine/research_transition_guard.py", "engine/reference_portfolio.py"} & copied)
    excluded = {r["path"]: r["reason"] for r in manifest["references_not_copied"]}
    assert excluded[".env"] == "SECRET_OR_CREDENTIAL_PATH"
    assert excluded["source-secret.txt"] == "POSSIBLE_EMBEDDED_SECRET_NOT_COPIED"
    assert "ignored.bin" not in excluded


def test_symlink_not_dereferenced_and_large_files_reference_only(repository, tmp_path):
    outside = tmp_path / "outside-secret"
    outside.write_text("never archive me")
    (repository / "escape.txt").symlink_to(outside)
    (repository / "large.dat").write_bytes(b"x" * 101)
    receipt = g.capture_legacy_snapshot({"research": repository}, archive_root=repository / "research/archives/legacy", max_file_bytes=100)
    manifest = json.loads(Path(receipt["manifest_path"]).read_bytes())
    refs = {r["path"]: r["reason"] for r in manifest["references_not_copied"]}
    assert refs["escape.txt"] == "SYMLINK_NOT_DEREFERENCED"
    assert refs["large.dat"] == "SIZE_LIMIT_REFERENCE_ONLY"


def test_native_legacy_dashboard_dist_is_source_and_opaque_data_is_preserved(repository):
    native = repository / "apps/research-observatory/dist"
    (native / "data").mkdir(parents=True)
    (native / "app.js").write_bytes(b"const legacySource = true;\n")
    (native / "data/old.json").write_bytes(b'{"synthetic":"opaque legacy dashboard payload"}')
    git(repository, "add", "apps/research-observatory/dist/app.js")
    (repository / "other/dist").mkdir(parents=True)
    (repository / "other/dist/generated.js").write_bytes(b"generated file")
    result = g.capture_legacy_snapshot({"research": repository}, archive_root=repository / "research/archives/legacy")
    manifest = json.loads(Path(result["manifest_path"]).read_bytes())
    paths = {r["path"] for r in manifest["entries"]}
    assert "apps/research-observatory/dist/app.js" in paths
    assert "apps/research-observatory/dist/data/old.json" in paths
    assert "other/dist/generated.js" not in paths


@pytest.mark.parametrize("path", ["../outside", "/absolute", "a/../b", "a\\b", "./relative"])
def test_path_escape_rejected(repository, path):
    with pytest.raises(ValueError, match="path|Path|relative"):
        g.capture_legacy_snapshot({"research": repository}, archive_root=repository / "archive", exclude_paths=[path])


def test_corrupt_archive_object_is_not_validated(repository):
    result = g.capture_legacy_snapshot({"research": repository}, archive_root=repository / "research/archives/legacy")
    path = Path(result["manifest_path"])
    manifest = json.loads(path.read_bytes())
    (path.parent.parent / manifest["entries"][0]["object_path"]).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="missing or corrupt"):
        g.verify_legacy_snapshot(path)


def entry(name="test_factor", **overrides):
    args = dict(generation_id=g.DEFAULT_GENERATION, factor_id=name, definition_sha256="1" * 64,
                implementation_sha256="2" * 64, feature_sha256="3" * 64, approval_evidence_sha256="4" * 64,
                admitted_at="2020-01-01T00:00:00+09:00")
    return g.make_factor_entry(**{**args, **overrides})


def metadata(item):
    return {key: item[key] for key in ("generation_id", "factor_id", "entry_sha256")}


def test_empty_new_generation_does_not_import_old_approved(repository):
    receipt = g.capture_legacy_snapshot({"research": repository}, archive_root=repository / "research/archives/legacy")
    initialized = g.initialize_generation(repository, archive_manifest=receipt["manifest_path"], activate=True)
    assert initialized["approved_factor_count"] == 0 and initialized["legacy_gold_imported"] is False
    active = g.load_active_generation(repository)
    assert active["approved_factors"] == []
    assert g.validate_factor_inputs(active, []) == []
    with pytest.raises(ValueError, match="no legacy fallback"):
        g.validate_factor_inputs(active, [{**metadata(entry()), "status": "APPROVED"}])
    assert g.initialize_generation(repository, archive_manifest=receipt["manifest_path"], activate=True) == initialized


def test_nonempty_generation_exact_allowlist_order_and_temporal_admission():
    a, b = entry("a"), entry("b")
    manifest = g.make_generation(purpose="SYNTHETIC", approved_factors=[a, b])
    assert g.validate_factor_inputs(manifest, [metadata(b), metadata(a)], decision_at="2020-02-01T00:00:00+09:00") == [b, a]
    with pytest.raises(ValueError, match="after this decision"):
        g.validate_factor_inputs(manifest, [metadata(a)], decision_at="2019-12-31T00:00:00+09:00")


def test_mixed_generation_stale_hash_and_contradictory_provenance_rejected():
    approved = entry()
    manifest = g.make_generation(purpose="SYNTHETIC", approved_factors=[approved])
    for change in ({"generation_id": "legacy"}, {"entry_sha256": "0" * 64}, {"source_kind": "LEGACY_GOLD_APPROVED"}):
        with pytest.raises(ValueError):
            g.validate_factor_inputs(manifest, [{**metadata(approved), **change}])
    with pytest.raises(ValueError, match="Mixed/legacy"):
        g.make_generation(approved_factors=[entry(generation_id="legacy")])


def test_pointer_deleted_tampered_or_escaping_never_falls_back(repository):
    with pytest.raises(ValueError, match="legacy fallback forbidden"):
        g.load_active_generation(repository)
    receipt = g.capture_legacy_snapshot({"research": repository}, archive_root=repository / "research/archives/legacy")
    g.initialize_generation(repository, archive_manifest=receipt["manifest_path"], activate=True)
    path = repository / g.ACTIVE_PATH
    pointer = json.loads(path.read_bytes())
    pointer["manifest_path"] = "../escape.json"
    pointer["pointer_sha256"] = g.digest({k: v for k, v in pointer.items() if k != "pointer_sha256"})
    path.write_bytes(g.canonical(pointer))
    with pytest.raises(ValueError, match="Path escape"):
        g.load_active_generation(repository)


def test_existing_active_pointer_cannot_be_silently_replaced(repository):
    receipt = g.capture_legacy_snapshot({"research": repository}, archive_root=repository / "research/archives/legacy")
    g.initialize_generation(repository, archive_manifest=receipt["manifest_path"], activate=True)
    with pytest.raises(ValueError, match="Immutable artifact collision"):
        g.initialize_generation(repository, archive_manifest=receipt["manifest_path"], generation_id="other-generation", activate=True)


def test_gold_inventory_metadata_only_read_only_required():
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, sql):
            assert sql == g.GOLD_METADATA_SQL
            assert "evaluation" not in sql and "factor_value" not in sql
            assert "config->>'research_definition_hash'" in sql
        def fetchall(self): return [(1, "legacy", "1", "a" * 64, "APPROVED", "b" * 64, "c" * 64)]
    class Connection:
        read_only = True
        def cursor(self): return Cursor()
    result = g.legacy_gold_inventory(Connection())
    assert result["new_generation_admission"] == "NONE" and result["factor_values_read"] is False
    Connection.read_only = False
    with pytest.raises(ValueError, match="read-only"):
        g.legacy_gold_inventory(Connection())
