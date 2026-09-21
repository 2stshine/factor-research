"""Inspect Bronze readiness without reading factor results or granting PIT approval."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from engine.regime_inputs import PIT_FLAGS


def audit_bronze(paths):
    sources = []
    for path in paths:
        path = Path(path).resolve()
        body = path.read_bytes()
        report = json.loads(body)
        if report.get("status") != "passed" or not isinstance(report.get("rows_by_series"), dict):
            raise ValueError("Expected a completed Bronze verification report")
        rows = report["rows_by_series"]
        if sum(rows.values()) != report.get("rows", report.get("selected_row_count")):
            raise ValueError("Bronze verification counts disagree")
        sources.append({
            "verification_file": str(path), "verification_sha256": hashlib.sha256(body).hexdigest(),
            "manifest_uri": report["manifest_uri"], "bronze_rows": sum(rows.values()),
            "series_count": len(rows), "series": sorted(rows),
            "status": "BLOCKED_PENDING_PIT_AND_REGIME_BINDING",
            "pit_flags": {k: report.get(k) for k in PIT_FLAGS},
            "block_reasons": [k.upper() + "_NOT_VERIFIED" for k in PIT_FLAGS if report.get(k) is not True]
                             + ["NO_BOUND_SILVER_REGIME_APPROVAL"],
        })
    return {"schema_version": "bronze-regime-readiness-v1",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "mode": "LOCAL_VERIFICATION_REPORTS_NOT_LIVE_S3_RECHECK",
            "sources": sources, "bronze_series": sum(x["series_count"] for x in sources),
            "bronze_rows": sum(x["bronze_rows"] for x in sources),
            "approved_regime_series": 0, "factor_evaluation_executed": False,
            "oos_accessed": False, "pit_approval_granted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bronze-verification", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_bronze(args.bronze_verification)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({k: report[k] for k in ("bronze_series", "bronze_rows", "approved_regime_series")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
