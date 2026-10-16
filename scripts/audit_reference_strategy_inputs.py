"""Read-only readiness evidence for the current reference strategy evaluation.

Never read legacy factor performance, assume an absent event means no event,
promote BUILDING contracts, or substitute close returns for next-open returns.
"""
import argparse
from pathlib import Path

from engine.reference_db import connect
from engine.phenomenon_reference_collection import read_collection_program
from engine.research_generation import digest
from scripts.publish_reference_expansion import save_json, sha

ROOT = Path(__file__).resolve().parents[1]
QUERIES = {
    "contracts": """SELECT source,asset_type,field_name,methodology_version,
        dividend_treatment,status,coverage_start,coverage_end,certified_at,updated_at,
        metadata->>'invalidated_reason' AS invalidated_reason,
        metadata->>'invalidated_at' AS invalidated_at,
        metadata->'research_role' AS research_role
        FROM public.price_return_contract ORDER BY source,asset_type,field_name""",
    "index_assets": """SELECT asset_id,name,asset_type,exchange FROM public.asset
        WHERE asset_type='index' OR name ILIKE '%총수익%' OR name ILIKE '%total return%'
        ORDER BY asset_id""",
    "related_tables": """SELECT table_schema,table_name FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema','pg_catalog') AND
        table_name ~* '(price|return|calendar|session|index|corporate|dividend|listing)'
        ORDER BY table_schema,table_name""",
}


def audit(output):
    from psycopg.rows import dict_row
    program, _, _ = read_collection_program(ROOT)
    result = {}
    with connect() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SET LOCAL statement_timeout='30s'")
        cur.execute("SHOW transaction_read_only")
        if cur.fetchone()["transaction_read_only"] != "on":
            raise ValueError("Read-only source audit required")
        cur.execute("SELECT transaction_timestamp() AS observed_at")
        observed = cur.fetchone()["observed_at"].isoformat()
        for name, query in QUERIES.items():
            cur.execute(query)
            result[name] = [{k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in r.items()} for r in cur.fetchall()]
    krx = [r for r in result["contracts"] if r["source"] == "KRX" and r["asset_type"] == "stock"]
    contracts = {r["field_name"]: r for r in krx}
    close = contracts.get("total_return_close")
    blockers = []
    if not close or close["status"] != "CERTIFIED":
        blockers.append({"code": "KRX_CLOSE_TR_NOT_CERTIFIED", "status": close["status"] if close else "ABSENT",
                         "reason": close.get("invalidated_reason") if close else None,
                         "note": "Close TR would not by itself satisfy the required open-to-open contract."})
    if "total_return_open" not in contracts:
        blockers.append({"code": "NO_REGISTERED_KRX_OPEN_TR_CONTRACT",
                         "note": "Raw open prices require a separately reviewed corporate-action/share-path adapter."})
    if not any("calendar" in r["table_name"] or "session" in r["table_name"] for r in result["related_tables"]):
        blockers.append({"code": "NO_DEDICATED_CALENDAR_OR_SESSION_TABLE_FOUND",
                         "note": "Does not prove there is no usable official calendar in external files."})
    # The exact public registry is reported, not a claim about every Bronze file.
    blockers.append({"code": "REVIEWED_EXECUTION_BUNDLE_REQUIRED",
                     "note": "Need exact source files for historical universe/cap, first opens, asset and market TR; metadata is insufficient."})
    payload = {"schema": "reference-strategy-live-input-audit-v1", "observed_at": observed,
               "program_sha256": program["program_sha256"], "reference_count": sum(len(d["reference_ids"]) for d in program["reference_datasets"]),
               "read_only": True, "returns_or_factor_values_read": False, "performance_computed": False,
               "queries": QUERIES, "query_sha256": digest(QUERIES), "code_sha256": sha(__file__),
               "source_metadata": result, "blockers": blockers,
               "status": "INPUT_REPAIR_AND_EXECUTION_ADAPTER_REQUIRED",
               "scope": "CURRENT_RDS_REGISTRY_NOT_EXHAUSTIVE_EXTERNAL_SOURCE_SEARCH"}
    save_json(output, payload)
    print({"status": payload["status"], "reference_count": payload["reference_count"], "blockers": blockers})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    audit(p.parse_args().output)
