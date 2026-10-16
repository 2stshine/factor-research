"""Freeze an outcome-blind 2015 FY issuer source-discovery universe.

Current mappings are lookup hints, never historical issuer certification.
No database/network, financial-value imputation, or research result access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from engine.research_memory_transfer import write_artifact


def prepare(ledger_path, identity_path, output):
    ledger_path, identity_path, output = map(Path, (ledger_path, identity_path, output))
    if output.exists():
        raise ValueError("Use a new immutable corpus plan")
    identity_bytes = identity_path.read_bytes()
    evidence = json.loads(identity_bytes)
    if (evidence.get("schema_version") != "historical-financial-identity-source-extract-v1"
            or evidence.get("read_only") is not True):
        raise ValueError("Unexpected source-discovery identity evidence")
    rows = pd.read_parquet(ledger_path, columns=["asset_id", "metric", "period_end", "fiscal_period"])
    selected = rows.loc[rows.metric.eq("revenue") & rows.fiscal_period.eq("FY")
                        & rows.period_end.eq(pd.Timestamp("2015-12-31")), "asset_id"]
    ids = sorted({int(value) for value in selected})
    grouped, excluded = {}, []
    for asset in ids:
        matches = [row for row in evidence["rows"] if str(row["asset_id"]) == str(asset)
                   and row["status"] == "CERTIFIED"]
        corps = {row["identifier"] for row in matches
                 if row["source"] == "DART" and row["identifier_type"] == "corp_code"
                 and re.fullmatch(r"\d{8}", row["identifier"])}
        stocks = {row["identifier"] for row in matches
                  if row["source"] == "KRX" and row["identifier_type"] == "ticker"
                  and re.fullmatch(r"\d{6}", row["identifier"])}
        if len(corps) != 1 or len(stocks) != 1:
            excluded.append({"asset_id": asset, "reason": "NO_UNIQUE_LOOKUP_IDENTITY",
                             "corp_count": len(corps), "stock_count": len(stocks)})
            continue
        corp, stock = next(iter(corps)), next(iter(stocks))
        entry = grouped.setdefault(corp, {"corp_code": corp, "stock_code": stock, "asset_ids": []})
        if entry["stock_code"] != stock:
            raise ValueError("One issuer maps to several lookup tickers; review scope explicitly")
        entry["asset_ids"].append(asset)
    if not grouped or excluded:
        raise ValueError(f"Source universe needs identity review: selected={len(ids)}, unresolved={len(excluded)}")
    manifest = {
        "schema_version": "dart-statement-corpus-plan-v1", "corpus_id": "historical-revenue-2015-20261002-v1",
        "issuers": [grouped[key] for key in sorted(grouped)],
        "fiscal_year": 2015, "quarters": ["Q1", "Q2", "Q3"],
        "list_start": "20150101", "list_end": "20230731",
        "identity_source_sha256": hashlib.sha256(identity_bytes).hexdigest(),
        "max_calls": 12000, "max_bytes": 2147483648, "max_documents": 8000,
        "universe_policy": "Every asset in the preserved certified ledger with 2015-12-31 FY revenue; no values, returns, or candidate success used for selection",
        "source_ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        "fiscal_calendar_scope": "December FY endpoint only; non-December issuers require a separate explicit calendar plan",
        "source_asset_count": len(ids), "issuer_count": len(grouped),
        "identity_status": "LOOKUP_HINT_ONLY_HISTORICAL_MAPPING_NOT_CERTIFIED",
        "research_authorized_by_plan": False, "silver_publish_authorized_by_plan": False,
    }
    write_artifact(output, manifest)
    print(json.dumps({key: manifest[key] for key in ("corpus_id", "issuer_count", "source_asset_count", "max_calls", "identity_status")}, indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.ledger, args.identity, args.output)
