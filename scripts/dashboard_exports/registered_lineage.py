"""Optional, future-only reviewer projection. Never a candidate-input export.

Call only after the original release/result/packet authentication. Failure of
this optional audit withholds lineage, not the authenticated research record.
No captured text, source files, review text, or raw outcomes are returned.
"""
from collections import Counter
import re

from engine.knowledge_lineage import AUTHENTICATION, RELATIONS, canonical_hash, _sha
from engine.knowledge_registration import read_registered_lineage

VERSION = "registered-lineage-public-v1"


def public_spec(spec):
    """Copy, never mutate the frozen payload used for packet authentication."""
    if isinstance(spec, dict) and "knowledge_lineage" in spec:
        return {k: v for k, v in spec.items() if k != "knowledge_lineage"}
    return spec


def retained_lineage(root, epoch, name, payload):
    """Read the retained capture only when this candidate opted in."""
    spec = payload.get("research_spec", {})
    raw_present = isinstance(spec, dict) and "knowledge_lineage" in spec
    block = epoch.get("knowledge_lineage")
    bindings = block.get("candidate_bindings") if isinstance(block, dict) else None
    registered = isinstance(bindings, dict) and name in bindings
    malformed = block is not None and (not isinstance(block, dict) or not isinstance(bindings, dict))
    if not raw_present and not registered and not malformed:
        return None  # Legacy: no reads, new fields, or backfill.

    def withheld(reason):
        return {"schema_version": VERSION, "status": "WITHHELD", "reason": reason}

    if malformed or not raw_present or not registered:
        return withheld("REGISTRATION_DECLARATION_INCOMPLETE")
    try:
        audit = read_registered_lineage(root, epoch, name)
        declaration = spec["knowledge_lineage"]
        if (audit.get("status") != "RECORDED_AT_REGISTRATION"
                or canonical_hash(declaration) != audit["declaration_hash"]
                or payload["factor"]["definition_hash"] != audit["definition_hash"]
                or spec.get("strategy_sha256") != audit["strategy_sha256"]):
            return withheld("FROZEN_DECLARATION_IDENTITY_MISMATCH")
        # Only allowlisted identity fields; exceptions never expose local paths.
        identities = ("definition_hash", "strategy_sha256", "declaration_hash",
                      "capture_id", "knowledge_snapshot_hash")
        if (not re.fullmatch(r"[0-9a-f]{16}", audit["definition_hash"])
                or not all(_sha(audit[k]) for k in identities if k != "definition_hash")):
            return withheld("INVALID_REGISTERED_IDENTITIES")
        return {"schema_version": VERSION, "status": "RECORDED_AT_REGISTRATION",
                "registered_at": epoch["created_at"],
                "declared_at": declaration["declared_at"],
                "snapshot_captured_at": declaration["snapshot_captured_at"],
                **{k: audit[k] for k in identities},
                "lesson_references": audit["lesson_references"],
                "historical_backfill": False, "follow_up_executed": False,
                "independent_evidence": False, "snapshot_content_safety_audited": False}
    except (ValueError, OSError, KeyError, TypeError, AttributeError, StopIteration):
        return withheld("RETAINED_REGISTRATION_AUDIT_FAILED")


def resolve_public_lineage(records, pending, sanitize):
    """Second pass: match the exact sanitized review view used during capture.

    Existing capture/registration hashes are of exporter output after safe().
    A missing, stale, or changed endpoint is counted without exposing its ID.
    The graph must only read this projection, never raw research_spec metadata.
    """
    if not pending:
        return
    public = {r["record_id"]: r for r in sanitize(records)}
    for record in records:
        lineage = pending.get(record["record_id"])
        if lineage is None:
            continue
        if lineage["status"] != "RECORDED_AT_REGISTRATION":
            record["registered_lineage"] = lineage
            continue
        retained = dict(lineage)
        refs, withheld = [], Counter()
        seen = set()
        for ref in lineage["lesson_references"]:
            rid = ref.get("record_id")
            source = public.get(rid)
            if rid == record["record_id"] or rid in seen:
                withheld["INVALID_REFERENCE_IDENTITY"] += 1
            elif source is None:
                withheld["SOURCE_NOT_PUBLIC"] += 1
            elif (source.get("visibility") != "RELEASED_QUALITATIVE"
                    or source.get("review_status") != "REVIEWED_CURRENT"
                    or not isinstance(source.get("review"), dict)
                    or source["review"].get("status") != "REVIEWED"
                    or source.get("provenance", {}).get("authentication") != AUTHENTICATION):
                withheld["SOURCE_NOT_CURRENT_REVIEWED"] += 1
            elif canonical_hash(source["review"]) != ref.get("review_hash"):
                withheld["SOURCE_REVIEW_VERSION_CHANGED"] += 1
            elif (source["provenance"].get("packet_sha256") != ref.get("packet_sha256")
                    or source["review"].get("packet_sha256") != ref.get("packet_sha256")):
                withheld["SOURCE_PACKET_VERSION_CHANGED"] += 1
            elif ref.get("relation") not in RELATIONS:
                withheld["UNSUPPORTED_RELATION"] += 1
            else:
                refs.append({k: ref[k] for k in ("record_id", "review_hash", "packet_sha256", "relation")})
            seen.add(rid)
        retained.update({"reference_authentication": "CURRENT_PUBLIC_REVIEW_VERSION_AND_PACKET",
                         "lesson_references": refs, "withheld_reference_count": sum(withheld.values()),
                         "withheld_reference_reasons": dict(sorted(withheld.items()))})
        record["registered_lineage"] = retained
