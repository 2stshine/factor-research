"""Read-only KIS observation-timing audit; never grant historical PIT approval."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


SUMMARY_SQL = """
SELECT count(*) AS rows,
       min(trade_date) AS first_trade_date, max(trade_date) AS latest_trade_date,
       min(first_observed_at) AS first_observed_at,
       max(first_observed_at) AS latest_observed_at,
       count(*) FILTER (WHERE provider_available_at IS NULL) AS provider_time_unknown,
       count(*) FILTER (WHERE historical_revision_risk) AS historical_revision_risk_rows,
       count(*) FILTER (WHERE availability_basis='POLICY_ASSUMPTION') AS policy_assumption_rows,
       count(*) FILTER (WHERE trade_date < (first_observed_at AT TIME ZONE 'Asia/Seoul')::date)
           AS observed_after_trade_date,
       count(*) FILTER (WHERE first_observed_at < '2016-01-01'::timestamptz)
           AS observations_received_before_2016,
       count(*) FILTER (WHERE first_observed_at IS NULL OR research_available_at IS NULL)
           AS missing_asof_timestamps
FROM public.kis_market_observation
"""


def fingerprint(path: Path) -> dict:
    body = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body)}


def source_checks(root: Path) -> tuple[list[dict], list[dict]]:
    files = [root / "pipeline/silver/kis_flows.py",
             root / "pipeline/silver_quality/migrations/015_kis_market_flows.sql",
             root / "docs/kis-market-flows.md"]
    evidence = [fingerprint(path) for path in files]
    code = files[0].read_text()
    sql = "".join(files[1].read_text().split())
    checks = {
        "actual_receipt_not_trade_date": "observed = max(datetime.fromisoformat(r['fetched_at'])" in code,
        "historical_revision_risk_preserved": "'historical_revision_risk': True" in code,
        "policy_is_not_provider_publication": "'availability_basis': 'POLICY_ASSUMPTION'" in code,
        "asof_requires_actual_observation": "k.first_observed_at<=cutoff" in sql,
        "asof_requires_policy_availability": "k.research_available_at<=cutoff" in sql,
        "versions_include_observation_time":
            "PRIMARYKEY(asset_id,trade_date,venue,kind,revision,first_observed_at)" in sql,
    }
    return [{"check": k, "passed": v, "kind": "CODE_CONTRACT_NOT_DATA_PROOF"}
            for k, v in checks.items()], evidence


def database_summary() -> dict:
    from engine.silver import connect
    try:
        with connect(read_only=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout='30000ms'")
                cur.execute("SELECT to_regclass('public.kis_market_observation')")
                if cur.fetchone()[0] is None:
                    return {"status": "TABLE_NOT_PRESENT", "rows_examined": 0}
                cur.execute(SUMMARY_SQL)
                counts = dict(zip([x.name for x in cur.description], cur.fetchone()))
                cur.execute("""SELECT kind,venue,count(*) FROM public.kis_market_observation
                               GROUP BY kind,venue ORDER BY kind,venue""")
                groups = [{"kind": r[0], "venue": r[1], "rows": r[2]} for r in cur.fetchall()]
                return {"status": "READ_ONLY_AGGREGATES_VERIFIED", "rows_examined": counts["rows"],
                        "counts": counts, "groups": groups,
                        "does_not_prove_first_release_values": True}
    except (Exception, SystemExit) as exc:
        # Database/credential errors can contain credentials or endpoints. Never persist str(exc).
        return {"status": "CONNECTION_OR_QUERY_UNAVAILABLE", "rows_examined": None,
                "error_class": type(exc).__name__, "error_details_redacted": True}


def audit(root: Path, *, live: bool = False) -> dict:
    checks, evidence = source_checks(root)
    db = database_summary() if live else {"status": "NOT_QUERIED", "rows_examined": None}
    return {"schema_version": "kis-pit-review-v1",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "scope": ["KIS_INVESTOR_FLOWS", "KIS_SHORT_TRADES"],
            "code_checks": checks, "evidence": evidence, "database": db,
            "historical_pit_approved": False, "approval_changed": False,
            "status": "HISTORICAL_VINTAGE_UNPROVEN",
            "confirmed": [
                "Strict asof filters actual receipt time as well as assumed availability.",
                "Historical backfills are explicitly revision-risk observations, not initial releases.",
            ] if all(x["passed"] for x in checks) else [],
            "remaining": ["No first-release value ledger has been established for 2015+ backfills.",
                          "Next-day 08:30 KST is a policy assumption, not provider publication evidence.",
                          "Live aggregate checks do not authenticate the source value or its first vintage."],
            "mutations": {"database": False, "bronze": False, "approval": False, "campaign": False}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-repo", type=Path,
                        default=Path(__file__).resolve().parents[2] / "TeamAlpha-data")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.data_repo, live=args.live)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=str, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "database_status": report["database"]["status"],
                      "rows_examined": report["database"]["rows_examined"],
                      "code_checks_passed": sum(x["passed"] for x in report["code_checks"])}))


if __name__ == "__main__":
    main()
