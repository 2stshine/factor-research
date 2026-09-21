"""Read-only source audit of FMP Bronze. Never manufactures PIT approvals.

Outputs are immutable audit artifacts, not Bronze edits or Silver publication.
The macro replay is explicitly NOT asserted identical to the later S3 snapshot.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import html
import io
import csv
import json
from pathlib import Path
import re
import urllib.request


URLS = {
    "bok_rates.html": "https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643",
    "bok_meetings.html": "https://www.bok.or.kr/portal/singl/crncyPolicyDrcMtg/listYear.do?menuNo=200755&mtgSe=A",
    "cftc_announcements.html": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalSpecialAnnouncements/index.htm",
    "cftc_archive.html": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/index.htm",
    "cboe_history.html": "https://www.cboe.com/tradable_products/vix/vix_historical_data",
    "VVIX_History.csv": "https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv",
    "VIX9D_History.csv": "https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv",
    "VIX3M_History.csv": "https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv",
    "cboe_policies.pdf": "https://cdn.cboe.com/resources/indices/governance/Cboe_Index_Policies_Practices.pdf",
    "bok_emergency_20200316.html": "https://www.bok.or.kr/portal/bbs/B0000169/view.do?depth=201295&menuNo=201295&nttId=10057043&oldMenuNo=201151&programType=multiCont&relate=Y",
}

# Latest revised catch-up schedule, Dec 9 2025, not the superseded Nov schedule.
# These are targeted counterexamples, NOT a complete historical release calendar.
COT_EXCEPTIONS = {
    "2025-01-07": "2025-01-13",
    "2025-09-30": "2025-11-19", "2025-10-07": "2025-11-21",
    "2025-10-14": "2025-11-25", "2025-10-21": "2025-12-02",
    "2025-10-28": "2025-12-05", "2025-11-04": "2025-12-09",
    "2025-11-10": "2025-12-10", "2025-11-18": "2025-12-12",
    "2025-11-25": "2025-12-15", "2025-12-02": "2025-12-17",
    "2025-12-09": "2025-12-19", "2025-12-16": "2025-12-23",
}


def sha(body):
    return hashlib.sha256(body).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def write_new(path, value):
    body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(body)


def fetch_evidence(out):
    for name, url in URLS.items():
        path = out / "evidence" / name
        meta = path.with_suffix(path.suffix + ".receipt.json")
        if path.exists() and meta.exists():
            receipt = json.loads(meta.read_bytes())
            if receipt["sha256"] != sha(path.read_bytes()) or receipt["url"] != url:
                raise ValueError("Evidence cache hash/URL mismatch")
            continue
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PIT-data-audit"})
            with urllib.request.urlopen(request, timeout=25) as response:
                body = response.read()
                receipt = {"url": url, "final_url": response.url, "status": response.status,
                           "received_at": datetime.now(timezone.utc).isoformat(),
                           "sha256": sha(body), "bytes": len(body),
                           "content_type": response.headers.get("Content-Type")}
            write_new(path, body)
            write_new(meta, receipt)
            print(name, receipt["status"], receipt["bytes"], flush=True)
        except Exception as exc:
            # Do not log credentials/request headers. All URLs are public.
            print(name, type(exc).__name__, flush=True)


def load_run(path, *, macro=False):
    run_body = path.read_bytes()
    run = json.loads(run_body)
    if run.get("complete") is not True:
        raise ValueError("Incomplete input run")
    rows, proofs = defaultdict(list), []
    for part in run["partitions"]:
        if part["from"] < "2015-01-01":
            continue
        pm_path = Path(part["selection_manifest_uri" if macro else "manifest_uri"])
        pm_body = pm_path.read_bytes()
        pm = json.loads(pm_body)
        raw_path, obs_path = Path(pm["source_object_uri"]), Path(pm["object_uri"])
        raw_body, obs_body = raw_path.read_bytes(), obs_path.read_bytes()
        rm_path = raw_path.with_name("manifest.json")
        rm_body = rm_path.read_bytes()
        rm = json.loads(rm_body)
        if not (pm["complete"] and rm["complete"] and rm["status_code"] == 200):
            raise ValueError("Bad source receipt")
        if not (sha(raw_body) == pm["source_sha256"] == rm["sha256"] and sha(obs_body) == pm["sha256"]):
            raise ValueError("Raw/projection hash mismatch")
        if len(raw_body) != rm["content_length"] or len(obs_body) != pm["content_length"]:
            raise ValueError("Raw/projection byte-length mismatch")
        received = datetime.fromisoformat(rm["received_at"])
        if received.tzinfo is None or received > datetime.now(timezone.utc):
            raise ValueError("Invalid receipt timestamp")
        if pm["received_at"] != rm["received_at"]:
            raise ValueError("Changed receipt timestamp")
        originals, observations = json.loads(raw_body), json.loads(obs_body)
        count = "selected_row_count" if macro else "row_count"
        if len(observations) != pm[count] or len(observations) != part[count]:
            raise ValueError("Partition row-count mismatch")
        for row in observations:
            if row["payload"] != originals[row["source_row_index"]]:
                raise ValueError("Raw projection mismatch")
            if not macro:
                if row["payload_sha256"] != sha(encoded(row["payload"])):
                    raise ValueError("Row hash mismatch")
                if row["observed_at"] != rm["received_at"] or row["system_known_at"] != rm["received_at"]:
                    raise ValueError("Backdated system knowledge")
            rows[row["series_id"]].append({**row, "audit_received_at": rm["received_at"],
                "audit_source_uri": str(raw_path), "audit_manifest": str(pm_path)})
        proofs.append({"partition": str(pm_path), "manifest_sha256": sha(pm_body),
                       "raw_uri": str(raw_path), "raw_sha256": sha(raw_body),
                       "raw_receipt_sha256": sha(rm_body), "projection_sha256": sha(obs_body),
                       "rows": len(observations), "received_at": rm["received_at"]})
    return rows, {"run": str(path), "run_sha256": sha(run_body), "partitions": proofs,
                  "macro_replay_not_live_s3_snapshot": macro}


def parse_bok_rates(body):
    # Only table rows, excluding JavaScript/chart labels and commented old HTML.
    page = re.sub(r"<!--.*?-->", "", body.decode(), flags=re.S)
    rates = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)]
        if len(cells) != 3 or not re.fullmatch(r"\d{4}", cells[0]):
            continue
        day = re.fullmatch(r"(\d{1,2})월\s*(\d{1,2})일", cells[1])
        if day:
            date = f"{cells[0]}-{int(day[1]):02}-{int(day[2]):02}"
            value = float(cells[2])
            if date in rates and rates[date] != value:
                raise ValueError("Conflicting official policy rates")
            rates[date] = value
    if len(rates) < 20:
        raise ValueError("Unrecognized BOK table")
    return sorted(rates.items())


def policy_comparison(rows, rates):
    comparisons = []
    for row in rows:
        p = row["payload"]
        # A sensitivity check of the manifest's claimed UTC convention; NOT certification.
        assumed_kst = datetime.fromisoformat(p["date"]) + timedelta(hours=9)
        day = str(assumed_kst.date())
        eligible = [(d, v) for d, v in rates if d <= day]
        expected = eligible[-1][1] if eligible else None
        comparisons.append({"provider_date": p["date"], "assumed_kst": assumed_kst.isoformat(),
            "actual": p.get("actual"), "official_effective_rate": expected,
            "matches_effective_date_rate": p.get("actual") == expected,
            "official_rate_date": eligible[-1][0] if eligible else None,
            "source_row_index": row["source_row_index"], "raw_uri": row["audit_source_uri"]})
    return comparisons


def compare_cboe(rows, body):
    records = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
    official = {}
    for r in records:
        r = {k.strip().upper(): v for k, v in r.items() if k}
        date = datetime.strptime(r["DATE"], "%m/%d/%Y").strftime("%Y-%m-%d")
        close = float(r.get("CLOSE", r.get("VVIX")))
        if date in official:
            raise ValueError("Duplicate official index date")
        official[date] = close
    mismatches, absent, matched = [], [], 0
    for row in rows:
        p = row["payload"]
        day = p["date"][:10]
        if day not in official:
            absent.append(day)
        elif abs(p["close"] - official[day]) <= 1e-6:
            matched += 1
        else:
            mismatches.append({"date": day, "fmp_close": p["close"], "official_close": official[day]})
    local_dates = {r["payload"]["date"][:10] for r in rows}
    missing_local = sorted(d for d in official if min(local_dates) <= d <= max(local_dates) and d not in local_dates)
    return {"official_rows": len(official), "official_latest": max(official), "matched": matched,
            "mismatch_count": len(mismatches), "mismatches": mismatches,
            "fmp_dates_absent_from_official": absent, "official_dates_missing_in_fmp": missing_local,
            "tolerance_absolute": 1e-6, "first_vintage_proven": False}


def verify_cot_exceptions(body):
    """Fail closed if the captured primary-source exception table changed."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", body.decode()))
    text = re.sub(r"\s+", " ", text)
    latest = text.split("December 9, 2025:", 1)[1].split("November 18, 2025:", 1)[0]
    for ref, release in COT_EXCEPTIONS.items():
        if ref == "2025-01-07":
            if "January 07, 2025:" not in text or "Monday, January 13, 2025" not in text:
                raise ValueError("CFTC January exception evidence missing")
            continue
        ref_text = datetime.fromisoformat(ref).strftime("%m/%d/%Y")
        release_text = datetime.fromisoformat(release).strftime("%m/%d/%Y")
        if not re.search(re.escape(ref_text) + r"\s+\d{2}/\d{2}/2025\s+" + re.escape(release_text), latest):
            raise ValueError("CFTC release exception not supported by captured latest schedule")


