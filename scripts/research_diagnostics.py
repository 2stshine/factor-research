"""Local synthetic-only broker for budgeted diagnostic planning.

init / references / packet / act / score. No production data, credentials,
network, campaign imports, factor gates, or publication. Public-only host agents
use packet and act; manifest/scorer are grader-only by logical convention.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from engine.adaptive_research import DiagnosticSession, canonical, digest, make_contract
from engine.adaptive_diagnostic_policies import adaptive_reference, fixed_reference, score_episode
from engine.research_diagnostic_lab import DiagnosticLab, DIAGNOSTIC_CATALOG, SCENARIOS

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("engine/adaptive_research.py", "engine/adaptive_diagnostic_policies.py",
           "engine/research_diagnostic_lab.py", "scripts/research_diagnostics.py")


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def fingerprints():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def load_run(run):
    manifest = read(run / "private-manifest.json")
    if manifest["source_sha256"] != fingerprints():
        raise ValueError("Frozen run source mismatch; preserve old run and create a versioned new run")
    if manifest["plan_sha256"] != digest(manifest["plan"]):
        raise ValueError("Plan integrity mismatch")
    return manifest


def init_run(run, plan_path):
    if run.exists():
        raise FileExistsError(run)
    plan = read(plan_path)
    if plan["runtime"]["mode"] != "SYNTHETIC_ONLY":
        raise ValueError("Only synthetic runs supported")
    order = list(SCENARIOS)
    random.Random(plan["comparison"]["case_order_seed"]).shuffle(order)
    host = []
    for i, scenario in enumerate(order):
        seed = plan["comparison"]["host_smoke_seed_base"] + i
        # Opaque identifiers, not a hash of the truth-bearing scenario.
        case_id = "case-" + hashlib.sha256(f"anonymous-case-{i}-7182026".encode()).hexdigest()[:8]
        host.append({"case_id": case_id, "scenario": scenario, "seed": seed})
    manifest = {"version": "diagnostic-run-v1", "created_at": datetime.now(timezone.utc).isoformat(),
                "mode": "SYNTHETIC_ONLY", "isolation_level": "LOGICAL_ONLY", "plan": plan,
                "plan_sha256": digest(plan), "source_sha256": fingerprints(), "host_cases": host,
                "oracle_policy": "GRADER_ONLY_NOT_OS_ENFORCED", "model_cost": "UNMEASURED"}
    run.mkdir(parents=True)
    save(run / "private-manifest.json", manifest)
    # Save exact sources as generated run artifacts, not hashes alone. Future
    # fixes create a new run; the old experiment remains reproducible.
    save(run / "source-snapshot.json", {name: (ROOT / name).read_text() for name in SOURCES})
    save(run / "public-index.json", {"case_ids": [c["case_id"] for c in host],
                                    "mode": "SYNTHETIC_ONLY", "isolation_level": "LOGICAL_ONLY"})
    return {"run": str(run), "plan_sha256": manifest["plan_sha256"],
            "case_ids": [c["case_id"] for c in host]}


def session_for(run, manifest, case, planner):
    path = run / "sessions" / case["case_id"] / f"{planner}.sqlite"
    lab = DiagnosticLab(case["seed"], case["scenario"])
    if path.exists():
        session = DiagnosticSession(path)
    else:
        cfg = manifest["plan"]["runtime"]
        session = DiagnosticSession(path, make_contract(lab.public_case(), DIAGNOSTIC_CATALOG,
                                    planner_kind=planner, max_cost_units=cfg["max_cost_units"],
                                    max_actions=cfg["max_actions"]))
    return session, lab


def public_session(run, case_id):
    manifest = load_run(run)
    matches = [c for c in manifest["host_cases"] if c["case_id"] == case_id]
    if len(matches) != 1:
        raise ValueError("Unknown public case")
    return session_for(run, manifest, matches[0], "HOST_LLM")


def aggregate(rows):
    n = len(rows)
    normal = [r for r in rows if r["score"]["normal_effect_preserved"] is not None]
    abstain = [r for r in rows if r["score"]["correct_abstention"] is not None]
    return {"episodes": n, "completed": sum(r["score"]["complete"] for r in rows),
            "primary_correct": sum(r["score"]["primary_conclusion_correct"] for r in rows),
            "false_finding_count": sum(len(r["score"]["false_findings"]) for r in rows),
            "unsupported_normal_conclusions": sum(r["score"]["unsupported_normal_conclusion"] for r in rows),
            "normal_preserved": sum(r["score"]["normal_effect_preserved"] for r in normal),
            "normal_cases": len(normal),
            "correct_abstention": sum(r["score"]["correct_abstention"] for r in abstain),
            "abstention_cases": len(abstain),
            "tool_cost_units": sum(r["score"]["tool_cost_units"] for r in rows),
            "invalid_or_failed_actions": sum(r["score"]["invalid_or_failed_actions"] for r in rows),
            "planner_tokens": None, "planner_monetary_cost": None,
            "uncertainty": "Smoke counts only; repeated seeds are not independent fixture families."}


def run_references(run):
    manifest = load_run(run)
    cases = list(manifest["host_cases"])
    for seed in manifest["plan"]["comparison"]["reference_seeds"]:
        for index, scenario in enumerate(SCENARIOS):
            cases.append({"case_id": f"reference-{seed}-{index}", "scenario": scenario, "seed": seed})
    rows = []
    for case in cases:
        for name, policy in (("FIXED_REFERENCE", fixed_reference), ("SCRIPTED_ADAPTIVE_REFERENCE", adaptive_reference)):
            session, lab = session_for(run, manifest, case, name)
            export = session.run(policy, lab.run)
            rows.append({"case_id": case["case_id"], "scenario": case["scenario"], "seed": case["seed"],
                         "planner": name, "score": score_episode(export, lab.oracle()),
                         "trace_sha256": export["root_sha256"]})
    result = {"version": "diagnostic-reference-results-v1", "plan_sha256": manifest["plan_sha256"],
              "source_sha256": manifest["source_sha256"], "actual_llm_experiment": False,
              "rows": rows, "aggregates": {name: aggregate([r for r in rows if r["planner"] == name])
                                             for name in ("FIXED_REFERENCE", "SCRIPTED_ADAPTIVE_REFERENCE")}}
    save(run / "reference-results.json", result)
    return result["aggregates"]


def score_run(run):
    manifest = load_run(run)
    rows, missing = [], []
    for case in manifest["host_cases"]:
        for name in ("FIXED_REFERENCE", "SCRIPTED_ADAPTIVE_REFERENCE", "HOST_LLM"):
            path = run / "sessions" / case["case_id"] / f"{name}.sqlite"
            if not path.exists():
                missing.append({"case_id": case["case_id"], "planner": name})
                continue
            export = DiagnosticSession(path).export()
            lab = DiagnosticLab(case["seed"], case["scenario"])
            rows.append({"case_id": case["case_id"], "scenario": case["scenario"], "seed": case["seed"],
                         "planner": name, "score": score_episode(export, lab.oracle()),
                         "trace_sha256": export["root_sha256"]})
    groups = {name: aggregate([r for r in rows if r["planner"] == name])
              for name in ("FIXED_REFERENCE", "SCRIPTED_ADAPTIVE_REFERENCE", "HOST_LLM")}
    host = groups["HOST_LLM"]
    integration = not missing and host["completed"] == len(manifest["host_cases"]) and host["invalid_or_failed_actions"] == 0
    review = host["false_finding_count"] == 0 and host["unsupported_normal_conclusions"] == 0
    return {"version": "diagnostic-matched-comparison-v1", "plan_sha256": manifest["plan_sha256"],
            "source_sha256": manifest["source_sha256"], "mode": "SYNTHETIC_ONLY",
            "isolation_level": "LOGICAL_ONLY", "rows": rows, "aggregates": groups, "missing": missing,
            "integration": "PASS" if integration else "INCOMPLETE_OR_FAILED",
            "diagnostic_review": "PASS" if review and integration else "REVIEW_REQUIRED",
            "adaptive_superiority": "NOT_ESTABLISHED_SMALL_SMOKE_AND_MODEL_COST_UNMEASURED",
            "production_rollout_allowed": False, "real_factor_approval": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "references", "packet", "act", "score"):
        p = sub.add_parser(command)
        p.add_argument("--run", type=Path, required=True)
        if command == "init":
            p.add_argument("--plan", type=Path, default=ROOT / "research/v2/adaptive-plan.json")
        if command in {"packet", "act"}:
            p.add_argument("--case", required=True)
        if command == "act":
            p.add_argument("--action", type=Path, required=True)
            p.add_argument("--request-id", required=True)
            p.add_argument("--revision", type=int, required=True)
        if command == "score":
            p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "init":
        value = init_run(args.run, args.plan)
    elif args.command == "references":
        value = run_references(args.run)
    elif args.command == "score":
        value = score_run(args.run)
        save(args.output, value)
        value = {k: v for k, v in value.items() if k not in {"rows", "source_sha256"}}
    else:
        session, lab = public_session(args.run, args.case)
        if args.command == "packet":
            value = session.request()
        else:
            value = session.submit(read(args.action), request_id=args.request_id,
                                   expected_revision=args.revision, execute=lab.run)
            value = {"receipt": value, "next_packet": session.request() if session.packet()["state"]["state"] == "ACTIVE" else session.packet()}
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
