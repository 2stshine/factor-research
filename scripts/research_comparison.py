"""Versioned 24-case synthetic comparison broker; no real data or OOS access.

Researchers use packet/act only. init/references/score are evaluator operations.
All isolation is logical, not an OS security claim. Existing v3 stays unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from engine.adaptive_research import canonical, digest
from engine.research_comparison_lab import ComparisonLab, CATALOG, SCENARIOS_BY_QUESTION
from engine.research_comparison_runtime import ComparisonSession, make_contract
from engine.research_comparison_policies import ORDERS, lean_fixed, score_episode

ROOT = Path(__file__).resolve().parents[1]
PLANNERS = ("LEAN_FIXED_REFERENCE", "HOST_LLM")
SOURCES = (
    "engine/adaptive_research.py", "engine/research_diagnostic_lab.py",
    "engine/adaptive_diagnostic_policies.py", "engine/research_diagnostic_claims.py",
    "engine/research_comparison_lab.py", "engine/research_comparison_runtime.py",
    "engine/research_comparison_policies.py", "scripts/research_comparison.py",
    "research/v2/comparison-host-wrapper.txt",
)


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def fingerprints():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}


def load_run(run):
    manifest = read(run / "private-manifest.json")
    if manifest["source_sha256"] != fingerprints():
        raise ValueError("Frozen source mismatch; never modify a running/scored version")
    if manifest["plan_sha256"] != digest(manifest["plan"]):
        raise ValueError("Frozen plan integrity mismatch")
    if manifest["cases_sha256"] != digest(manifest["cases"]):
        raise ValueError("Case index integrity mismatch")
    snapshot = read(run / "source-snapshot.json")
    if {p: hashlib.sha256(s.encode()).hexdigest() for p, s in snapshot.items()} != manifest["source_sha256"]:
        raise ValueError("Source snapshot integrity mismatch")
    return manifest


def init_run(run, plan_path):
    if run.exists():
        raise FileExistsError(run)
    plan = read(plan_path)
    if plan["runtime"]["mode"] != "SYNTHETIC_ONLY":
        raise ValueError("Only synthetic evaluation supported")
    cfg = plan["comparison"]
    if cfg["conditions"] != list(PLANNERS):
        raise ValueError("Unknown planner set")
    if cfg["question_families"] != {k: list(v) for k, v in SCENARIOS_BY_QUESTION.items()}:
        raise ValueError("Question family plan differs from implementation")
    if cfg["fixed_orders"] != {k: list(v) for k, v in ORDERS.items()}:
        raise ValueError("Fixed checklist plan differs from implementation")
    if not cfg["replicate_seed_bases"] or len(set(cfg["replicate_seed_bases"])) != len(cfg["replicate_seed_bases"]):
        raise ValueError("Distinct replicate seed bases required")
    cases, family_index = [], 0
    for question, scenarios in cfg["question_families"].items():
        for scenario in scenarios:
            for replicate, base in enumerate(cfg["replicate_seed_bases"]):
                cases.append({"question_kind": question, "scenario": scenario,
                              "seed": base + 100 * family_index, "replicate": replicate + 1})
            family_index += 1
    random.Random(cfg["case_order_seed"]).shuffle(cases)
    for index, case in enumerate(cases):
        # The ID hashes an anonymous position, never a truth-bearing scenario.
        case["case_id"] = "case-" + digest({"position": index, "opaque_namespace": "research-comparison-v4"})[:12]
    if len(cases) != cfg["episodes_per_planner"]:
        raise ValueError("Episode count differs from frozen plan")
    if len({c["seed"] for c in cases}) != len(cases):
        raise ValueError("Evaluation seeds collide")
    manifest = {"version": "research-comparison-run-v4", "created_at": datetime.now(timezone.utc).isoformat(),
                "mode": "SYNTHETIC_ONLY", "isolation_level": "LOGICAL_ONLY", "plan": plan,
                "plan_sha256": digest(plan), "source_sha256": fingerprints(), "cases": cases,
                "cases_sha256": digest(cases), "planner_cost": "UNMEASURED",
                "oracle_access": "GRADER_ONLY_LOGICAL_BOUNDARY", "production_rollout_allowed": False}
    run.mkdir(parents=True)
    save(run / "private-manifest.json", manifest)
    save(run / "source-snapshot.json", {name: (ROOT / name).read_text() for name in SOURCES})
    public = {"version": manifest["version"], "case_ids": [c["case_id"] for c in cases],
              "plan_sha256": manifest["plan_sha256"], "mode": "SYNTHETIC_ONLY"}
    save(run / "public-index.json", public)
    return public


def session_for(run, manifest, case, planner):
    if planner not in PLANNERS:
        raise ValueError("Unknown planner")
    path = run / "sessions" / case["case_id"] / f"{planner}.sqlite"
    lab = ComparisonLab(case["seed"], case["scenario"], case["question_kind"])
    cfg = manifest["plan"]["runtime"]
    public_case = {**lab.public_case(), "session_case_id": case["case_id"]}
    expected = make_contract(public_case, CATALOG, planner_kind=planner,
                             max_cost_units=cfg["max_cost_units"], max_actions=cfg["max_actions"])
    if path.exists():
        session = ComparisonSession(path)
        if session.events()[0]["contract"] != expected:
            raise ValueError("Session does not match frozen case identity, planner or budget")
    else:
        session = ComparisonSession(path, expected)
    return session, lab


def public_session(run, case_id):
    manifest = load_run(run)
    matches = [c for c in manifest["cases"] if c["case_id"] == case_id]
    if len(matches) != 1:
        raise ValueError("Unknown public case")
    return session_for(run, manifest, matches[0], "HOST_LLM")


def aggregate(rows):
    def total(key):
        return sum(r["score"][key] for r in rows)
    requests, useful, expected = total("data_requested"), total("useful_data_request"), total("expected_data_request")
    return {
        "episodes": len(rows), "completed": total("complete"), "primary_correct": total("primary_correct"),
        "evidence_supported_primary_correct": total("evidence_supported_primary_correct"),
        "unsupported_conclusions": total("unsupported_conclusion"),
        "unsupported_findings": sum(len(r["score"]["unsupported_findings"]) for r in rows),
        "false_findings_vs_generator": sum(len(r["score"]["false_findings_vs_generator"]) for r in rows),
        "data_requests": requests, "useful_data_requests": useful, "expected_data_requests": expected,
        "data_request_precision": useful / requests if requests else None,
        "data_request_recall": useful / expected if expected else None,
        "economic_diagnostics_observed": total("economic_diagnostic_observed"),
        "tool_cost_units": total("tool_cost_units"), "actions": total("actions"),
        "invalid_or_failed_actions": total("invalid_or_failed_actions"),
        "planner_tokens": None, "planner_monetary_cost": None,
    }


def run_references(run):
    manifest = load_run(run)
    target = run / "reference-results.json"
    if target.exists():
        raise FileExistsError(target)
    rows = []
    for case in manifest["cases"]:
        session, lab = session_for(run, manifest, case, "LEAN_FIXED_REFERENCE")
        export = session.run(lean_fixed, lab.run)
        rows.append({**case, "planner": "LEAN_FIXED_REFERENCE", "score": score_episode(export, lab.oracle()),
                     "trace_sha256": export["root_sha256"]})
    result = {"version": "lean-fixed-comparison-reference-v4", "plan_sha256": manifest["plan_sha256"],
              "actual_llm_experiment": False, "rows": rows, "aggregate": aggregate(rows)}
    save(target, result)
    # Avoid giving future researchers diagnostic/truth results through normal progress output.
    return {"reference_episodes": len(rows), "results_saved": str(target), "grader_only": True}


def status_run(run):
    manifest = load_run(run)
    groups = {}
    for planner in PLANNERS:
        states = {}
        for case in manifest["cases"]:
            path = run / "sessions" / case["case_id"] / f"{planner}.sqlite"
            state = session_for(run, manifest, case, planner)[0].packet()["state"]["state"] if path.exists() else "NOT_STARTED"
            states[state] = states.get(state, 0) + 1
        groups[planner] = states
    return {"expected_episodes_per_planner": len(manifest["cases"]), "states": groups,
            "scores_exposed": False}


def score_run(run):
    manifest = load_run(run)
    # Do not release a partial scoreboard for tuning subsequent case decisions.
    state = status_run(run)
    if any(set(group) - {"STOPPED", "ACTION_BUDGET_EXHAUSTED"} for group in state["states"].values()):
        raise ValueError("All frozen cases must terminate or exhaust the action budget before scorer release")
    rows, pairs = [], []
    for case in manifest["cases"]:
        pair = {}
        for planner in PLANNERS:
            session, lab = session_for(run, manifest, case, planner)
            export = session.export()
            score = score_episode(export, lab.oracle())
            rows.append({**case, "planner": planner, "score": score, "trace_sha256": export["root_sha256"]})
            pair[planner] = score
        fixed, host = (pair[p] for p in PLANNERS)
        delta = int(host["evidence_supported_primary_correct"]) - int(fixed["evidence_supported_primary_correct"])
        pairs.append({**case, "host_accuracy_result": "WIN" if delta > 0 else "LOSS" if delta < 0 else "TIE",
                      "host_minus_fixed_correct": delta,
                      "host_minus_fixed_tool_cost": host["tool_cost_units"] - fixed["tool_cost_units"]})
    aggregates = {p: aggregate([r for r in rows if r["planner"] == p]) for p in PLANNERS}
    families = []
    for question, scenarios in manifest["plan"]["comparison"]["question_families"].items():
        for scenario in scenarios:
            matches = [r for r in pairs if r["question_kind"] == question and r["scenario"] == scenario]
            delta = sum(r["host_minus_fixed_correct"] for r in matches)
            families.append({"question_kind": question, "scenario": scenario, "cases": len(matches),
                             "host_accuracy_result": "WIN" if delta > 0 else "LOSS" if delta < 0 else "TIE",
                             "host_minus_fixed_correct": delta,
                             "host_minus_fixed_tool_cost": sum(r["host_minus_fixed_tool_cost"] for r in matches)})
    fixed, host = (aggregates[p] for p in PLANNERS)
    integration = all(a["completed"] == len(manifest["cases"]) and a["invalid_or_failed_actions"] == 0 for a in aggregates.values())
    safe = host["unsupported_conclusions"] == host["unsupported_findings"] == 0
    data_ok = host["useful_data_requests"] == host["expected_data_requests"] and host["data_requests"] == host["useful_data_requests"]
    accuracy_ok = host["evidence_supported_primary_correct"] >= fixed["evidence_supported_primary_correct"]
    readiness = integration and safe and data_ok and accuracy_ok
    better = (host["primary_correct"] >= fixed["primary_correct"] and (
        any(p["host_accuracy_result"] == "WIN" for p in pairs) or (
            host["primary_correct"] == fixed["primary_correct"] and host["tool_cost_units"] < fixed["tool_cost_units"])))
    return {
        "version": "research-comparison-results-v4", "created_at": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": manifest["plan_sha256"], "source_sha256": manifest["source_sha256"],
        "mode": "SYNTHETIC_ONLY", "isolation_level": "LOGICAL_ONLY", "rows": rows,
        "aggregates": aggregates, "paired_cases": pairs, "paired_families": families,
        "by_question": {q: {p: aggregate([r for r in rows if r["planner"] == p and r["question_kind"] == q])
                            for p in PLANNERS} for q in SCENARIOS_BY_QUESTION},
        "integration": "PASS" if integration else "REVIEW_REQUIRED",
        "bounded_pilot_readiness": "REVIEW_GENERATOR_MISMATCHES_THEN_ELIGIBLE" if readiness else "REVIEW_REQUIRED",
        "followup_preference": "ADAPTIVE_BOUNDED_FOLLOWUP_CANDIDATE" if readiness and better else "LEAN_FIXED_DEFAULT",
        "adaptive_general_superiority": "NOT_ESTABLISHED",
        "statistical_significance_claim": False, "model_total_cost_savings_claim": False,
        "real_factor_trials": 0, "oos_reveals": 0, "gold_writes": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "references", "packet", "act", "status", "score"):
        p = sub.add_parser(command)
        p.add_argument("--run", type=Path, required=True)
        if command == "init":
            p.add_argument("--plan", type=Path, default=ROOT / "research/v2/comparison-plan-20261001.json")
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
        result = init_run(args.run, args.plan)
    elif args.command == "references":
        result = run_references(args.run)
    elif args.command == "status":
        result = status_run(args.run)
    elif args.command == "score":
        result = score_run(args.run)
        save(args.output, result)
        result = {k: v for k, v in result.items() if k not in {"rows", "source_sha256", "paired_cases", "paired_families"}}
    else:
        session, lab = public_session(args.run, args.case)
        if args.command == "packet":
            result = session.request()
        else:
            receipt = session.submit(read(args.action), request_id=args.request_id,
                                     expected_revision=args.revision, execute=lab.run)
            next_packet = session.request() if session.packet()["state"]["state"] == "ACTIVE" else session.packet()
            result = {"receipt": receipt, "next_packet": next_packet}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
