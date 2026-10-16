"""Versioned, non-publishing financial-input repair and audit.

Fetches only the certified financial revision ledger, not returns or Gold.
Old panels and campaigns are never edited. CLI credentials are optional and
stay in process memory; this supports an already-authenticated AWS CLI session.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import types

import numpy as np
import pandas as pd

from engine import fundamentals, fundamental_contract, panel as panel_engine, silver
from engine.research_memory_transfer import write_artifact

ROOT = Path(__file__).resolve().parents[1]
LEGACY_SOURCE_SHA256 = "75688eb83726135e574fbbefe9653e791e2192ac35edc4c4d0cc3590c7336111"


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def task_connection(profile=None):
    """Use existing authorized credentials without logging or persisting them."""
    if not profile:
        with silver.connect(read_only=True) as conn:
            yield conn
        return
    silver._load_environment()
    secret_id = os.environ.get("SILVER_DB_SECRET_ID")
    if not secret_id:
        raise ValueError("SILVER_DB_SECRET_ID is required for AWS CLI authentication")
    result = subprocess.run([
        "aws", "secretsmanager", "get-secret-value", "--profile", profile,
        "--secret-id", secret_id, "--query", "SecretString", "--output", "text",
    ], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("Configured Secrets Manager read failed; credentials not logged")
    url = json.loads(result.stdout)["SILVER_DB_URL"]
    original = silver.database_url
    try:
        silver.database_url = lambda: url
        with silver.connect(read_only=True) as conn:
            yield conn
    finally:
        silver.database_url = original


def fetch(destination, *, profile=None, timeout_seconds=600):
    destination = Path(destination).absolute()
    cache = ROOT / ".cache"
    if cache.is_symlink() or destination.parent != cache or destination.exists():
        raise ValueError("Use a new direct child directory of the nonsymlink repository .cache")
    destination.mkdir()
    started = datetime.now(timezone.utc).isoformat()
    with task_connection(profile) as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW transaction_read_only")
            if cur.fetchone()[0] != "on":
                raise ValueError("Financial extraction requires a read-only transaction")
            cur.execute("SHOW transaction_isolation")
            isolation = cur.fetchone()[0]
            if isolation != "repeatable read":
                raise ValueError("Financial extraction requires repeatable-read isolation")
            if not 30 <= timeout_seconds <= 900:
                raise ValueError("Read-only extraction timeout must be 30..900 seconds")
            cur.execute("SELECT set_config('statement_timeout', %s, true)", (f"{timeout_seconds}s",))
        rows = silver.load_fundamentals(conn, sorted(fundamentals.ALL_METRICS))
    # Preserve exact numeric text and revision identifiers; no rounding or fill.
    for column in ("asset_id",):
        rows[column] = pd.to_numeric(rows[column], errors="raise").astype("int64")
    for column in ("value", "quality_run_id", "revision_key"):
        rows[column] = rows[column].map(lambda value: None if pd.isna(value) else str(value))
    for column in ("period_end", "available_date"):
        rows[column] = pd.to_datetime(rows[column], errors="raise")
    rows["available_at"] = pd.to_datetime(rows["available_at"], errors="raise", utc=True)
    path = destination / "certified-financial-rows.parquet"
    rows.to_parquet(path, index=False)
    receipt = {
        "schema_version": "certified-financial-ledger-extract-v1",
        "started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
        "source": "RDS public.fundamental with certified DART filter",
        "query_sha256": hashlib.sha256(silver.FUNDAMENTAL_SQL.encode()).hexdigest(),
        "query": silver.FUNDAMENTAL_SQL, "metrics": sorted(fundamentals.ALL_METRICS),
        "row_count": len(rows), "asset_count": rows.asset_id.nunique(),
        "quality_run_ids": sorted(rows.quality_run_id.dropna().unique().tolist()),
        "parquet_sha256": file_sha(path), "storage_numeric_representation": "exact decimal text",
        "read_only": True, "isolation": isolation.upper().replace(" ", "_"),
        "historical_original_filing_values_verified_by_this_extraction": False,
        "return_evaluations": 0, "oos_reads": 0, "gold_writes": 0,
    }
    write_artifact(destination / "source-receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("row_count", "asset_count", "parquet_sha256")}, indent=2))
    print("Saved certified ledger:", destination)


def _load_rows(directory):
    receipt = json.loads((directory / "source-receipt.json").read_text())
    path = directory / "certified-financial-rows.parquet"
    if (receipt.get("schema_version") != "certified-financial-ledger-extract-v1"
            or file_sha(path) != receipt.get("parquet_sha256")
            or receipt.get("read_only") is not True
            or receipt.get("isolation") != "REPEATABLE_READ"
            or receipt.get("query_sha256") != hashlib.sha256(silver.FUNDAMENTAL_SQL.encode()).hexdigest()
            or receipt.get("query") != silver.FUNDAMENTAL_SQL
            or receipt.get("metrics") != sorted(fundamentals.ALL_METRICS)):
        raise ValueError("Certified ledger extraction binding changed")
    rows = pd.read_parquet(path)
    if (len(rows) != receipt.get("row_count")
            or int(rows.asset_id.nunique()) != receipt.get("asset_count")
            or rows.quality_run_id.isna().any()
            or sorted(rows.quality_run_id.astype(str).unique()) != receipt.get("quality_run_ids")):
        raise ValueError("Certified ledger row/asset/quality-run provenance changed")
    return rows, receipt


def _legacy_materializer():
    # The exact previously audited repository-owned implementation is evidence,
    # not arbitrary external Python. A different Git version is never accepted.
    body = subprocess.check_output(["git", "show", "HEAD:engine/fundamentals.py"], cwd=ROOT)
    if hashlib.sha256(body).hexdigest() != LEGACY_SOURCE_SHA256:
        raise ValueError("Legacy implementation differs; explicitly review a new audit baseline")
    module = types.ModuleType("legacy_fundamentals_for_input_audit")
    module.__file__ = str(ROOT / "engine/fundamentals.py")
    exec(compile(body, "audited-legacy-fundamentals", "exec"), module.__dict__)
    return module


def _ordered(frame):
    return frame.sort_values(["asset_id", "ym"], kind="mergesort").reset_index(drop=True)


def compare_financial_inputs(before, after, *, end_month="2023-06"):
    """Input-only change counts. Never read forward-return or Gold columns."""
    keys = ["asset_id", "ym"]
    pd.testing.assert_frame_equal(_ordered(before[keys]), _ordered(after[keys]))
    start, end = pd.Period("2015-01", freq="M"), pd.Period(end_month, freq="M")
    if end < start:
        raise ValueError("Financial input audit end precedes its start")
    columns = [*keys, *sorted(fundamentals.PIT_FEATURES)]
    # Select declared financial observations before numeric comparisons; labels
    # and financial values beyond this audit window never enter the calculation.
    left = _ordered(before.loc[before.ym.between(start, end), columns])
    right = _ordered(after.loc[after.ym.between(start, end), columns])
    results = []
    for field in sorted(fundamentals.PIT_FEATURES):
        a, b = pd.to_numeric(left[field], errors="coerce"), pd.to_numeric(right[field], errors="coerce")
        same = np.isclose(a, b, equal_nan=True, rtol=1e-12, atol=1e-8)
        changed = ~same
        results.append({
            "field": field, "rows_in_scope": len(right), "changed_rows": int(changed.sum()),
            "assets_with_changes": int(right.loc[changed, "asset_id"].nunique()),
            "finite_to_missing": int((a.notna() & b.isna()).sum()),
            "missing_to_finite": int((a.isna() & b.notna()).sum()),
            "both_finite_changed": int((changed & a.notna() & b.notna()).sum()),
        })
    return results


def rebuild(directory, parent_path, *, audit_end_month="2023-06"):
    directory, parent_path = Path(directory).resolve(), Path(parent_path).resolve()
    if directory.parent != (ROOT / ".cache").resolve() or directory == parent_path.parent:
        raise ValueError("Use a separate direct cache child; never replace the parent panel")
    for name in ("panel.pkl", "build-receipt.json", "input-change-audit.json", "materialized-v2.pkl"):
        if (directory / name).exists():
            raise ValueError(f"Refusing to replace repair output: {name}")
    rows, source_receipt = _load_rows(directory)
    before_sha = file_sha(parent_path)
    with parent_path.open("rb") as stream:
        parent = pickle.load(stream)
    # Deliberately do not _load the old cache as an execution panel. Only its
    # authenticated nonfinancial inputs/labels are reused; financials replay.
    panel_engine.verify_return_roles(parent)
    panel_engine.verify_asset_identity(parent)
    silver.verify_total_return_validation_evidence(parent.meta.get("return_contract_validation_evidence"))
    features = sorted(fundamentals.PIT_FEATURES)
    excluded = set(features) | {"available_date", "me_date"}
    excluded.update(column for column in parent.monthly if str(column).startswith("f_"))
    base = parent.monthly.drop(columns=list(excluded), errors="ignore").copy()
    started = datetime.now(timezone.utc).isoformat()
    print("Replaying certified financial ledger with contiguous-quarter v2...", flush=True)
    fund = fundamental_contract.materialize(rows)
    with (directory / "materialized-v2.pkl").open("xb") as stream:
        pickle.dump(fund, stream)
    monthly = fundamentals.attach(base, fund, features)
    monthly = monthly.sort_values(["Code", "ym"]).reset_index(drop=True)
    new_panel = panel_engine.Panel(monthly=monthly, dead=parent.dead.copy(), meta=dict(parent.meta))
    new_panel.meta.pop(fundamental_contract.META_KEY, None)
    fundamental_contract.bind(new_panel, rows, materialized=fund)
    fundamental_contract.verify(new_panel, require_financial=True)
    panel_engine.verify_return_roles(new_panel)
    panel_engine.verify_asset_identity(new_panel)
    pd.testing.assert_frame_equal(_ordered(base), _ordered(monthly[base.columns]))
    print("Replaying exact old implementation against the same ledger for input-only attribution...", flush=True)
    legacy = _legacy_materializer().materialize_pit(rows, verbose=False)
    legacy_monthly = fundamentals.attach(base, legacy, features)
    changes = compare_financial_inputs(legacy_monthly, monthly, end_month=audit_end_month)
    actual_dates = rows.loc[rows.metric.eq("revenue"), ["period_end", "fiscal_period", "available_date"]].copy()
    history = actual_dates.groupby([actual_dates.period_end.dt.year.rename("year"), "fiscal_period"]).size()
    audit = {
        "schema_version": "same-ledger-financial-methodology-input-audit-v1",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "audit_start_month": "2015-01", "audit_end_month": audit_end_month,
        "old_materializer_sha256": LEGACY_SOURCE_SHA256,
        "new_methodology": fundamentals.FUNDAMENTAL_METHODOLOGY_VERSION,
        "new_materializer_sha256": fundamentals.source_sha256(),
        "source_parquet_sha256": source_receipt["parquet_sha256"],
        "changes": changes,
        "revenue_source_year_period_counts": [
            {"year": int(year), "fiscal_period": period, "rows": int(count)}
            for (year, period), count in history.items()],
        "historical_backfill_applied": False,
        "return_evaluations": 0, "oos_performance_evaluations": 0,
        "oos_performance_inspections": 0, "gold_writes": 0,
        "full_parent_bytes_loaded_for_preservation": True,
        "interpretation": "Same certified ledger, changed materialization only; not independent original-filing PIT verification",
    }
    if file_sha(parent_path) != before_sha:
        raise ValueError("Parent panel changed during rebuild; do not activate this result")
    output = directory / "panel.pkl"
    with output.open("xb") as stream:
        pickle.dump(new_panel, stream)
        stream.flush()
        os.fsync(stream.fileno())
    with output.open("rb") as stream:
        fundamental_contract.verify(pickle.load(stream), require_financial=True)
    write_artifact(directory / "input-change-audit.json", audit)
    receipt = {
        "schema_version": "isolated-financial-panel-rebuild-v1", "started_at": started,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "parent_path": str(parent_path), "parent_sha256": before_sha, "parent_unchanged": True,
        "panel_sha256": file_sha(output), "financial_contract_sha256": new_panel.meta[fundamental_contract.META_KEY]["sha256"],
        "source_receipt_sha256": file_sha(directory / "source-receipt.json"),
        "status": "LOCAL_REPLAY_VERIFIED_LIVE_PRICE_IDENTITY_RECHECK_PENDING",
        "default_cache_changed": False, "activated": False, "historical_backfill_applied": False,
        "real_factor_trials": 0, "oos_reveal": False, "gold_write": False,
        "oos_performance_evaluations": 0, "oos_performance_inspections": 0,
        "full_parent_bytes_loaded_for_preservation": True,
    }
    write_artifact(directory / "build-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    print("Changed inputs:", json.dumps([row for row in changes if row["changed_rows"]], ensure_ascii=False))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("fetch")
    command.add_argument("--destination", type=Path, required=True)
    command.add_argument("--aws-cli-profile")
    command.add_argument("--timeout-seconds", type=int, default=600)
    command = commands.add_parser("rebuild")
    command.add_argument("--directory", type=Path, required=True)
    command.add_argument("--parent-panel", type=Path, required=True)
    command.add_argument("--audit-end-month", default="2023-06")
    args = parser.parse_args()
    if args.command == "fetch":
        fetch(args.destination, profile=args.aws_cli_profile, timeout_seconds=args.timeout_seconds)
    elif args.command == "rebuild":
        rebuild(args.directory, args.parent_panel, audit_end_month=args.audit_end_month)


if __name__ == "__main__":
    main()
