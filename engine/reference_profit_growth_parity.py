"""Independent SQL computation on all feature rows plus real PostgreSQL sample."""
from __future__ import annotations
import hashlib
import sqlite3

import pandas as pd

from engine import reference_gold as gold, reference_profit_growth as lib
from engine.reference_expansion_parity import _compare
from engine.research_generation import digest


def validate_parity(panel, values, conn):
    ids = sorted(values.reference_id.unique())
    if not set(ids) <= set(lib.SPECS):
        raise ValueError("Unknown parity definitions")
    frame = lib.prepare(panel)[["asset_id", "stock_code", "date", *lib.FEATURES]].copy()
    frame.date = frame.date.dt.strftime("%Y-%m-%d")
    query = " UNION ALL ".join(f"SELECT '{ref}' AS reference_id,asset_id,stock_code,date,{lib.SPECS[ref]['sql']} AS value FROM reference_input" for ref in ids)
    sql = f"SELECT * FROM ({query}) measured WHERE value IS NOT NULL AND abs(value)<=1.7976931348623157e308"
    fields = ["asset_id TEXT", "stock_code TEXT", "date TEXT"] + [c + " DOUBLE PRECISION" for c in lib.FEATURES]
    records = list(frame.astype(object).where(pd.notna(frame), None).itertuples(index=False, name=None))
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE reference_input (" + ",".join(fields) + ")")
        db.executemany("INSERT INTO reference_input VALUES (" + ",".join("?" for _ in fields) + ")", records)
        cursor = db.execute(sql)
        result = pd.DataFrame(cursor.fetchall(), columns=[c[0] for c in cursor.description])
    count = _compare(values, result, "SQLite")
    rows = gold.canonical_values(values)
    assets = sorted({r["asset_id"] for r in rows})
    sample = sorted({assets[(len(assets) - 1) * i // 9] for i in range(10)})
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout='180s'")
        cur.execute("CREATE TEMP TABLE reference_input (" + ",".join(fields) + ") ON COMMIT DROP")
        with cur.copy("COPY reference_input FROM STDIN") as copy:
            for row in records:
                if int(row[0]) in sample:
                    copy.write_row(row)
        cur.execute(sql)
        result = pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])
        cur.execute("DROP TABLE pg_temp.reference_input")
    subset = values.loc[values.asset_id.astype(int).isin(sample)]
    sample_count = _compare(subset, result, "PostgreSQL")
    common = dict(passed=True, sql_sha256=hashlib.sha256(sql.encode()).hexdigest(), rtol=1e-10, atol=0)
    return {**common, "kind": "INDEPENDENT_SQLITE_FULL_POSTGRES_FIXED_SAMPLE", "rows_compared": count,
            "values_sha256": digest(rows), "sqlite_full": {**common, "rows_compared": count},
            "postgres_sample": {**common, "rows_compared": sample_count, "asset_ids": sample,
                "selection": "TEN_EVENLY_SPACED_SORTED_ASSET_IDS_ALL_MONTHS", "values_sha256": digest(gold.canonical_values(subset))}}
