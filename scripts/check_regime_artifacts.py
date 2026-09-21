"""Read-only verification of the portable registered regime runtime artifacts.

No API, DB, campaign, result, or OOS reads. Local evidence references are checked
for existence only: their absence does not invalidate an embedded runtime input,
and their presence does not establish historical PIT or a completed re-audit.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import unquote, urlparse

from engine.regime_inputs import read_context


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "research/regime_sources.json"


def _inside(root, path):
    path = Path(path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Runtime dependency escapes repository checkout")
    return path


def _index_bytes(root, relative):
    """Inspect Git's index without changing it or reading unrelated objects."""
    result = subprocess.run(["git", "-C", str(root), "show", f":{relative}"],
                            capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def _local_references(approval, owner):
    for entry in approval["evidence"]:
        values = {entry.get("local_path"), entry.get("uri")}
        for value in values - {None}:
            if not isinstance(value, str):
                continue
            parsed = urlparse(value)
            if parsed.scheme and parsed.scheme != "file":
                continue
            if parsed.scheme == "file" and parsed.netloc not in ("", "localhost"):
                continue
            path = Path(unquote(parsed.path) if parsed.scheme == "file" else value)
            yield (path if path.is_absolute() else owner.parent / path).resolve()


def check_artifacts(root=ROOT, *, registry=REGISTRY, tracked_only=False):
    root = Path(root).resolve()
    registry_path = _inside(root, root / registry)
    payload = json.loads(registry_path.read_bytes())
    if payload.get("schema_version") != "diagnostic-regime-registry-v1":
        raise ValueError("Unsupported regime registry")
    runtime, refs, contexts, errors = set(), set(), [], []
    enabled_count = 0
    for entry in payload["contexts"]:
        if entry.get("enabled") is not True:
            continue
        enabled_count += 1
        try:
            path = _inside(root, registry_path.parent / entry["file"])
            runtime.add(path)
            body = path.read_bytes()
            if hashlib.sha256(body).hexdigest() != entry["sha256"]:
                raise ValueError("Registered regime context hash mismatch")
            bundle = json.loads(body)
            # Resolve/check all runtime dependencies before read_context follows
            # approval_file paths. External/symlink dependencies are not portable.
            for item in bundle["contexts"]:
                runtime.add(_inside(root, path.parent / item["approval_file"]))
            prepared = read_context(path)  # byte hash + source/approval binding
            for item, checked in zip(bundle["contexts"], prepared["contexts"]):
                owner = (path.parent / item["approval_file"]).resolve()
                refs.update(_local_references(checked["approval"], owner))
                contexts.append(checked["source"]["context_id"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({"context_id": entry.get("context_id"), "error": str(exc)})
    if not enabled_count:
        errors.append({"error": "No enabled regime contexts"})
    if len(contexts) != len(set(contexts)):
        errors.append({"error": "Duplicate regime context identity"})
    files = []
    for path in sorted(runtime):
        if not path.is_file():
            continue  # The associated context read already records the failure.
        body = path.read_bytes()
        files.append({"path": path.relative_to(root).as_posix(), "bytes": len(body),
                      "sha256": hashlib.sha256(body).hexdigest()})
    if tracked_only:
        for path in sorted(runtime | {registry_path}):
            relative = path.relative_to(root).as_posix()
            indexed = _index_bytes(root, relative)
            if indexed is None:
                errors.append({"file": relative, "error": "Missing from Git index"})
            elif not path.is_file() or indexed != path.read_bytes():
                errors.append({"file": relative, "error": "Working bytes differ from Git index"})
    existence = Counter("present" if path.is_file() else "missing" for path in refs)
    return {
        "schema_version": "regime-artifact-check-v1",
        "runtime_status": "FAIL" if errors else "PASS",
        "registry": registry_path.relative_to(root).as_posix(),
        "registry_sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
        "enabled_bundles": enabled_count, "contexts": len(contexts),
        "runtime_files": files, "runtime_file_count": len(files),
        "runtime_bytes": sum(item["bytes"] for item in files),
        "git_index_required": tracked_only, "errors": errors,
        "reaudit": {
            "status": "INCOMPLETE_LOCAL_REFERENCES" if existence["missing"] else "LOCAL_REFERENCES_PRESENT",
            "local_reference_count": len(refs), "present": existence["present"],
            "missing": existence["missing"],
            "outside_checkout": sum(not path.is_relative_to(root) for path in refs),
            "required_for_runtime": False, "evidence_hashes_rechecked": False,
            "historical_pit_verified_by_this_check": False,
            "note": "Existence only; remote evidence is not fetched. Raw evidence is separately retained, not distributed here.",
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", default=REGISTRY)
    parser.add_argument("--tracked-only", action="store_true",
                        help="Require registry/runtime bytes to match Git's index")
    parser.add_argument("--list-runtime", action="store_true",
                        help="Print the exact runtime file paths, one per line")
    args = parser.parse_args()
    try:
        result = check_artifacts(args.root, registry=args.registry, tracked_only=args.tracked_only)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"runtime_status": "FAIL", "error": str(exc)}))
        raise SystemExit(1)
    if args.list_runtime:
        print("\n".join(item["path"] for item in result["runtime_files"]))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["runtime_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
