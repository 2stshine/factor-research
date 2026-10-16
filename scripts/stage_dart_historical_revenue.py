"""Stage revenue evidence from the nine fixed historical DART pilot ZIPs.

No HTTP, database access, ZIP extraction, source replacement or certification.
The deliberately narrow parser supports the pilot's December-year-end main
statements, not arbitrary DART reports. Unsupported structures fail closed.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from scripts.backfill_dart_historical_filings import (
    ISSUERS, WINDOWS, PilotError, select_original, validate_list, validate_zip,
)


SCHEMA = "dart-historical-revenue-staging-v1"
SCALES = {"원": 1, "천원": 1000, "백만원": 1000000}
HEADINGS = {
    "연결손익계산서": "CFS", "연결포괄손익계산서": "CFS",
    "손익계산서": "OFS", "포괄손익계산서": "OFS",
}
LABELS = frozenset({"매출액", "수익(매출액)"})
PERIOD = re.compile(
    r"^(제\s*\d+\s*기\s*(?:1분기|반기|3분기))\s+"
    r"(\d{4})\.(\d{2})\.(\d{2})\s*부터\s*"
    r"(\d{4})\.(\d{2})\.(\d{2})\s*까지$"
)
LIMITATIONS = [
    "PIT_UNVERIFIED: receipt-addressed raw evidence is not historical-vintage certification",
    "Original selection is limited to the pilot's filing windows; corrections are not complete",
    "Three fixed issuers, December fiscal year, 2015 Q1/Q2/Q3, revenue only",
    "Quarter start is derived from explicit period end and the literal 3개월 column label",
    "No current/previous-year comparative values are backdated",
    "No financial backfill publication, Silver/Gold writes, or factor-input connection",
]


class StagingError(ValueError):
    pass


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def decode_document(raw: bytes) -> tuple[str, dict]:
    if len(raw) > 100 * 1024 * 1024:
        raise StagingError("XML_SIZE_LIMIT")
    declared = re.search(br'encoding\s*=\s*["\']([^"\']+)["\']', raw[:200])
    declared_name = declared.group(1).decode("ascii", errors="replace") if declared else None
    try:
        text = raw.decode("utf-8", errors="strict")
        encoding = "utf-8"
    except UnicodeDecodeError:
        try:
            text = raw.decode("cp949", errors="strict")
            encoding = "cp949"
        except UnicodeDecodeError:
            raise StagingError("UNSUPPORTED_DOCUMENT_ENCODING") from None
    if text.encode(encoding) != raw:
        raise StagingError("ENCODING_ROUNDTRIP_MISMATCH")
    return text, {
        "declared_encoding": declared_name, "strict_decoding": encoding,
        "encoding_declaration_mismatch": bool(declared_name and declared_name.lower() != encoding),
        "parser": "non-executing HTMLParser with explicit DART cr entity handling",
        "xml_well_formedness_certified": False,
    }


class StatementTables(HTMLParser):
    """Retain source slices/cell spans; restrict scope using DART TITLE nodes."""

    def __init__(self, text: str, encoding: str):
        super().__init__(convert_charrefs=False)
        self.source, self.encoding = text, encoding
        self.line_offsets = [0] + [m.end() for m in re.finditer("\n", text)]
        self.major = None
        self.scope = None
        self.section = None
        self.title = None
        self.tables = []
        self.active = None
        self.depth = 0
        self.ordinal = 0
        self.issuer_codes = []
        self.document_types = []

    def source_offset(self, position):
        line, column = position
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "company-name":
            self.issuer_codes.append(attrs.get("aregcik"))
        elif tag == "document-name":
            self.document_types.append(attrs.get("acode"))
        if tag == "title":
            self.title = {"parts": [], "line": self.getpos()[0]}
        if tag == "table":
            self.depth += 1
            ordinal = self.ordinal
            self.ordinal += 1
            if self.active is not None:
                raise StagingError("NESTED_MAIN_STATEMENT_TABLE_UNSUPPORTED")
            if self.scope is not None:
                self.active = {
                    "scope": self.scope, "section": self.section,
                    "ordinal": ordinal, "start": self.getpos(), "rows": [],
                    "row": None, "cell": None, "in_header": False,
                }
            return
        if self.active is None:
            return
        table = self.active
        if tag == "thead":
            table["in_header"] = True
        elif tag == "tr":
            if table["row"] is not None:
                raise StagingError("NESTED_TABLE_ROW")
            table["row"] = {"cells": [], "header": table["in_header"], "line": self.getpos()[0]}
        elif tag in {"td", "te", "th"} and table["row"] is not None:
            if table["cell"] is not None:
                raise StagingError("NESTED_TABLE_CELL")
            try:
                rowspan, colspan = int(attrs.get("rowspan", "1")), int(attrs.get("colspan", "1"))
            except ValueError:
                raise StagingError("INVALID_TABLE_SPAN") from None
            if not (1 <= rowspan <= 50 and 1 <= colspan <= 50):
                raise StagingError("UNSUPPORTED_TABLE_SPAN")
            table["cell"] = {"parts": [], "rowspan": rowspan, "colspan": colspan,
                             "tag": tag, "line": self.getpos()[0]}
        elif tag == "br" and table["cell"] is not None:
            table["cell"]["parts"].append("\n")

    def handle_data(self, data):
        if self.title is not None:
            self.title["parts"].append(data)
        if self.active is not None and self.active["cell"] is not None:
            self.active["cell"]["parts"].append(data)

    def handle_entityref(self, name):
        entities = {"cr": "\n", "amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'", "nbsp": "\u00a0"}
        if name in entities:
            self.handle_data(entities[name])
        elif self.active is not None or self.title is not None:
            raise StagingError("UNKNOWN_STATEMENT_ENTITY")

    def handle_charref(self, name):
        try:
            value = chr(int(name[1:], 16) if name.lower().startswith("x") else int(name))
        except (ValueError, OverflowError):
            raise StagingError("INVALID_CHARACTER_REFERENCE") from None
        self.handle_data(value)

    def handle_endtag(self, tag):
        if tag == "title" and self.title is not None:
            text = " ".join("".join(self.title["parts"]).split())
            normalized = compact(text)
            if re.match(r"^[IVX]+\.", normalized):
                self.major = "FINANCIALS" if normalized == "III.재무에관한사항" else None
                self.scope = None
            elif re.match(r"^\d+\.", normalized):
                self.scope = ({"2.연결재무제표": "CFS", "4.재무제표": "OFS"}.get(normalized)
                              if self.major == "FINANCIALS" else None)
            self.section = {"title": text, "line": self.title["line"]} if self.scope else None
            self.title = None
        if self.active is not None:
            table = self.active
            if tag in {"td", "te", "th"} and table["cell"] is not None:
                cell = table["cell"]
                cell["raw_text"] = "".join(cell.pop("parts"))
                cell["text"] = " ".join(cell["raw_text"].split())
                table["row"]["cells"].append(cell)
                table["cell"] = None
            elif tag == "tr" and table["row"] is not None:
                if table["cell"] is not None:
                    raise StagingError("UNTERMINATED_TABLE_CELL")
                table["rows"].append(table["row"])
                table["row"] = None
            elif tag == "thead":
                table["in_header"] = False
            elif tag == "table":
                if table["row"] is not None:
                    raise StagingError("UNTERMINATED_TABLE_ROW")
                start, close = self.source_offset(table["start"]), self.source_offset(self.getpos())
                closing_tag = re.match(r"</table\s*>", self.source[close:], re.I)
                if closing_tag is None:
                    raise StagingError("UNSUPPORTED_TABLE_CLOSING_TAG")
                end = close + closing_tag.end()
                table["anchor"] = {
                    "table_ordinal_zero_based": table["ordinal"],
                    "physical_start_line": table["start"][0], "physical_end_line": self.getpos()[0],
                    "table_sha256": sha(self.source[start:end].encode(self.encoding)),
                }
                self.tables.append(table)
                self.active = None
        if tag == "table":
            self.depth -= 1
            if self.depth < 0:
                raise StagingError("UNBALANCED_TABLES")


def expand_grid(table: dict) -> list[list[dict]]:
    rows = table["rows"]
    if not rows or len(rows) > 1000:
        raise StagingError("TABLE_ROW_LIMIT")
    cells = {}
    for row_index, row in enumerate(rows):
        column = 0
        for cell_index, cell in enumerate(row["cells"]):
            while (row_index, column) in cells:
                column += 1
            entry = {**cell, "source_row": row_index, "source_cell": cell_index}
            if row_index + cell["rowspan"] > len(rows) or column + cell["colspan"] > 80:
                raise StagingError("TABLE_SPAN_OUT_OF_BOUNDS")
            for rr in range(row_index, row_index + cell["rowspan"]):
                for cc in range(column, column + cell["colspan"]):
                    if (rr, cc) in cells:
                        raise StagingError("OVERLAPPING_TABLE_SPANS")
                    cells[rr, cc] = entry
            column += cell["colspan"]
    width = max((c for r, c in cells), default=-1) + 1
    if width < 3 or any((r, c) not in cells for r in range(len(rows)) for c in range(width)):
        raise StagingError("NONRECTANGULAR_STATEMENT_GRID")
    return [[cells[r, c] for c in range(width)] for r in range(len(rows))]


def heading_metadata(table: dict, quarter: str) -> dict | None:
    rows = table["rows"]
    if not rows or len(rows[0]["cells"]) != 1:
        return None
    first = compact(rows[0]["cells"][0]["text"])
    if first not in HEADINGS:
        return None
    if HEADINGS[first] != table["scope"]:
        raise StagingError("STATEMENT_SECTION_SCOPE_MISMATCH")
    texts = [c["text"] for row in rows for c in row["cells"]]
    units = [re.fullmatch(r"\(\s*단위\s*:\s*(원|천원|백만원)\s*\)", t) for t in texts]
    units = [m for m in units if m]
    if len(units) != 1:
        raise StagingError("NO_UNIQUE_STATEMENT_UNIT")
    current = []
    for text in texts:
        match = PERIOD.fullmatch(text)
        if match and match.group(2) == "2015":
            current.append((text, match))
    if len(current) != 1:
        raise StagingError("NO_UNIQUE_CURRENT_STATEMENT_PERIOD")
    period_text, match = current[0]
    label = compact(match.group(1))
    try:
        start = date(*map(int, match.groups()[1:4]))
        end = date(*map(int, match.groups()[4:7]))
    except ValueError:
        raise StagingError("INVALID_STATEMENT_PERIOD") from None
    expected = {"Q1": (date(2015, 3, 31), "1분기"), "Q2": (date(2015, 6, 30), "반기"), "Q3": (date(2015, 9, 30), "3분기")}[quarter]
    if start != date(2015, 1, 1) or end != expected[0] or not label.endswith(expected[1]):
        raise StagingError("STATEMENT_PERIOD_OUTSIDE_FIXED_SCOPE")
    return {"heading": rows[0]["cells"][0]["text"], "current_label": label,
            "period_text": period_text, "period_start": start.isoformat(), "period_end": end.isoformat(),
            "unit_raw": units[0].group(0), "unit_name": units[0].group(1),
            "unit_scale_to_krw": SCALES[units[0].group(1)], "anchor": table["anchor"]}


def numeric_amount(raw: str, scale: int) -> str:
    text = raw.strip()
    if len(text) > 100:
        raise StagingError("REVENUE_NUMBER_LENGTH_LIMIT")
    negative = text.startswith("(") and text.endswith(")")
    text = text[1:-1] if negative else text
    if not re.fullmatch(r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", text) or (negative and text.startswith("-")):
        raise StagingError("AMBIGUOUS_REVENUE_AMOUNT")
    with localcontext() as context:
        context.prec = len(text) + len(str(scale)) + 4
        value = Decimal(text.replace(",", "")) * scale * (-1 if negative else 1)
    return format(value, "f")


def table_revenue(table: dict, header: dict) -> list[dict]:
    grid = expand_grid(table)
    header_rows = [i for i, row in enumerate(table["rows"]) if row["header"]]
    if header_rows != [0, 1]:
        raise StagingError("UNSUPPORTED_STATEMENT_HEADER_DEPTH")
    current_columns = [i for i, cell in enumerate(grid[0]) if compact(cell["text"]) == header["current_label"]]
    if len(current_columns) != 2:
        raise StagingError("CURRENT_PERIOD_MUST_HAVE_EXACTLY_TWO_COLUMNS")
    choices = {}
    for col in current_columns:
        subheading = compact(grid[1][col]["text"])
        if subheading not in {"3개월", "누적"} or subheading in choices:
            raise StagingError("AMBIGUOUS_CURRENT_DURATION_COLUMNS")
        choices[subheading] = col
    if set(choices) != {"3개월", "누적"}:
        raise StagingError("MISSING_CURRENT_DURATION_COLUMN")
    matching_rows = [i for i, row in enumerate(grid[2:], 2) if compact(row[0]["text"]) in LABELS]
    if len(matching_rows) != 1:
        raise StagingError("NO_UNIQUE_REVENUE_ROW")
    row_index = matching_rows[0]
    records = []
    for duration, column in choices.items():
        cell = grid[row_index][column]
        if cell["rowspan"] != 1 or cell["colspan"] != 1:
            raise StagingError("SPANNED_REVENUE_VALUE_UNSUPPORTED")
        end = date.fromisoformat(header["period_end"])
        start = header["period_start"] if duration == "누적" else date(end.year, end.month - 2, 1).isoformat()
        records.append({
            "fs_type": table["scope"], "metric": "revenue", "account_label_raw": grid[row_index][0]["text"],
            "amount_role": "CURRENT_YTD" if duration == "누적" else "CURRENT_QUARTER",
            "period_start": start, "period_end": end.isoformat(),
            "period_start_evidence": "EXPLICIT_HEADER_PERIOD" if duration == "누적" else "DERIVED_FROM_EXPLICIT_END_AND_3_MONTH_COLUMN",
            "declared_report_period_start": header["period_start"], "declared_report_period_end": header["period_end"],
            "period_header_raw": header["period_text"], "duration_column_raw": duration,
            "amount_raw": cell["raw_text"], "unit_raw": header["unit_raw"],
            "unit_scale_to_krw": header["unit_scale_to_krw"],
            "amount_krw_decimal": numeric_amount(cell["raw_text"], header["unit_scale_to_krw"]),
            "currency": "KRW", "section": table["section"], "statement_heading": header["heading"],
            "header_table_anchor": header["anchor"], "value_table_anchor": table["anchor"],
            "source_row_zero_based": cell["source_row"], "source_cell_zero_based": cell["source_cell"],
            "expanded_column_zero_based": column, "value_physical_line": cell["line"],
            "column_header_path": [grid[0][column]["text"], grid[1][column]["text"]],
            "expanded_header_rows": [[c["text"] for c in row] for row in grid[:2]],
        })
    return records


def parse_statement_document(raw: bytes, quarter: str, *, expected_corp: str | None = None) -> dict:
    if quarter not in {"Q1", "Q2", "Q3"}:
        raise StagingError("UNSUPPORTED_QUARTER")
    text, decoding = decode_document(raw)
    parser = StatementTables(text, decoding["strict_decoding"])
    parser.feed(text)
    parser.close()
    if parser.active is not None or parser.depth != 0:
        raise StagingError("UNTERMINATED_DOCUMENT_TABLE")
    if expected_corp is not None:
        if parser.issuer_codes != [expected_corp]:
            raise StagingError("XML_ISSUER_IDENTITY_MISMATCH")
        # DART's document form ACODE is 11013 for BOTH Q1 and Q3. It is
        # distinct from the financial API's reprt_code=11014 for Q3.
        expected_form = "11012" if quarter == "Q2" else "11013"
        if parser.document_types != [expected_form]:
            raise StagingError("XML_REPORT_FORM_MISMATCH")
    candidates = {"CFS": [], "OFS": []}
    rejected = []
    pending = None
    for table in parser.tables:
        try:
            header = heading_metadata(table, quarter)
            if header is not None:
                pending = (table["scope"], header)
                continue
            if pending is None:
                continue
            fs_type, header = pending
            pending = None
            if table["scope"] != fs_type:
                raise StagingError("STATEMENT_HEADER_SCOPE_DRIFT")
            revenue_cells = [c for row in table["rows"] for c in row["cells"] if compact(c["text"]) in LABELS]
            if not revenue_cells:
                continue
            candidates[fs_type].append(table_revenue(table, header))
        except StagingError as exc:
            rejected.append({"fs_type": table["scope"], "reason": str(exc), "table_anchor": table["anchor"]})
            pending = None
    rows = []
    for fs_type, results in candidates.items():
        if any(r["fs_type"] == fs_type for r in rejected):
            continue
        if len(results) == 1:
            rows.extend(results[0])
        else:
            rejected.append({"fs_type": fs_type, "reason": "NO_UNIQUE_MAIN_REVENUE_STATEMENT"})
    return {"rows": rows, "rejections": rejected, "decoding": decoding, "xml_sha256": sha(raw),
            "xml_issuer_codes": parser.issuer_codes, "xml_document_form_codes": parser.document_types}


def safe_read(root: Path, relative: str) -> bytes:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise StagingError("INVALID_PROVENANCE_PATH")
    actual = root / path
    if actual.is_symlink() or any(p.is_symlink() for p in actual.parents):
        raise StagingError("SYMLINK_PROVENANCE_FORBIDDEN")
    try:
        if actual.stat().st_size > 100 * 1024 * 1024:
            raise StagingError("SOURCE_OBJECT_SIZE_LIMIT")
        return actual.read_bytes()
    except OSError:
        raise StagingError("PROVENANCE_OBJECT_MISSING") from None


def read_object(root: Path, meta: dict, endpoint: str, params: dict) -> bytes:
    if meta.get("endpoint") != endpoint or meta.get("params") != params:
        raise StagingError("PROVENANCE_REQUEST_SCOPE_MISMATCH")
    body = safe_read(root, str(meta.get("body_path") or ""))
    if len(body) != meta.get("bytes") or sha(body) != meta.get("sha256"):
        raise StagingError("PROVENANCE_SHA_OR_SIZE_MISMATCH")
    return body


def stage(root: Path) -> dict:
    root = root.absolute()
    results, all_rows = [], []
    for ticker, corp in ISSUERS:
        for window in WINDOWS:
            quarter, start, end, _, _ = window
            scope = f"{ticker}-{quarter}"
            result = {"scope": scope, "stock_code": ticker, "corp_code": corp, "quarter": quarter}
            try:
                meta_bytes = safe_read(root, f"documents/{scope}.json")
                meta = json.loads(meta_bytes)
                list_meta = json.loads(safe_read(root, f"objects/list-{scope}.json"))
                params = {"corp_code": corp, "bgn_de": start, "end_de": end, "last_reprt_at": "N", "pblntf_ty": "A",
                          "sort": "date", "sort_mth": "asc", "page_no": "1", "page_count": "100"}
                list_body = read_object(root, list_meta, "list.json", params)
                selected = select_original(validate_list(list_body), ticker, corp, window)
                row = selected.get("selected")
                if row is None or row["rcept_no"] != meta.get("receipt_no") or row["rcept_dt"] != meta.get("official_rcept_dt"):
                    raise StagingError("ORIGINAL_SELECTION_PROVENANCE_MISMATCH")
                if meta.get("list_sha256") != sha(list_body):
                    raise StagingError("DISCLOSURE_LIST_SHA_MISMATCH")
                receipt = row["rcept_no"]
                archive_bytes = read_object(root, meta["document"], "document.xml", {"rcept_no": receipt})
                members = validate_zip(archive_bytes, expected_receipt=receipt)
                if len(members) != 1 or members != meta.get("members") or members[0]["name"] not in {f"/{receipt}.xml", f"{receipt}.xml"}:
                    raise StagingError("UNSUPPORTED_PILOT_ZIP_MEMBERS")
                with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                    raw = archive.read(members[0]["name"])
                parsed = parse_statement_document(raw, quarter, expected_corp=corp)
                filed = datetime.strptime(row["rcept_dt"], "%Y%m%d").date()
                for value in parsed["rows"]:
                    if filed < date.fromisoformat(value["period_end"]):
                        raise StagingError("PUBLICATION_PRECEDES_STATEMENT_PERIOD")
                evidence = {
                    "stock_code": ticker, "corp_code": corp, "quarter": quarter, "receipt_no": receipt,
                    "official_filed_date": filed.isoformat(), "filed_date_source": "OpenDART list.json rcept_dt",
                    "financial_available_at": None, "original_first_publication_proven": False,
                    "pit_status": "PIT_UNVERIFIED", "input_connected": False,
                    "document_metadata_sha256": sha(meta_bytes), "list_sha256": sha(list_body),
                    "zip_sha256": sha(archive_bytes), "zip_relative_path": meta["document"]["body_path"],
                    "xml_member_name": members[0]["name"], "xml_sha256": parsed["xml_sha256"],
                    "collected_at": meta["document"]["received_at"], "decoding": parsed["decoding"],
                    "xml_issuer_codes": parsed["xml_issuer_codes"], "xml_document_form_codes": parsed["xml_document_form_codes"],
                }
                all_rows.extend([{**evidence, **value} for value in parsed["rows"]])
                result.update(status="STAGED_PIT_UNVERIFIED" if len(parsed["rows"]) == 4 and not parsed["rejections"] else "PARTIAL_OR_UNSUPPORTED",
                              staged_rows=len(parsed["rows"]), rejections=parsed["rejections"], evidence=evidence)
            except (StagingError, PilotError, KeyError, ValueError, TypeError) as exc:
                reason = str(exc) if isinstance(exc, (StagingError, PilotError)) else "INVALID_PROVENANCE_METADATA"
                result.update(status="REJECTED", staged_rows=0, rejections=[{"reason": reason}])
            results.append(result)
    return {
        "schema_version": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(), "source_root": str(root),
        "status": "STAGED_PIT_UNVERIFIED" if len(all_rows) == 36 and all(x["status"] == "STAGED_PIT_UNVERIFIED" for x in results) else "PARTIAL_OR_UNSUPPORTED",
        "scope_count": len(results), "staged_row_count": len(all_rows), "documents": results, "rows": all_rows,
        "api_calls": 0, "zip_extractions": 0, "silver_writes": False, "gold_writes": False,
        "certification_changed": False, "official_input_connected": False, "limitations": LIMITATIONS,
        "staging_script_sha256": sha(Path(__file__).read_bytes()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    target = args.output or args.input / "staged-revenue-v1.json"
    if target.exists() or target.is_symlink():
        parser.exit(2, "Staging target already exists; immutable evidence must not be replaced.\n")
    report = stage(args.input)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write("\n")
    print(json.dumps({"path": str(target.absolute()), "status": report["status"], "scope_count": report["scope_count"],
                      "staged_row_count": report["staged_row_count"], "api_calls": 0, "silver_writes": False}, ensure_ascii=False))
    if report["status"] != "STAGED_PIT_UNVERIFIED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
