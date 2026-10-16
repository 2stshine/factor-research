"""Adopt an immutable input-only shadow for a NEW assumed-PIT diagnostic.

This wrapper grants no factor-input, trading, promotion or registry authority.
The original shadow remains PIT_UNKNOWN / NOT_APPROVED. Its historically
modeled observation clock is distinct from this contract's actual adoption
timestamp. No factor values, returns, database or production state are read.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import median

import pandas as pd

from engine.regime_shadow import RULES


SCHEMA_VERSION = "research-regime-diagnostic-adoption-v1"
MARKETS = ("KOSPI", "KOSDAQ")
ROW_KEYS = frozenset({
    "month", "effective_month", "decision_at", "market_id", "source_id", "status",
    "approval_status", "pit_status", "regime", "trend", "relative_risk", "close", "sma_10m",
    "trend_distance", "rv63_annualized", "rv21_annualized", "risk_change_21_over_63",
    "risk_change_status", "prior_12m_rv63_median", "rv63_prior_12m_percentile",
    "prior_reference_months", "prior_reference_valid_months", "reference_values",
    "expected_sessions_this_month", "missing_or_late_sessions", "calendar_verified",
    "known_at_semantics", "reason", "input_sha256", "rules_version", "rules_sha256",
})
ADOPTED_ROW_KEYS = ROW_KEYS | {
    "original_pit_status", "original_approval_status", "assumption_policy_id",
    "assumption_policy_sha256", "diagnostic_contract_id",
}
ASSUMPTIONS = [
    "Historical index values may include later revisions; first vintages are not independently verified.",
    "Daily known_at is modeled at observation-day end in Asia/Seoul, not an observed historical receipt.",
    "The historical trading calendar is a local-source union; a bound final-month completion proof does not certify the full history.",
    "Month-t context is used for month-t+1 diagnostic outcomes only. The adoption timestamp is not historical data availability.",
    "HIGH/LOW means relative to twelve prior monthly risk snapshots, not absolute safety or a return forecast.",
    "Unknown, missing, late and warm-up observations remain unknown; the wrapper does not impute or reclassify them.",
]


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(",", ":")).encode()).hexdigest()


def _body(path: Path) -> tuple[dict, str]:
    body = path.read_bytes()
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    return payload, hashlib.sha256(body).hexdigest()


def _month(value: str) -> pd.Period:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ValueError("Expected YYYY-MM month")
    result = pd.Period(value, freq="M")
    if str(result) != value:
        raise ValueError("Expected canonical month")
    return result


def _aware(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Expected aware timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Expected aware timestamp")
    return result


def _sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _finite(value: object) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def _close(actual: object, expected: float) -> bool:
    return _finite(actual) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12)


def _policy(policy: dict) -> None:
    if policy.get("schema_version") != "regime-assumption-policy-v1":
        raise ValueError("Unsupported assumption policy")
    required = {
        "user_authorized": True, "diagnostics_only": True, "new_campaigns_only": True,
        "historical_backtest_allowed_under_assumptions": True,
        "historical_pit_verified": False, "factor_feature_allowed": False,
        "intraday_allowed": False, "promotion_gates_unchanged": True,
        "raw_receipt_timestamps_must_be_preserved": True,
        "existing_approvals_must_not_be_relabelled": True,
        "automatic_gold_publication_allowed": False,
    }
    if any(policy.get(key) is not expected for key, expected in required.items()):
        raise ValueError("Policy does not authorize this diagnostic-only assumed-PIT scope")
    if not isinstance(policy.get("policy_id"), str) or not policy["policy_id"].strip():
        raise ValueError("Assumption policy identity missing")


def _row(row: dict, *, market: str, assumed: bool) -> None:
    if not isinstance(row, dict) or set(row) != (ADOPTED_ROW_KEYS if assumed else ROW_KEYS):
        raise ValueError("Unexpected or missing market input fields; outcomes are forbidden")
    month = _month(row.get("month"))
    if row.get("market_id") != market or row.get("effective_month") != str(month + 1):
        raise ValueError("Market isolation or next-month mapping violated")
    decision = pd.Timestamp(row.get("decision_at"))
    if decision.tzinfo is None or decision != month.end_time.tz_localize("Asia/Seoul"):
        raise ValueError("Decision must be KST calendar month end")
    expected_pit = "PIT_ASSUMED" if assumed else "PIT_UNKNOWN"
    expected_approval = "DIAGNOSTIC_ASSUMPTION_ACCEPTED" if assumed else "NOT_APPROVED"
    if row.get("pit_status") != expected_pit or row.get("approval_status") != expected_approval:
        raise ValueError("Original or adopted provenance status changed")
    if assumed and (row.get("original_pit_status") != "PIT_UNKNOWN"
                    or row.get("original_approval_status") != "NOT_APPROVED"):
        raise ValueError("Original provenance not preserved")
    if row.get("calendar_verified") is not False:
        raise ValueError("Cannot convert assumed calendar to certified calendar")
    if row.get("known_at_semantics") != "ASSUMED_OBSERVATION_DAY_END_KST_NOT_RECEIPT":
        raise ValueError("Historical availability convention not declared")
    if row.get("rules_sha256") != _digest(RULES) or row.get("rules_version") != RULES["version"]:
        raise ValueError("Only predeclared shadow rules are eligible")
    if not _sha(row.get("input_sha256")):
        raise ValueError("Missing row input fingerprint")
    if row.get("status") not in {"READY_SHADOW", "UNKNOWN"}:
        raise ValueError("Unsupported original row state")
    if row["status"] == "UNKNOWN":
        if row.get("regime") != "UNKNOWN" or not row.get("reason"):
            raise ValueError("Missing or warm-up states cannot be relabeled")
        return
    if row.get("reason") or row.get("missing_or_late_sessions"):
        raise ValueError("Ready row contains missing evidence")
    for key in ("close", "sma_10m", "rv63_annualized", "rv21_annualized"):
        if not _finite(row.get(key)) or row[key] < 0 or (key in {"close", "sma_10m"} and row[key] == 0):
            raise ValueError("Ready row lacks finite continuous context")
    reference = row.get("reference_values")
    if (not isinstance(reference, list) or len(reference) != 12
            or any(not _finite(value) or value < 0 for value in reference)
            or row.get("prior_reference_valid_months") != 12
            or row.get("prior_reference_months") != [str(month - i) for i in range(12, 0, -1)]):
        raise ValueError("Prior reference must exclude current month and be contiguous")
    threshold = median(reference)
    risk = row["rv63_annualized"]
    trend = "UP" if row["close"] >= row["sma_10m"] else "DOWN"
    relative = "HIGH" if risk > threshold else "LOW"
    percentile = 100 * (sum(value < risk for value in reference)
                        + .5 * sum(value == risk for value in reference)) / 12
    if (row.get("trend") != trend or row.get("relative_risk") != relative
            or row.get("regime") != f"{trend}_{relative}"
            or not _close(row.get("prior_12m_rv63_median"), threshold)
            or not _close(row.get("rv63_prior_12m_percentile"), percentile)
            or not _close(row.get("trend_distance"), row["close"] / row["sma_10m"] - 1)):
        raise ValueError("Continuous values and regime labels disagree")
    if risk:
        if not _close(row.get("risk_change_21_over_63"), row["rv21_annualized"] / risk - 1):
            raise ValueError("Risk-change diagnostic disagrees")
    elif row.get("risk_change_21_over_63") is not None:
        raise ValueError("Zero risk cannot have a risk-change ratio")


def _completion(provenance: dict, *, root: Path, market: str) -> dict | None:
    """Bind and recheck existing completion files, never infer missing sessions."""
    proof = provenance.get("explicit_month_completion")
    if proof is None:
        return None
    paths = {}
    contents = {}
    for field in ("contract", "calendar_evidence"):
        path = Path(proof.get(f"{field}_file", "")).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Completion evidence must stay with source shadow")
        content, fingerprint = _body(path)
        if fingerprint != proof.get(f"{field}_sha256"):
            raise ValueError("Completion evidence hash mismatch")
        paths[field], contents[field] = str(path), content
    contract, evidence = contents["contract"], contents["calendar_evidence"]
    if (contract.get("schema_version") != "regime-shadow-month-completion-v1"
            or sorted(contract.get("market_ids", [])) != sorted(MARKETS)
            or contract.get("calendar_evidence_sha256") != proof["calendar_evidence_sha256"]
            or evidence.get("schema_version") != "versioned-expected-market-sessions-v1"
            or evidence.get("source_kind") != "VERSIONED_CALENDAR_LIBRARY"
            or evidence.get("calendar_name") != "XKRX"
            or not evidence.get("package_version")
            or not _sha(evidence.get("calendar_implementation_sha256"))):
        raise ValueError("Invalid independent calendar evidence")
    month = _month(contract.get("month"))
    expected = evidence.get("expected_sessions")
    if (evidence.get("month") != str(month) or not isinstance(expected, list) or not expected
            or expected != sorted(set(expected)) or expected != proof.get("expected_sessions")
            or contract.get("complete_through") != str(month.end_time.date())
            or proof.get("complete_through") != contract.get("complete_through")):
        raise ValueError("Completion period or session list mismatch")
    for day in expected:
        date = pd.Timestamp(day)
        if date.tzinfo is not None or str(date.date()) != day or date.to_period("M") != month:
            raise ValueError("Noncanonical completion date")
    local = provenance.get("local_calendar", {}).get("dates", [])
    raw = provenance.get("raw_files", [])
    if ([day for day in local if day[:7] == str(month)] != expected
            or sorted(file["trade_date"] for file in raw if file["trade_date"][:7] == str(month)) != expected):
        raise ValueError(f"{market} dates differ from independent completion evidence")
    return {"month": str(month), "complete_through": contract["complete_through"],
            "contract_sha256": proof["contract_sha256"],
            "calendar_evidence_sha256": proof["calendar_evidence_sha256"],
            "source_kind": evidence["source_kind"], "package_version": evidence["package_version"],
            "calendar_implementation_sha256": evidence["calendar_implementation_sha256"],
            "expected_sessions": expected, "calendar_verified": False,
            "historical_calendar_recertified": False, "files": paths}


def adopt_shadow_bundle(shadow_path: Path, policy_path: Path, *, contract_id: str,
                        authorization_ref: str, adopted_at: str,
                        start_month: str, end_month: str) -> dict:
    """Build (but do not save) a scoped, hash-bound NEW diagnostic contract.

    The caller must freeze the returned object before viewing factor outcomes.
    ``authorization_ref`` identifies the human's implementation authorization;
    this function cannot authenticate a human from free-form text. The existing
    explicit policy is also required. No production registry is modified.
    """
    start, end = _month(start_month), _month(end_month)
    accepted = _aware(adopted_at)
    if start > end:
        raise ValueError("Invalid diagnostic month scope")
    if not all(isinstance(v, str) and v.strip() for v in (contract_id, authorization_ref)):
        raise ValueError("Contract and authorization identities are required")
    source, source_sha = _body(Path(shadow_path))
    policy, policy_sha = _body(Path(policy_path))
    _policy(policy)
    if (source.get("schema_version") != "local-krx-regime-shadow-bundle-v1"
            or source.get("status") != "EXPERIMENTAL_SHADOW_NOT_APPROVED"
            or source.get("pit_status") != "PIT_UNKNOWN"
            or set(source.get("markets", {})) != set(MARKETS)):
        raise ValueError("Expected untouched two-market shadow bundle")
    if any(source.get(flag) is not False for flag in
           ("factor_returns_accessed", "active_registry_changed", "db_accessed", "network_accessed")):
        raise ValueError("Only isolated input-only shadows can be adopted")
    if accepted < _aware(source.get("created_at")):
        raise ValueError("Adoption predates the source artifact")
    source_day = pd.Timestamp(source.get("as_of"))
    if source_day.tzinfo is not None or source_day != source_day.normalize():
        raise ValueError("Invalid source as-of date")
    if (end.end_time.normalize() > source_day
            or source_day.date() > pd.Timestamp(accepted).tz_convert("Asia/Seoul").date()):
        raise ValueError("Diagnostic scope extends beyond completed source history")
    result = {
        "schema_version": SCHEMA_VERSION, "contract_id": contract_id,
        "authorization_ref": authorization_ref, "adopted_at": adopted_at,
        "adoption_time_is_historical_availability": False,
        "status": "NEW_DIAGNOSTIC_CONTRACT", "pit_status": "PIT_ASSUMED",
        "approval_status": "DIAGNOSTIC_ASSUMPTION_ACCEPTED",
        "source_original_pit_status": "PIT_UNKNOWN", "source_original_approval_status": "NOT_APPROVED",
        "purpose": "DIAGNOSTIC_ONLY", "new_research_only": True,
        "factor_feature_allowed": False, "trading_allowed": False,
        "promotion_gates_unchanged": True, "automatic_gold_publication_allowed": False,
        "factor_returns_accessed": False, "active_registry_changed": False,
        "raw_modified": False, "raw_bytes_reverified": False,
        "historical_pit_verified": False, "calendar_verified": False,
        "scope": {"start_month": start_month, "end_month": end_month,
                  "market_ids": list(MARKETS), "clock": "KST_CALENDAR_MONTH_END",
                  "outcome_mapping": "SIGNAL_MONTH_T_TO_OUTCOME_MONTH_T_PLUS_1"},
        "assumptions": list(ASSUMPTIONS), "rules": deepcopy(RULES), "rules_sha256": _digest(RULES),
        "source": {"file": str(Path(shadow_path).resolve()), "sha256": source_sha,
                   "as_of": source["as_of"], "created_at": source["created_at"],
                   "compiler_sha256": source.get("compiler_sha256"),
                   "engine_sha256": source.get("engine_sha256")},
        "policy": {"file": str(Path(policy_path).resolve()), "sha256": policy_sha,
                   "policy_id": policy["policy_id"], "snapshot": deepcopy(policy)},
        "markets": {},
    }
    for market in MARKETS:
        data = source["markets"][market]
        if (data.get("market_id") != market or data.get("rules") != RULES
                or data.get("rules_sha256") != _digest(RULES)
                or data.get("pit_status") != "PIT_UNKNOWN"
                or data.get("approval_status") != "NOT_APPROVED"
                or data.get("calendar_verified") is not False):
            raise ValueError("Source market policy or provenance mismatch")
        original_rows = data.get("rows", [])
        months = [row["month"] for row in original_rows]
        if not months or months != sorted(set(months)):
            raise ValueError("Source rows must be sorted and unique")
        provenance = data.get("source_provenance", {})
        local = provenance.get("local_calendar", {}).get("dates", [])
        raw_files = provenance.get("raw_files", [])
        if (not local or local != sorted(set(local)) or not raw_files
                or any(not _sha(file.get("sha256")) for file in raw_files)):
            raise ValueError("Missing source-file or calendar provenance")
        selected = []
        for original in original_rows:
            if start_month <= original["month"] <= end_month:
                _row(original, market=market, assumed=False)
                row = deepcopy(original)
                row.update(original_pit_status="PIT_UNKNOWN", original_approval_status="NOT_APPROVED",
                           pit_status="PIT_ASSUMED", approval_status="DIAGNOSTIC_ASSUMPTION_ACCEPTED",
                           assumption_policy_id=policy["policy_id"], assumption_policy_sha256=policy_sha,
                           diagnostic_contract_id=contract_id)
                selected.append(row)
        if [row["month"] for row in selected] != [str(m) for m in pd.period_range(start, end, freq="M")]:
            raise ValueError("Requested scope contains absent source months")
        result["markets"][market] = {
            "source_id": data["source_id"], "source_provenance_sha256": _digest(provenance),
            "raw_file_manifest_sha256": _digest(raw_files), "raw_file_count": len(raw_files),
            "calendar_dates_sha256": _digest(local), "calendar_session_count": len(local),
            "calendar_semantics": provenance.get("local_calendar", {}).get("semantics"),
            "last_complete_input_month": provenance.get("last_complete_input_month"),
            "historical_receipts_available": False,
            "completion_evidence": _completion(provenance, root=Path(shadow_path).parent, market=market),
            "rows": selected,
        }
    result["contract_sha256"] = _digest(result)
    validate_adoption(result)
    return result


def validate_adoption(payload: dict) -> None:
    """Validate a frozen self-contained contract, without reopening its sources."""
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported adoption contract")
    check = deepcopy(payload)
    fingerprint = check.pop("contract_sha256", None)
    if fingerprint != _digest(check):
        raise ValueError("Adoption contract hash mismatch")
    exact = {
        "status": "NEW_DIAGNOSTIC_CONTRACT", "pit_status": "PIT_ASSUMED",
        "approval_status": "DIAGNOSTIC_ASSUMPTION_ACCEPTED", "purpose": "DIAGNOSTIC_ONLY",
        "source_original_pit_status": "PIT_UNKNOWN", "source_original_approval_status": "NOT_APPROVED",
        "new_research_only": True, "factor_feature_allowed": False, "trading_allowed": False,
        "promotion_gates_unchanged": True, "automatic_gold_publication_allowed": False,
        "factor_returns_accessed": False, "active_registry_changed": False,
        "historical_pit_verified": False, "calendar_verified": False, "raw_modified": False,
        "adoption_time_is_historical_availability": False, "raw_bytes_reverified": False,
    }
    if any(payload.get(key) != value or type(payload.get(key)) is not type(value)
           for key, value in exact.items()):
        raise ValueError("Diagnostic-only assumed-PIT boundary violated")
    accepted = _aware(payload.get("adopted_at"))
    if payload.get("rules") != RULES or payload.get("rules_sha256") != _digest(RULES):
        raise ValueError("Rules changed")
    if payload.get("assumptions") != ASSUMPTIONS:
        raise ValueError("Required interpretation assumptions missing")
    if not _sha(payload.get("source", {}).get("sha256")) or not _sha(payload.get("policy", {}).get("sha256")):
        raise ValueError("Missing bound source or policy")
    policy = payload["policy"]
    _policy(policy.get("snapshot", {}))
    if policy.get("policy_id") != policy["snapshot"]["policy_id"]:
        raise ValueError("Policy identity mismatch")
    scope = payload.get("scope", {})
    start, end = _month(scope.get("start_month")), _month(scope.get("end_month"))
    source_day = pd.Timestamp(payload["source"].get("as_of"))
    if (source_day.tzinfo is not None or source_day != source_day.normalize()
            or end.end_time.normalize() > source_day
            or accepted < _aware(payload["source"].get("created_at"))
            or source_day.date() > pd.Timestamp(accepted).tz_convert("Asia/Seoul").date()):
        raise ValueError("Adoption/source/scope timing mismatch")
    if (start > end or scope.get("market_ids") != list(MARKETS)
            or scope.get("clock") != "KST_CALENDAR_MONTH_END"
            or scope.get("outcome_mapping") != "SIGNAL_MONTH_T_TO_OUTCOME_MONTH_T_PLUS_1"
            or set(payload.get("markets", {})) != set(MARKETS)):
        raise ValueError("Scope mismatch")
    expected = [str(month) for month in pd.period_range(start, end, freq="M")]
    for market, data in payload["markets"].items():
        if any(not _sha(data.get(key)) for key in
               ("source_provenance_sha256", "raw_file_manifest_sha256", "calendar_dates_sha256")):
            raise ValueError("Missing calendar/source fingerprints")
        if [row["month"] for row in data["rows"]] != expected:
            raise ValueError("Adopted scope is not contiguous and exact")
        for row in data["rows"]:
            _row(row, market=market, assumed=True)
            if (row.get("assumption_policy_sha256") != policy["sha256"]
                    or row.get("assumption_policy_id") != policy["policy_id"]
                    or row.get("diagnostic_contract_id") != payload.get("contract_id")
                    or row.get("source_id") != data.get("source_id")):
                raise ValueError("Row contract binding mismatch")


def market_rows(payload: dict, market_id: str) -> list[dict]:
    """Return a defensive copy of the exact signal-month diagnostic scope."""
    validate_adoption(payload)
    if market_id not in MARKETS:
        raise ValueError("Only separately declared KOSPI/KOSDAQ contexts are available")
    return deepcopy(payload["markets"][market_id]["rows"])
