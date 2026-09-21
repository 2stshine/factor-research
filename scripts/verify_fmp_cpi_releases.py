"""Read original CPI release landing pages; never infer missing values or approval."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from html.parser import HTMLParser
import html
import json
from pathlib import Path
import re

from scripts.prepare_bok_policy import get_http, save, encode
from scripts.verify_fmp_remaining import load_exact_macro

BASE = "https://mods.go.kr"
LIST = BASE + "/board.es?mid=a10301040100&bid=213&tag=&nPage="


def strip(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", re.sub(r"<!--.*?-->", "", text, flags=re.S)))).strip()


def list_links(body):
    page = re.sub(r"<!--.*?-->", "", body.decode(), flags=re.S)
    result = []
    for attrs, inner in re.findall(r'<a (class="board_link"[^>]*)>(.*?)</a>', page, re.S):
        name = strip(inner)
        match = re.fullmatch(r"(20\d\d)년\s*(\d{1,2})월(?:\s*및\s*연간)?\s*소비자물가\s*동향", name)
        if match:
            number = re.search(r"list_no=(\d+)", attrs)[1]
            period = f"{match[1]}-{int(match[2]):02}"
            url = BASE + f"/board.es?mid=a10301040100&bid=213&act=view&list_no={number}"
            result.append({"reference_month": period, "title": name, "url": url, "list_no": number})
    return result


class Content(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif "board_content" in dict(attrs).get("class", "").split():
                self.depth = 1
    def handle_endtag(self, tag):
        if tag == "div" and self.depth:
            self.depth -= 1
    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)


def parse_release(body):
    page = body.decode()
    p = Content()
    p.feed(page)
    content = re.sub(r"\s+", " ", " ".join(p.parts)).strip()
    text = strip(page)
    date = re.search(r"게시일\s*(\d{4}-\d{2}-\d{2})", text)
    # The headline precedes core/subgroup measures; never search all text for a convenient number.
    headline = re.split(r"농산물|식료품|생활물가|신선식품|연간", content, maxsplit=1)[0]
    def rate(label):
        m = re.search(label + r"\s*([+-]?\d+(?:\.\d+)?)\s*%([^%]{0,65})", headline)
        if not m:
            if re.search(label + r"\s*(?:변동(?:이)?\s*없|동일|보합)", headline):
                return 0.0
            return None
        value, tail = float(m[1]), m[2]
        # In 'MoM x%, YoY y% 각각 상승', shared direction follows the next percentage.
        if "상승" not in tail and "하락" not in tail:
            after = headline[m.end(1):]
            direction = re.search(r"상승|하락", after)
        else:
            direction = re.search(r"상승|하락", tail)
        if value == 0:
            return 0.0
        if not direction:
            return None
        return -abs(value) if direction[0] == "하락" else abs(value)
    return {"publication_date": date[1] if date else None,
            "mom": rate("전월(?:대비|비)"), "yoy": rate("전년(?:동월)?(?:대비|비)"),
            "revision_notice": bool(re.search(r"(?:변경|수정|정정).{0,30}(?:게시|보도자료|수록)", content)),
            "headline": headline, "content": content}


def collect(out):
    links, seen, reached_start = [], set(), False
    for n in range(1, 24):
        path, _ = get_http(out, f"cpi-list-{n:02}.html", LIST + str(n))
        page_links = list_links(path.read_bytes())
        for row in page_links:
            if row["list_no"] in seen:
                raise ValueError("Pagination repeated a release")
            seen.add(row["list_no"])
            if "2015-01" <= row["reference_month"] <= "2026-08":
                links.append(row)
        print("CPI list", n, len(links), flush=True)
        if any(r["reference_month"] < "2015-01" for r in page_links):
            reached_start = True
            break
    if not reached_start or len(links) != 140 or len({r["reference_month"] for r in links}) != 140:
        raise ValueError(f"Incomplete/ambiguous original release discovery: {len(links)}")
    def one(row):
        path, meta = get_http(out, "cpi-releases/" + row["reference_month"] + ".html", row["url"])
        parsed = parse_release(path.read_bytes())
        return {**row, **parsed, "sha256": meta["sha256"], "received_at": meta["received_at"], "path": str(path.resolve())}
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = []
        for i, row in enumerate(pool.map(one, links), 1):
            results.append(row)
            if i % 20 == 0:
                print("CPI release", i, "/", len(links), flush=True)
    save(out / "cpi-original-releases.json", encode(sorted(results, key=lambda x: x["reference_month"])))
    print("CPI parsed", sum(x["mom"] is not None and x["yoy"] is not None for x in results), flush=True)


def compare(out, policy_root):
    original = json.loads((out / "cpi-original-releases-v2.json").read_bytes())
    refs = {r["reference_month"]: r for r in original}
    rows, _ = load_exact_macro(policy_root)
    results = []
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    for symbol, field in (("KR_CPI_MOM", "mom"), ("KR_CPI_YOY", "yoy")):
        for row in rows[symbol]:
            p = row["payload"]
            release = datetime.fromisoformat(p["date"]) + timedelta(hours=9)
            mon = re.search(r"\(([A-Z][a-z]{2})\)", p["event"])[1]
            month = months.index(mon) + 1
            year = release.year - (month > release.month)
            ref = f"{year}-{month:02}"
            official = refs.get(ref)
            value = official.get(field) if official else None
            status = "NOT_PARSED" if value is None else "MATCH" if value == p["actual"] else "DIFFERENCE"
            results.append({"series_id": symbol, "reference_month": ref, "fmp_date": p["date"],
                "fmp_kst_by_documented_utc": release.isoformat(), "fmp_actual": p["actual"],
                "official_value": value, "value_check": status,
                "official_publication_date": official["publication_date"] if official else None,
                "release_date_matches": official is not None and release.strftime("%Y-%m-%d") == official["publication_date"],
                "official_url": official["url"] if official else None,
                "official_sha256": official["sha256"] if official else None,
                "official_revision_notice": official.get("revision_notice", False) if official else None,
                "raw_uri": row["audit_source_uri"], "source_row_index": row["source_row_index"]})
    report = {"scope": "Dated official release landing pages; not a claim of exact historical intraday delivery",
              "first_release_immutability_proven": False, "new_approval_issued": False,
              "rows": results, "counts": {k: sum(x["value_check"] == k for x in results) for k in ("MATCH", "DIFFERENCE", "NOT_PARSED")},
              "release_date_matches": sum(x["release_date_matches"] for x in results)}
    save(out / "cpi-comparison-v2.json", encode(report))
    print(report["counts"], "dates", report["release_date_matches"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--collect", action="store_true")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--reparse", action="store_true")
    p.add_argument("--policy-root", type=Path, default=Path("output/regime_inputs/kr-policy-pit-20260920"))
    args = p.parse_args()
    if args.collect:
        collect(args.output)
    if args.reparse:
        original = json.loads((args.output / "cpi-original-releases.json").read_bytes())
        from scripts.prepare_bok_policy import sha
        for row in original:
            body = Path(row["path"]).read_bytes()
            if sha(body) != row["sha256"]:
                raise ValueError("Changed official release evidence")
            row.update(parse_release(body))
        save(args.output / "cpi-original-releases-v2.json", encode(original))
    if args.compare:
        compare(args.output, args.policy_root)
