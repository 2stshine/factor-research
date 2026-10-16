"""Install only the reviewed, isolated original-document Silver tables.

Requires --apply; refuses any pre-existing target table/function rather than
replacing user state. Never publishes a row, changes core fundamental or Gold,
or relaxes an existing quality guard. Caller transaction is atomic.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from engine import silver
from engine.research_memory_transfer import write_artifact

EXPECTED_SHA = "1d3e08af5f4f74516518e2ba61110b97142afdd687669e8b9d33b24e17764b4b"
MIGRATION = Path(__file__).resolve().parents[2] / "TeamAlpha-data/pipeline/silver_quality/migrations/020_dart_historical_revenue.sql"
EXISTENCE_SQL = """SELECT to_regclass('public.fundamental_document_dataset'),
to_regclass('public.fundamental_document_revenue'),
to_regprocedure('public.reject_document_revenue_mutation()'),
to_regprocedure('public.require_document_revenue_building()')"""


def install(output, *, apply=False):
    if not apply:
        raise ValueError("Explicit --apply is required")
    output = Path(output)
    if output.exists():
        raise ValueError("Use a new immutable schema installation receipt")
    raw = MIGRATION.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
        raise ValueError("Migration differs from independently tested frozen DDL")
    with silver.connect(read_only=False) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL search_path=public,pg_catalog")
                cur.execute(EXISTENCE_SQL)
                if any(cur.fetchone()):
                    raise ValueError("Target namespace already exists; no replacement allowed")
                cur.execute(raw.decode("utf-8"))
                cur.execute(EXISTENCE_SQL)
                created = cur.fetchone()
                if not all(created):
                    raise ValueError("Expected namespace was not fully created")
                cur.execute("""SELECT c.relname,t.tgname FROM pg_trigger t
                    JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='public' AND c.relname IN
                    ('fundamental_document_dataset','fundamental_document_revenue') AND NOT t.tgisinternal
                    ORDER BY c.relname,t.tgname""")
                triggers = cur.fetchall()
                expected = {"trg_document_dataset_building", "trg_document_revenue_building",
                            "trg_document_dataset_immutable", "trg_document_revenue_immutable"}
                if {r[1] for r in triggers} != expected:
                    raise ValueError("Source append-only guards differ from tested DDL")
    receipt = dict(schema_version="dart-historical-source-schema-install-v1", status="INSTALLED",
        completed_at=datetime.now(timezone.utc).isoformat(), migration_sha256=EXPECTED_SHA,
        namespace=list(created), guards=[list(r) for r in triggers], transaction_committed=True,
        existing_table_rows_modified=0, source_observations_inserted=0, gold_writes=0)
    write_artifact(output, receipt)
    print(receipt)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    install(a.output, apply=a.apply)
