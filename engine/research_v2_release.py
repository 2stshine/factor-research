"""Closed Discovery reanalysis -> reviewed qualitative release -> isolated memory.

This connector does not read raw frames, DBs, OOS, legacy lessons or benchmark
answers. Preparation calls only PilotBroker.export, after all sessions close.
Frozen exported reports are reviewer-only; memory receives qualitative prose.
The host checks artifact hashes, not cryptographic identity or economic truth.
Independent critic decisions must be supplied externally, never fabricated here.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from engine.research_memory_v2 import MemoryStore, canonical, digest

VERSION = "real-pilot-qualitative-release-v1"
NAMESPACE = "research-v2:real-pilot20261002"
ARMS = ("FIXED_REFERENCE", "HOST_LLM")
CHECKS = {"citations_verified", "scope_preserved", "unknowns_preserved", "no_causal_claim", "no_statistics_in_memory"}
TRANSFORM = "accepted-lesson-to-memory-exact-copy-with-labeled-rivals-and-unrun-proposals-v1"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required")
    return parsed.astimezone(timezone.utc)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text())


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = canonical(value) + "\n"
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(content)
    except FileExistsError:
        if path.read_text() != content:
            raise ValueError("Immutable artifact already exists with different content") from None
    return _sha(path)


def _text(value, label, *, qualitative=True):
    if not isinstance(value, str) or not value.strip() or len(value) > 3500:
        raise ValueError(f"Invalid {label}")
    if qualitative and re.search(r"[0-9%％]", value):
        raise ValueError("Memory prose must omit numeric statistics; retain dates/horizons in scope metadata")
    if qualitative and re.search(r"인과(?:관계|적 효과)?(?:를|가)?\s*(?:입증했다|증명했다|확정됐다)|causally proven|causal mechanism established", value, re.I):
        raise ValueError("Affirmative causal proof is not supported")


def _strings(value, label, *, required=False):
    if not isinstance(value, list) or (required and not value):
        raise ValueError(f"Invalid {label}")
    for item in value:
        _text(item, label)
    if len(value) != len(set(value)):
        raise ValueError(f"Duplicate {label}")


def _closed_export(export, case, arm, manifest_sha):
    if (export.get("case_id") != case["case_id"] or export.get("arm") != arm
            or export.get("pilot_manifest_sha256") != manifest_sha
            or export.get("mode") != "REAL_DISCOVERY_REANALYSIS"
            or export.get("state", {}).get("state") != "STOPPED"):
        raise ValueError("All twelve bound sessions must be explicitly closed before review release")
    events = export.get("events", [])
    if not events or events[0].get("contract", {}).get("data_contract_sha256") != case["data_contract_sha256"]:
        raise ValueError("Session is not bound to the frozen data contract")
    terminal = [(i, e) for i, e in enumerate(events) if e.get("status") in
                {"STOPPED", "DATA_REQUESTED_NOT_ACQUIRED", "NEW_TEST_PENDING_REVIEW"}]
    if not terminal:
        raise ValueError("Explicit terminal result is required")
    index, stop = terminal[-1]
    if stop.get("decision", {}).get("payload", {}).get("mechanism_identified") is True:
        raise ValueError("Source claims unauthorized causal identification")
    reports = []
    for evidence in export["state"].get("evidence", []):
        response = evidence.get("response", {})
        if (evidence.get("response_sha256") != digest(response)
                or response.get("evidence_scope", {}).get("contract_sha256") != case["data_contract_sha256"]
                or response.get("scope") != "FROZEN_DISCOVERY_ONLY"
                or response.get("status") not in {"COMPUTED", "NOT_COMPUTED", "INSUFFICIENT_SUPPORT"}
                or response.get("causal_identification") is not False):
            raise ValueError("Unbound or unauthorized diagnostic report")
        reports.append(deepcopy(evidence))
    if not reports:
        raise ValueError("Closed session has no reviewable evidence")
    # Ignore later PROMPT/read deliveries. Bind the immutable terminal prefix,
    # not the latest read-log root, which can legitimately advance on inspection.
    return {"version": VERSION, "case_id": case["case_id"], "arm": arm,
            "pilot_manifest_sha256": manifest_sha, "data_contract_sha256": case["data_contract_sha256"],
            "terminal_prefix_sha256": digest(events[:index + 1]), "terminal_event_sha256": digest(stop),
            "terminal_status": stop["status"], "terminal_decision": stop["decision"],
            "reports": reports, "unperformed_required_diagnostics": export.get("unperformed_required_diagnostics", []),
            "explanation_complete": export.get("explanation_complete", False),
            "independent_oos_claim": False, "factor_admission_trials": 0, "gold_writes": 0}


def prepare_review(pilot_root: Path, output: Path, *, broker_factory=None):
    """Freeze a self-contained reviewer bundle; no lesson interpretation is generated."""
    if broker_factory is None:
        from engine.research_v2_pilot import PilotBroker
        broker_factory = PilotBroker
    broker = broker_factory(pilot_root)
    manifest, frozen = broker.manifest, broker.frozen
    if len(broker.cases) != 6 or manifest.get("factor_admission_trials") != 0 or manifest.get("oos_reads") != 0:
        raise ValueError("Expected the exact six-case Discovery protocol reanalysis, without new admission/OOS")
    exports = []
    for cid, case in broker.cases.items():
        for arm in ARMS:
            exports.append(_closed_export(broker.export(cid, arm), case, arm, manifest["manifest_sha256"]))
    output = Path(output)
    if output.exists():
        raise FileExistsError("Use a fresh release directory; prior bundles remain immutable")
    output.mkdir(parents=True)
    cases, evidence_index = {}, {}
    for cid, case in broker.cases.items():
        root_id = "pilot-root-" + digest({"snapshot": manifest["discovery_snapshot_sha256"],
                    "definition": case["definition_sha256"], "contract": case["data_contract_sha256"]})
        scope = {"market": "KOSPI_KOSDAQ", "universe": "FROZEN_INVESTABLE_KRX_COMMON_STOCKS",
                 "period": f"{frozen['signal_start']}/{frozen['signal_end']}", "horizon": "ONE_MONTH_RETURN",
                 "data_snapshot": manifest["discovery_snapshot_sha256"], "feature_definition": case["definition_sha256"],
                 "pit_policy": "POLICY_BOUND_FEATURES_AND_PIT_ASSUMED_REGIME", "protocol_version": VERSION,
                 "regime_definition": frozen["regime_contract_sha256"], "cost_model": "NO_VERIFIED_HOLDINGS_EXECUTION"}
        entry = {"case_id": cid, "root_id": root_id, "scope": scope, "sources": [],
                 "source_statuses": {}, "unperformed_diagnostics": {}, "evidence_ids": []}
        for source in (x for x in exports if x["case_id"] == cid):
            relative = f"sources/{cid}/{source['arm']}.json"
            entry["sources"].append({"path": relative, "sha256": _write(output / relative, source),
                                      "terminal_prefix_sha256": source["terminal_prefix_sha256"], "arm": source["arm"]})
            entry["unperformed_diagnostics"][source["arm"]] = source["unperformed_required_diagnostics"]
            for report in source["reports"]:
                eid = f"{cid}/{report['diagnostic_id']}/{report['response_sha256'][:20]}"
                if eid not in evidence_index:
                    evidence_index[eid] = {"evidence_id": eid, "case_id": cid, "root_id": root_id,
                                           "report": report["response"], "source_arms": []}
                evidence_index[eid]["source_arms"].append(source["arm"])
                entry["source_statuses"][eid] = report["response"]["status"]
                entry["evidence_ids"].append(eid)
        entry["evidence_ids"] = sorted(set(entry["evidence_ids"]))
        cases[cid] = entry
    bundle = {"schema_version": VERSION, "created_at": _now(), "audience": "CLOSED_DISCOVERY_REVIEWER_ONLY",
              "pilot_manifest_sha256": manifest["manifest_sha256"], "cases": cases, "evidence": evidence_index,
              "research_time_distinct_from_market_time": True, "isolation_level": "LOGICAL_ONLY",
              "independent_oos_claim": False, "new_factor_approval": False, "same_case_arms_are_independent_evidence": False}
    bundle["bundle_sha256"] = digest(bundle)
    _write(output / "review-bundle.json", bundle)
    for cid in cases:
        _write(output / "templates" / f"{cid}.json", draft_template(bundle, cid))
    return {"bundle_sha256": bundle["bundle_sha256"], "cases": list(cases), "sessions_closed": len(exports),
            "review_bundle": str(output / "review-bundle.json"), "status": "AWAITING_ACTUAL_ANALYST_AND_CRITIC"}


def load_bundle(root):
    root = Path(root).resolve()
    bundle = _read(root / "review-bundle.json")
    body = deepcopy(bundle)
    if body.pop("bundle_sha256", None) != digest(body) or bundle["schema_version"] != VERSION:
        raise ValueError("Review bundle hash mismatch")
    for case in bundle["cases"].values():
        for source in case["sources"]:
            path = (root / source["path"]).resolve()
            if not path.is_relative_to(root) or _sha(path) != source["sha256"]:
                raise ValueError("Frozen source export hash mismatch")
            if _read(path)["terminal_prefix_sha256"] != source["terminal_prefix_sha256"]:
                raise ValueError("Frozen source terminal prefix mismatch")
    return bundle


def draft_template(bundle, cid):
    case = bundle["cases"][cid]
    return {"schema_version": VERSION, "case_id": cid, "author": "", "title_ko": "",
            "evidence_bundle_sha256": bundle["bundle_sha256"], "scope": case["scope"],
            "facts": [], "interpretations": [], "unknowns": [], "limitations": [],
            "competing_explanations": [], "next_tests": [], "source_statuses": case["source_statuses"],
            "unperformed_diagnostics": case["unperformed_diagnostics"], "causal_claim": False}


def validate_draft(bundle, draft):
    cid = draft.get("case_id")
    if cid not in bundle["cases"] or set(draft) != set(draft_template(bundle, cid)):
        raise ValueError("Draft schema/case mismatch")
    case = bundle["cases"][cid]
    for key in ("schema_version", "evidence_bundle_sha256", "scope", "source_statuses", "unperformed_diagnostics", "causal_claim"):
        if draft[key] != draft_template(bundle, cid)[key]:
            raise ValueError(f"Draft changed frozen {key}")
    _text(draft["author"], "author", qualitative=False)
    _text(draft["title_ko"], "Korean title")
    if not re.search(r"[가-힣]", draft["title_ko"]):
        raise ValueError("Korean lesson title required")
    known = set(case["evidence_ids"])
    def refs(value, required=True):
        if not isinstance(value, list) or (required and not value) or any(x not in known for x in value) or len(value) != len(set(value)):
            raise ValueError("Statement cites missing, duplicate or cross-case evidence")
    for section in ("facts", "interpretations"):
        if not isinstance(draft[section], list) or not draft[section]:
            raise ValueError("Facts and interpretations must be separated and nonempty")
        for item in draft[section]:
            if not isinstance(item, dict) or set(item) != {"text", "evidence_ids"}:
                raise ValueError("Statement schema mismatch")
            _text(item["text"], section)
            refs(item["evidence_ids"])
    _strings(draft["unknowns"], "unknowns", required=True)
    _strings(draft["limitations"], "limitations", required=True)
    rivals = draft["competing_explanations"]
    if not isinstance(rivals, list) or len(rivals) < 2:
        raise ValueError("At least two competing explanations required")
    for rival in rivals:
        if not isinstance(rival, dict) or set(rival) != {"explanation", "status", "evidence_ids", "distinguishing_evidence"}:
            raise ValueError("Competing explanation schema mismatch")
        if rival["status"] not in {"UNTESTED", "CONSISTENT_NOT_PROVEN", "WEAKENED"}:
            raise ValueError("Competing explanation cannot be labeled causal truth")
        _text(rival["explanation"], "competing explanation")
        _text(rival["distinguishing_evidence"], "distinguishing evidence")
        if len(rival["explanation"]) + len(rival["distinguishing_evidence"]) > 3800:
            raise ValueError("Competing explanation exceeds the memory statement budget")
        refs(rival["evidence_ids"], required=rival["status"] != "UNTESTED")
    if not isinstance(draft["next_tests"], list):
        raise ValueError("Next tests must be an explicit proposal list")
    for test in draft["next_tests"]:
        if not isinstance(test, dict) or set(test) != {"question", "design", "status", "evidence_ids"} or test["status"] != "PROPOSED_NOT_RUN":
            raise ValueError("Follow-up tests must remain PROPOSED_NOT_RUN")
        _text(test["question"], "next question")
        _text(test["design"], "next design")
        if len(test["question"]) + len(test["design"]) > 3800:
            raise ValueError("Follow-up proposal exceeds the memory statement budget")
        refs(test["evidence_ids"])
    if len(canonical(_qualitative_payload(draft))) > 8000:
        raise ValueError("Qualitative lesson exceeds the memory envelope budget")
    return digest(draft)


def validate_critic(bundle, draft, critic):
    draft_sha = validate_draft(bundle, draft)
    if set(critic) != {"draft_sha256", "evidence_bundle_sha256", "reviewer", "decision", "issues", "checks", "reviewed_at"}:
        raise ValueError("Critic schema mismatch")
    if critic["draft_sha256"] != draft_sha or critic["evidence_bundle_sha256"] != bundle["bundle_sha256"]:
        raise ValueError("Critic is not bound to this exact draft/evidence")
    _text(critic["reviewer"], "reviewer", qualitative=False)
    if critic["reviewer"] == draft["author"]:
        raise ValueError("Independent reviewer identity required")
    if critic["decision"] not in {"ACCEPT", "REVISE", "REJECT"} or not isinstance(critic["issues"], list):
        raise ValueError("Invalid critic disposition")
    if not isinstance(critic["checks"], dict) or set(critic["checks"]) != CHECKS or any(type(v) is not bool for v in critic["checks"].values()):
        raise ValueError("Critic must explicitly account for every review check")
    if _time(critic["reviewed_at"]) < _time(bundle["created_at"]) or _time(critic["reviewed_at"]) > _time(_now()):
        raise ValueError("Critic review timestamp is outside the observed review window")
    if critic["decision"] != "ACCEPT" or critic["issues"] or not all(critic["checks"].values()):
        raise ValueError("Only a fully accepted independent review can be released")
    return digest(critic)


def _qualitative_payload(draft):
    return {k: deepcopy(draft[k]) for k in ("case_id", "title_ko", "facts", "interpretations", "unknowns", "limitations",
                "competing_explanations", "next_tests", "source_statuses", "unperformed_diagnostics", "scope")}


def stage(root: Path, draft: dict, critic: dict):
    root = Path(root)
    bundle = load_bundle(root)
    critic_sha = validate_critic(bundle, draft, critic)
    cid, draft_sha = draft["case_id"], digest(draft)
    existing = root / "accepted" / f"{cid}.json"
    if existing.exists():
        prior = _read(existing)
        if prior["draft_sha256"] == draft_sha and prior["critic_sha256"] == critic_sha:
            return prior
        raise ValueError("Accepted case is immutable; corrections require a separately versioned release")
    _write(root / "drafts" / f"{draft_sha}.json", draft)
    _write(root / "critics" / f"{critic_sha}.json", critic)
    payload = canonical(_qualitative_payload(draft))
    envelope = {"evidence_id": f"qualitative:{cid}:{draft_sha}", "root_id": bundle["cases"][cid]["root_id"],
                "source_sha256": bundle["bundle_sha256"], "payload": payload, "payload_sha256": digest(payload),
                "scope": draft["scope"], "released_at": _now(), "visibility": "RELEASED_QUALITATIVE",
                "origin": "V2_PUBLIC_EXPORT", "release_receipt_id": f"accepted:{cid}:{critic_sha}"}
    accepted = {"version": VERSION, "case_id": cid, "draft_sha256": draft_sha, "critic_sha256": critic_sha,
                "evidence_bundle_sha256": bundle["bundle_sha256"], "envelope": envelope,
                "isolation_level": "LOGICAL_ONLY", "economic_truth_certified": False,
                "new_factor_approval": False, "memory_transform": TRANSFORM}
    accepted["accepted_sha256"] = digest(accepted)
    _write(existing, accepted)
    return accepted


def public_filter(root: Path):
    """Authenticate full envelope, accepted critic, source bytes and timing on every use."""
    root = Path(root)
    def allowed(envelope, research_as_of):
        try:
            bundle = load_bundle(root)
            for cid in bundle["cases"]:
                path = root / "accepted" / f"{cid}.json"
                if not path.exists():
                    continue
                accepted = _read(path)
                if accepted["envelope"] != envelope:
                    continue
                body = deepcopy(accepted)
                if body.pop("accepted_sha256", None) != digest(body):
                    return False
                draft = _read(root / "drafts" / f"{accepted['draft_sha256']}.json")
                critic = _read(root / "critics" / f"{accepted['critic_sha256']}.json")
                if validate_critic(bundle, draft, critic) != accepted["critic_sha256"]:
                    return False
                expected_payload = canonical(_qualitative_payload(draft))
                return (envelope["payload"] == expected_payload and envelope["payload_sha256"] == digest(expected_payload)
                        and envelope["source_sha256"] == bundle["bundle_sha256"]
                        and envelope["root_id"] == bundle["cases"][cid]["root_id"]
                        and envelope["scope"] == draft["scope"]
                        and draft["case_id"] == cid and accepted["case_id"] == cid
                        and envelope["evidence_id"] == f"qualitative:{cid}:{digest(draft)}"
                        and envelope["release_receipt_id"] == f"accepted:{cid}:{digest(critic)}"
                        and envelope["visibility"] == "RELEASED_QUALITATIVE" and envelope["origin"] == "V2_PUBLIC_EXPORT"
                        and _time(critic["reviewed_at"]) <= _time(envelope["released_at"]) <= _time(research_as_of))
            return False
        except (ValueError, KeyError, OSError, TypeError):
            return False
    return allowed


def memory_arguments(draft, envelope):
    """Deterministic, meaning-preserving transform; no new LLM review is claimed."""
    eid = envelope["evidence_id"]
    statements = lambda entries: [{"text": e["text"], "evidence_ids": [eid]} for e in entries]
    interpretations = statements(draft["interpretations"])
    for rival in draft["competing_explanations"]:
        interpretations.append({"text": f"대안 설명 [{rival['status']}]: {rival['explanation']} / 구분할 근거: {rival['distinguishing_evidence']}", "evidence_ids": [eid]})
    unknowns = list(draft["unknowns"])
    for test in draft["next_tests"]:
        unknowns.append(f"후속 제안 [PROPOSED_NOT_RUN]: {test['question']} / {test['design']}")
    limits = list(draft["limitations"])
    for eid_source, status in draft["source_statuses"].items():
        if status != "COMPUTED":
            limits.append(f"원자료 진단 상태 보존: {eid_source} = {status}")
    for arm, tests in draft["unperformed_diagnostics"].items():
        if tests:
            limits.append(f"미실행 진단 보존 ({arm}): {', '.join(tests)}")
    return {"claim_id": "pilot-" + draft["case_id"], "author": draft["author"],
            "facts": statements(draft["facts"]), "interpretations": interpretations,
            "unknowns": unknowns, "limitations": limits, "scope": draft["scope"],
            "supports": [eid], "counterevidence": [], "expected_revision": 0}


def activate(root: Path, memory_database: Path):
    root = Path(root)
    bundle = load_bundle(root)
    for cid in bundle["cases"]:
        if not (root / "accepted" / f"{cid}.json").is_file():
            raise ValueError("All six cases need accepted independent reviews before activation")
    guard = public_filter(root)
    mem = MemoryStore(memory_database, namespace=NAMESPACE, public_filter=guard)
    receipts = []
    for cid in bundle["cases"]:
        accepted = _read(root / "accepted" / f"{cid}.json")
        envelope = accepted["envelope"]
        if not guard(envelope, _now()):
            raise ValueError("Qualitative release authentication failed")
        draft = _read(root / "drafts" / f"{accepted['draft_sha256']}.json")
        critic = _read(root / "critics" / f"{accepted['critic_sha256']}.json")
        prefix = accepted["accepted_sha256"]
        mem.register_evidence(envelope, key=f"release-evidence:{prefix}")
        arguments = memory_arguments(draft, envelope)
        proposal = mem.propose(**arguments, key=f"release-proposal:{prefix}")
        rationale = ("Existing accepted independent lesson review " + accepted["critic_sha256"] +
                     "; deterministic transform " + TRANSFORM + "; no additional LLM review or economic truth certification.")
        mem.review(proposal["revision_id"], expected_sha256=proposal["content_sha256"], reviewer=critic["reviewer"],
                   decision=critic["decision"], rationale=rationale, key=f"release-review:{prefix}")
        receipt = {"version": VERSION, "case_id": cid, "accepted_sha256": prefix,
                   "draft_sha256": accepted["draft_sha256"], "critic_sha256": accepted["critic_sha256"],
                   "transform_policy": TRANSFORM, "transform_arguments_sha256": digest(arguments),
                   "memory_revision_id": proposal["revision_id"], "memory_content_sha256": proposal["content_sha256"],
                   "reviewer": critic["reviewer"], "namespace": NAMESPACE, "new_model_review_performed": False,
                   "economic_truth_certified": False, "factor_approval_changed": False}
        _write(root / "activation" / f"{cid}.json", receipt)
        receipts.append(receipt)
    result = {"version": VERSION, "status": "SIX_REVIEWED_QUALITATIVE_MEMORIES_ACTIVE", "namespace": NAMESPACE,
              "receipts": receipts, "evidence_bundle_sha256": bundle["bundle_sha256"], "independent_oos_claim": False,
              "same_case_arms_are_independent_evidence": False, "legacy_memory_imported": False}
    _write(root / "activation.json", result)
    return result
