"""Issuer date coverage and latest CLOSE check (NAV is never treated as CLOSE)."""
from __future__ import annotations

import argparse
from datetime import datetime
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.prepare_bok_policy import save, encode, sha
from scripts.fmp_pit_audit import load_run


def historical_nav(body):
    # Issuer's XML export has bare ampersands in hyperlink attributes. Escape
    # those only in the parser input. The downloaded source bytes stay intact.
    text = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[\da-fA-F]+;)", "&amp;", body.decode())
    root = ET.fromstring(text)
    ns = {"s": "urn:schemas-microsoft-com:office:spreadsheet"}
    tag = "{urn:schemas-microsoft-com:office:spreadsheet}"
    sheets = [s for s in root.findall("s:Worksheet", ns) if s.attrib.get(tag + "Name") == "Historical"]
    if len(sheets) != 1:
        raise ValueError("Ambiguous issuer historical sheet")
    rows = [[c.findtext("s:Data", namespaces=ns) for c in r.findall("s:Cell", ns)]
            for r in sheets[0].findall("s:Table/s:Row", ns)]
    if rows[0][:2] != ["As Of", "NAV per Share"]:
        raise ValueError("Issuer sheet schema changed")
    dates = {}
    for r in rows[1:]:
        day = datetime.strptime(r[0], "%b %d, %Y").strftime("%Y-%m-%d")
        if day in dates:
            raise ValueError("Duplicate issuer date")
        dates[day] = float(r[1])
    return dates


def latest_close(body):
    text = html.unescape(body.decode()).replace('\\"', '"')
    found = []
    for match in re.finditer(r'"closingPrice":(\{[^{}]*\})', text):
        row = json.loads(match[1])
        if row.get("name") != "closingPrice":
            continue
        found.append((datetime.strptime(row["formattedAsOfDate"], "%b %d, %Y").strftime("%Y-%m-%d"),
                      float(row["formattedValue"].replace(",", ""))))
    if len(set(found)) != 1:
        raise ValueError("Missing/ambiguous closing price")
    return found[0]


def run(out, data_root):
    rows = {}
    for version in ("korea-external-v1", "korea-risk-v1"):
        path = data_root / "regime/fmp-external" / version / "snapshot=backfill-20260920/runs/from=2015-01-01/to=2026-09-18/manifest.json"
        values, _ = load_run(path)
        rows.update(values)
    result = []
    for symbol in ("EWY", "EEM", "FXI", "EWT"):
        workbook = out / "official" / f"ishares-{symbol}.xls"
        page = out / "official" / f"ishares-{symbol}.html"
        evidence = []
        for p in (workbook, page):
            receipt = json.loads(p.with_suffix(p.suffix + ".receipt.json").read_bytes())
            if sha(p.read_bytes()) != receipt["sha256"]:
                raise ValueError("Changed issuer evidence")
            evidence.append({"path": str(p.resolve()), **receipt})
        nav = historical_nav(workbook.read_bytes())
        day, close = latest_close(page.read_bytes())
        fmp = {r["payload"]["date"]: r["payload"]["close"] for r in rows[symbol]}
        result.append({"series_id": symbol, "fmp_rows": len(fmp),
                       "issuer_nav_dates_in_fmp_range": sum(min(fmp) <= d <= max(fmp) for d in nav),
                       "fmp_dates_without_issuer_nav": sorted(set(fmp) - set(nav)),
                       "issuer_nav_dates_missing_fmp": sorted(d for d in nav if min(fmp) <= d <= max(fmp) and d not in fmp),
                       "latest_price_sample": {"date": day, "issuer_close": close, "fmp_close": fmp.get(day),
                                               "matches": day in fmp and abs(close - fmp[day]) <= 1e-6},
                       "historical_close_comparison": "NOT_PERFORMED_ISSUER_EXPORT_IS_NAV_NOT_CLOSE",
                       "new_pit_approval": False, "evidence": evidence})
    save(out / "etf-issuer-check.json", encode(result))
    print(json.dumps([{k: v for k, v in r.items() if k != "evidence"} for r in result], indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--data-root", type=Path, default=Path("/Users/mac/Documents/GitHub/TeamAlpha-data/data"))
    args = p.parse_args()
    run(args.output, args.data_root)
