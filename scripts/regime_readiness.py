"""Read-only completion gate for a fixed, independently reviewed regime scope.

Checks evidence bindings and approved-context usability, not the economic truth
of historical vintages. Does not run diagnostics, mutate approvals or campaigns,
query databases, or remove blocked requirements from the declared scope.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from engine.regime_inputs import load_campaign_context
from engine.regimes import classify_monthly_market

SCHEMA = "regime-review-scope-v1"
RESULT_SCHEMA = "regime-readiness-v1"


def _month(value):
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}", value) is None:
        raise ValueError("Months must have YYYY-MM format")
    return pd.Period(value, freq="M")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(path):
    manifest = json.loads(path.read_bytes())
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("Unsupported regime review scope schema")
    start = _month(manifest["period"]["start_month"])
    end = _month(manifest["period"]["end_month"])
    if start > end:
        raise ValueError("Reversed review period")
    requirements = manifest.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("A nonempty fixed requirement set is mandatory")
    seen = set()
    for req in requirements:
        if not isinstance(req, dict):
            raise ValueError("Each requirement must be an object")
        identity = req.get("id")
        if not isinstance(identity, str) or not identity.strip() or identity in seen:
            raise ValueError("Requirement identities must be nonempty and unique")
        seen.add(identity)
        if not isinstance(req.get("role"), str) or not req["role"].strip():
            raise ValueError("Each requirement needs a role")
        if req.get("context_id") is not None and (not isinstance(req["context_id"], str) or not req["context_id"].strip()):
            raise ValueError("Invalid context identity")
        if not isinstance(req.get("blockers"), list) or not all(isinstance(b, str) and b.strip() for b in req["blockers"]):
            raise ValueError("Blockers must be an explicit string list")
        if not isinstance(req.get("evidence"), list):
            raise ValueError("Evidence must be an explicit list")
        for item in req["evidence"]:
            if (not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"].strip()
                    or not isinstance(item.get("sha256"), str)
                    or re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is None):
                raise ValueError("Evidence requires a local path and SHA256")
    return manifest, pd.period_range(start, end, freq="M")


def _evidence(items, base):
    results = []
    for item in items:
        path = (base / item["path"]).resolve()
        check = {"path": str(path), "expected_sha256": item["sha256"]}
        if not path.is_file():
            check["status"] = "MISSING_EVIDENCE"
        else:
            check["actual_sha256"] = _sha(path)
            check["status"] = "VERIFIED_HASH" if check["actual_sha256"] == item["sha256"] else "EVIDENCE_HASH_MISMATCH"
        results.append(check)
    return results


def _registry(path):
    if not path.is_file():
        return "MISSING_REGISTRY", {}, None
    try:
        bundle = load_campaign_context(registry_path=path)
        contexts = {} if bundle is None else {c["source"]["context_id"]: c for c in bundle["contexts"]}
        if bundle and len(contexts) != len(bundle["contexts"]):
            raise ValueError("Duplicate context identities in registry")
        return "VERIFIED_REGISTRY", contexts, None
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return "INVALID_REGISTRY", {}, str(exc)


def _availability(item, months):
    source = item["source"]
    base = {"context_id": source["context_id"], "source_id": source["source_id"],
            "kind": source.get("kind"), "approval_sha256": item["approval_sha256"],
            "requested_months": len(months)}
    scope = source.get("scope")
    if scope is not None:
        if not isinstance(scope, dict) or not {"start_month", "end_month"}.issubset(scope):
            return {**base, "status": "INVALID_CONTEXT_SCOPE"}
        first, last = _month(scope["start_month"]), _month(scope["end_month"])
        if first > last:
            return {**base, "status": "INVALID_CONTEXT_SCOPE"}
        base["approved_scope"] = {"start_month": str(first), "end_month": str(last)}
        if months[0] < first or months[-1] > last:
            return {**base, "status": "OUT_OF_APPROVED_SCOPE", "usable_months": None,
                    "reason": "Requested period exceeds explicitly approved scope; no automatic scope shrink"}
    if source.get("kind") not in {"macro_state", "market_index"}:
        return {**base, "status": "INVALID_CONTEXT", "reason": "Unsupported context kind"}
    value_column = "state" if source["kind"] == "macro_state" else "close"
    rows = source.get("rows")
    if not isinstance(rows, list):
        return {**base, "status": "INVALID_CONTEXT", "reason": "Rows must be a list"}
    if not rows:
        return {**base, "status": "NO_USABLE_ROWS", "usable_months": 0,
                "missing_months": list(months.astype(str))}
    frame = pd.DataFrame(rows)
    if not {"month", "known_at", value_column}.issubset(frame.columns):
        return {**base, "status": "INVALID_CONTEXT", "reason": "Missing month, known_at or value field"}
    # Do not use values after the declared audit period. Earlier rows are warm-up.
    frame["month"] = [_month(m) for m in frame["month"]]
    frame = frame.loc[frame["month"] <= months[-1]].copy()
    if frame["month"].duplicated().any():
        return {**base, "status": "UNRESOLVED_REVISIONS", "reason": "Duplicate months require upstream PIT resolution"}
    frame["known_at"] = pd.to_datetime(frame["known_at"], errors="raise")
    if frame["known_at"].isna().any() or frame["known_at"].dt.tz is not None:
        return {**base, "status": "INVALID_CONTEXT", "reason": "Expected verified nonmissing KST-naive known_at"}
    if (frame["known_at"].dt.to_period("M") < frame["month"]).any():
        return {**base, "status": "INVALID_CONTEXT", "reason": "known_at precedes observation month"}
    if item["approval"].get("schema_version") == "pit-regime-approval-v2":
        # Match freeze_context's narrow policy-only day-bound contract. A
        # same-day intraday timestamp must not pass this readiness check.
        bounds = frame["month"].dt.end_time.dt.floor("s")
        if not frame["known_at"].eq(bounds).all():
            return {**base, "status": "INVALID_CONTEXT",
                    "reason": "Policy day-bound input requires exact month-end bounds"}
    requested = frame.loc[frame["month"].isin(months)].set_index("month")
    missing = [str(m) for m in months if m not in requested.index]
    timely = requested["known_at"] <= requested.index.end_time
    late = requested.index[~timely].astype(str).tolist()
    unknown = []
    if source["kind"] == "macro_state":
        states = source.get("states")
        if (not isinstance(states, list) or len(states) < 2 or len(states) != len(set(states))
                or "UNKNOWN" in states or not all(isinstance(s, str) and s for s in states)):
            return {**base, "status": "INVALID_CONTEXT", "reason": "Invalid macro state dictionary"}
        if not isinstance(source.get("classification_rules"), dict) or not source["classification_rules"].get("version"):
            return {**base, "status": "INVALID_CONTEXT", "reason": "Missing frozen classification rule version"}
        if not set(frame["state"]).issubset(set(states) | {"UNKNOWN"}):
            return {**base, "status": "INVALID_CONTEXT", "reason": "Unrecognized macro state"}
        unknown = requested.index[requested["state"].eq("UNKNOWN")].astype(str).tolist()
        usable = int((timely & requested["state"].ne("UNKNOWN")).sum())
    else:
        if source.get("official_market_index") is not True or not source.get("market_id"):
            return {**base, "status": "INVALID_CONTEXT", "reason": "Only an identified official market index is allowed"}
        if frame["close"].map(lambda value: isinstance(value, bool)).any():
            return {**base, "status": "INVALID_CONTEXT", "reason": "Boolean index level"}
        # Classifier validates finite positive prices and causal historical windows.
        usable = int(timely.sum())
    base.update(usable_months=usable, missing_months=missing, late_months=late,
                unknown_months=unknown, usable_fraction=usable / len(months))
    if not usable:
        return {**base, "status": "NO_USABLE_ROWS"}
    if source["kind"] == "market_index":
        classify_frame = frame.copy()
        classify_frame["month"] = classify_frame["month"].astype(str)
        classified = classify_monthly_market(classify_frame,
            as_of=str(months[-1].end_time.date()), market_id=source["market_id"], source_id=source["source_id"])
        selected = classified.loc[classified["month"].isin(months.astype(str))]
        ready = selected.loc[selected["detail_status"].eq("READY"), "month"].tolist()
        base.update(classified_months=len(ready), warmup_or_missing_months=[str(m) for m in months if str(m) not in ready],
                    warmup_observations_before_period=int((frame["month"] < months[0]).sum()),
                    classification_is_input_only_not_factor_analysis=True)
        if usable < len(months):
            return {**base, "status": "INCOMPLETE_PERIOD_COVERAGE"}
        if len(ready) < len(months):
            return {**base, "status": "INSUFFICIENT_HISTORY"}
    elif usable < len(months):
        return {**base, "status": "INCOMPLETE_PERIOD_COVERAGE"}
    return {**base, "status": "READY"}


def audit_readiness(manifest_path, registry_path, *, allow_assumed=False):
    manifest_path, registry_path = Path(manifest_path).resolve(), Path(registry_path).resolve()
    manifest, months = _manifest(manifest_path)
    registry_status, contexts, registry_error = _registry(registry_path)
    requirements = []
    for req in manifest["requirements"]:
        evidence = _evidence(req["evidence"], manifest_path.parent)
        result = {"id": req["id"], "role": req["role"], "context_id": req.get("context_id"),
                  "blockers": req["blockers"], "evidence": evidence, "requested_months": len(months)}
        if not evidence or any(e["status"] == "MISSING_EVIDENCE" for e in evidence):
            result["status"] = "MISSING_EVIDENCE"
        elif any(e["status"] == "EVIDENCE_HASH_MISMATCH" for e in evidence):
            result["status"] = "EVIDENCE_HASH_MISMATCH"
        elif req["blockers"]:
            result["status"] = "EVIDENCE_INCOMPLETE"
        elif req["role"] == "CURRENT_RESEARCH_INPUT":
            result.update(status="SEPARATE_RESEARCH_INPUT_GATE_REQUIRED",
                          reason="A diagnostic regime context cannot certify DART/KRX factor input provenance")
        elif registry_status != "VERIFIED_REGISTRY":
            result["status"] = registry_status
        elif not req.get("context_id") or req["context_id"] not in contexts:
            result["status"] = "MISSING_APPROVED_CONTEXT"
        elif (req["role"] == "MARKET_REGIME_CANDIDATE"
              and contexts[req["context_id"]]["source"].get("kind") != "market_index"):
            result.update(status="CONTEXT_ROLE_MISMATCH", reason="A macro context cannot complete the market-index requirement")
        else:
            try:
                result.update(_availability(contexts[req["context_id"]], months))
                accepted = contexts[req["context_id"]]["approval"]
                if accepted.get("schema_version") == "pit-regime-assumption-v1":
                    result.update(pit_status="PIT_ASSUMED",
                                  assumption_policy_sha256=accepted["assumption_policy_sha256"])
                    result["availability_status"] = result["status"]
                    if not allow_assumed:
                        result["status"] = "ASSUMPTION_NOT_HISTORICAL_VERIFICATION"
                    elif result["status"] == "READY":
                        result["status"] = "READY_ASSUMED"
            except (ValueError, KeyError, TypeError) as exc:
                result.update(status="INVALID_CONTEXT", reason=str(exc))
        requirements.append(result)
    ready = sum(r["status"] in {"READY", "READY_ASSUMED"} for r in requirements)
    assumed_ready = sum(r["status"] == "READY_ASSUMED" for r in requirements)
    complete = ready == len(requirements) and registry_status == "VERIFIED_REGISTRY"
    return {"schema_version": RESULT_SCHEMA, "mode": "READ_ONLY_PRE_EXECUTION_GATE",
            "manifest_path": str(manifest_path), "manifest_sha256": _sha(manifest_path),
            "registry_path": str(registry_path), "registry_sha256": _sha(registry_path) if registry_path.is_file() else None,
            "registry_status": registry_status, "registry_error": registry_error,
            "period": manifest["period"], "required_count": len(requirements), "ready_count": ready,
            "status_counts": dict(Counter(r["status"] for r in requirements)), "requirements": requirements,
            "status": ("COMPLETE_UNDER_ASSUMPTIONS" if assumed_ready else "COMPLETE")
                      if complete else "PARTIAL" if ready else "BLOCKED", "complete": complete,
            "assumed_inputs_allowed": allow_assumed, "assumed_ready_count": assumed_ready,
            "scope_was_reduced": False, "historical_truth_recertified": False,
            "new_pit_approval_granted": False, "diagnostic_analysis_executed": False,
            "campaign_or_registry_modified": False, "database_accessed": False,
            "meaning": "Completion describes the supplied fixed scope and usable accepted contexts. READY_ASSUMED is an explicit user assumption acceptance, never historical-vintage verification. Declared blockers are not automatically waived."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--allow-assumed", action="store_true",
                        help="Accept separately authorized assumptions for usability, never historical PIT certification")
    args = parser.parse_args(argv)
    report = audit_readiness(args.manifest, args.registry, allow_assumed=args.allow_assumed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "ready": report["ready_count"],
                      "required": report["required_count"], "analysis_executed": False}))
    return 2 if args.require_complete and not report["complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
