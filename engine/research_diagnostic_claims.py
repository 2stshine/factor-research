"""Standalone future economic-evidence contract; not connected to frozen v3.

This pure helper classifies supplied reports and checks economic finding citations.
It does not execute diagnostics, authenticate evidence, assess causality, compute
scores, rescore history, or modify a runtime. Frozen v3's AVAILABLE status is not
silently translated into COMPUTED; integration needs a separate explicit contract.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from numbers import Real


CONTRACT_VERSION = "economic-diagnostic-claims-v1"
ASSOCIATION_METRICS = ("signal_to_economic_change_ic", "economic_change_to_return_ic")
_STATUSES = frozenset({"COMPUTED", "NOT_COMPUTED", "EXECUTION_FAILED"})
_FINDINGS = frozenset({"ECONOMIC_OUTCOME_UNAVAILABLE", "MECHANISM_UNIDENTIFIED"})


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _strings(values, name):
    if (not isinstance(values, Sequence) or isinstance(values, (str, bytes))
            or any(not _text(value) for value in values)):
        raise ValueError(f"{name} must be a sequence of nonempty strings")
    if len(set(values)) != len(values):
        raise ValueError(f"Duplicate {name}")
    return list(values)


def _has_association_estimate(metrics):
    """Require an allowlisted outcome association's finite numeric mean.

    Counts, lags, arbitrary numeric leaves and unknown summaries are metadata,
    not association estimates. Any supplied allowlisted estimate with an invalid
    mean keeps the report unresolved. A valid zero/negative mean is still an
    assessed association; significance and measurement validity are not certified.
    """
    if not isinstance(metrics, Mapping):
        return False
    estimates = [metrics[name] for name in ASSOCIATION_METRICS if name in metrics]
    if not estimates:
        return False
    for estimate in estimates:
        value = estimate.get("mean") if isinstance(estimate, Mapping) else None
        if not isinstance(value, (Real, Decimal)) or isinstance(value, bool):
            return False
        try:
            if not Decimal(str(value)).is_finite():
                return False
        except InvalidOperation:
            return False
    return True


def classify_economic_claims(evidence, *, findings=(), evidence_ids=()) -> dict:
    """Classify one unambiguous economic_link report and its cited findings.

    Each evidence entry needs unique evidence_id, diagnostic_id and a response
    mapping with a recognized status. A response diagnostic_id, when present,
    must match its envelope. Missing datasets must be distinct nonempty strings.
    Unknown statuses, IDs, finding codes and multiple economic reports raise
    ValueError. This helper accepts only the two economic finding codes above;
    other diagnostic findings belong to their own future contracts.

    EXECUTION_FAILED must be represented explicitly as a report by a future
    adapter; absence of an economic report means UNTESTED, never inferred failure.
    COMPUTED requires metrics.signal_to_economic_change_ic.mean or
    metrics.economic_change_to_return_ic.mean as a finite numeric estimate;
    every supplied allowlisted estimate must have a valid mean. Metadata-only,
    empty or nonfinite estimates remain UNRESOLVED.
    A valid missing-data report does not license a finding unless its evidence ID
    is cited. MECHANISM_UNIDENTIFIED is only a neutral limitation, never a scored
    fact. No generating scenario/oracle is accepted as input.
    """
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        raise ValueError("evidence must be a sequence of observed reports")
    requested = _strings(findings, "findings")
    cited = _strings(evidence_ids, "evidence_ids")
    if set(requested) - _FINDINGS:
        raise ValueError("Unknown economic finding code")
    observed_ids, economic = set(), []
    for entry in evidence:
        if not isinstance(entry, Mapping):
            raise ValueError("Evidence entries must be mappings")
        identifier, diagnostic = entry.get("evidence_id"), entry.get("diagnostic_id")
        if not _text(identifier) or not _text(diagnostic):
            raise ValueError("Evidence and diagnostic IDs must be nonempty strings")
        if identifier in observed_ids:
            raise ValueError("Duplicate evidence ID")
        observed_ids.add(identifier)
        response = entry.get("response")
        if not isinstance(response, Mapping):
            raise ValueError("Evidence response must be a mapping")
        status = response.get("status")
        if not isinstance(status, str) or status not in _STATUSES:
            raise ValueError("Unknown diagnostic status")
        if response.get("diagnostic_id", diagnostic) != diagnostic:
            raise ValueError("Response diagnostic ID does not match evidence envelope")
        missing = _strings(response.get("missing_datasets", ()), "missing_datasets")
        if diagnostic == "economic_link":
            economic.append((identifier, response, missing))
    if set(cited) - observed_ids:
        raise ValueError("Citations must reference observed evidence IDs")
    if len(economic) > 1:
        raise ValueError("Multiple economic_link reports are ambiguous")

    state, identifier, missing = "UNTESTED", None, []
    if economic:
        identifier, response, reported_missing = economic[0]
        state = "UNRESOLVED"
        if response["status"] == "NOT_COMPUTED" and reported_missing:
            state, missing = "DATA_UNAVAILABLE", reported_missing
        elif response["status"] == "COMPUTED" and not reported_missing:
            if _has_association_estimate(response.get("metrics", {})):
                state = "ASSOCIATION_ASSESSED"

    accepted, rejected, neutral, rejection_reasons = [], [], [], {}
    for finding in sorted(requested):
        if finding == "MECHANISM_UNIDENTIFIED":
            neutral.append(finding)
        elif state == "DATA_UNAVAILABLE" and identifier in cited:
            accepted.append(finding)
        else:
            rejected.append(finding)
            rejection_reasons[finding] = ("MISSING_DATA_EVIDENCE_NOT_CITED"
                                         if state == "DATA_UNAVAILABLE" else "MISSING_DATA_NOT_OBSERVED")
    return {
        "contract_version": CONTRACT_VERSION, "scope": "STANDALONE_FUTURE_CONTRACT",
        "runtime_connected": False, "historical_scores_modified": False,
        "evidence_authenticated": False, "measurement_validity_reverified": False,
        "economic_status": state, "causal_identification": "NOT_IDENTIFIED",
        "economic_evidence_id": identifier, "missing_datasets": list(missing),
        "accepted_findings": accepted, "rejected_findings": rejected,
        "neutral_limitations": neutral, "rejection_reasons": rejection_reasons,
        "claims_valid": not rejected,
    }
