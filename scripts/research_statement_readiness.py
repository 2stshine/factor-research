"""Bounded read-only DART FY pairing probe for an explicit asset cohort.

Not a market-wide coverage result, source PIT certification or factor run.
No return columns, campaign results, OOS, current-profile backfills or writes
to RDS are used. The supplied cohort, fiscal year and as-of are explicit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from engine import silver
from engine.research_statement_evidence import pair_annual_cfo_assets

SQL = """
SELECT asset_id, source, filing_id, report_code, business_year, period_end,
       fiscal_period, fs_type, statement_type, account_id, account_name,
       current_amount, current_cumulative_amount, current_period_label,
       currency, filed, available_at, revision_key, line_key, quality_run_id,
       metric, mapping_version, metric_candidate_count
FROM public.dart_standardized_statement_line
WHERE asset_id = ANY(%s) AND business_year = %s AND fiscal_period = 'FY'
  AND source = 'DART' AND available_at <= %s
ORDER BY asset_id, available_at, revision_key, filing_id, fs_type, line_key
"""


def body(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str,
                      separators=(",", ":"), allow_nan=False).encode()


def probe(*, asset_ids, business_year, as_of, scope_ref, output, connect=None):
    if output.exists():
        raise FileExistsError(output)
    # Validate inputs before any source access. Empty cohort is intentionally
    # not a completed study and oversized cohort requires a separate workflow.
    if not asset_ids or len(asset_ids) > 100:
        raise ValueError("Specify 1..100 asset IDs; this is a bounded cohort probe")
    pair_annual_cfo_assets([], business_year=business_year, as_of=as_of,
                          eligible_asset_ids=asset_ids, scope_ref=scope_ref)
    connect = connect or silver.connect
    with connect(read_only=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = 15000")
            cur.execute("SHOW transaction_read_only")
            if cur.fetchone()[0] != "on":
                raise ValueError("Read-only source transaction required")
            cur.execute("SELECT pg_get_viewdef('public.dart_standardized_statement_line'::regclass, true)")
            view_definition = cur.fetchone()[0]
            cur.execute(SQL, (asset_ids, business_year, as_of))
            columns = [column.name for column in cur.description]
            rows = cur.fetchmany(20001)
            if len(rows) > 20000:
                raise ValueError("Bounded cohort row limit exceeded")
            records = [dict(zip(columns, row)) for row in rows]
    paired = pair_annual_cfo_assets(records, business_year=business_year, as_of=as_of,
                                   eligible_asset_ids=asset_ids, scope_ref=scope_ref)
    bridge_path = Path(__file__).resolve().parents[1] / "engine/research_statement_evidence.py"
    payload = {
        "schema_version": "dart-fy-cohort-probe-v2", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": "EXECUTED_READ_ONLY_COHORT_PROBE", "scope_ref": scope_ref,
        "research_stage": "INPUT_CONNECTION_NOT_FACTOR_EVALUATION",
        "real_factor_trials": 0, "sealed_results_accessed": False, "gold_write": False,
        "source_extraction": {"relation": "public.dart_standardized_statement_line", "read_only": True,
            "row_count": len(records), "asset_ids": asset_ids,
            "business_year": business_year, "as_of": as_of,
            "query_sha256": hashlib.sha256(SQL.encode()).hexdigest(),
            "query_definition": SQL,
            "view_definition": view_definition,
            "view_definition_sha256": hashlib.sha256(view_definition.encode()).hexdigest(),
            "rows_sha256": hashlib.sha256(body(records)).hexdigest(),
            "query_includes_all_standardized_metrics": True,
            "certified_dq_filter": "EXPECTED_SOURCE_CONTRACT_NOT_INDEPENDENTLY_VERIFIED",
            "unmapped_filing_completeness_verified": False},
        "limitations": ["Explicit asset cohort, not KRX-universe coverage.",
                        "Certified DQ filtering is an expected source contract, not independently verified by this probe; exact view definition is retained for review.",
                        "This probe does not certify source vintages, unit scale or completeness of certification lineage.",
                        "Wholly unmapped newer filings are invisible to the standardized view.",
                        "No economic outcome, factor returns, industry control or trading execution evaluated."],
        "evidence": paired,
        "source_rows": json.loads(body(records)),
        "compiler_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "bridge_sha256": hashlib.sha256(bridge_path.read_bytes()).hexdigest(),
        "source_snapshot": {"scripts/research_statement_readiness.py": Path(__file__).read_text(),
                            "engine/research_statement_evidence.py": bridge_path.read_text()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(body(payload) + b"\n")
    return {"status": payload["status"], "rows": len(records), "coverage": paired["coverage"],
            "output": str(output), "factor_evaluated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-ids", nargs="+", type=int, required=True)
    parser.add_argument("--business-year", type=int, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--scope-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = probe(asset_ids=args.asset_ids, business_year=args.business_year, as_of=args.as_of,
                   scope_ref=args.scope_ref, output=args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
