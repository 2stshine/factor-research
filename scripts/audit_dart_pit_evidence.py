"""Read-only audit of the local DART financial Bronze PIT evidence.

This never treats a quality status, valid receipt number, or filesystem mtime as
proof that an API response was the value published in the historical receipt.
No campaign, factor result, or database is read by this script. The optional
bounded sample check reads public official disclosure pages, without API keys.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.request


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_helpers(source: Path) -> dict:
    """Execute only the exact pure functions/constants being audited."""
    tree = ast.parse(source.read_text())
    names = {"METRIC_MAP", "REPRT", "_DT_RE"}
    functions = {"_filed_from_rcept", "_available_date", "_period_end_from_dt", "_amount"}
    kept = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in names for t in node.targets
        ):
            kept.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            kept.append(node)
    env = {"date": date, "timedelta": timedelta, "re": re}
    exec(compile(ast.Module(body=kept, type_ignores=[]), str(source), "exec"), env)
    if not (names | functions).issubset(env):
        raise ValueError("Audited source helpers changed; review before continuing")
    return env


def analyze_rows(rows: list, source: Path, helpers: dict) -> dict:
    count = Counter(raw_rows=len(rows))
    receipts = set()
    examples = []
    match = re.search(r"year=(\d{4})/corp=([^/]+)/([^/]+)\.json$", source.as_posix())
    if not match:
        raise ValueError(f"Unexpected source layout: {source}")
    year, ticker, stem = match.groups()
    code = stem[:5]
    period = helpers["REPRT"].get(code)
    if period is None:
        return {"counts": {"unrecognized_report_file": 1}, "receipts": [], "examples": []}
    fp, month, day = period
    for r in rows:
        receipt = str(r.get("rcept_no") or "")
        if receipt:
            receipts.add(receipt)
        filed = helpers["_filed_from_rcept"](receipt)
        if filed is None:
            count["raw_rows_without_parseable_receipt_date"] += 1
        if not re.fullmatch(r"\d{14}", receipt):
            count["raw_rows_without_14_digit_receipt"] += 1
        if r.get("account_nm") not in helpers["METRIC_MAP"]:
            count["unmapped_metric_rows"] += 1
            continue
        count["mapped_metric_rows"] += 1
        amount = helpers["_amount"](r.get("thstrm_amount"))
        if amount is None:
            count["mapped_missing_or_invalid_amount_rows"] += 1
            continue
        count["mapped_numeric_rows_before_silver_quality_filter"] += 1
        if str(r.get("stock_code") or "") != ticker:
            count["mapped_numeric_ticker_mismatch"] += 1
        if str(r.get("reprt_code") or "") != code:
            count["mapped_numeric_report_mismatch"] += 1
        end = helpers["_period_end_from_dt"](r.get("thstrm_dt"))
        if end is None:
            count["mapped_numeric_period_end_fallback_rows"] += 1
            end = date(int(r.get("bsns_year") or year), month, day)
        available = helpers["_available_date"](end, fp, filed)
        if filed is None:
            count["mapped_numeric_assumed_deadline_availability_rows"] += 1
        elif filed < end:
            count["mapped_numeric_receipt_before_period_end_rows"] += 1
        if not receipt:
            count["mapped_numeric_fallback_revision_key_rows"] += 1
        if r.get("rcept_dt"):
            count["mapped_numeric_rows_with_explicit_rcept_dt"] += 1
        if (filed is None or end > available) and len(examples) < 3:
            examples.append({"file": str(source), "receipt": receipt,
                             "period_end": end.isoformat(),
                             "available_date": available.isoformat(),
                             "account_nm": r.get("account_nm")})
    return {"counts": dict(count), "receipts": sorted(receipts), "examples": examples}


def audit(repo: Path, upstream: Path) -> dict:
    silver_file = upstream / "pipeline/silver/financials.py"
    helpers = source_helpers(silver_file)
    root = upstream / "data/financials/dart"
    counts = Counter({key: 0 for key in (
        "raw_rows_without_parseable_receipt_date",
        "raw_rows_without_14_digit_receipt",
        "mapped_numeric_assumed_deadline_availability_rows",
        "mapped_numeric_fallback_revision_key_rows",
        "mapped_numeric_period_end_fallback_rows",
        "mapped_numeric_receipt_before_period_end_rows",
        "mapped_numeric_ticker_mismatch",
        "mapped_numeric_report_mismatch",
        "mapped_numeric_rows_with_explicit_rcept_dt",
        "files_with_multiple_receipt_ids",
    )})
    yearly = {}
    receipts = set()
    tickers = set()
    manifest = hashlib.sha256()
    examples = []
    receipt_min = receipt_max = None
    multiple_receipt_files = []
    for i, path in enumerate(sorted(root.glob("year=*/corp=*/*.json")), 1):
        body = path.read_bytes()
        rows = json.loads(body)
        if not isinstance(rows, list):
            raise ValueError(f"Expected raw row list: {path}")
        d = analyze_rows(rows, path, helpers)
        year = path.parts[-3].split("=", 1)[1]
        tickers.add(path.parts[-2].split("=", 1)[1])
        counts.update(d["counts"])
        counts["files"] += 1
        yearly.setdefault(year, Counter()).update(d["counts"])
        yearly[year]["files"] += 1
        receipts.update(d["receipts"])
        dates = [helpers["_filed_from_rcept"](x) for x in d["receipts"]]
        dates = [x for x in dates if x is not None]
        if dates:
            receipt_min = min([min(dates)] + ([receipt_min] if receipt_min else []))
            receipt_max = max([max(dates)] + ([receipt_max] if receipt_max else []))
        if len(d["receipts"]) > 1:
            counts["files_with_multiple_receipt_ids"] += 1
            if len(multiple_receipt_files) < 10:
                multiple_receipt_files.append({"file": str(path), "receipt_ids": d["receipts"]})
        if len(examples) < 20:
            examples.extend(d["examples"][:20-len(examples)])
        manifest.update((str(path.relative_to(root)) + "\0" + hashlib.sha256(body).hexdigest() + "\n").encode())
        if i % 20000 == 0:
            print(f"DART read-only scan: {i:,} source files", flush=True)
    safe_bind = [silver_file, upstream / "pipeline/bronze/financials.py",
                 upstream / "pipeline/bronze/dart_full_statements.py",
                 upstream / "pipeline/common/sink.py", repo / "engine/fundamentals.py",
                 repo / "engine/silver.py"]
    return {
        "schema_version": "dart-pit-evidence-audit-v1",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "status": "HISTORICAL_VINTAGE_NOT_VERIFIED",
        "pit_approved": False,
        "scope": "All local legacy major-account Bronze files; not a live RDS certification",
        "counts": dict(counts), "ticker_count": len(tickers), "unique_receipt_ids": len(receipts),
        "receipt_date_range": [str(receipt_min), str(receipt_max)],
        "yearly": {y: dict(c) for y, c in sorted(yearly.items())},
        "raw_source_manifest_sha256": manifest.hexdigest(),
        "raw_manifest_algorithm": "sorted relative path + NUL + SHA256(body) + newline",
        "source_root": str(root),
        "source_code_bindings": [{"path": str(p), "sha256": digest(p)} for p in safe_bind],
        "examples": examples, "multiple_receipt_file_examples": multiple_receipt_files,
        "source_availability": {
            "regular_disclosure_directory_exists": (upstream / "data/financials/dart_disclosures").exists(),
            "legacy_full_statement_directory_exists": (upstream / "data/financials/dart_full").exists(),
            "note": "Absence is local only; remote S3 completeness has not been established."
        },
        "verified_behaviors": [
            "Research replays retained revisions by available_date and backward as-of joins.",
            "Research does not read fundamental_current for historical features.",
            "Major-account collection is scoped by company/year/report, not receipt or historical as-of.",
            "Major-account files can be replaced in-place when response content changes.",
            "Silver replaces/updates rows inside the same revision_key rather than retaining response vintages.",
            "A valid receipt prefix supplies filed date; official list rcept_dt is not joined in this pipeline.",
            "The pure fallback uses a statutory deadline, which does not prove real publication."
        ],
        "not_proven": [
            "Each amount equals the archived original/particular correction receipt body.",
            "Every relevant first and correction filing is retained.",
            "Receipt prefix dates equal authoritative publication dates for all financial receipts.",
            "Exact live RDS input row counts or same-receipt overwrite history.",
            "The local filesystem modification time is the historical publication/receipt time."
        ],
        "live_database_attempt": {"status": "UNAVAILABLE", "exception_type": "EndpointConnectionError",
                                  "query_executed": False,
                                  "note": "Read-only connection could not reach configured secret endpoint; no credentials printed."},
        "minimum_remediation": [
            "Bind each used financial metric to receipt-addressed official original or correction evidence and immutable response hash.",
            "Join official disclosure rcept_dt; fail closed when actual publication evidence is missing, never use statutory deadline as proof.",
            "Preserve source response versions for the same receipt and detect changed values before publication.",
            "Compare the complete disclosure ledger against retained financial filings; report missing originals/corrections.",
            "After evidence reconstruction, query the live exact research cohort and approve only verified fields/periods."
        ],
        "mutations": {"bronze": False, "database": False, "campaign": False, "approval_registry": False},
    }


def render(report: dict) -> str:
    c = report["counts"]
    lines = ["# DART financial PIT evidence audit", "", "Status: **HISTORICAL_VINTAGE_NOT_VERIFIED**. No new approval.", "",
             "This is a full scan of the local major-account Bronze, not all live Silver rows.", "",
             f"- Files: {c.get('files', 0):,}; raw rows: {c.get('raw_rows', 0):,}; tickers: {report['ticker_count']:,}.",
             f"- Mapped numeric rows before Silver quality exclusions: {c.get('mapped_numeric_rows_before_silver_quality_filter', 0):,}.",
             f"- Assumed-deadline availability rows among these: {c.get('mapped_numeric_assumed_deadline_availability_rows', 0):,}.",
             f"- Period-end fallback rows: {c.get('mapped_numeric_period_end_fallback_rows', 0):,}.",
             f"- Unique receipts: {report['unique_receipt_ids']:,}; receipt-prefix date range: {' through '.join(report['receipt_date_range'])}.",
             "", "## Verified code behavior", ""]
    lines += [f"- {s}" for s in report["verified_behaviors"]]
    lines += ["", "## Evidence not established", ""]
    lines += [f"- {s}" for s in report["not_proven"]]
    lines += ["", "The read-only database connection failed at the configured secret endpoint (EndpointConnectionError), before SQL execution. Local file counts must not be reported as certified live rows.",
              "", "## Minimal next actions", ""]
    lines += [f"- {s}" for s in report["minimum_remediation"]]
    lines += ["", "Code bindings and the raw-file aggregate digest are in dart_review.json. No originals, database records, campaigns, or approval registry were changed.", ""]
    return "\n".join(lines)


def check_correction_samples(upstream: Path, output: Path) -> dict:
    """Three deterministic long-lag cases; never infer value differences."""
    examples = [("000270", "20211210000418", "20160330004381"),
                ("002880", "20210218001076", "20160330003994"),
                ("003160", "20230309000352", "20160330002579")]
    evidence = output / "dart_official"
    evidence.mkdir(parents=True, exist_ok=True)
    findings = []
    for ticker, current, original in examples:
        raw = upstream / f"data/financials/dart/year=2015/corp={ticker}/11011.json"
        rows = json.loads(raw.read_bytes())
        actual = sorted({str(r.get("rcept_no") or "") for r in rows})
        if actual != [current]:
            raise ValueError("Snapshot changed; sample requires re-review")
        documents = []
        for receipt in (current, original):
            url = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + receipt
            target = evidence / f"{receipt}.html"
            if target.exists():
                raise FileExistsError(target)
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read()
            target.write_bytes(body)
            page = body.decode("utf-8", "replace")
            options = {}
            for value, text in re.findall(r'<option[^>]*value="([^"]+)"[^>]*>(.*?)</option>', page, re.S):
                if re.fullmatch(r"rcpNo=\d{14}", value):
                    options[value[6:]] = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()
            if original not in options or current not in options:
                raise ValueError("Official main selector lacks expected historical family")
            if "[정정]" not in options[current] or "[정정]" in options[original]:
                raise ValueError("Official correction/original role differs")
            title = re.search(r"<title>(.*?)</title>", page, re.S)
            documents.append({"url": url, "path": str(target.resolve()),
                              "sha256": hashlib.sha256(body).hexdigest(),
                              "received_at": datetime.now(timezone.utc).isoformat(),
                              "title": re.sub(r"\s+", " ", title.group(1)).strip() if title else None,
                              "official_main_family": options})
        findings.append({"ticker": ticker, "business_year": "2015", "report_code": "11011",
                         "local_source": str(raw), "source_sha256": digest(raw),
                         "local_rows": len(rows), "local_receipt_ids": actual,
                         "current_receipt": current, "original_receipt": original,
                         "current_is_official_correction": True,
                         "original_receipt_present_in_this_local_scope": original in actual,
                         "original_value_compared": False, "documents": documents})
    result = {"schema_version": "dart-correction-samples-v1", "sample_count": len(findings),
              "selection_rule": "First three sorted 2015 annual scopes with receipt year >= 2019 (bounded audit, not representative rate)",
              "confirmed": "Three local annual financial snapshots contain a later official correction and not their official original receipt.",
              "not_claimed": "No value difference, live RDS absence, or look-ahead contamination has been established by these selector checks.",
              "samples": findings}
    target = output / "dart_correction_samples.json"
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, default=Path("/Users/mac/Documents/GitHub/TeamAlpha-data"))
    parser.add_argument("--output", type=Path, default=Path("output/pit_review_20260921"))
    parser.add_argument("--check-correction-samples", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    if args.check_correction_samples:
        result = check_correction_samples(args.upstream, args.output)
        print(json.dumps({"sample_count": result["sample_count"], "confirmed": result["confirmed"]}))
        return
    report = audit(repo, args.upstream)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in [("dart_review.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                          ("dart_review.md", render(report))]:
        path = args.output / name
        if path.exists():
            raise FileExistsError(f"Preserve prior audit: {path}")
        path.write_text(content)
    print(json.dumps({"status": report["status"], "counts": report["counts"],
                      "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