def series_stats(symbol, rows, kind):
    dates = [x["payload"]["date"] for x in rows]
    groups = defaultdict(list)
    for row in rows:
        groups[row["payload"]["date"]].append(row["payload"])
    duplicates = [{"date": d, "count": len(v), "distinct_payloads": len({encoded(x) for x in v}),
                   "payloads": v} for d, v in groups.items() if len(v) > 1]
    field = "actual" if kind == "macro" else "openInterestAll" if kind == "cot" else "close"
    null_count = sum(r["payload"].get(field) is None for r in rows)
    reasons = {
        "macro": ["RELEASE_TIME_AND_REFERENCE_PERIOD_NOT_INDEPENDENTLY_VERIFIED", "FIRST_RELEASE_VINTAGES_NOT_PROVEN", "EXACT_S3_SNAPSHOT_NOT_LOCALLY_AVAILABLE"],
        "cot": ["POSITION_DATE_IS_NOT_PUBLICATION_DATE", "COMPLETE_EXCEPTION_RELEASE_CALENDAR_MISSING", "HISTORICAL_REVISIONS_NOT_RESOLVED"],
        "index": ["US_CLOSE_TIME_NOT_BOUND_TO_KOREAN_DECISION_CALENDAR", "RESTATEMENT_HISTORY_NOT_RESOLVED"],
        "fx": ["PROVIDER_SESSION_TIMEZONE_AND_FIXING_UNVERIFIED", "HISTORICAL_REVISION_POLICY_UNVERIFIED"],
        "etf": ["US_SESSION_CLOSE_AVAILABILITY_UNVERIFIED", "CORPORATE_ACTION_ADJUSTMENT_VINTAGES_UNVERIFIED"],
    }[kind].copy()
    if duplicates:
        reasons.append("DUPLICATE_TIMESTAMP_REQUIRES_EXPLICIT_RESOLUTION")
    return {"series_id": symbol, "kind": kind, "rows": len(rows), "first": min(dates), "latest": max(dates),
            "tested_value_field": field, "null_value_rows": null_count,
            "missing_released_at": sum(r.get("released_at") is None for r in rows),
            "missing_available_at": sum(r.get("available_at") is None for r in rows),
            "missing_vintage": sum(r.get("vintage") is None for r in rows),
            "weekend_provider_dates": sum(datetime.fromisoformat(d[:10]).weekday() >= 5 for d in dates),
            "duplicates": duplicates, "duplicate_excess": sum(x["count"] - 1 for x in duplicates),
            "received_at_first": min(r["audit_received_at"] for r in rows),
            "received_at_latest": max(r["audit_received_at"] for r in rows),
            "status": "DEFERRED", "pit_approved": False, "historical_backtest_allowed": False,
            "silver_publish_allowed": False, "reasons": reasons}


