"""Evaluate every active reference, without changing Gold or strategy approval.

snapshot-audit is an explicit, non-authorizing diagnostic, NEVER a fallback for
a failed database connection. live-admission checks every persisted Gold row.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from engine import reference_admission as admission, reference_gold as gold
from engine.phenomenon_reference_collection import read_collection_program
from engine.phenomenon_references import _validated_frame
from engine.reference_library import definition_hash
from engine.reference_db import connect
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_json, save_json, sha

ROOT = Path(__file__).resolve().parents[1]


def evaluate(*, cache_receipt, output, mode):
    if mode not in {"snapshot-audit", "live-admission"}:
        raise ValueError("Explicit evaluation mode required")
    program, catalog, generation = read_collection_program(ROOT)
    source = load_json(cache_receipt)
    if source.get("candidate_program_sha256", source.get("program_sha256")) != program["program_sha256"]:
        raise ValueError("Cache receipt does not identify the active program")
    entries = program["reference_datasets"]
    ids = {r for entry in entries for r in entry["reference_ids"]}
    definitions = {r: catalog[r] for r in ids}
    policy = admission.AdmissionPolicy()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    plan = {"schema": "reference-admission-run-v1", "program_sha256": program["program_sha256"],
            "generation_sha256": digest(generation), "catalog_sha256": program["catalog_sha256"],
            "cache_receipt_sha256": sha(cache_receipt), "mode": mode, "policy": asdict(policy),
            "code_sha256": {"admission": sha(admission.__file__), "runner": sha(__file__)},
            "forward_returns_read": False}
    save_json(output / "plan.json", plan)
    # Explicit mode, never exception-driven offline fallback.
    conn = connect() if mode == "live-admission" else None
    rows, receipts, monthly_support = [], [], []
    try:
        for index, entry in enumerate(entries):
            did = entry["dataset_id"]
            path = Path(source["cache_paths"][did])
            if path.is_symlink() or not path.is_file() or sha(path) != source["cache_file_sha256"][did]:
                raise ValueError("Exact immutable cache file mismatch")
            if conn is not None:
                frame, metadata = gold.load_library(conn, dataset_id=did, generation_id=gold.GENERATION, snapshot_path=path)
                frame = _validated_frame(frame, metadata)
                if set(metadata["definitions"]) != set(entry["reference_ids"]):
                    raise ValueError("Live dataset definition partition mismatch")
                for ref, definition in metadata["definitions"].items():
                    if definition_hash(definition) != definition_hash(catalog[ref]):
                        raise ValueError("Live definition differs from active catalog")
            else:
                # Explicit diagnostics of historically verified frozen bytes.
                # This does not invoke or masquerade as the live Gold loader.
                frame = pd.read_parquet(path)
                from engine.phenomenon_references import VALUE_COLUMNS
                frame = frame[sorted(VALUE_COLUMNS)]
            if len(frame) != source["dataset_rows"][did] or set(frame.reference_id) != set(entry["reference_ids"]):
                raise ValueError("Cache count or reference partition mismatch")
            batch = []
            for ref, values in frame.groupby("reference_id", sort=True):
                result = admission.assess_measurement(values, catalog[ref], policy=policy)
                result["dataset_id"] = did
                batch.append(result)
                for date, group in values.groupby("date"):
                    monthly_support.append({"reference_id": ref, "date": str(pd.Timestamp(date).date()),
                                            "assets": int(group.asset_id.nunique()), "rows": len(group)})
            receipt = {"dataset_id": did, "cache_sha256": source["cache_file_sha256"][did],
                       "rows": len(frame), "live_all_row_verified": conn is not None}
            save_json(output / "datasets" / (did + ".json"), {"receipt": receipt, "assessments": batch})
            rows.extend(batch)
            receipts.append(receipt)
            print(f"{index + 1}/{len(entries)} datasets; {len(rows)}/{len(ids)} references assessed", flush=True)
        after, _, after_generation = read_collection_program(ROOT)
        if after != program or after_generation != generation:
            raise ValueError("Active program changed during evaluation")
        report = admission.finalize(rows, definitions, program_sha256=program["program_sha256"], policy=policy,
                                    live_database_verified=conn is not None, source_receipts=receipts)
        save_json(output / "admission.json", report)
        save_json(output / "monthly-support.json", monthly_support)
        summary = {"status": report["status"], "references": len(rows), "rows": sum(r["rows"] for r in rows),
                   "counts": pd.Series([r["status"] for r in report["decisions"]]).value_counts().to_dict(),
                   "assessments": pd.Series([r["assessment"] for r in report["decisions"]]).value_counts().to_dict(),
                   "completed_at": datetime.now(timezone.utc).isoformat(), "admission_sha256": report["admission_sha256"],
                   "strategy_performance_evaluated": False, "gold_changed": False}
        save_json(output / "summary.json", summary)
        print(summary, flush=True)
        return report
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-receipt", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=["snapshot-audit", "live-admission"], required=True)
    args = parser.parse_args()
    evaluate(cache_receipt=args.cache_receipt, output=args.output, mode=args.mode)
