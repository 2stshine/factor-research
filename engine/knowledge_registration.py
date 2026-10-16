"""Optional, future-only lineage capture and registration binding.

Captures archive existing knowledge bytes locally; they are not a new prompt
feed or content-safety certificate. Reviewer evidence is read only in memory.
No candidate execution, knowledge refresh, database access or publication.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from engine.knowledge_lineage import (
    AUTHENTICATION, canonical_hash, validate_lineage, _stamp,
)

CAPTURE_VERSION = "knowledge-capture-v1"
REGISTRATION_VERSION = "registered-knowledge-lineage-v1"
CAPTURE_FIELDS = {
    "schema_version", "captured_at", "knowledge_snapshot_hash", "knowledge_text",
    "reviewed_lesson_versions", "source_ledger_sha256", "catalog_sha256",
    "authentication", "snapshot_content_safety_audited",
}
VERSION_FIELDS = {"record_id", "review_hash", "packet_sha256"}
MAX_CAPTURE_BYTES = 8 * 1024 * 1024


def _now():
    return datetime.now(timezone.utc).isoformat()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _authenticated(root, as_of):
    # Export function is read-only. Never call refresh_candidate_lessons here.
    from scripts.dashboard_exports.export_research_catalog import export
    return export(Path(root), as_of)


def _versions(records):
    versions = []
    seen = set()
    for record in records:
        rid = record["record_id"]
        _require(rid not in seen, "Duplicate authenticated lesson identity")
        seen.add(rid)
        if (record.get("visibility") != "RELEASED_QUALITATIVE"
                or record.get("review_status") != "REVIEWED_CURRENT"):
            continue
        _require(record.get("provenance", {}).get("authentication") == AUTHENTICATION,
                 "Lesson authentication is required")
        _require(isinstance(record.get("review"), dict), "Reviewed lesson body missing")
        packet = record["provenance"].get("packet_sha256")
        _require(_sha(packet), "Invalid authenticated packet hash")
        versions.append({"record_id": rid, "review_hash": canonical_hash(record["review"]),
                         "packet_sha256": packet})
    return sorted(versions, key=lambda row: row["record_id"])


def _capture_path(root, capture_id):
    _require(_sha(capture_id), "Capture ID must be a SHA-256, not an arbitrary path")
    directory = Path(root).resolve() / "memory/knowledge_snapshots"
    path = directory / f"{capture_id}.json"
    _require(path.resolve().is_relative_to(Path(root).resolve()), "Capture path escapes research root")
    return path


def capture_knowledge(root):
    """Archive an already generated knowledge file; never generate a prompt.

    Exact reconstruction authenticates the lesson projection and ties bytes to
    current records. Input-context sections are inherited from that file, so
    this is deliberately NOT a safety audit of the full knowledge document.
    captured_at is owned by this tool, never supplied by a CLI argument/mtime.
    """
    from scripts.knowledge import _knowledge_parts, _render_knowledge
    from engine.epochs import _write_new

    root = Path(root)
    knowledge_path = root / "KNOWLEDGE.md"
    ledger_path = root / "memory/candidate_lessons.jsonl"
    raw, ledger_bytes = knowledge_path.read_bytes(), ledger_path.read_bytes()
    _require(0 < len(raw) < MAX_CAPTURE_BYTES // 2, "Knowledge snapshot size is unsupported")
    text = raw.decode("utf-8")
    catalog = _authenticated(root, _now())
    ledger_hash = hashlib.sha256(ledger_bytes).hexdigest()
    _require(catalog.get("source", {}).get("ledger_file_sha256") == ledger_hash,
             "Ledger changed during authentication")
    rows = [json.loads(line) for line in ledger_bytes.decode("utf-8").splitlines() if line.strip()]
    _require(len({row["record_id"] for row in rows}) == len(rows), "Duplicate source ledger identity")
    records = catalog["records"]
    authenticated = {row["record_id"]: row for row in records}
    accepted = []
    for row in rows:
        current = authenticated.get(row["record_id"])
        if current is None:
            continue
        copy = dict(row)
        if current.get("review_status") == "REVIEWED_CURRENT":
            _require(canonical_hash(row.get("review")) == canonical_hash(current.get("review")),
                     "Rendered review differs from authenticated review")
        else:
            # Do not let a stale saved CURRENT flag bypass the exporter's fresh
            # review validation when reproducing candidate-facing lesson text.
            copy.pop("review", None)
            copy.pop("review_validation", None)
        accepted.append(copy)
    parts = _knowledge_parts(root, context_text=text)
    _require(_render_knowledge(parts, accepted).encode("utf-8") == raw,
             "Knowledge is not the current authenticated qualitative view; refresh through the existing workflow first")
    _require(knowledge_path.read_bytes() == raw and ledger_path.read_bytes() == ledger_bytes,
             "Knowledge or ledger changed during capture")
    payload = {
        "schema_version": CAPTURE_VERSION, "captured_at": _now(),
        "knowledge_snapshot_hash": hashlib.sha256(raw).hexdigest(), "knowledge_text": text,
        "reviewed_lesson_versions": _versions(records), "source_ledger_sha256": ledger_hash,
        "catalog_sha256": canonical_hash(catalog), "authentication": AUTHENTICATION,
        "snapshot_content_safety_audited": False,
    }
    capture_id = canonical_hash(payload)
    path = _capture_path(root, capture_id)
    if path.exists():
        _require(load_capture(root, capture_id) == payload, "Existing capture differs")
    else:
        _write_new(path, payload)
    # Only identities and status leave this function, never a new candidate prompt.
    return {"capture_id": capture_id, "path": str(path), "captured_at": payload["captured_at"],
            "knowledge_snapshot_hash": payload["knowledge_snapshot_hash"],
            "reviewed_lesson_versions": payload["reviewed_lesson_versions"],
            "snapshot_content_safety_audited": False, "candidate_registered": False}


def load_capture(root, capture_id):
    path = _capture_path(root, capture_id)
    _require(path.stat().st_size <= MAX_CAPTURE_BYTES, "Capture is too large")
    payload = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(payload, dict) and set(payload) == CAPTURE_FIELDS,
             "Unsupported capture fields")
    _require(payload["schema_version"] == CAPTURE_VERSION
             and payload["authentication"] == AUTHENTICATION
             and payload["snapshot_content_safety_audited"] is False,
             "Unsupported capture contract")
    _require(canonical_hash(payload) == capture_id, "Capture content hash mismatch")
    _stamp(payload["captured_at"])
    _require(isinstance(payload["knowledge_text"], str), "Knowledge text missing")
    raw = payload["knowledge_text"].encode("utf-8")
    _require(raw and hashlib.sha256(raw).hexdigest() == payload["knowledge_snapshot_hash"],
             "Captured knowledge byte hash mismatch")
    _require(_sha(payload["source_ledger_sha256"]) and _sha(payload["catalog_sha256"]),
             "Capture source identities missing")
    versions = payload["reviewed_lesson_versions"]
    _require(isinstance(versions, list), "Capture lesson versions missing")
    seen = set()
    for row in versions:
        _require(isinstance(row, dict) and set(row) == VERSION_FIELDS,
                 "Invalid captured lesson version")
        rid = row["record_id"]
        _require(isinstance(rid, str) and rid and rid not in seen
                 and _sha(row["review_hash"]) and _sha(row["packet_sha256"]),
                 "Invalid or duplicate captured lesson identity")
        seen.add(rid)
    return payload


def _captured_declaration(metadata, captured, cutoff):
    _require(isinstance(metadata, dict), "Lineage declaration must be a mapping")
    _require(metadata.get("snapshot_captured_at") == captured["captured_at"],
             "Declaration capture time differs from tool-owned capture time")
    _require(metadata.get("knowledge_snapshot_hash") == captured["knowledge_snapshot_hash"],
             "Declaration snapshot differs from capture")
    _require(_stamp(captured["captured_at"]) <= _stamp(metadata.get("declared_at")) <= _stamp(cutoff),
             "Capture/declaration is later than registration or out of order")
    available = {row["record_id"]: row for row in captured["reviewed_lesson_versions"]}
    refs = metadata.get("lesson_references")
    _require(isinstance(refs, list), "Declared lesson references missing")
    for ref in refs:
        _require(isinstance(ref, dict), "Invalid declared lesson reference")
        version = available.get(ref.get("record_id"))
        _require(version is not None, "Lesson was not captured as public and reviewed at snapshot time")
        _require(all(ref.get(key) == version[key] for key in VERSION_FIELDS),
                 "Lesson review or packet version differs from capture")


def _source_declaration(root, factor, spec, strategy_digest):
    path = Path(spec.get("strategy_file", ""))
    if not path.is_absolute():
        path = Path(root).resolve().parent / path
    _require(path.resolve().is_relative_to(Path(root).resolve().parent / "factors/candidates"),
             "Opt-in source must be a candidate file in this repository")
    raw = path.read_bytes()
    _require(_sha(strategy_digest) and hashlib.sha256(raw).hexdigest() == strategy_digest
             and spec.get("strategy_sha256") == strategy_digest,
             "Candidate source changed since registry load")
    _require(spec.get("factor_name") == factor.name, "Candidate name/spec binding mismatch")
    tree = ast.parse(raw, filename=str(path))
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Name)
                   and isinstance(node.ctx, ast.Store) and node.id == "RESEARCH_SPEC"]
    top = [node for node in tree.body if isinstance(node, ast.Assign)
           and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
           and node.targets[0].id == "RESEARCH_SPEC"]
    _require(len(assignments) == len(top) == 1,
             "Opt-in requires one top-level literal RESEARCH_SPEC assignment")
    try:
        literal = ast.literal_eval(top[0].value)
    except (ValueError, TypeError, SyntaxError):
        raise ValueError("Opt-in RESEARCH_SPEC must be a literal mapping") from None
    _require(isinstance(literal, dict) and "knowledge_lineage" in literal,
             "Candidate source has no literal lineage declaration")
    metadata = literal["knowledge_lineage"]
    _require(metadata == spec.get("knowledge_lineage"), "Loaded declaration differs from actual candidate source")
    # The core API can be called without the CLI. Bind the actual Factor to the
    # loader's content-addressed module too, not just a same-name declaration.
    code = getattr(factor.compute, "__code__", None)
    namespace = getattr(factor.compute, "__globals__", {})
    _require(code is not None
             and code.co_filename == f"{path.resolve()}#sha256={strategy_digest}"
             and namespace.get("FACTOR") is factor
             and namespace.get("RESEARCH_SPEC") == literal,
             "Factor was not loaded from the declared candidate source")
    return metadata


def prepare_registration(root, capture_id, factors, specs, strategy_digests, *, cutoff):
    """Validate before any registration write; omission is a read-free no-op."""
    if not capture_id and specs is None:
        return None
    specs = specs or {}
    declared = [factor for factor in factors if "knowledge_lineage" in specs.get(factor.name, {})]
    if not capture_id:
        _require(not declared, "knowledge_lineage requires explicit --knowledge-capture")
        return None
    _require(declared, "Knowledge capture supplied but no candidate opted in")
    _require(set(specs) == {factor.name for factor in factors}, "Candidate spec set differs from registration set")
    captured = load_capture(root, capture_id)
    _require(_stamp(captured["captured_at"]) <= _stamp(cutoff), "Capture was generated after registration cutoff")
    declarations = {}
    for factor in declared:
        metadata = _source_declaration(root, factor, specs[factor.name], strategy_digests[factor.name])
        _captured_declaration(metadata, captured, cutoff)
        declarations[factor.name] = metadata
    current = _authenticated(root, cutoff)["records"]
    bindings = {}
    for factor in declared:
        metadata = declarations[factor.name]
        checked = validate_lineage(metadata, captured["knowledge_text"].encode("utf-8"), current, cutoff=cutoff)
        bindings[factor.name] = {
            "definition_hash": factor.definition_hash, "strategy_sha256": strategy_digests[factor.name],
            "declaration_hash": checked["declaration_hash"], "capture_id": capture_id,
            "knowledge_snapshot_hash": captured["knowledge_snapshot_hash"],
            "declaration": metadata,
        }
    return {"schema_version": REGISTRATION_VERSION, "status": "VALIDATED_BEFORE_REGISTRATION",
            "registered_at": cutoff, "candidate_bindings": bindings,
            "snapshot_content_safety_audited": False, "independent_evidence": False,
            "follow_up_executed": False}


def read_registered_lineage(root, epoch, name):
    """Verify retained registration identities, not today's candidate or review.

    This read-only audit deliberately does not rebind old declarations to current
    source files, current KNOWLEDGE, or subsequently revised lesson reviews.
    """
    block = epoch.get("knowledge_lineage")
    if block is None or name not in block.get("candidate_bindings", {}):
        return {"status": "NOT_RECORDED", "historical_backfill": False}
    _require(block.get("schema_version") == REGISTRATION_VERSION
             and block.get("status") == "RECORDED_AT_REGISTRATION"
             and block.get("registered_at") == epoch.get("created_at"),
             "Registered lineage time/contract mismatch")
    binding = block["candidate_bindings"][name]
    candidate = next((row for row in epoch["candidates"] if row["name"] == name), None)
    _require(candidate is not None and all(binding.get(key) == candidate.get(key)
             for key in ("definition_hash", "strategy_sha256")), "Frozen candidate/lineage identity mismatch")
    metadata = binding["declaration"]
    _require(canonical_hash(metadata) == binding["declaration_hash"], "Registered declaration hash mismatch")
    captured = load_capture(root, binding["capture_id"])
    _require(binding["knowledge_snapshot_hash"] == captured["knowledge_snapshot_hash"],
             "Registered snapshot hash mismatch")
    _captured_declaration(metadata, captured, epoch["created_at"])
    return {"status": "RECORDED_AT_REGISTRATION", "historical_backfill": False,
            "definition_hash": binding["definition_hash"], "strategy_sha256": binding["strategy_sha256"],
            "declaration_hash": binding["declaration_hash"], "capture_id": binding["capture_id"],
            "knowledge_snapshot_hash": binding["knowledge_snapshot_hash"],
            "lesson_references": metadata["lesson_references"], "follow_up_executed": False,
            "independent_evidence": False, "snapshot_content_safety_audited": False}
