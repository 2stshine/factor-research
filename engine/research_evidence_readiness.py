"""Check claim-level evidence metadata without executing or certifying research.

READY means that supplied attestations satisfy the declared metadata contract.
It is not a fresh source/coverage/PIT audit, an economic verdict, or permission
to read a dataset. No data values, returns, ICs, files, DBs or research ledgers
are read. An access broker and authenticated evaluator must verify the supplied
scope, availability, coverage and runtime bindings before actual execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


SCHEMA_VERSION = "research-evidence-readiness-v1"
ROLES = frozenset({"feature", "diagnostic", "outcome", "regime", "execution"})
# Regime here means diagnostic context, never a tradable conditioning feature.
ASSUMPTION_ROLES = frozenset({"diagnostic", "regime"})
PRESENCE_STATUSES = frozenset({"PRESENT", "MISSING", "UNKNOWN", "ERROR"})


@dataclass(frozen=True)
class EvidenceRequirement:
    evidence_id: str
    role: str
    coverage_contract_ref: str
    allow_assumed_policy_ref: str | None = None


@dataclass(frozen=True)
class ResearchClaim:
    claim_id: str
    requirements: tuple[EvidenceRequirement, ...]


@dataclass(frozen=True)
class EvidenceCapability:
    evidence_id: str
    role: str
    presence: str = "UNKNOWN"
    linked: bool = False
    scope_checked: bool = False
    required_coverage_checked: bool = False
    required_coverage_passed: bool = False
    availability_checked: bool = False
    verification: str = "UNVERIFIED"
    source_ref: str | None = None
    known_at: str | None = None
    scope_ref: str | None = None
    runtime_binding: str | None = None
    coverage_contract_ref: str | None = None
    coverage_evidence_ref: str | None = None
    assumption_policy_ref: str | None = None


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _aware_datetime(value: object) -> datetime | None:
    if not _text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _require_role(role: str) -> None:
    if role not in ROLES:
        raise ValueError(f"Unknown evidence role: {role!r}")


def _check_requirement(requirement, capability, *, scope_ref, runtime_binding, as_of):
    result = {"evidence_id": requirement.evidence_id, "role": requirement.role,
              "status": "MISSING", "reasons": []}
    if capability is None or capability.presence == "MISSING":
        result["reasons"] = ["EVIDENCE_MISSING"]
        return result
    if capability.presence in {"UNKNOWN", "ERROR"}:
        result.update(status="UNVERIFIED", reasons=[f"EVIDENCE_{capability.presence}"])
        return result

    violations = []

    def add(status, reason):
        violations.append((status, reason))

    if capability.role != requirement.role:
        add("OUT_OF_SCOPE", "ROLE_MISMATCH")
    if capability.linked is not True:
        add("PRESENT_NOT_CONNECTED", "NOT_LINKED")
    if capability.scope_checked is not True:
        add("UNVERIFIED", "SCOPE_NOT_CHECKED")
    if not _text(capability.scope_ref):
        add("UNVERIFIED", "SCOPE_BINDING_MISSING")
    elif capability.scope_ref != scope_ref:
        add("OUT_OF_SCOPE", "SCOPE_BINDING_MISMATCH")
    if not _text(capability.runtime_binding):
        add("UNVERIFIED", "RUNTIME_BINDING_MISSING")
    elif capability.runtime_binding != runtime_binding:
        add("OUT_OF_SCOPE", "RUNTIME_BINDING_MISMATCH")
    if capability.required_coverage_checked is not True:
        add("UNVERIFIED", "REQUIRED_COVERAGE_NOT_CHECKED")
    if capability.required_coverage_passed is not True:
        add("UNVERIFIED", "COVERAGE_REQUIREMENT_NOT_MET")
    if not _text(capability.coverage_evidence_ref):
        add("UNVERIFIED", "COVERAGE_EVIDENCE_MISSING")
    if not _text(capability.coverage_contract_ref):
        add("UNVERIFIED", "COVERAGE_CONTRACT_MISSING")
    elif capability.coverage_contract_ref != requirement.coverage_contract_ref:
        add("OUT_OF_SCOPE", "COVERAGE_CONTRACT_MISMATCH")
    if not _text(capability.source_ref):
        add("UNVERIFIED", "SOURCE_REFERENCE_MISSING")
    if capability.availability_checked is not True:
        add("UNVERIFIED", "AVAILABILITY_NOT_CHECKED")
    known_at = _aware_datetime(capability.known_at)
    if known_at is None:
        add("UNVERIFIED", "KNOWN_AT_MISSING_OR_INVALID")
    elif known_at > as_of:
        add("OUT_OF_SCOPE", "EVIDENCE_NOT_YET_KNOWN")

    if capability.verification == "PIT_ASSUMED":
        if requirement.role not in ASSUMPTION_ROLES:
            add("UNVERIFIED", "ASSUMPTION_FORBIDDEN_FOR_ROLE")
        if not _text(requirement.allow_assumed_policy_ref):
            add("UNVERIFIED", "ASSUMPTION_NOT_ALLOWED_BY_REQUIREMENT")
        if not _text(capability.assumption_policy_ref):
            add("UNVERIFIED", "ASSUMPTION_PROVENANCE_MISSING")
        elif capability.assumption_policy_ref != requirement.allow_assumed_policy_ref:
            add("OUT_OF_SCOPE", "ASSUMPTION_POLICY_MISMATCH")
    elif capability.verification != "VERIFIED":
        add("UNVERIFIED", "VERIFICATION_NOT_ACCEPTED")

    # Preserve every reason, even when one higher-priority state summarizes it.
    priority = {"OUT_OF_SCOPE": 0, "PRESENT_NOT_CONNECTED": 1, "UNVERIFIED": 2}
    result.update(
        status=min((state for state, _ in violations), key=priority.get) if violations else "READY",
        reasons=[reason for _, reason in violations],
        verification=capability.verification,
        source_ref=capability.source_ref,
        coverage_evidence_ref=capability.coverage_evidence_ref,
        assumption_policy_ref=capability.assumption_policy_ref,
    )
    return result


def assess_readiness(
    claims: Sequence[ResearchClaim],
    capabilities: Sequence[EvidenceCapability],
    *,
    scope_ref: str,
    runtime_binding: str,
    as_of: str,
) -> dict:
    """Assess each declared claim; missing evidence is NOT_TESTABLE, not REJECT.

    ``known_at`` is the supplied evidence artifact's availability timestamp.
    ``availability_checked`` attests that the referenced contract also checked
    underlying row-level availability/maturity for its role. The timestamp alone
    cannot establish historical first-release vintage or future-outcome maturity.
    References are opaque bindings, not URLs fetched or attestations verified here.
    An empty claim set is NOT_READY. Empty requirements or duplicate IDs are errors.
    """
    if not _text(scope_ref) or not _text(runtime_binding):
        raise ValueError("Nonempty scope_ref and runtime_binding are required")
    cutoff = _aware_datetime(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a timezone-aware ISO timestamp")
    evidence = {}
    for capability in capabilities:
        if not isinstance(capability, EvidenceCapability):
            raise ValueError("Capabilities must use EvidenceCapability; arbitrary metrics are not inputs")
        if not _text(capability.evidence_id) or capability.evidence_id in evidence:
            raise ValueError("Capability IDs must be nonempty and unique")
        _require_role(capability.role)
        if capability.presence not in PRESENCE_STATUSES:
            raise ValueError(f"Unknown presence status: {capability.presence!r}")
        evidence[capability.evidence_id] = capability

    rows = []
    claim_ids = set()
    for claim in claims:
        if not isinstance(claim, ResearchClaim):
            raise ValueError("Claims must use ResearchClaim")
        if not _text(claim.claim_id) or claim.claim_id in claim_ids:
            raise ValueError("Claim IDs must be nonempty and unique")
        claim_ids.add(claim.claim_id)
        if not claim.requirements:
            raise ValueError("A claim must declare at least one evidence requirement")
        requirement_ids = set()
        required = []
        for requirement in claim.requirements:
            if not isinstance(requirement, EvidenceRequirement):
                raise ValueError("Requirements must use EvidenceRequirement")
            if not _text(requirement.evidence_id) or requirement.evidence_id in requirement_ids:
                raise ValueError("Requirement IDs must be nonempty and unique within a claim")
            requirement_ids.add(requirement.evidence_id)
            _require_role(requirement.role)
            if not _text(requirement.coverage_contract_ref):
                raise ValueError("Every requirement must declare its coverage contract")
            required.append(_check_requirement(
                requirement, evidence.get(requirement.evidence_id),
                scope_ref=scope_ref, runtime_binding=runtime_binding, as_of=cutoff,
            ))
        rows.append({"claim_id": claim.claim_id,
                     "status": "READY" if all(item["status"] == "READY" for item in required) else "NOT_TESTABLE",
                     "requirements": required})
    ready = sum(row["status"] == "READY" for row in rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "assessment": "SUPPLIED_METADATA_CONTRACT_ONLY",
        "status": "READY" if rows and ready == len(rows) else "PARTIAL" if ready else "NOT_READY",
        "scope_ref": scope_ref, "runtime_binding": runtime_binding, "as_of": as_of,
        "ready_claims": ready, "total_claims": len(rows), "claims": rows,
        "source_or_coverage_reverified": False,
        "research_executed": False,
        "economic_verdict": "NOT_ASSESSED",
    }
