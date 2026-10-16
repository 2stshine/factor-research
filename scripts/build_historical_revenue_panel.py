"""Build a new inactive panel from certified, bounded original-document revenue.

No old cache activation, source-table write, candidate evaluation or Gold access.
The price/return frame is preserved byte-for-value. Only declared financial
inputs are replaced, with separate base and document-source provenance.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import pickle

import pandas as pd

from engine import fundamental_contract as fc, fundamentals
from engine import historical_fundamental_overlay as overlay
from engine.research_memory_transfer import write_artifact
from scripts.repair_fundamental_panel import _load_rows, file_sha, task_connection

ROOT = Path(__file__).resolve().parents[1]


def replace_financials(parent, base_rows, bundle):
    parent_binding = fc.verify(parent, require_financial=True)
    if fc.META_KEY not in parent.meta:
        raise ValueError("Use a legacy base panel, never stack document overlays implicitly")
    base_ledger = fc._ledger(base_rows)
    if base_ledger != parent.meta[fc.META_KEY]["ledger"]:
        # Equal attached values are not source identity: unavailable quarters
        # can hide a changed amount behind the same NaN. Fail closed even for
        # encoding-only differences; those need an explicit parent rebind.
        raise ValueError("Supplied base ledger does not reproduce the exact parent source ledger")
    features = sorted(fundamentals.PIT_FEATURES)
    base_replay = fc.materialize(base_rows, verbose=False)
    original_inputs = parent.monthly.drop(columns=[*features, "available_date"], errors="ignore")
    expected_parent = fundamentals.attach(original_inputs, base_replay, features)
    if fc._financial_digest(expected_parent, features) != fc._financial_digest(parent.monthly, features):
        raise ValueError("Supplied base ledger does not reproduce parent financial inputs")
    dropped_signals = sorted(c for c in parent.monthly if c.startswith("f_"))
    protected_columns = sorted(set(parent.monthly.columns) - set(features) - {"available_date"} - set(dropped_signals))
    protected = parent.monthly[protected_columns].copy(deep=True)
    frame = overlay.materialize(base_rows, bundle, verbose=True)
    result = deepcopy(parent)
    result.monthly = fundamentals.attach(protected, frame, sorted(fundamentals.PIT_FEATURES))
    # Compare identical stock-month keys rather than relying on merge row order.
    sort = ["asset_id", "ym"]
    pd.testing.assert_frame_equal(protected.sort_values(sort).reset_index(drop=True),
        result.monthly[protected_columns].sort_values(sort).reset_index(drop=True), check_flags=False)
    non_revenue = ["asset_id", "ym", *sorted(set(features) - {"revenue", "revenue_ttm"})]
    pd.testing.assert_frame_equal(parent.monthly[non_revenue].sort_values(sort).reset_index(drop=True),
        result.monthly[non_revenue].sort_values(sort).reset_index(drop=True), check_flags=False)
    result.meta.pop(fc.META_KEY, None)
    overlay.bind(result, base_rows, bundle, materialized=frame)
    result.meta["historical_overlay_parent_reconciliation"] = {
        "parent_financial_contract_sha256": parent_binding["contract_sha256"],
        "parent_original_ledger_sha256": parent.meta[fc.META_KEY]["ledger"]["ledger_sha256"],
        "supplied_normalized_ledger_sha256": base_ledger["ledger_sha256"],
        "base_financial_frame_replay_equal": True,
        "non_revenue_features_equal": True, "dropped_precomputed_signals": dropped_signals,
        "raw_ledger_encoding_identity_claim": True,
    }
    fc.verify(result, require_financial=True)
    return result


def build(parent_path, ledger_directory, dataset_version, destination, *, profile=None):
    parent_path, ledger_directory, destination = map(Path, (parent_path, ledger_directory, destination))
    destination = destination.absolute()
    if (destination.exists() or destination.is_symlink() or destination.parent != ROOT / ".cache"
            or any(p.is_symlink() for p in destination.parents)):
        raise ValueError("Use a new direct child of repository .cache")
    before = file_sha(parent_path)
    with parent_path.open("rb") as stream:
        parent = pickle.load(stream)
    fc.verify(parent, require_financial=True)
    rows, source_receipt = _load_rows(ledger_directory)
    with task_connection(profile) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT run_id::text,status FROM public.dq_run WHERE run_id=ANY(%s::uuid[])",
                        (source_receipt["quality_run_ids"],))
            statuses = dict(cur.fetchall())
            if statuses != {run: "CERTIFIED" for run in source_receipt["quality_run_ids"]}:
                raise ValueError("Base financial source DQ certification changed")
        bundle = overlay.read_bundle(conn, dataset_version)
    result = replace_financials(parent, rows, bundle)
    if before != file_sha(parent_path):
        raise ValueError("Parent changed during isolated rebuild")
    destination.mkdir()
    write_artifact(destination / "source-bundle.json", bundle)
    target = destination / "panel.pkl"
    with target.open("xb") as stream:
        pickle.dump(result, stream)
        stream.flush()
        os.fsync(stream.fileno())
    with target.open("rb") as stream:
        verified = fc.verify(pickle.load(stream), require_financial=True)
    receipt = dict(schema_version="historical-revenue-isolated-panel-build-v1",
        completed_at=datetime.now(timezone.utc).isoformat(), status="LOCAL_REPLAY_VERIFIED_LIVE_PRICE_REAUDIT_PENDING",
        parent_path=str(parent_path.resolve()), parent_sha256=before, parent_unchanged=True,
        base_ledger_directory=str(ledger_directory.resolve()), base_ledger_parquet_sha256=source_receipt["parquet_sha256"],
        base_financial_quality_run_statuses=statuses, source_dataset=dataset_version,
        source_bundle_sha256=file_sha(destination / "source-bundle.json"), panel_sha256=file_sha(target),
        financial_contract=verified, historical_backfill_applied=True, price_and_label_values_unchanged=True,
        base_source_first_vintage_independently_verified=False, document_source_certification="BOUNDED_INCLUDED_ROWS_ONLY",
        default_cache_changed=False, activated=False, candidate_evaluations=0, oos_inspections=0, gold_writes=0)
    write_artifact(destination / "build-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ("parent", "ledger-directory", "destination"):
        p.add_argument("--" + flag, type=Path, required=True)
    p.add_argument("--dataset-version", required=True)
    p.add_argument("--aws-cli-profile")
    a = p.parse_args()
    build(a.parent, a.ledger_directory, a.dataset_version, a.destination, profile=a.aws_cli_profile)
