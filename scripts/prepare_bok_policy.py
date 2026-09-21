"""Collect immutable official policy decisions and the exact FMP S3 snapshot.

Read-only network access. This collector never grants research approval.
Use the bundled PDF Python for --fetch-bok; the repository Python for --fetch-s3.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request


BUCKET = "soma-quant-bronze-31-159372032315-ap-northeast-2-an"
PREFIX = "macro/fmp/economic-calendar/korea-coverage-v1/snapshot=backfill-20260920/"
RUN = PREFIX + "runs/from=2015-01-01/to=2026-09-18/manifest.json"
BOK = "https://www.bok.or.kr"
CALENDAR = BOK + "/portal/singl/crncyPolicyDrcMtg/listYear.do?menuNo=200755&mtgSe=A&pYear="


def sha(body):
    return hashlib.sha256(body).hexdigest()


def encode(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode()


def save(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError(f"Refusing to replace immutable artifact: {path}")
    else:
        with path.open("xb") as f:
            f.write(body)


def get_http(out, name, url):
    path = out / "official" / name
    receipt = path.with_suffix(path.suffix + ".receipt.json")
    if path.exists():
        meta = json.loads(receipt.read_bytes())
        if meta["url"] != url or sha(path.read_bytes()) != meta["sha256"]:
            raise ValueError("Changed evidence cache")
        return path, meta
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 source-validation"})
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read()
                meta = {"url": url, "final_url": r.url, "sha256": sha(body), "status": r.status,
                        "received_at": datetime.now(timezone.utc).isoformat(), "bytes": len(body)}
            save(path, body)
            save(receipt, encode(meta))
            return path, meta
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def meeting_links(body, year, through):
    page = body.decode()
    if f"<h3>{year}년</h3>" not in page:
        raise ValueError("Wrong calendar year")
    result = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
        if len(cells) < 2:
            continue
        day = re.search(r"(\d{1,2})월\s*(\d{1,2})일", cells[0])
        if not day:
            continue
        date = f"{year}-{int(day[1]):02}-{int(day[2]):02}"
        if date > through:
            continue
        links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*title="([^"]+\.pdf)"', cells[1])
        links = [(html.unescape(u), html.unescape(t)) for u, t in links if "fileDown.do" in u]
        if len(links) != 1:
            raise ValueError(f"Ambiguous/missing decision PDF for {date}: {links}")
        result.append({"decision_date": date, "url": BOK + links[0][0], "title": links[0][1]})
    if not result or len({x["decision_date"] for x in result}) != len(result):
        raise ValueError("Empty/duplicate meeting calendar")
    return result


def parse_decision(text, date):
    compact = re.sub(r"\s+", "", text)
    y, m, d = map(int, date.split("-"))
    date_verified = f"{y}년{m}월{d}일" in compact[:700]
    # Use the announced target, not the previous rate, growth forecast or loan rate.
    start = compact.find("한국은행기준금리")
    clause = compact[start:start + 220] if start >= 0 else ""
    clause = re.split(r"(?:운용하기로|운용하여|운용한다|유지하여|인하하여|인상하여|다[.。]|□)", clause)[0]
    # %p is the size of the change, not the new policy rate.
    numbers = re.findall(r"(\d+(?:\.\d+)?)%(?!p)", clause)
    target = float(numbers[-1]) if numbers and len(numbers) <= 2 else None
    return {"document_date_verified": date_verified, "target_rate_pct": target,
            "rate_clause": clause, "header_excerpt": compact[:180]}


def fetch_bok(out, through):
    from pypdf import PdfReader

    meetings, calendars = [], []
    for year in range(2014, int(through[:4]) + 1):
        path, meta = get_http(out, f"calendar-{year}.html", CALENDAR + str(year))
        rows = meeting_links(path.read_bytes(), year, through)
        meetings.extend(rows)
        calendars.append({**meta, "path": str(path.resolve()), "year": year,
                          "decision_dates": [x["decision_date"] for x in rows]})
        print("calendar", year, len(rows), flush=True)

    def collect(row):
        path, meta = get_http(out, "decisions/" + row["decision_date"] + ".pdf", row["url"])
        if not path.read_bytes().startswith(b"%PDF"):
            raise ValueError("Decision download is not PDF")
        reader = PdfReader(io.BytesIO(path.read_bytes()))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(pages)
        save(path.with_suffix(".txt"), text.encode())
        parsed = parse_decision(text, row["decision_date"])
        return {**row, **parsed, "pdf_sha256": meta["sha256"], "pdf_path": str(path.resolve()),
                "text_sha256": sha(text.encode()), "downloaded_at": meta["received_at"],
                "pages": len(pages)}

    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, result in enumerate(pool.map(collect, meetings), 1):
            results.append(result)
            if i % 15 == 0:
                print("decisions", i, "/", len(meetings), flush=True)
    body = {"schema_version": "bok-official-decision-evidence-v2", "through": through,
            "calendars": calendars, "decisions": sorted(results, key=lambda x: x["decision_date"])}
    save(out / "official/decisions-v2.json", encode(body))
    invalid = [x for x in results if not x["document_date_verified"] or x["target_rate_pct"] is None]
    print("decisions", len(results), "unparsed", len(invalid), flush=True)
    for row in invalid:
        print(json.dumps(row, ensure_ascii=False), flush=True)


def fetch_s3(out):
    import boto3
    # CLI can reuse still-valid role credentials after its SSO token expires.
    # Capture credentials in memory only; never print, persist or add them to URLs.
    credentials = subprocess.run(["aws", "configure", "export-credentials", "--profile", "teamalpha",
                                  "--format", "process"], capture_output=True, check=True)
    credential = json.loads(credentials.stdout)
    client = boto3.client("s3", region_name="ap-northeast-2",
        aws_access_key_id=credential["AccessKeyId"], aws_secret_access_key=credential["SecretAccessKey"],
        aws_session_token=credential["SessionToken"])
    dest = out / "bronze_mirror"

    def read(key):
        if not key.startswith(PREFIX):
            raise ValueError("Out-of-scope S3 key")
        path = dest / key
        receipt = path.with_suffix(path.suffix + ".download.json")
        if path.exists():
            body = path.read_bytes()
            meta = json.loads(receipt.read_bytes())
            if meta["sha256"] != sha(body):
                raise ValueError("Mirror hash changed")
            return body
        obj = client.get_object(Bucket=BUCKET, Key=key)
        with obj["Body"] as stream:
            body = stream.read()
        save(path, body)
        save(receipt, encode({"s3_uri": f"s3://{BUCKET}/{key}", "sha256": sha(body),
             "etag": obj.get("ETag"), "version_id": obj.get("VersionId"),
             "s3_last_modified": obj["LastModified"].isoformat(),
             "downloaded_at": datetime.now(timezone.utc).isoformat()}))
        return body

    run = json.loads(read(RUN))
    if run["complete"] is not True:
        raise ValueError("Incomplete S3 run")
    keys = []
    for part in run["partitions"]:
        base = part["selection_manifest_uri"].removeprefix(f"s3://{BUCKET}/").rsplit("/", 1)[0]
        keys += [base + "/" + x for x in ("raw/manifest.json", "raw/response.json", "selection_manifest.json", "selected.json")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in pool.map(read, keys):
            pass
    rows, manifests = [], []
    counts = {}
    for part in run["partitions"]:
        key = part["selection_manifest_uri"].removeprefix(f"s3://{BUCKET}/")
        pm = json.loads(read(key))
        raw_key = pm["source_object_uri"].removeprefix(f"s3://{BUCKET}/")
        raw_body = read(raw_key)
        selected_body = read(pm["object_uri"].removeprefix(f"s3://{BUCKET}/"))
        rm = json.loads(read(raw_key.rsplit("/", 1)[0] + "/manifest.json"))
        if not (sha(raw_body) == rm["sha256"] == pm["source_sha256"] and sha(selected_body) == pm["sha256"]):
            raise ValueError("S3 source/projection hash mismatch")
        if rm["received_at"] != pm["received_at"]:
            raise ValueError("Changed source receipt")
        raw, selected = json.loads(raw_body), json.loads(selected_body)
        if len(selected) != part["selected_row_count"]:
            raise ValueError("S3 partition count mismatch")
        for row in selected:
            if row["payload"] != raw[row["source_row_index"]]:
                raise ValueError("S3 raw projection mismatch")
            counts[row["series_id"]] = counts.get(row["series_id"], 0) + 1
            if row["series_id"] == "KR_POLICY_RATE":
                rows.append({**row, "raw_uri": pm["source_object_uri"], "raw_sha256": pm["source_sha256"],
                             "received_at": rm["received_at"], "selection_sha256": pm["sha256"]})
        manifests.append({"uri": part["selection_manifest_uri"], "sha256": sha(read(key)),
                          "raw_sha256": sha(raw_body), "projection_sha256": sha(selected_body)})
    if counts != run["rows_by_series"] or sum(counts.values()) != run["selected_row_count"]:
        raise ValueError("S3 run totals mismatch")
    save(out / "bronze_policy.json", encode({"schema_version": "exact-fmp-s3-policy-evidence-v1",
        "run_uri": f"s3://{BUCKET}/{RUN}", "run_sha256": sha(read(RUN)),
        "rows_by_series": counts, "partitions": manifests, "policy_rows": rows}))
    print("S3 verified", len(manifests), "partitions", sum(counts.values()), "selected rows", len(rows), "policy rows", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--through", default="2026-08-31")
    parser.add_argument("--fetch-bok", action="store_true")
    parser.add_argument("--fetch-s3", action="store_true")
    args = parser.parse_args()
    if args.fetch_s3:
        fetch_s3(args.output)
    if args.fetch_bok:
        fetch_bok(args.output, args.through)
