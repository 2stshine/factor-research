"""Read-only, bounded source-query parity; no factor or return summaries."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from engine import silver
from engine.research_panel_query import deferred_identity_sql

SCOPE = "EXPLICIT_COHORT_INPUT_PARITY_NOT_UNIVERSE_OR_PERFORMANCE_CERTIFICATION"


def cohort_queries(original, optimized, asset_ids):
    if (not isinstance(asset_ids, (list, tuple)) or not asset_ids or len(asset_ids) > 10
            or any(type(value) is not int or value <= 0 for value in asset_ids)
            or len(set(asset_ids)) != len(asset_ids)):
        raise ValueError("Specify 1..10 distinct positive asset IDs")
    marker = "      AND a.asset_type = 'stock'"
    queries = []
    for sql in (original, optimized):
        if sql.count(marker) != 1:
            raise ValueError("Unrecognized cohort restriction point")
        queries.append(sql.replace(marker, marker + "\n      AND p.asset_id = ANY(%s)"))
    return queries


def validate_parity_record(evidence, original, optimized):
    """Check artifact consistency; this is not independent source authentication."""
    if not isinstance(evidence, dict):
        raise ValueError("Parity record must be an object")
    queries = cohort_queries(original, optimized, evidence.get("asset_ids"))
    ids = sorted(evidence["asset_ids"])
    rows, hashes = evidence.get("rows"), evidence.get("result_sha256")
    observed = evidence.get("observed_asset_ids")
    if (evidence.get("schema_version") != "deferred-identity-query-parity-v2"
            or evidence.get("scope") != SCOPE
            or any(evidence.get(flag) is not True for flag in (
                "parity_pass", "exact_columns_and_row_values_equal", "requested_cohort_observed",
                "read_only", "same_database_snapshot"))
            or evidence.get("original_query_sha256") != hashlib.sha256(original.encode()).hexdigest()
            or evidence.get("optimized_query_sha256") != hashlib.sha256(optimized.encode()).hexdigest()
            or evidence.get("queries") != queries
            or evidence.get("query_sha256") != [hashlib.sha256(sql.encode()).hexdigest() for sql in queries]
            or not isinstance(observed, list) or len(observed) != 2
            or any(not isinstance(group, list) or any(type(value) is not int for value in group)
                   for group in observed) or observed != [ids, ids]
            or not isinstance(rows, list) or len(rows) != 2
            or any(type(count) is not int or not len(ids) <= count <= 5000 for count in rows)
            or rows[0] != rows[1]
            or not isinstance(hashes, list) or len(hashes) != 2 or hashes[0] != hashes[1]
            or any(not isinstance(value, str) or len(value) != 64
                   or set(value) - set("0123456789abcdef") for value in hashes)
            or type(evidence.get("factor_trials")) is not int or evidence["factor_trials"] != 0
            or evidence.get("gold_write") is not False):
        raise ValueError("Successful parity record with matching query/result/cohort hashes required")


def probe(asset_ids, output, *, connect=None):
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    original = silver.PRICE_SNAPSHOT_SQL
    optimized = deferred_identity_sql(original)
    queries = cohort_queries(original, optimized, asset_ids)
    with (connect or silver.connect)(read_only=True) as conn:
        if getattr(conn, "autocommit", None) is not False:
            raise ValueError("Autocommit must be disabled for one database snapshot")
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout=15000")
            cur.execute("SHOW transaction_read_only")
            if cur.fetchone()[0] != "on":
                raise ValueError("Read-only transaction required")
            cur.execute("SHOW transaction_isolation")
            if cur.fetchone()[0] != "repeatable read":
                raise ValueError("Same repeatable-read snapshot required")
            results, times = [], []
            for sql in queries:
                started = time.perf_counter()
                cur.execute(sql, (asset_ids,))
                columns = [column.name for column in cur.description]
                rows = cur.fetchmany(5001)
                if len(rows) > 5000:
                    raise ValueError("Cohort row budget exceeded")
                results.append((columns, rows))
                times.append(time.perf_counter() - started)
    same = results[0] == results[1]
    observed_ids = [sorted({row[columns.index("asset_id")] for row in rows})
                    for columns, rows in results]
    cohort_observed = all(ids == sorted(asset_ids) and all(type(value) is int for value in ids)
                          for ids in observed_ids)
    result_hashes = [hashlib.sha256(json.dumps(value, default=str, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode()).hexdigest() for value in results]
    passed = same and cohort_observed and bool(results[0][1]) and result_hashes[0] == result_hashes[1]
    payload = {
        "schema_version": "deferred-identity-query-parity-v2",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": SCOPE,
        "read_only": True, "same_database_snapshot": True, "asset_ids": asset_ids,
        "rows": [len(value[1]) for value in results],
        "observed_asset_ids": observed_ids, "requested_cohort_observed": cohort_observed,
        "parity_pass": passed,
        "exact_columns_and_row_values_equal": same,
        "result_sha256": result_hashes,
        "query_seconds": times,
        "timing_caveat": "Original ran first; warm-cache/order effects prevent a controlled speed claim.",
        "queries": queries,
        "query_sha256": [hashlib.sha256(sql.encode()).hexdigest() for sql in queries],
        "original_query_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "optimized_query_sha256": hashlib.sha256(optimized.encode()).hexdigest(),
        "compiler_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "raw_values_in_report": False, "factor_trials": 0, "gold_write": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: payload[k] for k in ("scope", "rows", "exact_columns_and_row_values_equal", "query_seconds")}))
    if not passed:
        raise SystemExit("Query parity mismatch; do not use optimized query")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-ids", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    probe(args.asset_ids, args.output)
