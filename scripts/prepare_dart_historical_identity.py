"""Read-only issuer identity triangulation for the separate historical corpus.

The certified FY receipt is an issuer-to-asset anchor, not a quarter value.
Historical listing periods are imported from an existing certified snapshot;
current corpCode/date.min lookup mappings are never promoted to evidence.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID

from engine.research_memory_transfer import write_artifact
from scripts.repair_fundamental_panel import task_connection

SNAPSHOT_ID = "5fc0dfd3244c33e73d22309ac931dcad57144f6c17c08609c5a5cd88a86ed13b"
SNAPSHOT_SQL = """SELECT s.snapshot_id,s.payload,s.quality_run_id::text,q.status
FROM public.asset_listing_snapshot s JOIN public.dq_run q ON q.run_id=s.quality_run_id
WHERE s.snapshot_id=%s AND q.status='CERTIFIED'"""
FY_SQL = """SELECT DISTINCT f.asset_id,f.filing_id,f.quality_run_id::text,q.status
FROM public.fundamental f JOIN public.asset a ON a.asset_id=f.asset_id
JOIN public.dq_run q ON q.run_id=f.quality_run_id AND q.status='CERTIFIED'
WHERE f.source='DART' AND a.exchange='KRX' AND a.asset_type='stock'
AND f.data_basis='STANDARDIZED' AND f.unit_type='currency' AND f.metric='revenue'
AND f.fiscal_period='FY' AND f.period_end=DATE '2015-12-31'
AND f.available_date<=DATE '2023-07-31'
ORDER BY f.asset_id,f.filing_id,f.quality_run_id::text"""


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def validate_snapshot(row):
    sid, payload, quality_run, status = row
    UUID(str(quality_run))
    body = {k: v for k, v in payload.items() if k != "snapshot_id"}
    digest = sha(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
    if status != "CERTIFIED" or sid != payload["snapshot_id"] or sid != digest:
        raise ValueError("Listing source certification/fingerprint mismatch")
    if payload["schema"] != "asset-listing-snapshot-v1":
        raise ValueError("Unsupported listing snapshot")
    if payload["coverage_start"] > "2015-01-01" or payload["verified_through"] < "2023-07-31":
        raise ValueError("Listing snapshot does not cover the historical window")
    seen, rows = set(), []
    for p in payload["periods"]:
        start = max(date(2015, 1, 1), date.fromisoformat(p["start"]))
        end = min(date(2023, 8, 1), date.fromisoformat(p["end"]) + timedelta(days=1)
                  if p["end"] else date(2023, 8, 1))
        if start >= end:
            continue
        key = (p["asset_id"], p["ticker"], str(start), str(end))
        # The all-security listing source contains valid alphanumeric class
        # tickers. The numeric-only research plan is restricted downstream.
        if key in seen or not re.fullmatch(r"[0-9A-Z]{6}", p["ticker"]):
            raise ValueError("Duplicate or malformed historical listing identity")
        seen.add(key)
        rows.append(dict(asset_id=p["asset_id"], stock_code=p["ticker"], valid_from=str(start),
                         valid_until_exclusive=str(end), quality_run_id=quality_run, status=status))
    for ticker in {r["stock_code"] for r in rows}:
        periods = sorted((r["valid_from"], r["valid_until_exclusive"]) for r in rows if r["stock_code"] == ticker)
        if any(a[1] > b[0] for a, b in zip(periods, periods[1:])):
            raise ValueError("Overlapping historical ticker episodes")
    return rows


def extract(output, *, profile=None):
    output = Path(output)
    if output.exists():
        raise ValueError("Identity extraction destination must be new")
    with task_connection(profile) as conn:
        with conn.cursor() as cur:
            cur.execute(SNAPSHOT_SQL, (SNAPSHOT_ID,))
            found = cur.fetchall()
            if len(found) != 1:
                raise ValueError("Expected certified listing snapshot unavailable")
            listing_rows = validate_snapshot(found[0])
            cur.execute(FY_SQL)
            columns = [d.name for d in cur.description]
            fy_rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    timestamp = datetime.now(timezone.utc).isoformat()
    proof = dict(schema_version="certified-listing-snapshot-extract-v1", read_only=True,
                 recorded_at=timestamp, query_sha256=sha(SNAPSHOT_SQL.encode()),
                 snapshot_id=found[0][0], payload=found[0][1], quality_run_id=found[0][2], status=found[0][3])
    output.mkdir(parents=True)
    write_artifact(output / "listing-source.json", proof)
    proof_sha = sha((output / "listing-source.json").read_bytes())
    write_artifact(output / "listing.json", dict(schema_version="historical-listing-identity-v1",
                   identity_methodology="RDS_CERTIFIED_LISTING_EPISODE_WITH_FROZEN_SOURCE_PROOF",
                   identity_evidence_sha256=proof_sha, rows=listing_rows))
    write_artifact(output / "fy-reference.json", dict(schema_version="certified-fy-identity-reference-v1",
                   read_only=True, recorded_at=timestamp, query_sha256=sha(FY_SQL.encode()), rows=fy_rows,
                   limitation="Issuer identity anchor only; does not certify historical quarterly amounts"))
    print(json.dumps(dict(listing_rows=len(listing_rows), fy_anchor_rows=len(fy_rows), output=str(output))))


def qualify_fy(extract_dir):
    """Add explicit FY scope proven by the frozen extraction SQL, not inferred values."""
    source = Path(extract_dir) / "fy-reference.json"
    raw = source.read_bytes()
    value = json.loads(raw)
    if (value["query_sha256"] != sha(FY_SQL.encode()) or value.get("read_only") is not True
            or value["schema_version"] != "certified-fy-identity-reference-v1"):
        raise ValueError("FY extract is not bound to the exact 2015-12-31 source query")
    for row in value["rows"]:
        if row["status"] != "CERTIFIED":
            raise ValueError("Uncertified FY identity anchor")
        UUID(row["quality_run_id"])
    target = source.with_name("fy-reference-scoped.json")
    if target.exists():
        raise ValueError("Scoped FY extract already exists")
    write_artifact(target, {**value, "fiscal_period_end": "2015-12-31", "source_extract_sha256": sha(raw),
                           "scope_basis": "EXACT_READ_ONLY_SQL_PREDICATE", "source_query": FY_SQL})
    print(json.dumps({"output": str(target), "rows": len(value["rows"])}))


def assemble(extract_dir, corpus_root, plan_path, output):
    extract_dir, corpus_root, plan_path, output = map(Path, (extract_dir, corpus_root, plan_path, output))
    if output.exists():
        raise ValueError("Identity bundle destination must be new")
    listing_raw, fy_raw = (extract_dir / "listing.json").read_bytes(), (extract_dir / "fy-reference-scoped.json").read_bytes()
    listing, fy, plan = json.loads(listing_raw), json.loads(fy_raw), json.loads(plan_path.read_bytes())
    official = {}
    for path in sorted((corpus_root / "objects").glob("*.json")):
        meta = json.loads(path.read_bytes())
        if meta["endpoint"] != "list.json":
            continue
        body = (corpus_root / meta["body_path"]).read_bytes()
        if sha(body) != meta["sha256"]:
            raise ValueError("Official list body hash mismatch")
        value = json.loads(body)
        for row in value.get("list", []):
            key = (row["corp_code"], row["rcept_no"])
            if key in official and official[key][0] != row:
                raise ValueError("Conflicting official issuer identity")
            official[key] = (row, meta["sha256"])
    mappings, unresolved = [], []
    for issuer in plan["issuers"]:
        for asset in issuer["asset_ids"]:
            anchors = sorted(r["filing_id"] for r in fy["rows"] if r["asset_id"] == asset
                             and (issuer["corp_code"], r["filing_id"]) in official)
            episodes = [r for r in listing["rows"] if r["asset_id"] == asset and r["stock_code"] == issuer["stock_code"]]
            if not anchors or not episodes:
                unresolved.append(dict(asset_id=asset, corp_code=issuer["corp_code"], stock_code=issuer["stock_code"],
                                  reason="MISSING_OFFICIAL_FY_ISSUER_ANCHOR" if not anchors else "MISSING_CERTIFIED_LISTING_EPISODE"))
                continue
            receipt = anchors[0]
            for episode in episodes:
                mappings.append({**{k: episode[k] for k in ("asset_id", "stock_code", "valid_from", "valid_until_exclusive")},
                    "corp_code": issuer["corp_code"], "basis": "CERTIFIED_FY_AND_LISTING_EPISODE",
                    "fy_reference_sha256": sha(fy_raw), "fy_receipt_no": receipt,
                    "fy_issuer_sha256": official[(issuer["corp_code"], receipt)][1], "listing_snapshot_sha256": sha(listing_raw)})
    write_artifact(output, dict(schema_version="dart-historical-identity-v1", mappings=mappings, unresolved=unresolved,
                               corpus_plan_sha256=sha(plan_path.read_bytes()), no_current_mapping_backdating=True))
    print(json.dumps(dict(mappings=len(mappings), unresolved=len(unresolved), output=str(output))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--aws-profile")
    p = sub.add_parser("qualify-fy")
    p.add_argument("--extract-dir", required=True, type=Path)
    p = sub.add_parser("assemble")
    for key in ("extract-dir", "corpus-root", "plan-path", "output"):
        p.add_argument("--" + key, required=True, type=Path)
    a = parser.parse_args()
    if a.command == "extract":
        extract(a.output, profile=a.aws_profile)
    elif a.command == "qualify-fy":
        qualify_fy(a.extract_dir)
    else:
        assemble(a.extract_dir, a.corpus_root, a.plan_path, a.output)
