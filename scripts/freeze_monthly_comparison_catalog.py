"""Freeze current approved identities, read-only; never read evaluations or scores."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from psycopg.rows import dict_row

from engine import silver
from strategies.run_monthly_comparison import save_new


def build_catalog(rows, *, as_of, prior):
    names = [row["name"] for row in rows]
    if not names or len(set(names)) != len(names):
        raise ValueError("Each approved factor must have exactly one current version")
    if set(names) != {row["name"] for row in prior["factors"]}:
        raise ValueError("Approved membership changed; the authorized same-set replacement no longer applies")
    factors = []
    for row in sorted(rows, key=lambda r: r["name"]):
        if row["status"] != "APPROVED" or row["frequency"] != "daily":
            raise ValueError("Expected current approved daily identities")
        if not re.fullmatch(r"(?:[a-f0-9]{16}|[a-f0-9]{64})", row["definition_hash"] or ""):
            raise ValueError("Every factor needs a definition hash")
        if not re.fullmatch(r"[a-f0-9]{64}", row["implementation_hash"] or ""):
            raise ValueError("Every factor needs a SQL implementation hash")
        if str(row["predicted_sign"]) not in {"-1", "1"} or int(row["version"]) < 1:
            raise ValueError("Invalid factor direction or version")
        factors.append(dict(row, predicted_sign=int(row["predicted_sign"])))
    return {
        "schema_version": "approved-monthly-comparison-catalog-v1",
        "as_of": as_of, "status": "DB_VERIFIED_FROZEN_SNAPSHOT", "is_live": False,
        "approval_verified_at": as_of, "approved_count": len(factors), "factors": factors,
        "source": "Read-only gold.factor identity metadata; evaluations and factor_value not read",
        "score_semantics": "Gold values already direction-adjusted; do not multiply sign again",
        "selection_note": "Current approved definitions selected retrospectively, not historical approval PIT",
    }


def freeze(prior_path, output):
    prior_path, output = Path(prior_path), Path(output)
    if output.exists():
        raise FileExistsError("Use a new immutable snapshot directory")
    prior_bytes = prior_path.read_bytes()
    with silver.connect(read_only=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SET LOCAL statement_timeout='20s'")
            cur.execute("SHOW transaction_read_only")
            if cur.fetchone()["transaction_read_only"] != "on":
                raise RuntimeError("Read-only transaction required")
            cur.execute("SELECT transaction_timestamp() AS as_of")
            as_of = cur.fetchone()["as_of"].isoformat()
            cur.execute("""SELECT factor_key AS name,version,status,implementation_hash,
                config->>'research_definition_hash' AS definition_hash,
                config->>'frequency' AS frequency,config->>'predicted_sign' AS predicted_sign,
                config->>'lookback_translation' AS lookback_translation
                FROM gold.factor WHERE status='APPROVED' ORDER BY factor_key,version""")
            catalog = build_catalog(cur.fetchall(), as_of=as_of, prior=json.loads(prior_bytes))
            cur.execute("""SELECT source,asset_type,field_name,methodology_version,
                dividend_treatment,status,coverage_start,coverage_end,certified_at
                FROM public.price_return_contract ORDER BY source,asset_type,field_name""")
            contracts = cur.fetchall()
            cur.execute("""SELECT name,asset_type,exchange FROM public.asset
                WHERE exchange='KRX' AND (asset_type='index' OR name ILIKE '%총수익%'
                    OR name ILIKE '%total return%') ORDER BY name""")
            assets = cur.fetchall()
            cur.execute("""SELECT table_schema,table_name FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema','pg_catalog')
                AND (table_name ILIKE '%calendar%' OR table_name ILIKE '%session%')
                ORDER BY table_schema,table_name""")
            calendars = cur.fetchall()
    catalog["prior_snapshot_sha256"] = hashlib.sha256(prior_bytes).hexdigest()
    audit = {"as_of": as_of, "read_only": True, "performance_computed": False,
             "return_contracts": contracts, "index_assets": assets, "calendar_tables": calendars,
             "factor_value_has_availability_timestamp": False,
             "limitations": ["Metadata inventory, not execution certification",
                             "Gold score rows have no available_at: upstream PIT lineage required"]}
    # Date values are metadata only, serialized without database connection details.
    audit = json.loads(json.dumps(audit, default=str))
    save_new(output / "catalog.json", catalog)
    save_new(output / "input-audit.json", audit)
    return {"status": "CURRENT_IDENTITIES_FROZEN", "factors": len(catalog["factors"]), "as_of": as_of}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(args.prior, args.output)))
