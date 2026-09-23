"""Compose existing accepted snapshots; no API, new research, or registry write."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from engine.korea_macro_direction import CONTEXT_ID, PARENTS, RULES, STATES, VERSION, classify
from engine.assumed_macro_regimes import completed_end_month
from engine.regime_inputs import digest, make_assumption_acceptance, read_context
from scripts.build_assumed_fmp_regimes import save


def build(parent_path, policy_path, output, *, as_of):
    parent_path, policy_path, output = map(lambda p: Path(p).resolve(), (parent_path, policy_path, output))
    if output.exists():
        raise FileExistsError("Use a new artifact directory")
    completed_end_month(as_of)  # validate before comparing date strings or writing
    bundle = read_context(parent_path)
    contexts = {item["source"]["context_id"]: item for item in bundle["contexts"]}
    if len(contexts) != len(bundle["contexts"]):
        raise ValueError("Duplicate parent context identity")
    policy = json.loads(policy_path.read_bytes())
    parents = {}
    for name, cid in PARENTS.items():
        item = contexts[cid]
        source, approval = item["source"], item["approval"]
        if (source.get("pit_status") != "PIT_ASSUMED" or source.get("macro_type") != "assumed_macro"
                or approval.get("assumption_policy_sha256") != digest(policy)):
            raise ValueError("Exact accepted macro parents and same user policy required")
        parents[name] = source
    start = max(p["scope"]["start_month"] for p in parents.values())
    end = min(p["scope"]["end_month"] for p in parents.values())
    # Do not extend a frozen parent's acceptance scope.
    end_date = pd.Period(end, freq="M").end_time.date().isoformat()
    effective_as_of = min(as_of, end_date)
    rows = classify(parents["production"]["rows"], parents["inflation"]["rows"],
                    start_month=start, as_of=effective_as_of)
    lineage = {"parent_context_file_sha256": hashlib.sha256(parent_path.read_bytes()).hexdigest(),
               "parents": {name: {"context_id": p["context_id"], "source_sha256": digest(p),
                  "normalized_sha256": p["normalized_sha256"],
                  "approval_sha256": contexts[p["context_id"]]["approval_sha256"]}
                  for name, p in parents.items()}, "rules": RULES}
    source = {"context_id": CONTEXT_ID, "source_id": VERSION + "-" + digest(lineage)[:16],
              "kind": "macro_state", "macro_type": "korea_production_inflation_direction",
              "frequency": "MONTH_END", "storage_layer": "DERIVED_RESEARCH_CONTEXT",
              "pit_status": "PIT_ASSUMED", "known_at_semantics": "ASSUMED_HISTORICAL_AVAILABILITY",
              "scope": {"start_month": rows[0]["month"], "end_month": rows[-1]["month"],
                        "intraday_allowed": False, "factor_feature_allowed": False},
              "states": STATES, "classification_rules": RULES, "parent_lineage": lineage,
              "assumptions": [
                  "Inherits the explicitly accepted parent current-value vintage and provider-event UTC assumptions; not first-release PIT verification.",
                  "Each of six contiguous decision-month snapshots remains its original as-of value; later releases are never backdated.",
                  "Production YoY momentum and CPI YoY direction are proxies, not GDP growth, price-level deflation or an official recession label.",
                  "Provider event dates are preserved; statistical reference periods were not supplied and remain unknown.",
                  "Fixed diagnostic only; no factor gates, weights, trading decisions or existing campaigns changed."],
              "rows": rows}
    output.mkdir(parents=True)
    # Self-contained parent evidence and receipts: no future reliance on a mutable path.
    parent_hash = save(output / "parent-contexts.json", {
        "contexts": [contexts[cid] for cid in PARENTS.values()]})
    approval = make_assumption_acceptance(source, policy,
        [{"uri": str(output / "parent-contexts.json"), "sha256": parent_hash}],
        accepted_at=datetime.now(timezone.utc).isoformat())
    approval_hash = save(output / "assumption-acceptance.json", approval)
    context_hash = save(output / "context.json", {"schema_version": "diagnostic-regime-input-v1",
        "contexts": [{"source": source, "approval_file": "assumption-acceptance.json",
                       "approval_sha256": approval_hash}]})
    read_context(output / "context.json")
    summary = {"version": VERSION, "as_of": as_of, "pit_status": "PIT_ASSUMED",
               "context_id": CONTEXT_ID, "context_sha256": context_hash,
               "states": dict(Counter(r["state"] for r in rows)), "months": len(rows),
               "first_classified_month": next((r["month"] for r in rows if r["state"] != "UNKNOWN"), None),
               "latest_month": rows[-1]["month"], "latest_state": rows[-1]["state"],
               "months_with_reused_observations": sum(any(v["reused_snapshot_count"] for v in r["inputs"].values()) for r in rows),
               "factor_evaluation_executed": False, "existing_artifacts_modified": False,
               "registry_modified": False}
    save(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.parent, args.policy, args.output, as_of=args.as_of), ensure_ascii=False))


if __name__ == "__main__":
    main()
