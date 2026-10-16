"""Publish a bounded, separately versioned profit-growth reference batch.

Uses the already captured authenticated FY ledger. Rechecks source file hashes,
coverage, complete independent SQL parity and committed all-row DB readback.
Does not change the active research program or old Gold/legacy factors.
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pandas as pd

from engine import reference_gold as gold, reference_library as base
from engine import reference_profit_growth as lib, reference_financial_inputs as financial, reference_library_v2
from engine.reference_db import connect
from engine.reference_profit_growth_parity import validate_parity
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_input, load_json, save_json, sha, legacy_metadata_digest


def prepare_input(source):
    source = Path(source)
    identity, _ = load_input(source)
    evidence = load_json(source / "source-evidence.json")
    features_path = source / "financial-features.parquet"
    if sha(features_path) != evidence["financial_features_file_sha256"]:
        raise ValueError("Financial feature capture bytes changed")
    manifest = financial.verify_capture(evidence["financial_source"])
    if manifest["manifest_sha256"] != evidence["financial_evidence"]["extraction_manifest_sha256"]:
        raise ValueError("Financial ledger evidence mismatch")
    features = pd.read_parquet(features_path)
    features.asset_id = features.asset_id.astype(str)
    panel = identity[list(base._BASE)].merge(features[["asset_id", "date", *lib.FEATURES]],
                on=["asset_id", "date"], how="left", validate="one_to_one")
    panel = lib.prepare(panel)
    source_evidence = dict(schema_version="profit-growth-source-v1", parent_evidence_sha256=digest(evidence),
        parent_source_path=str(source.resolve()), financial_features_sha256=sha(features_path),
        financial_manifest_sha256=manifest["manifest_sha256"], source_contract=lib.SOURCE_CONTRACT,
        first_vintage_independently_verified=False, pit_status=lib.PIT_STATUS,
        legacy_gold_used=False, forward_labels_read=False)
    attestation = dict(status="CERTIFIED", source_type=lib.SOURCE_TYPE, source_contract=lib.SOURCE_CONTRACT,
        scope=base.INPUT_SCOPE, identity_contract=base.IDENTITY_CONTRACT, pit_status=lib.PIT_STATUS,
        first_vintage_independently_verified=False, evidence_sha256=digest(source_evidence),
        source_version=digest(source_evidence), input_sha256=lib.input_digest(panel))
    return panel, attestation, source_evidence


def run(source, output, *, apply=False, reference_ids=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    refs = sorted(reference_ids or lib.SPECS)
    if len(refs) != len(set(refs)) or not set(refs) <= set(lib.SPECS):
        raise ValueError("Explicit unique supported references required")
    panel, attestation, evidence = prepare_input(source)
    selected = [d for d in lib.definitions() if d["id"] in refs]
    old = base.load_catalog(reference_library_v2.CATALOG_PATH)
    if set(refs) & {d["id"] for d in old}:
        raise ValueError("Existing reference identifier reused")
    frames, summaries = [], []
    for definition in selected:
        p, raw = lib.calculate(panel, definition["id"])
        valid = raw.notna()
        values = p.loc[valid, list(base._BASE)].copy()
        values["reference_id"] = definition["id"]
        values["value"] = raw[valid]
        values["oriented_value"] = raw[valid] * definition["orientation"]
        values["definition_hash"] = base.definition_hash(definition)
        values["source_version"] = attestation["source_version"]
        values["input_sha256"] = attestation["input_sha256"]
        values = values.loc[:, base._OUTPUT].sort_values(["reference_id", "asset_id", "date"]).reset_index(drop=True)
        assets, months = values.asset_id.nunique(), values.date.nunique()
        if assets < 100 or months < 60:
            raise ValueError("Insufficient coverage; no automatic threshold reduction")
        summary = dict(reference_id=definition["id"], definition_hash=base.definition_hash(definition),
            status="MEASUREMENT_VALIDATED", input_rows=len(panel), value_rows=len(values),
            assets=int(assets), months=int(months), first_date=str(values.date.min().date()),
            last_date=str(values.date.max().date()), input_coverage_fraction=float(valid.mean()))
        summaries.append(summary)
        frames.append(values)
        print(summary, flush=True)
    values = pd.concat(frames, ignore_index=True)
    validation = dict(source_version=attestation["source_version"], input_sha256=attestation["input_sha256"],
        source_evidence_sha256=attestation["evidence_sha256"], implementation_sha256=lib.implementation_hash(),
        role="MEASUREMENT_CONTROL", alpha_approved=False, value_rows=len(values), references=summaries)
    with connect(read_only=False) as conn:
        before = legacy_metadata_digest(conn)
        parity = validate_parity(panel, values, conn)
        publication, rows = gold.build_publication(values, selected, attestation=attestation,
                                                   validation=validation, parity=parity)
        save_json(output / "source-evidence.json", evidence)
        save_json(output / "input-attestation.json", attestation)
        save_json(output / "publication.json", publication)
        path = output / "values.parquet"
        if path.exists():
            pd.testing.assert_frame_equal(pd.read_parquet(path), values, check_exact=True)
        else:
            values.to_parquet(path, index=False)
        receipt = gold.publish(conn, publication, rows, apply=apply)
        after = legacy_metadata_digest(conn)
        if before != after:
            raise ValueError("Legacy metadata changed; rollback required")
    receipt.update(outer_transaction_committed=apply, legacy_metadata_before=before, legacy_metadata_after=after)
    save_json(output / ("receipt-applied.json" if apply else "receipt-dry-run.json"), receipt)
    if apply:
        with connect() as conn:
            readback, metadata = gold.load_library(conn, dataset_id=publication["dataset_id"], snapshot_path=path)
            if metadata != publication or len(readback) != len(values):
                raise ValueError("Committed readback mismatch")
        save_json(output / "committed-verification.json", dict(dataset_id=publication["dataset_id"],
            rows=len(readback), reference_ids=refs, passed=True, profitability_approved=False))
    print(receipt, flush=True)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", action="append")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(args.source, args.output, apply=args.apply, reference_ids=args.reference)
