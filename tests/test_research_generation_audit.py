"""Independent synthetic archive/registry safety audit; no actual research blobs."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

from engine import research_generation as g


@pytest.fixture
def saved(tmp_path):
    repo = tmp_path / "synthetic-repository"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, capture_output=True)
    (repo / "definition.py").write_bytes(b"synthetic_definition = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "definition.py"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Synthetic", "-c", "user.email=audit@example.invalid",
                    "commit", "-qm", "synthetic fixture"], check=True, capture_output=True)
    receipt = g.capture_legacy_snapshot({"synthetic": repo}, archive_root=repo / "research/archives/synthetic")
    return repo, receipt


def manifest_of(receipt):
    path = Path(receipt["manifest_path"])
    return path, json.loads(path.read_bytes())


def rewrite_fixture_manifest(path, manifest):
    manifest["archive_id"] = g.digest({key: value for key, value in manifest.items() if key != "archive_id"})
    path.write_bytes(g.canonical(manifest))


def factor(name="synthetic_new"):
    return g.make_factor_entry(generation_id=g.DEFAULT_GENERATION, factor_id=name,
        definition_sha256="1" * 64, implementation_sha256="2" * 64,
        feature_sha256="3" * 64, approval_evidence_sha256="4" * 64,
        admitted_at="2020-01-01T00:00:00+09:00")


def test_archive_verification_does_not_read_or_modify_changed_original(saved):
    repo, receipt = saved
    (repo / "definition.py").write_bytes(b"synthetic_definition = 999\n")
    before = (repo / "definition.py").read_bytes()
    assert g.verify_legacy_snapshot(receipt["manifest_path"])["archive_id"] == receipt["archive_id"]
    assert (repo / "definition.py").read_bytes() == before


@pytest.mark.parametrize("damage", ["missing", "same_size_changed", "truncated", "symlink"])
def test_corrupt_or_redirected_cas_objects_are_never_approved(saved, tmp_path, damage):
    _, receipt = saved
    path, manifest = manifest_of(receipt)
    target = path.parent.parent / manifest["entries"][0]["object_path"]
    raw = target.read_bytes()
    if damage == "missing":
        target.unlink()
    elif damage == "same_size_changed":
        target.write_bytes(b"x" * len(raw))
    elif damage == "truncated":
        target.write_bytes(raw[:3])
    else:
        external = tmp_path / "external-synthetic-data"
        external.write_bytes(raw)
        target.unlink()
        target.symlink_to(external)
    with pytest.raises(ValueError):
        g.verify_legacy_snapshot(path)


@pytest.mark.parametrize("mutation", ["duplicate_path", "object_escape", "source_escape", "noncas_location", "wrong_size"])
def test_rehashed_malformed_fixture_archive_still_rejects_unsafe_structure(saved, mutation):
    _, receipt = saved
    path, manifest = manifest_of(receipt)
    if mutation == "duplicate_path":
        manifest["entries"].append(deepcopy(manifest["entries"][0]))
    elif mutation == "object_escape":
        manifest["entries"][0]["object_path"] = "../../outside"
    elif mutation == "source_escape":
        manifest["entries"][0]["path"] = "../definition.py"
    elif mutation == "noncas_location":
        manifest["entries"][0]["object_path"] = "definition.py"
    else:
        manifest["entries"][0]["bytes"] += 1
    rewrite_fixture_manifest(path, manifest)
    with pytest.raises(ValueError):
        g.verify_legacy_snapshot(path)


def test_capture_immutable_collision_never_overwrites_original_or_existing_object(saved):
    repo, receipt = saved
    path, manifest = manifest_of(receipt)
    target = path.parent.parent / manifest["entries"][0]["object_path"]
    target.write_bytes(b"intentionally corrupted synthetic CAS")
    before_original, before_object = (repo / "definition.py").read_bytes(), target.read_bytes()
    with pytest.raises(ValueError, match="Immutable artifact collision"):
        g.capture_legacy_snapshot({"synthetic": repo}, archive_root=path.parent.parent)
    assert target.read_bytes() == before_object
    assert (repo / "definition.py").read_bytes() == before_original


def test_activation_initializes_empty_even_when_old_gold_style_metadata_exists(saved):
    repo, receipt = saved
    (repo / "old-approved.json").write_text('{"factor_id":"old","status":"APPROVED"}')
    g.initialize_generation(repo, archive_manifest=receipt["manifest_path"], activate=True)
    active = g.load_active_generation(repo)
    assert active["approved_factors"] == []
    with pytest.raises(ValueError, match="no legacy fallback"):
        g.validate_factor_inputs(active, [{"factor_id": "old", "status": "APPROVED", "generation_id": g.DEFAULT_GENERATION, "entry_sha256": "1" * 64}])


@pytest.mark.parametrize("damage", ["deleted", "invalid_json", "list_not_object", "dangling_manifest", "altered_registry"])
def test_absent_or_broken_active_state_never_returns_legacy(saved, damage):
    repo, receipt = saved
    init = g.initialize_generation(repo, archive_manifest=receipt["manifest_path"], activate=True)
    path = repo / g.ACTIVE_PATH
    if damage == "deleted":
        path.unlink()
    elif damage == "invalid_json":
        path.write_text("not-json")
    elif damage == "list_not_object":
        path.write_text("[]")
    elif damage == "dangling_manifest":
        Path(init["manifest_path"]).unlink()
    else:
        manifest_path = Path(init["manifest_path"])
        manifest = json.loads(manifest_path.read_bytes())
        manifest["approved_factors"] = [factor()]
        manifest_path.write_bytes(g.canonical(manifest))
    with pytest.raises((ValueError, AttributeError, FileNotFoundError)):
        g.load_active_generation(repo)


def test_even_hash_consistent_synthetic_manifest_cannot_be_active_research(saved):
    repo, _ = saved
    manifest = g.make_generation(purpose="SYNTHETIC", approved_factors=[factor()])
    relative = g.REGISTRY_ROOT / g.DEFAULT_GENERATION / (manifest["generation_sha256"] + ".json")
    target = repo / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(g.canonical(manifest))
    pointer = {"schema_version": "active-research-generation-v1", "generation_id": g.DEFAULT_GENERATION,
        "generation_sha256": manifest["generation_sha256"], "manifest_path": relative.as_posix(),
        "legacy_gold_policy": "EXCLUDED_NO_FALLBACK"}
    pointer["pointer_sha256"] = g.digest(pointer)
    (repo / g.ACTIVE_PATH).write_bytes(g.canonical(pointer))
    with pytest.raises(ValueError, match="purpose"):
        g.load_active_generation(repo)


def test_duplicate_allowlist_or_selected_factor_is_rejected():
    entry = factor()
    with pytest.raises(ValueError, match="Duplicate approved"):
        g.make_generation(purpose="SYNTHETIC", approved_factors=[entry, entry])
    manifest = g.make_generation(purpose="SYNTHETIC", approved_factors=[entry])
    metadata = {key: entry[key] for key in ("factor_id", "generation_id", "entry_sha256")}
    with pytest.raises(ValueError, match="allowlist"):
        g.validate_factor_inputs(manifest, [metadata, metadata])


def test_caller_mutation_cannot_expand_validated_allowlist():
    original = g.make_generation(purpose="SYNTHETIC", approved_factors=[factor()])
    validated = g.validate_generation(original)
    validated["approved_factors"][0]["factor_id"] = "changed"
    assert original["approved_factors"][0]["factor_id"] == "synthetic_new"
    with pytest.raises(ValueError, match="digest"):
        g.validate_generation(validated)


def test_feature_content_authentication_is_explicitly_a_separate_consumer_requirement():
    manifest = g.make_generation(purpose="SYNTHETIC", approved_factors=[factor()])
    assert manifest["policy"]["feature_content_verification"] == "REQUIRED_SEPARATELY_BY_CONSUMER"
    assert "caller must verify actual feature bytes" in g.validate_factor_inputs.__doc__


@pytest.mark.parametrize("target", ["same_root", "ancestor"])
def test_noncanonical_parent_segments_cannot_bypass_archive_root_boundary(saved, target):
    repo, _ = saved
    # Both spellings currently evade lexical Path equality unless canonical
    # traversal is rejected before the repository/ancestor boundary check.
    archive = repo / ".." / repo.name if target == "same_root" else repo / ".."
    with pytest.raises(ValueError, match="path|Path|ancestor|root|canonical"):
        g.capture_legacy_snapshot({"synthetic": repo}, archive_root=archive)
