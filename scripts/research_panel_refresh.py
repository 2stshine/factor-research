"""Explicit separate-cache refresh using a parity-checked deferred identity query.

Does not edit the production SQL or the default cache, evaluate factors, reveal
OOS or publish Gold. This optional path requires a dedicated process; it does not
replace an already-running build. SQL and environment overrides are restored.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from engine import silver
from engine.research_panel_query import deferred_identity_sql
from scripts.research_panel_query_parity import validate_parity_record

ROOT = Path(__file__).resolve().parents[1]


def refresh(cache_dir: Path, parity_record: Path, *, runner=None):
    requested_root = ROOT / ".cache"
    if requested_root.is_symlink() or cache_dir.absolute().parent != requested_root.absolute():
        raise ValueError("Use a direct child of the repository's nonsymlink .cache directory")
    if cache_dir.exists() or cache_dir.is_symlink():
        raise ValueError("Cache destination must not exist or be a symlink")
    cache_dir = cache_dir.resolve()
    cache_root = (ROOT / ".cache").resolve()
    if cache_dir.parent != cache_root or cache_dir == cache_root or cache_dir.exists():
        raise ValueError("Use a new direct child directory under this repository's .cache")
    original = silver.PRICE_SNAPSHOT_SQL
    optimized = deferred_identity_sql(original)
    evidence_bytes = parity_record.read_bytes()
    evidence = json.loads(evidence_bytes)
    validate_parity_record(evidence, original, optimized)
    contract = {
        "schema_version": "separate-panel-query-refresh-v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cache_dir": str(cache_dir), "default_cache_changed": False,
        "parity_record": str(parity_record.resolve()),
        "parity_record_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        "original_sql": original, "optimized_sql": optimized,
        "original_query_sha256": evidence["original_query_sha256"],
        "optimized_query_sha256": evidence["optimized_query_sha256"],
        "parity_scope": "EXPLICIT_COHORT_ONLY",
        "parity_record_validation": "INTERNAL_CONSISTENCY_ONLY_NOT_SOURCE_AUTHENTICATION",
        "execution_mode": "EXPLICIT_OPTIONAL_SEPARATE_CACHE",
        "no_general_speed_claim": True,
        "real_factor_trials": 0, "oos_reveal": False, "gold_write": False,
    }
    environment = {key: os.environ.get(key) for key in ("CACHE_DIR", "RESEARCH_TIMING_LOG")}
    try:
        os.environ["CACHE_DIR"] = str(cache_dir)
        os.environ["RESEARCH_TIMING_LOG"] = str(cache_dir / "research-timings.jsonl")
        if runner is None:
            from scripts import run
        else:
            run = runner
        paths = {"CACHE": cache_dir, "PANEL_CACHE": cache_dir / "panel.pkl",
                 "PANEL_ARCHIVE": cache_dir / "panels", "TRIAL_DB": cache_dir / "trials.sqlite3",
                 "PARITY_CHECKPOINT_ROOT": cache_dir / "implementation-parity-checkpoints",
                 "GOLD_SIGNAL_CACHE_ROOT": cache_dir / "gold-signals"}
        for name, expected in paths.items():
            actual = getattr(run, name, None)
            if actual is None or Path(actual).resolve() != expected:
                raise ValueError(f"Runner {name} is not bound to the separate cache")
        cache_dir.mkdir()
        with (cache_dir / "input-query-contract.json").open("x") as stream:
            json.dump(contract, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        silver.PRICE_SNAPSHOT_SQL = optimized
        run.cmd_build(None)
    finally:
        silver.PRICE_SNAPSHOT_SQL = original
        for key, value in environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    receipt = {"schema_version": "separate-panel-build-receipt-v1",
               "completed_at": datetime.now(timezone.utc).isoformat(),
               "panel_sha256": run._file_sha256(cache_dir / "panel.pkl"),
               "status": "BUILD_COMPLETED_IDENTITY_REAUDIT_PENDING",
               "default_cache_changed": False, "real_factor_trials": 0,
               "oos_reveal": False, "gold_write": False}
    with (cache_dir / "build-receipt.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps(receipt))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--parity-record", type=Path, required=True)
    args = parser.parse_args()
    refresh(args.cache_dir, args.parity_record)
