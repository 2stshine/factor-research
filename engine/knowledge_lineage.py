"""Future-only declarations of qualitative knowledge use; no causal inference.

This optional validator does not register candidates, refresh memory, create
lessons, read files, or publish a candidate-facing view of reviewer evidence.
The caller supplies current authenticated records from the existing exporter.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

VERSION = "knowledge-lineage-v1"
AUTHENTICATION = "CURRENT_RELEASE_STATE_AND_EXACT_PACKET_REBUILD"
FIELDS = {"schema_version", "knowledge_snapshot_hash", "snapshot_captured_at",
          "declared_at", "referenced_lesson_record_ids", "lesson_references"}
REFERENCE_FIELDS = {"record_id", "review_hash", "packet_sha256", "relation"}
RELATIONS = {"DECLARED_QUALITATIVE_LESSON_USE", "DECLARED_COMPARISON_REFERENCE"}


def canonical_hash(value):
    """Same JSON convention as engine.lesson_evidence.digest."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _stamp(value):
    _require(isinstance(value, str), "An explicit timezone-aware timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid timestamp") from None
    _require(parsed.tzinfo is not None, "An explicit timezone-aware timestamp is required")
    return parsed.astimezone(timezone.utc)


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_lineage(metadata, knowledge_bytes, authenticated_records, *, cutoff):
    """Validate a declaration against exact bytes and currently authenticated reviews.

    ``cutoff`` is the externally supplied proposed/preregistered cutoff, not a
    clock inferred from file mtimes. Declared timestamps are not independent
    proof of historical availability. Preserve the declaration and snapshot
    inside a new immutable registration before claiming preregistered lineage.
    Omitted legacy metadata remains NOT_RECORDED; no retrofit is performed.
    """
    if metadata is None:
        return {"schema_version": VERSION, "status": "NOT_RECORDED",
                "referenced_lesson_record_ids": [], "historical_backfill": False,
                "independent_evidence": False, "follow_up_executed": False}
    _require(isinstance(metadata, dict) and set(metadata) == FIELDS,
             "Only the versioned identity/timestamp fields are permitted")
    _require(metadata["schema_version"] == VERSION, "Unsupported lineage schema")
    _require(isinstance(knowledge_bytes, bytes) and bool(knowledge_bytes),
             "Exact nonempty snapshot bytes are required")
    _require(_sha(metadata["knowledge_snapshot_hash"]) and
             hashlib.sha256(knowledge_bytes).hexdigest() == metadata["knowledge_snapshot_hash"],
             "Knowledge snapshot hash mismatch")
    _require(_stamp(metadata["snapshot_captured_at"]) <= _stamp(metadata["declared_at"]) <= _stamp(cutoff),
             "Snapshot/declaration must precede the registration cutoff")
    ids = metadata["referenced_lesson_record_ids"]
    refs = metadata["lesson_references"]
    _require(isinstance(ids, list) and all(isinstance(x, str) for x in ids)
             and len(ids) == len(set(ids)), "Unique referenced lesson record IDs are required")
    _require(isinstance(refs, list) and all(isinstance(r, dict) and set(r) == REFERENCE_FIELDS for r in refs),
             "Only identity hashes and a declared relationship are permitted in references")
    _require([r["record_id"] for r in refs] == ids, "Reference list and IDs must match exactly")
    index = {}
    for record in authenticated_records:
        rid = record.get("record_id")
        _require(isinstance(rid, str) and rid not in index, "Duplicate or invalid authenticated record ID")
        index[rid] = record
    for ref in refs:
        record = index.get(ref["record_id"])
        _require(record is not None, "Referenced lesson is absent from current authenticated release")
        _require(record.get("visibility") == "RELEASED_QUALITATIVE"
                 and record.get("review_status") == "REVIEWED_CURRENT"
                 and record.get("provenance", {}).get("authentication") == AUTHENTICATION,
                 "Pending, stale, or unauthenticated lessons cannot be referenced")
        _require(isinstance(record.get("review"), dict) and _sha(ref["review_hash"])
                 and canonical_hash(record["review"]) == ref["review_hash"], "Review hash mismatch")
        _require(_sha(ref["packet_sha256"]) and record["provenance"].get("packet_sha256") == ref["packet_sha256"],
                 "Evidence packet hash mismatch")
        _require(ref["relation"] in RELATIONS, "No inferred causality, support, or executed follow-up relationship")
    return {"schema_version": VERSION, "status": "VALID_DECLARATION_NOT_REGISTRATION",
            "knowledge_snapshot_hash": metadata["knowledge_snapshot_hash"],
            "declaration_hash": canonical_hash(metadata),
            "referenced_lesson_record_ids": list(ids), "historical_backfill": False,
            "independent_evidence": False, "follow_up_executed": False,
            "snapshot_content_safety_audited": False,
            "boundary": "Identity validation only; preserve candidate source and snapshot before new registration. No original review text or OOS values are returned."}
