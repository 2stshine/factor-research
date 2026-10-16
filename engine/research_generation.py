"""Local legacy preservation and fail-closed research-generation contracts.

This is NOT the existing Silver input/Gold cache generation. Snapshot bytes are
copied opaquely; no old evaluation, return, or lesson content is interpreted.
No database state is changed. A new active generation initially admits nothing.
An old Gold APPROVED flag is never an admission into the new generation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from typing import Mapping, Sequence

DEFAULT_GENERATION = "reference-factor-v3"
ACTIVE_PATH = Path("research/active-generation.json")
REGISTRY_ROOT = Path("research/generations")
SCHEMA = "research-generation-v1"
HASH = re.compile(r"[a-f0-9]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\Z")
SOURCE_KIND = "NEW_GENERATION_RAW_APPROVED"
LEGACY_NATIVE_DASHBOARD = "apps/research-observatory/dist/"
POLICY = {"legacy_gold": "EXCLUDED_NO_FALLBACK", "cross_generation": "REJECT",
          "factor_admission": "EXACT_GENERATION_AND_ENTRY_DIGEST_ALLOWLIST",
          "feature_content_verification": "REQUIRED_SEPARATELY_BY_CONSUMER"}
EXCLUDED_DIRS = frozenset({".git", ".venv", "venv", "node_modules", ".cache", "cache", "caches",
                           "output", "outputs", "dist", "build", ".pytest_cache", "__pycache__",
                           ".mypy_cache", ".ruff_cache", ".aws", ".ssh", ".vercel", "coverage"})
V3_EXCLUDES = ("research/archives/", "research/generations/", "research/v3/", "research/active-generation.json",
               "engine/research_generation.py", "scripts/research_generation.py", "tests/test_research_generation.py",
               "engine/research_transition_guard.py", "tests/test_research_transition_guard.py",
               "engine/reference_", "scripts/reference_", "tests/test_reference_", "docs/research-v3")
SECRET_NAMES = re.compile(r"(?i)(?:^\.env(?:\..*)?$|credentials?(?:\..*)?$|secrets?(?:\..*)?$|.*\.(?:pem|key|p12|pfx|kdbx)$|id_(?:rsa|ed25519|ecdsa)(?:\.pub)?$)")
SECRET_BYTES = re.compile(rb"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|"
                          rb"(?i:(?:access_token|refresh_token|aws_secret_access_key|api_key|password))"
                          rb"[\"']?\s*[:=]\s*[\"'][^\"'\r\n]{16,}[\"']")


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _identifier(value, label="identifier"):
    _require(isinstance(value, str) and IDENTIFIER.fullmatch(value), f"Invalid {label}")
    return value


def _aware(value):
    _require(isinstance(value, str), "Timezone-aware timestamp string required")
    parsed = datetime.fromisoformat(value)
    _require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "Timezone-aware timestamp required")
    return parsed


def _relative(value):
    _require(isinstance(value, str) and "\\" not in value and "\x00" not in value, "Unsafe relative path")
    path = PurePosixPath(value)
    _require(not path.is_absolute() and path.parts and all(p not in {".", ".."} for p in path.parts), "Path escape rejected")
    _require(str(path) == value, "Noncanonical relative path")
    return path


def _no_symlinks(path):
    path = Path(path).absolute()
    # Do not normalize away traversal: symlink/.. may have different filesystem
    # semantics, and lexical ancestor checks must not accept an alias of root.
    _require(".." not in path.parts, "Noncanonical parent traversal path rejected")
    _require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), "Symlink path rejected")
    return path


def _immutable(path, data):
    path = _no_symlinks(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _require(path.is_file() and path.read_bytes() == data, "Immutable artifact collision")
    else:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())


def _git(root, *arguments):
    return subprocess.run(["git", "-C", str(root), *arguments], check=True, capture_output=True).stdout


def _excluded(path):
    parts = PurePosixPath(path).parts
    if any(part in EXCLUDED_DIRS and not (part == "dist" and path.startswith(LEGACY_NATIVE_DASHBOARD)) for part in parts):
        return "CACHE_OUTPUT_OR_GENERATED_DIRECTORY"
    if any(SECRET_NAMES.fullmatch(part) for part in parts):
        return "SECRET_OR_CREDENTIAL_PATH"
    if path.endswith((".pyc", ".pyo")) or parts[-1] == ".DS_Store":
        return "GENERATED_FILE"
    return None


def capture_legacy_snapshot(repository_roots: Mapping[str, Path], *, archive_root: Path,
                            exclude_paths: Sequence[str] = (), max_file_bytes=32 * 1024 * 1024) -> dict:
    """Copy current tracked/nonignored-untracked working bytes, not just HEAD.

    Original files (including dirty campaign/lesson records) remain untouched.
    Ignored files, cache/output, secrets, v3 implementation and this archive are
    not copied. Excluded or oversized files are references, NOT recoverable
    backup claims. No result/return parsing occurs. A concurrent source change
    fails before the snapshot manifest is finalized; orphan CAS blobs are safe.
    """
    archive_root = _no_symlinks(archive_root)
    _require(repository_roots and type(max_file_bytes) is int and max_file_bytes > 0, "Explicit repositories/positive size limit required")
    custom = tuple(str(_relative(p)) for p in exclude_paths)
    repositories, entries, references, observed = {}, [], [], []
    for name, source in sorted(repository_roots.items()):
        _identifier(name, "repository name")
        root = _no_symlinks(source)
        _require(root.is_dir() and archive_root != root and archive_root not in root.parents,
                 "Archive must not be a repository root or its ancestor")
        top = Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
        _require(top == root.resolve(), "Requested source must be the exact Git repository root")
        head = os.fsdecode(_git(root, "rev-parse", "HEAD")).strip()
        tracked = {os.fsdecode(p) for p in _git(root, "ls-files", "--cached", "-z").split(b"\0") if p}
        listed = sorted({os.fsdecode(p) for p in _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0") if p})
        repositories[name] = {"original_root": str(root), "git_head": head,
                              "source": "CURRENT_WORKING_BYTES_INCLUDING_DIRTY_AND_NONIGNORED_UNTRACKED"}
        for relative in listed:
            safe = _relative(relative)
            source_path = root / safe
            # Never let the capture's own growing files, or new-generation work,
            # change its identity on a second otherwise identical invocation.
            if source_path.is_relative_to(archive_root) or any(relative.startswith(p) for p in (*V3_EXCLUDES, *custom)):
                continue
            info = {"repository": name, "path": relative, "original_path": str(source_path), "tracked": relative in tracked}
            reason = _excluded(relative)
            if source_path.is_symlink() or any(p.is_symlink() for p in source_path.parents):
                reason = reason or "SYMLINK_NOT_DEREFERENCED"
            if reason:
                references.append({**info, "reason": reason, "copied": False})
                continue
            if not source_path.is_file():
                references.append({**info, "reason": "MISSING_WORKING_FILE", "copied": False})
                continue
            before = source_path.stat()
            if before.st_size > max_file_bytes:
                references.append({**info, "reason": "SIZE_LIMIT_REFERENCE_ONLY", "bytes": before.st_size, "copied": False})
                continue
            raw = source_path.read_bytes()  # Opaque copy/hash; never interpret outcomes.
            if SECRET_BYTES.search(raw):
                references.append({**info, "reason": "POSSIBLE_EMBEDDED_SECRET_NOT_COPIED", "copied": False})
                continue
            sha = hashlib.sha256(raw).hexdigest()
            object_path = Path("objects/sha256") / sha[:2] / sha
            _immutable(archive_root / object_path, raw)
            entries.append({**info, "sha256": sha, "bytes": len(raw), "mode": stat.S_IMODE(before.st_mode),
                            "object_path": object_path.as_posix(), "copied": True})
            observed.append((source_path, sha, stat.S_IMODE(before.st_mode)))
    for path, sha, mode in observed:
        _no_symlinks(path)
        _require(path.is_file() and file_digest(path) == sha and stat.S_IMODE(path.stat().st_mode) == mode,
                 "Source working tree changed during capture; retry without replacing originals")
    body = {"schema_version": "legacy-research-snapshot-v1", "repositories": repositories,
            "entries": entries, "references_not_copied": references,
            "policy": {"source_paths_preserved": True, "opaque_results_backup_only": True,
                       "ignored_files_included": False, "default_excluded_directories": sorted(EXCLUDED_DIRS),
                       "native_dashboard_dist_included": LEGACY_NATIVE_DASHBOARD,
                       "new_generation_exclusions": list(V3_EXCLUDES), "extra_exclusions": list(custom),
                       "max_file_bytes": max_file_bytes, "secret_scan": "CONSERVATIVE_PATH_AND_LITERAL_PATTERN_FILTER_NOT_A_FORMAL_SECRET_AUDIT",
                       "external_gold_values_copied": False, "database_writes": False}}
    archive_id = digest(body)
    manifest = {**body, "archive_id": archive_id}
    manifest_path = archive_root / "snapshots" / f"{archive_id}.json"
    raw = canonical(manifest) + b"\n"
    _immutable(manifest_path, raw)
    return {"archive_id": archive_id, "manifest_path": str(manifest_path), "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "file_count": len(entries), "reference_only_count": len(references), "bytes": sum(r["bytes"] for r in entries),
            "originals_modified": False, "database_writes": False}


def verify_legacy_snapshot(manifest_path) -> dict:
    path = _no_symlinks(manifest_path)
    raw = path.read_bytes()
    manifest = json.loads(raw)
    _require(manifest.get("schema_version") == "legacy-research-snapshot-v1", "Unknown legacy snapshot")
    body = {k: v for k, v in manifest.items() if k != "archive_id"}
    _require(digest(body) == manifest.get("archive_id"), "Legacy manifest digest mismatch")
    archive_root = path.parent.parent
    seen = set()
    for row in manifest["entries"]:
        key = (row["repository"], row["path"])
        _require(key not in seen, "Duplicate archived source path")
        seen.add(key)
        _relative(row["path"])
        object_path = _relative(row["object_path"])
        _require(HASH.fullmatch(row["sha256"]) and str(object_path) == f"objects/sha256/{row['sha256'][:2]}/{row['sha256']}",
                 "Non-content-addressed archive object")
        source = _no_symlinks(archive_root / object_path)
        _require(source.is_file() and source.stat().st_size == row["bytes"] and file_digest(source) == row["sha256"],
                 "Archived object missing or corrupt")
    return {"archive_id": manifest["archive_id"], "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "file_count": len(seen), "reference_only_count": len(manifest["references_not_copied"])}


def make_factor_entry(*, generation_id, factor_id, definition_sha256, implementation_sha256,
                      feature_sha256, approval_evidence_sha256, admitted_at):
    entry = dict(generation_id=generation_id, factor_id=factor_id, source_kind=SOURCE_KIND,
                 definition_sha256=definition_sha256, implementation_sha256=implementation_sha256,
                 feature_sha256=feature_sha256, approval_evidence_sha256=approval_evidence_sha256,
                 admitted_at=admitted_at)
    entry["entry_sha256"] = digest(entry)
    _validate_entry(entry, generation_id)
    return entry


def _validate_entry(entry, generation_id):
    expected = {"generation_id", "factor_id", "source_kind", "definition_sha256", "implementation_sha256",
                "feature_sha256", "approval_evidence_sha256", "admitted_at", "entry_sha256"}
    _require(isinstance(entry, dict) and set(entry) == expected, "Unexpected factor admission fields")
    _identifier(entry["factor_id"], "factor_id")
    _require(entry["generation_id"] == generation_id and entry["source_kind"] == SOURCE_KIND, "Mixed/legacy factor generation rejected")
    _aware(entry["admitted_at"])
    _require(all(isinstance(entry[k], str) and HASH.fullmatch(entry[k]) for k in expected if k.endswith("sha256")), "Invalid factor entry digest")
    _require(digest({k: v for k, v in entry.items() if k != "entry_sha256"}) == entry["entry_sha256"], "Factor entry digest mismatch")


def make_generation(*, generation_id=DEFAULT_GENERATION, purpose="RESEARCH", parent_archive=None, approved_factors=()):
    body = {"schema_version": SCHEMA, "generation_id": generation_id, "purpose": purpose,
            "parent_archive": parent_archive, "policy": dict(POLICY), "approved_factors": list(approved_factors)}
    result = {**body, "generation_sha256": digest(body)}
    return validate_generation(result)


def validate_generation(manifest):
    expected = {"schema_version", "generation_id", "purpose", "parent_archive", "policy", "approved_factors", "generation_sha256"}
    _require(isinstance(manifest, dict) and set(manifest) == expected and manifest["schema_version"] == SCHEMA, "Invalid generation manifest")
    _identifier(manifest["generation_id"], "generation_id")
    _require(manifest["purpose"] in {"RESEARCH", "SYNTHETIC"} and manifest["policy"] == POLICY, "Unsupported/legacy-compatible generation policy")
    _require(isinstance(manifest["approved_factors"], list), "Explicit approved factor list required")
    _require(digest({k: v for k, v in manifest.items() if k != "generation_sha256"}) == manifest["generation_sha256"], "Generation digest mismatch")
    parent = manifest["parent_archive"]
    if parent is not None:
        _require(set(parent) == {"archive_id", "manifest_sha256"} and all(HASH.fullmatch(v) for v in parent.values()), "Invalid parent archive binding")
    seen = set()
    for entry in manifest["approved_factors"]:
        _validate_entry(entry, manifest["generation_id"])
        _require(entry["factor_id"] not in seen, "Duplicate approved factor id")
        seen.add(entry["factor_id"])
    return json.loads(canonical(manifest))  # Caller mutations cannot edit registry input.


def validate_factor_inputs(manifest, feature_entries, *, expected_generation_id=None, decision_at=None):
    """Validate membership/provenance only; caller must verify actual feature bytes.

    Empty active approval means reject every nonempty selection, not query old
    APPROVED Gold. The caller must require its expected purpose independently
    (e.g. never use SYNTHETIC fixtures in a production consumer).
    """
    generation = validate_generation(manifest)
    if expected_generation_id is not None:
        _require(generation["generation_id"] == expected_generation_id, "Unexpected active research generation")
    allowed = {e["factor_id"]: e for e in generation["approved_factors"]}
    seen, selected = set(), []
    for entry in feature_entries:
        factor_id = entry.get("factor_id")
        _require(factor_id in allowed and factor_id not in seen, "Factor is not in the exact active allowlist (no legacy fallback)")
        approved = allowed[factor_id]
        _require(entry.get("generation_id") == generation["generation_id"] and entry.get("entry_sha256") == approved["entry_sha256"],
                 "Mixed-generation or stale factor entry rejected")
        for key, value in entry.items():
            if key in approved:
                _require(value == approved[key], "Factor provenance fields contradict approved entry")
        if decision_at is not None:
            _require(_aware(approved["admitted_at"]) <= _aware(decision_at), "Factor admission occurred after this decision time")
        selected.append(approved)
        seen.add(factor_id)
    return selected


def initialize_generation(repo_root, *, archive_manifest, generation_id=DEFAULT_GENERATION, activate=False):
    """Create an immutable EMPTY registry, optionally create a first pointer.

    Existing active pointers are never silently replaced. A populated registry
    requires a separate reviewed future admission mechanism, not legacy import.
    """
    root = _no_symlinks(repo_root)
    archive = verify_legacy_snapshot(archive_manifest)
    manifest = make_generation(generation_id=generation_id, parent_archive={k: archive[k] for k in ("archive_id", "manifest_sha256")})
    relative = REGISTRY_ROOT / generation_id / (manifest["generation_sha256"] + ".json")
    _immutable(root / relative, canonical(manifest) + b"\n")
    pointer = {"schema_version": "active-research-generation-v1", "generation_id": generation_id,
               "generation_sha256": manifest["generation_sha256"], "manifest_path": relative.as_posix(),
               "legacy_gold_policy": "EXCLUDED_NO_FALLBACK"}
    pointer["pointer_sha256"] = digest(pointer)
    if activate:
        _immutable(root / ACTIVE_PATH, canonical(pointer) + b"\n")
    return {"generation": manifest, "manifest_path": str(root / relative), "active": bool(activate),
            "approved_factor_count": 0, "legacy_gold_imported": False}


def load_active_generation(repo_root):
    root = _no_symlinks(repo_root)
    path = _no_symlinks(root / ACTIVE_PATH)
    _require(path.is_file(), "No active research generation; legacy fallback forbidden")
    pointer = json.loads(path.read_bytes())
    _require(pointer.get("schema_version") == "active-research-generation-v1"
             and pointer.get("legacy_gold_policy") == "EXCLUDED_NO_FALLBACK"
             and pointer.get("pointer_sha256") == digest({k: v for k, v in pointer.items() if k != "pointer_sha256"}),
             "Active generation pointer integrity mismatch")
    relative = _relative(pointer["manifest_path"])
    expected = REGISTRY_ROOT / _identifier(pointer["generation_id"]) / (pointer["generation_sha256"] + ".json")
    _require(str(relative) == expected.as_posix(), "Active pointer references an unexpected registry path")
    target = _no_symlinks(root / relative)
    manifest = validate_generation(json.loads(target.read_bytes()))
    _require(manifest["purpose"] == "RESEARCH" and manifest["generation_id"] == pointer["generation_id"]
             and manifest["generation_sha256"] == pointer["generation_sha256"], "Active generation/purpose binding mismatch")
    return manifest


GOLD_METADATA_SQL = """
SELECT factor_id,factor_key,version,implementation_hash,status,
       config->>'research_definition_hash' AS research_definition_hash,
       config->>'gold_generation_digest' AS gold_generation_digest
FROM gold.factor ORDER BY factor_id
"""


def legacy_gold_inventory(conn):
    """Read definition/status metadata only; never evaluations or factor values."""
    _require(getattr(conn, "read_only", False) is True, "Gold inventory requires an explicitly read-only connection")
    with conn.cursor() as cursor:
        cursor.execute(GOLD_METADATA_SQL)
        rows = [dict(zip(("factor_id", "factor_key", "version", "implementation_hash", "status",
                          "research_definition_hash", "gold_generation_digest"), row)) for row in cursor.fetchall()]
    records = [{k: str(v) if v is not None else None for k, v in row.items()} for row in rows]
    body = {"schema_version": "legacy-gold-metadata-inventory-v1", "query_sha256": hashlib.sha256(GOLD_METADATA_SQL.encode()).hexdigest(),
            "rows": records, "factor_values_read": False, "evaluation_read": False, "database_writes": False,
            "physical_retention": "UNCHANGED_IN_EXISTING_GOLD", "new_generation_admission": "NONE"}
    return {**body, "inventory_sha256": digest(body)}
