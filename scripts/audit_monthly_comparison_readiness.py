"""Read-only current metadata audit; no factor values, scores, P&L or DB writes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from psycopg.rows import dict_row

from engine import silver


def audit(snapshot: Path, output: Path):
    if output.exists():
        raise FileExistsError("Use a new audit output path")
    body = snapshot.read_bytes()
    prior = {row["name"]: row for row in json.loads(body)["factors"]}
    with silver.connect(read_only=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SET LOCAL statement_timeout = '20s'")
            cur.execute("SHOW transaction_read_only")
            if cur.fetchone()["transaction_read_only"] != "on":
                raise RuntimeError("Read-only transaction required")
            cur.execute("SELECT transaction_timestamp() AS as_of")
            as_of = cur.fetchone()["as_of"]
            cur.execute("""SELECT factor_key,version,status,
                config->>'research_definition_hash' AS definition_hash,
                config->>'predicted_sign' AS predicted_sign
                FROM gold.factor WHERE status='APPROVED' ORDER BY factor_key,version""")
            approved = cur.fetchall()
            current = {}
            for row in approved:
                if row["factor_key"] in current:
                    raise ValueError("Multiple approved versions; explicit identity resolution required")
                current[row["factor_key"]] = row
            cur.execute("""SELECT factor_key,version,status,
                config->>'research_definition_hash' AS definition_hash
                FROM gold.factor WHERE factor_key = ANY(%s) ORDER BY factor_key,version""",
                (sorted(set(prior) - set(current)),))
            removed_statuses = cur.fetchall()
            cur.execute("""SELECT source,asset_type,field_name,methodology_version,
                dividend_treatment,status,coverage_start,coverage_end,certified_at
                FROM public.price_return_contract ORDER BY source,asset_type,field_name""")
            contracts = cur.fetchall()
            cur.execute("""SELECT asset_id,name,asset_type,exchange FROM public.asset
                WHERE exchange='KRX' AND (asset_type='index' OR name ILIKE '%총수익%'
                    OR name ILIKE '%total return%') ORDER BY asset_id""")
            index_assets = cur.fetchall()
            cur.execute("""SELECT table_schema,table_name FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema','pg_catalog')
                AND (table_name ILIKE '%calendar%' OR table_name ILIKE '%session%'
                    OR table_name ILIKE '%index%') ORDER BY table_schema,table_name""")
            calendar_index_tables = cur.fetchall()
    shared = sorted(set(prior) & set(current))
    missing = sorted(name for name, row in prior.items() if not row.get("definition_hash"))
    recovered = [name for name in missing if current.get(name, {}).get("definition_hash")]
    mismatches = [{"factor_id": name, "snapshot_definition_hash": prior[name]["definition_hash"],
                   "live_definition_hash": current[name]["definition_hash"], "live_version": current[name]["version"]}
                  for name in shared if prior[name].get("definition_hash")
                  and prior[name]["definition_hash"] != current[name]["definition_hash"]]
    result = {"schema_version": "monthly-comparison-live-readiness-v1", "as_of": as_of,
              "read_only": True, "factor_values_read": False, "performance_computed": False,
              "snapshot_sha256": hashlib.sha256(body).hexdigest(),
              "snapshot_factor_count": len(prior), "live_approved_count": len(current),
              "missing_snapshot_definition_count": len(missing),
              "definition_hashes_found_live": recovered,
              "snapshot_not_currently_approved": sorted(set(prior) - set(current)),
              "new_currently_approved": sorted(set(current) - set(prior)),
              "definition_mismatches": mismatches, "removed_factor_statuses": removed_statuses,
              "live_approved_definitions": approved, "return_contracts": contracts,
              "index_assets": index_assets, "calendar_index_tables": calendar_index_tables,
              "status": "BLOCKED_FROZEN_FACTOR_IDENTITY_CHANGED" if mismatches or set(prior) != set(current)
                        else "IDENTITIES_RECONCILED_EXECUTION_INPUTS_STILL_REQUIRED",
              "limitations": ["Metadata only, not verification of executable prices or corporate-action accounting.",
                              "Current definitions must not silently replace the frozen request.",
                              "Market TR and first-session-open contracts still require source validation."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")
    return {key: result[key] for key in ("status", "as_of", "snapshot_factor_count", "live_approved_count",
                                       "definition_hashes_found_live", "snapshot_not_currently_approved",
                                       "new_currently_approved")} | {"definition_mismatch_count": len(mismatches)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.snapshot, args.output), ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
