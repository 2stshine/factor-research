"""Explicit research comparison after measurement admission; no Gold writes."""
import argparse
from pathlib import Path

from engine import reference_strategy_evaluation as evaluation, reference_gold as gold
from engine.reference_admission import admitted_features
from engine.reference_db import connect
from engine.phenomenon_reference_collection import read_collection_program
from engine.phenomenon_references import _validated_frame
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_json, save_json, sha

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    # Hash and freeze parameters/input identities before computing any outcomes.
    program, _, _ = read_collection_program(ROOT)
    policy = load_json(ROOT / "research/phenomena/reference-evaluation-policy-v1.json")
    if policy["program_sha256"] != program["program_sha256"]:
        raise ValueError("Evaluation policy belongs to a different active program")
    plan = {"schema": "reference-strategy-evaluation-plan-v1", "program_sha256": program["program_sha256"],
            "admission_file_sha256": sha(args.admission), "bundle_file_sha256": sha(args.bundle),
            "contract_file_sha256": sha(args.contract), "selected_max_features": args.selected_max_features,
            "pca_components": args.pca_components, "registered_at": args.registered_at,
            "policy_sha256": digest(policy),
            "code_sha256": {"evaluation": sha(evaluation.__file__), "ridge": sha(evaluation.ridge.__file__),
                            "kernel": sha(evaluation.ridge.fit_ridge.__code__.co_filename),
                            "execution": sha(evaluation.monthly.__file__), "runner": sha(__file__)}}
    output = Path(args.output)
    save_json(output / "plan.json", plan)
    if (output / "result.json").exists():
        raise ValueError("Comparison already executed; retain existing outcomes")
    admission, bundle, contract = map(load_json, (args.admission, args.bundle, args.contract))
    if bundle["origin"] == "OBSERVED":
        frozen = policy["strategy_comparison"]
        rule = contract["score_rule"]
        for key in ("train_window_months", "min_train_months", "min_train_rows", "purge_gap_months", "max_feature_age_days", "alpha"):
            if rule[key] != frozen[key]:
                raise ValueError("Observed evaluation parameters differ from frozen policy: " + key)
        if args.selected_max_features != frozen["selected_max_features"] or args.pca_components != frozen["pca_components"]:
            raise ValueError("Observed model budget differs from frozen policy")
        for key in ("max_abs_correlation", "max_missing_fraction", "min_variance"):
            if rule["selection"][key] != frozen["selection"][key]:
                raise ValueError("Observed selection threshold differs from frozen policy: " + key)
    allowed = admitted_features(admission, program_sha256=program["program_sha256"], origin=bundle["origin"])
    refs = bundle["reference"]["features"]
    if bundle["origin"] == "OBSERVED" and {f["reference_id"] for f in refs} != set(allowed):
        raise ValueError("Initial observed comparison must include every admitted reference as candidate")
    if any(allowed.get(f["reference_id"]) != f["definition_sha256"] for f in refs):
        raise ValueError("Unadmitted reference cannot be selected")
    proof = None
    if bundle["origin"] == "OBSERVED":
        if not args.cache_receipt:
            raise ValueError("Observed runs require an exact Gold cache receipt and live DB validation")
        cache = load_json(args.cache_receipt)
        receipt_by_id = {r["dataset_id"]: r for r in admission["source_receipts"]}
        spec_by_ref = {f["reference_id"]: f for f in refs}
        with connect() as conn:
            for entry in program["reference_datasets"]:
                needed = set(entry["reference_ids"]) & set(spec_by_ref)
                if not needed:
                    continue
                did = entry["dataset_id"]
                path = Path(cache["cache_paths"][did])
                if sha(path) != receipt_by_id[did]["cache_sha256"]:
                    raise ValueError("Gold cache differs from admission")
                frame, metadata = gold.load_library(conn, dataset_id=did, generation_id=gold.GENERATION, snapshot_path=path)
                frame = _validated_frame(frame, metadata)
                for ref in needed:
                    evaluation.verify_feature_projection(bundle, ref, spec_by_ref[ref]["field"], frame)
        proof = {"schema": "reference-strategy-gold-binding-v1", "input_bundle_sha256": digest(bundle),
                 "admission_sha256": admission["admission_sha256"], "program_sha256": program["program_sha256"],
                 "reference_ids": sorted(spec_by_ref), "live_gold_all_rows_verified": True,
                 "feature_values_and_clocks_match": True}
    result = evaluation.compare(bundle, contract, admission, program_sha256=program["program_sha256"],
                                selected_max_features=args.selected_max_features, pca_components=args.pca_components,
                                registered_at=args.registered_at, measurement_verification=proof)
    after, _, _ = read_collection_program(ROOT)
    if after != program:
        raise ValueError("Active program changed during comparison")
    save_json(output / "result.json", result)
    save_json(output / "summary.json", {"empirical_use": result["empirical_use"],
              "models": {k: v["summary"] for k, v in result["models"].items()}, "selected_model": None,
              "admission_sha256": result["admission_sha256"], "alpha_approved": False})
    print({"status": "COMPARISON_COMPLETE_NOT_APPROVAL", "empirical_use": result["empirical_use"], "models": list(result["models"])})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("admission", "bundle", "contract", "output", "registered-at"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--selected-max-features", type=int, default=30)
    p.add_argument("--pca-components", type=int, default=10)
    p.add_argument("--cache-receipt")
    run(p.parse_args())