def audit(data_root, out, evidence_dir=None):
    evidence_dir = evidence_dir or out / "evidence"
    if (out / "audit.json").exists() or (out / "decisions.json").exists():
        raise FileExistsError("Use a new output directory; audit outputs are immutable")
    run_suffix = "runs/from=2015-01-01/to=2026-09-18/manifest.json"
    inputs = [
        (data_root / "macro/fmp/economic-calendar/korea-coverage-v1/snapshot=audit-replay-20260919/runs/from=2014-12-01/to=2026-09-18/manifest.json", True),
        *((data_root / f"regime/fmp-external/{v}/snapshot=backfill-20260920" / run_suffix, False)
          for v in ("korea-external-v1", "korea-risk-v1")),
    ]
    all_rows, kinds, lineage = {}, {}, []
    for path, macro in inputs:
        rows, proof = load_run(path, macro=macro)
        if set(all_rows).intersection(rows):
            raise ValueError("Overlapping input series")
        all_rows.update(rows)
        lineage.append(proof)
        spec = json.loads(path.read_bytes()).get("contract", {}).get("scope", {})
        kinds.update({s: "macro" if macro else spec[s]["kind"] for s in rows})
    stats = [series_stats(s, all_rows[s], kinds[s]) for s in sorted(all_rows)]
    evidence = []
    for p in sorted(evidence_dir.glob("*.receipt.json")):
        meta = json.loads(p.read_bytes())
        body = p.with_name(p.name.removesuffix(".receipt.json"))
        if sha(body.read_bytes()) != meta["sha256"]:
            raise ValueError("Evidence hash changed")
        evidence.append({**meta, "local_path": str(body.resolve())})
    bok_path = evidence_dir / "bok_rates.html"
    policy = policy_comparison(all_rows["KR_POLICY_RATE"], parse_bok_rates(bok_path.read_bytes())) if bok_path.exists() else None
    index_checks = {}
    for symbol in ("^VVIX", "^VIX9D", "^VIX3M"):
        p = evidence_dir / (symbol[1:] + "_History.csv")
        if p.exists():
            index_checks[symbol] = compare_cboe(all_rows[symbol], p.read_bytes())
    cot_counterexamples = []
    announcements = evidence_dir / "cftc_announcements.html"
    if not announcements.exists():
        raise ValueError("CFTC schedule evidence required for counterexamples")
    verify_cot_exceptions(announcements.read_bytes())
    for s, rows in all_rows.items():
        if kinds[s] != "cot":
            continue
        for row in rows:
            day = row["payload"]["date"][:10]
            if day in COT_EXCEPTIONS:
                naive = str((datetime.fromisoformat(day) + timedelta(days=3)).date())
                release = COT_EXCEPTIONS[day]
                cot_counterexamples.append({"series_id": s, "position_date": day, "naive_release_date": naive,
                    "official_scheduled_release_date": release,
                    "lookahead_days_if_plus_3": (datetime.fromisoformat(release) - datetime.fromisoformat(naive)).days,
                    "crosses_month_end": naive[:7] < release[:7], "source": URLS["cftc_announcements.html"],
                    "schedule_is_not_row_level_first_vintage_proof": True})
    for item in stats:
        result = index_checks.get(item["series_id"])
        if result:
            item["independent_current_value_matches"] = result["matched"]
            item["independent_current_value_mismatches"] = result["mismatch_count"]
            if result["mismatch_count"] or result["fmp_dates_absent_from_official"]:
                item["reasons"].append("CURRENT_OFFICIAL_HISTORY_DISCREPANCY_UNRESOLVED")
        if item["kind"] == "cot":
            item["verified_exception_counterexamples"] = sum(x["series_id"] == item["series_id"] for x in cot_counterexamples)
    macro_count = sum(k == "macro" for k in kinds.values())
    approved_count = sum(s["pit_approved"] for s in stats)
    report = {"schema_version": "fmp-historical-pit-audit-v1", "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer": "Codex source-evidence review; not an external certification authority",
        "scope": "2015-01-01..2026-09-18; diagnostics-only historical eligibility",
        "method": "all local raw/projection hashes and row bindings; targeted independent official reconciliation",
        "series_count": len(stats), "rows_examined": sum(x["rows"] for x in stats),
        "exact_backfill_local_series": len(stats) - macro_count, "macro_replay_series_not_s3_recertified": macro_count,
        "historical_approved_series": approved_count, "deferred_series": len(stats) - approved_count,
        "s3_live_rechecked": False, "bronze_mutated": False, "silver_or_gold_published": False,
        "factor_results_or_oos_read": False, "series": stats, "lineage": lineage, "evidence": evidence,
        "policy_rate_effective_date_comparison": policy, "cboe_current_history_comparison": index_checks,
        "cot_release_counterexamples": cot_counterexamples,
        "script_sha256": sha(Path(__file__).read_bytes()),
        "approval_policy": "No series approved from present-day agreement, assumed time lags, or collection success alone."}
    write_new(out / "audit.json", report)
    write_new(out / "decisions.json", {"schema_version": "pit-review-decisions-v1", "reviewed_at": report["reviewed_at"],
        "audit_sha256": sha((out / "audit.json").read_bytes()), "approvals": [], "series": stats})
    print(json.dumps({k: report[k] for k in ("series_count", "rows_examined", "historical_approved_series", "deferred_series")}, ensure_ascii=False))
    print("CBOE", json.dumps({s: {k: v for k, v in x.items() if k not in {"mismatches", "fmp_dates_absent_from_official", "official_dates_missing_in_fmp"}} for s, x in index_checks.items()}))
    if policy:
        print("POLICY", len(policy), "effective-date mismatches", sum(not x["matches_effective_date_rate"] for x in policy))
    print("COT", len(cot_counterexamples), "cross-month", sum(x["crosses_month_end"] for x in cot_counterexamples))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fetch-evidence", action="store_true")
    parser.add_argument("--evidence-dir", type=Path, help="Reuse a checksummed evidence cache without new HTTP calls")
    args = parser.parse_args()
    if args.fetch_evidence:
        fetch_evidence(args.output)
    else:
        if args.data_root is None:
            parser.error("--data-root required for audit")
        audit(args.data_root, args.output, args.evidence_dir)
