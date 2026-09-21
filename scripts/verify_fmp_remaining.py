"""Evidence-backed, read-only qualification of the remaining FMP Bronze series.

Does not manufacture historical PIT approvals or mutate research inputs.
Use the bundled Python for CSV analysis; only stdlib dependencies are required.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timedelta, timezone
import html
import io
import json
import math
from pathlib import Path
import re
import zipfile
from urllib.parse import urlencode

from scripts.prepare_bok_policy import get_http, save, encode, sha, PREFIX, RUN, BUCKET
from scripts.fmp_pit_audit import load_run, compare_cboe, COT_EXCEPTIONS

URLS = {
    "fmp-faq.html": "https://site.financialmodelingprep.com/it/faqs?code=marketPerformance",
    "cftc-compressed.html": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm",
    "ewt-split-sec.html": "https://www.sec.gov/Archives/edgar/data/1100663/000119312516737785/d231942d497.htm",
    "nyse-hours.html": "https://www.nyse.com/markets/hours-calendars",
}
COT_CODES = {"HG": "085692", "CL": "067651", "DX": "098662", "J6": "097741",
             "GC": "088691", "VX": "1170E1", "ZT": "042601", "ZN": "043602",
             "ZB": "020601", "ZQ": "045601"}
COT_FIELDS = dict(zip(
    ("openInterestAll", "noncommPositionsLongAll", "noncommPositionsShortAll",
     "noncommPositionsSpreadAll", "commPositionsLongAll", "commPositionsShortAll",
     "totReptPositionsLongAll", "totReptPositionsShortAll", "nonreptPositionsLongAll",
     "nonreptPositionsShortAll"),
    ("open_interest_all", "noncomm_positions_long_all", "noncomm_positions_short_all",
     "noncomm_postions_spread_all", "comm_positions_long_all", "comm_positions_short_all",
     "tot_rept_positions_long_all", "tot_rept_positions_short", "nonrept_positions_long_all",
     "nonrept_positions_short_all")))


def fetch_cot_api(out):
    base = "https://publicreporting.cftc.gov"
    path, _ = get_http(out, "cftc-dataset.json", base + "/api/views/6dca-aqww.json")
    metadata = json.loads(path.read_bytes())
    if metadata["name"] != "Legacy - Futures Only":
        raise ValueError("Wrong official report type")
    fields = {c["fieldName"] for c in metadata["columns"]}
    if not set(COT_FIELDS.values()) <= fields:
        raise ValueError("Official schema changed")
    def one(item):
        symbol, code = item
        where = (f"cftc_contract_market_code='{code}' AND report_date_as_yyyy_mm_dd >= '2015-01-01T00:00:00' "
                 "AND report_date_as_yyyy_mm_dd <= '2026-09-18T23:59:59'")
        params = {"$where": where, "$limit": "2000", "$order": "report_date_as_yyyy_mm_dd",
                  "$select": ",".join(["id", "cftc_contract_market_code", "report_date_as_yyyy_mm_dd", *COT_FIELDS.values()])}
        p, receipt = get_http(out, f"cot-{symbol}.json", base + "/resource/6dca-aqww.json?" + urlencode(params))
        cp, _ = get_http(out, f"cot-{symbol}-count.json", base + "/resource/6dca-aqww.json?" +
                        urlencode({"$where": where, "$select": "count(*)"}))
        rows = json.loads(p.read_bytes())
        if len(rows) != int(json.loads(cp.read_bytes())[0]["count"]) or len(rows) >= 2000:
            raise ValueError("Official response truncated")
        print("CFTC", symbol, len(rows), flush=True)
        return {"symbol": symbol, "rows": len(rows), **receipt}
    with ThreadPoolExecutor(max_workers=3) as pool:
        result = list(pool.map(one, COT_CODES.items()))
    save(out / "cot-fetch-results.json", encode(result))


def fetch(out):
    results = []
    def one(item):
        name, url = item
        try:
            path, meta = get_http(out, name, url)
            result = {"name": name, "status": "FETCHED", **meta, "path": str(path.resolve())}
        except Exception as exc:
            result = {"name": name, "url": url, "status": "FETCH_FAILED", "error_type": type(exc).__name__}
        print(name, result["status"], flush=True)
        return result
    results.extend(one(x) for x in URLS.items())
    listing = out / "official/cftc-compressed.html"
    if listing.exists():
        page = listing.read_text()
        jobs = []
        for year in range(2015, 2027):
            rel = f"/files/dea/history/deacot{year}.zip"
            if rel not in page:
                raise ValueError(f"Annual source URL not present in official listing: {year}")
            jobs.append((f"deacot{year}.zip", "https://www.cftc.gov" + rel))
        with ThreadPoolExecutor(max_workers=3) as pool:
            results.extend(pool.map(one, jobs))
    save(out / "fetch-results.json", encode(results))


def load_exact_macro(policy_root):
    mirror = policy_root / "bronze_mirror"
    proof = json.loads((policy_root / "bronze_policy.json").read_bytes())
    def read(uri):
        prefix = f"s3://{BUCKET}/"
        if not uri.startswith(prefix + PREFIX):
            raise ValueError("Out-of-scope source URI")
        path = mirror / uri.removeprefix(prefix)
        body = path.read_bytes()
        meta = json.loads(path.with_suffix(path.suffix + ".download.json").read_bytes())
        if meta["s3_uri"] != uri or meta["sha256"] != sha(body):
            raise ValueError("S3 mirror receipt/hash mismatch")
        return body
    run_body = read(proof["run_uri"])
    if sha(run_body) != proof["run_sha256"]:
        raise ValueError("Run hash mismatch")
    run = json.loads(run_body)
    if run["complete"] is not True:
        raise ValueError("Incomplete source")
    proof_parts = {p["uri"]: p for p in proof["partitions"]}
    rows, lineage = defaultdict(list), []
    for part in run["partitions"]:
        uri = part["selection_manifest_uri"]
        pm_body = read(uri)
        pm = json.loads(pm_body)
        raw_body = read(pm["source_object_uri"])
        obs_body = read(pm["object_uri"])
        rm_body = read(pm["source_object_uri"].rsplit("/", 1)[0] + "/manifest.json")
        rm = json.loads(rm_body)
        if not (pm["complete"] and rm["complete"] and rm["status_code"] == 200):
            raise ValueError("Incomplete partition")
        if not (sha(pm_body) == proof_parts[uri]["sha256"] and
                sha(raw_body) == pm["source_sha256"] == rm["sha256"] and sha(obs_body) == pm["sha256"]):
            raise ValueError("Source/projection hash mismatch")
        if len(raw_body) != rm["content_length"] or len(obs_body) != pm["content_length"]:
            raise ValueError("Byte length mismatch")
        if rm["received_at"] != pm["received_at"]:
            raise ValueError("Changed receipt")
        received = datetime.fromisoformat(rm["received_at"])
        if received.tzinfo is None or received > datetime.now(timezone.utc):
            raise ValueError("Invalid receipt time")
        raw, obs = json.loads(raw_body), json.loads(obs_body)
        if len(obs) != pm["selected_row_count"] or len(obs) != part["selected_row_count"]:
            raise ValueError("Partition row count mismatch")
        for row in obs:
            if row["payload"] != raw[row["source_row_index"]]:
                raise ValueError("Raw projection mismatch")
            rows[row["series_id"]].append({**row, "audit_source_uri": pm["source_object_uri"],
                                           "audit_received_at": received.isoformat()})
        lineage.append({"uri": uri, "sha256": sha(pm_body), "rows": len(obs),
                        "raw_sha256": sha(raw_body), "projection_sha256": sha(obs_body)})
    counts = {s: len(r) for s, r in rows.items()}
    if counts != run["rows_by_series"] or sum(counts.values()) != run["selected_row_count"]:
        raise ValueError("Source totals mismatch")
    return rows, {"run": proof["run_uri"], "run_sha256": sha(run_body), "partitions": lineage,
                  "source": "EXACT_S3_MIRROR_REHASHED", "s3_network_refetched_this_run": False}


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def quality(symbol, rows, kind):
    payloads = [r["payload"] for r in rows]
    dates = [p["date"] for p in payloads]
    fields = ["actual", "previous", "estimate"] if kind == "macro" else list(COT_FIELDS) if kind == "cot" else ["open", "high", "low", "close", "volume"]
    nulls = {f: sum(p.get(f) is None for p in payloads) for f in fields}
    issues, bydate = [], defaultdict(list)
    for row in rows:
        p = row["payload"]
        day = p["date"]
        datetime.fromisoformat(day)
        bydate[day].append(row)
        required = ["actual"] if kind == "macro" else fields
        errors = [f"NONNUMERIC_OR_NULL:{f}" for f in required if not numeric(p.get(f))]
        if kind in ("etf", "fx", "index") and all(numeric(p.get(f)) for f in fields):
            if min(p[f] for f in ("open", "high", "low", "close")) <= 0:
                errors.append("NONPOSITIVE_PRICE")
            if p["low"] > min(p["open"], p["close"]) + 1e-8 or p["high"] + 1e-8 < max(p["open"], p["close"]) or p["high"] < p["low"]:
                errors.append("OHLC_RANGE_INCONSISTENT")
            if p["volume"] < 0:
                errors.append("NEGATIVE_VOLUME")
        if kind == "cot" and all(numeric(p.get(f)) for f in fields):
            if any(p[f] < 0 or int(p[f]) != p[f] for f in fields):
                errors.append("INVALID_CONTRACT_COUNT")
            for side in ("Long", "Short"):
                total = p[f"noncommPositions{side}All"] + p["noncommPositionsSpreadAll"] + p[f"commPositions{side}All"]
                if total != p[f"totReptPositions{side}All"] or total + p[f"nonreptPositions{side}All"] != p["openInterestAll"]:
                    errors.append("POSITION_IDENTITY:" + side)
            if p.get("cftcContractMarketCode") != COT_CODES[symbol]:
                errors.append("CONTRACT_IDENTITY_MISMATCH")
        if errors:
            issues.append({"date": day, "reasons": errors, "raw_uri": row["audit_source_uri"],
                           "source_row_index": row["source_row_index"], "payload": p})
    duplicates = [{"date": d, "count": len(v), "payloads": [x["payload"] for x in v]} for d, v in sorted(bydate.items()) if len(v) > 1]
    result = {"series_id": symbol, "kind": kind, "rows": len(rows), "first": min(dates), "latest": max(dates),
              "source_integrity": "PASS", "field_null_counts": nulls,
              "field_null_rates": {f: n / len(rows) for f, n in nulls.items()},
              "duplicate_excess": sum(x["count"] - 1 for x in duplicates), "duplicates": duplicates,
              "weekday_counts": dict(sorted(Counter(datetime.fromisoformat(d[:10]).strftime("%A") for d in dates).items())),
              "quality_issue_rows": len(issues), "quality_issues": issues,
              "basic_quality": "ISSUES_FOUND" if issues or duplicates else "PASS",
              "independent_value_check": "NOT_PERFORMED",
              "historical_pit": "EVIDENCE_INCOMPLETE", "new_approval_issued": False}
    if kind == "macro":
        result["unit_counts"] = dict(Counter(str(p.get("unit")) for p in payloads))
        result["currency_counts"] = dict(Counter(str(p.get("currency")) for p in payloads))
        result["events_without_month_label"] = sum(not re.search(r"\((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\)", p.get("event", "")) for p in payloads)
        result["provider_utc_to_kst_changes_month"] = sum((datetime.fromisoformat(d) + timedelta(hours=9)).strftime("%Y-%m") != d[:7] for d in dates)
        result["provider_timezone_documentation"] = "UTC; documentary definition only, not row-level actual publication proof"
    elif kind in ("etf", "index"):
        # US day-end is after KST midnight: a US month-end close can belong to next KST month.
        result["us_date_to_next_kst_day_changes_month"] = sum((datetime.fromisoformat(d[:10]) + timedelta(days=1)).strftime("%Y-%m") != d[:7] for d in dates)
        result["time_check_is_sensitivity_not_approved_known_at"] = True
    return result


def compare_cot(symbol, rows, official):
    index = {}
    for p in official:
        code, day = p["cftc_contract_market_code"], p["report_date_as_yyyy_mm_dd"][:10]
        if code != COT_CODES[symbol] or day in index:
            raise ValueError("Wrong contract or duplicate official COT date")
        index[day] = p
    matches, absent, differences, compared = 0, [], [], 0
    local_dates = set()
    for row in rows:
        p = row["payload"]
        day = p["date"][:10]
        local_dates.add(day)
        if day not in index:
            absent.append(day)
            continue
        other = index[day]
        delta = {}
        for fmp, cftc in COT_FIELDS.items():
            if cftc not in other:
                raise ValueError("Missing official COT field")
            expected = int(other[cftc])
            compared += 1
            if not numeric(p.get(fmp)) or p[fmp] != expected:
                delta[fmp] = {"fmp": p.get(fmp), "cftc": expected}
        if delta:
            differences.append({"date": day, "fields": delta})
        else:
            matches += 1
    missing = sorted(set(index) - local_dates)
    return {"status": "PASS" if not differences and not absent and not missing else "DISCREPANCY",
            "fields": COT_FIELDS, "compared_values": compared, "matched_rows": matches,
            "different_rows": len(differences), "differences": differences,
            "fmp_dates_absent_official": absent, "official_dates_missing_fmp": missing,
            "vintage_scope": "CURRENT_OFFICIAL_HISTORY_ONLY", "first_vintage_proven": False}


def evidence_inventory(out, old):
    result = []
    for folder in (out / "official", old):
        for p in sorted(folder.glob("*.receipt.json")):
            meta = json.loads(p.read_bytes())
            body = p.with_name(p.name.removesuffix(".receipt.json"))
            if sha(body.read_bytes()) != meta["sha256"]:
                raise ValueError("Changed external evidence")
            result.append({"path": str(body.resolve()), **meta})
    return result


def audit(out, data_root, policy_root, old):
    if (out / "audit.json").exists():
        raise FileExistsError("Use a new audit output directory")
    rows, macro_lineage = load_exact_macro(policy_root)
    kinds = {s: "macro" for s in rows}
    lineage = [macro_lineage]
    suffix = "snapshot=backfill-20260920/runs/from=2015-01-01/to=2026-09-18/manifest.json"
    for version in ("korea-external-v1", "korea-risk-v1"):
        path = data_root / "regime/fmp-external" / version / suffix
        external, proof = load_run(path)
        if set(rows) & set(external):
            raise ValueError("Overlapping source series")
        rows.update(external)
        lineage.append(proof)
        spec = json.loads(path.read_bytes())["contract"]["scope"]
        kinds.update({s: spec[s]["kind"] for s in external})
    if len(rows) != 37 or sum(map(len, rows.values())) != 47483:
        raise ValueError("Unexpected frozen inventory")
    evidence = evidence_inventory(out, old)
    stats, comparisons = [], {}
    for symbol in sorted(rows):
        result = quality(symbol, rows[symbol], kinds[symbol])
        if kinds[symbol] == "cot":
            p = out / "official" / f"cot-{symbol}.json"
            result["official_comparison"] = compare_cot(symbol, rows[symbol], json.loads(p.read_bytes()))
            result["independent_value_check"] = result["official_comparison"]["status"]
            result["known_release_exception_rows"] = sum(r["payload"]["date"][:10] in COT_EXCEPTIONS for r in rows[symbol])
            result["remaining_requirements"] = ["ACTUAL_RELEASE_AND_CORRECTION_CALENDAR", "FIRST_VINTAGE_VALUES"]
        elif kinds[symbol] == "index":
            result["official_comparison"] = compare_cboe(rows[symbol], (old / f"{symbol[1:]}_History.csv").read_bytes())
            result["independent_value_check"] = "DISCREPANCY" if result["official_comparison"]["mismatch_count"] or result["official_comparison"]["fmp_dates_absent_from_official"] else "PASS"
            result["remaining_requirements"] = ["RESOLVE_VALUE_DIFFERENCES", "RESTATEMENT_VINTAGES", "VERIFIED_KST_AVAILABILITY"]
        elif kinds[symbol] == "macro":
            result["remaining_requirements"] = ["REFERENCE_PERIOD_AND_UNITS", "ORIGINAL_RELEASE_VALUES", "ACTUAL_PUBLICATION_DATES"]
        elif kinds[symbol] == "fx":
            result["remaining_requirements"] = ["EXACT_EOD_SESSION_AND_DST_CONTRACT", "INDEPENDENT_SAME_FIXING_VALUES", "CORRECTION_HISTORY"]
        else:
            result["remaining_requirements"] = ["INDEPENDENT_EXCHANGE_CLOSE_VALUES", "SPLIT_ADJUSTMENT_SCOPE", "CORRECTION_HISTORY", "VERIFIED_KST_AVAILABILITY"]
        if symbol == "KR_POLICY_RATE":
            result["historical_pit"] = "EXISTING_SCOPED_MONTH_END_APPROVAL"
            result["remaining_requirements"] = ["RAW_EVENT_FIELDS_NOT_APPROVED"]
        stats.append(result)
    document = {"schema_version": "fmp-remaining-validation-v1", "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "series_count": len(stats), "remaining_series_count": 36, "rows_examined": 47483,
                "remaining_rows_examined": 47483 - len(rows["KR_POLICY_RATE"]),
                "source_integrity": "PASS", "new_pit_approvals": 0,
                "fmp_api_calls": 0, "bronze_mutated": False, "campaigns_modified": False,
                "factor_results_or_oos_read": False, "series": stats, "lineage": lineage, "evidence": evidence}
    save(out / "audit.json", encode(document))
    print(json.dumps({k: document[k] for k in ("series_count", "remaining_rows_examined", "source_integrity", "new_pit_approvals")}))
    for s in stats:
        extra = s.get("official_comparison", {})
        print(s["series_id"], s["rows"], s["basic_quality"], s["quality_issue_rows"], s["independent_value_check"], extra.get("different_rows", extra.get("mismatch_count", "")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--fetch-cot-api", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--data-root", type=Path, default=Path("/Users/mac/Documents/GitHub/TeamAlpha-data/data"))
    parser.add_argument("--policy-root", type=Path, default=Path("output/regime_inputs/kr-policy-pit-20260920"))
    parser.add_argument("--prior-evidence", type=Path, default=Path("output/pit_audit/fmp-20260920/evidence"))
    args = parser.parse_args()
    if args.fetch:
        fetch(args.output)
    if args.fetch_cot_api:
        fetch_cot_api(args.output)
    if args.audit:
        audit(args.output, args.data_root, args.policy_root, args.prior_evidence)
