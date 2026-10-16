"""Strict, versioned parsing of 2015 original/corrected DART main statements.

No issuer list, filing selection, network, database or corpus write is performed.
Parsing a correction body does NOT backdate that correction or prove publication
lineage. Unsupported scopes fail closed independently; CFS parse failure is not
evidence of CFS nonexistence. Version 2 adds only observed Roman-I/note-marker
presentation and explicitly declared CFS absence. Economic labels stay frozen.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, localcontext
import hashlib
import html
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
import re

PARSER_VERSION = "dart-main-revenue-2015-v2"
SCHEMA_VERSION = "dart-historical-revenue-parse-v2"
SCALES = {"원": 1, "천원": 1000, "백만원": 1000000}
HEADINGS = {
    "연결손익계산서": "CFS", "연결포괄손익계산서": "CFS",
    "손익계산서": "OFS", "포괄손익계산서": "OFS",
}
# Frozen, exact semantic allowlist. Bare '수익', operating revenue, interest,
# segment sales and note-table totals are not synonyms added by convenience.
LABELS = frozenset({"매출액", "수익(매출액)"})
PERIOD = re.compile(
    r"^(제\s*\d+\s*기\s*(?:1분기|반기|3분기))\s+"
    r"(\d{4})\.(\d{2})\.(\d{2})\s*부터\s*"
    r"(\d{4})\.(\d{2})\.(\d{2})\s*까지$"
)


# Source-format additions observed in the frozen 590-document diagnostic:
# a leading Roman I enumerator and trailing "(주5,26)" are presentation/notes,
# not broader economic aliases. Bare 매출/영업수익 remain unsupported.
REVENUE_PRESENTATION = re.compile(r"^(?:I\.)?(매출액|수익\(매출액\))(?:\(주[0-9]+(?:,[0-9]+)*\))?$")
ABSENCE_LABELS = frozenset({
    "해당사항없음", "해당사항없습니다", "당사는해당사항없음",
    "당사는보고서제출일현재해당사항이없습니다",
    "당사는연결재무제표작성대상법인이아니므로해당사항없습니다",
    "공시서류작성기준일현재당사는연결대상종속기업을보유하고있지않습니다",
    "당사는당반기말과전반기말현재연결재무제표작성대상에해당하지않습니다",
    "당사는당분기말과전분기말현재연결재무제표작성대상에해당하지않습니다",
    "회사는한국채택국제회계기준에의한연결대상이없어연결재무제표를작성하지않습니다",
    "회사는한국채택국제기준에의한연결대상이없어연결재무제표를작성하지않습니다",
    "보고서제출일현재연결재무제표작성대상이아닙니다",
    "당사는연결대상종속기업이없습니다", "당사는연결대상종속법인이없습니다",
})


def revenue_label(text):
    match = REVENUE_PRESENTATION.fullmatch(compact(unicodedata.normalize("NFKC", text)))
    return match.group(1) if match else None


def explicit_cfs_absence(parser, quarter, xml_sha256):
    """An explicit declaration in the unique main CFS section, not inference.

    The COMPLETE text before the next title must equal an observed declaration,
    and the CFS section must contain no tables. Blank/unsupported sections,
    comments elsewhere, financial tables and future/conditional wording fail.
    This proves what this raw report declares, not the issuer's timeless status.
    """
    titles = parser.title_nodes
    selected = [(i, title) for i, title in enumerate(titles)
                if title["major"] == "FINANCIALS" and title["normalized"] == "2.연결재무제표"]
    if len(selected) != 1 or any(table["scope"] == "CFS" for table in parser.tables):
        return None
    index, title = selected[0]
    start = title["end_offset"]
    end = titles[index + 1]["start_offset"] if index + 1 < len(titles) else len(parser.source)
    body = parser.source[start:end]
    # Decode only known HTML text entities; no code/external resources execute.
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body).replace("&cr;", "\n")).split())
    normalized = compact(unicodedata.normalize("NFKC", text)).strip(' \"\'-※ㆍ•.')
    if normalized not in ABSENCE_LABELS or ("당반기말" in normalized and quarter != "Q2"):
        return None
    if "당분기말" in normalized and quarter == "Q2":
        return None
    return {
        "claim": "REPORT_EXPLICITLY_DECLARES_CFS_NOT_APPLICABLE",
        "xml_sha256": xml_sha256, "exact_text": text,
        "normalized_declaration": normalized,
        "section_title": title["text"], "section_physical_line": title["line"],
        "body_start_character_offset": start, "body_end_character_offset_exclusive": end,
        "body_physical_start_line": parser.source.count("\n", 0, start) + 1,
        "body_physical_end_line": parser.source.count("\n", 0, end) + 1,
        "source_slice_sha256": sha(body.encode(parser.encoding)),
        "scope_table_count": 0, "evidence_rule": "UNIQUE_MAIN_CFS_SECTION_COMPLETE_DECLARATION_WITHOUT_TABLES_V1",
    }


def source_sha256() -> str:
    """Full self-contained implementation hash for publisher input binding."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class ParseError(ValueError):
    pass


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def decode_document(raw: bytes) -> tuple[str, dict]:
    if len(raw) > 100 * 1024 * 1024:
        raise ParseError("XML_SIZE_LIMIT")
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
            raise ParseError("UNSUPPORTED_DOCUMENT_ENCODING") from None
    if text.encode(encoding) != raw:
        raise ParseError("ENCODING_ROUNDTRIP_MISMATCH")
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
        self.scope_sections = {"CFS": [], "OFS": []}
        self.title_nodes = []

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
            self.title = {"parts": [], "line": self.getpos()[0], "start": self.getpos()}
        if tag == "table":
            self.depth += 1
            ordinal = self.ordinal
            self.ordinal += 1
            if self.active is not None:
                raise ParseError("NESTED_MAIN_STATEMENT_TABLE_UNSUPPORTED")
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
                raise ParseError("NESTED_TABLE_ROW")
            table["row"] = {"cells": [], "header": table["in_header"], "line": self.getpos()[0]}
        elif tag in {"td", "te", "th"} and table["row"] is not None:
            if table["cell"] is not None:
                raise ParseError("NESTED_TABLE_CELL")
            try:
                rowspan, colspan = int(attrs.get("rowspan", "1")), int(attrs.get("colspan", "1"))
            except ValueError:
                raise ParseError("INVALID_TABLE_SPAN") from None
            if not (1 <= rowspan <= 50 and 1 <= colspan <= 50):
                raise ParseError("UNSUPPORTED_TABLE_SPAN")
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
            raise ParseError("UNKNOWN_STATEMENT_ENTITY")

    def handle_charref(self, name):
        try:
            value = chr(int(name[1:], 16) if name.lower().startswith("x") else int(name))
        except (ValueError, OverflowError):
            raise ParseError("INVALID_CHARACTER_REFERENCE") from None
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
            if self.scope is not None and normalized in {"2.연결재무제표", "4.재무제표"}:
                self.scope_sections[self.scope].append(dict(self.section))
            closing_start = self.source_offset(self.getpos())
            closing = re.match(r"</title\s*>", self.source[closing_start:], re.I)
            if closing is None:
                raise ParseError("UNSUPPORTED_TITLE_CLOSING_TAG")
            self.title_nodes.append({
                "text": text, "normalized": normalized, "line": self.title["line"],
                "start_offset": self.source_offset(self.title["start"]),
                "end_offset": closing_start + closing.end(), "major": self.major,
                "scope": self.scope,
            })
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
                    raise ParseError("UNTERMINATED_TABLE_CELL")
                table["rows"].append(table["row"])
                table["row"] = None
            elif tag == "thead":
                table["in_header"] = False
            elif tag == "table":
                if table["row"] is not None:
                    raise ParseError("UNTERMINATED_TABLE_ROW")
                start, close = self.source_offset(table["start"]), self.source_offset(self.getpos())
                closing_tag = re.match(r"</table\s*>", self.source[close:], re.I)
                if closing_tag is None:
                    raise ParseError("UNSUPPORTED_TABLE_CLOSING_TAG")
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
                raise ParseError("UNBALANCED_TABLES")


def expand_grid(table: dict) -> list[list[dict]]:
    rows = table["rows"]
    if not rows or len(rows) > 1000:
        raise ParseError("TABLE_ROW_LIMIT")
    cells = {}
    for row_index, row in enumerate(rows):
        column = 0
        for cell_index, cell in enumerate(row["cells"]):
            while (row_index, column) in cells:
                column += 1
            entry = {**cell, "source_row": row_index, "source_cell": cell_index}
            if row_index + cell["rowspan"] > len(rows) or column + cell["colspan"] > 80:
                raise ParseError("TABLE_SPAN_OUT_OF_BOUNDS")
            for rr in range(row_index, row_index + cell["rowspan"]):
                for cc in range(column, column + cell["colspan"]):
                    if (rr, cc) in cells:
                        raise ParseError("OVERLAPPING_TABLE_SPANS")
                    cells[rr, cc] = entry
            column += cell["colspan"]
    width = max((c for r, c in cells), default=-1) + 1
    if width < 3 or any((r, c) not in cells for r in range(len(rows)) for c in range(width)):
        raise ParseError("NONRECTANGULAR_STATEMENT_GRID")
    return [[cells[r, c] for c in range(width)] for r in range(len(rows))]


def heading_metadata(table: dict, quarter: str) -> dict | None:
    rows = table["rows"]
    if not rows or len(rows[0]["cells"]) != 1:
        return None
    first = compact(rows[0]["cells"][0]["text"])
    if first not in HEADINGS:
        return None
    if HEADINGS[first] != table["scope"]:
        raise ParseError("STATEMENT_SECTION_SCOPE_MISMATCH")
    texts = [c["text"] for row in rows for c in row["cells"]]
    units = [re.fullmatch(r"\(\s*단위\s*:\s*(원|천원|백만원)\s*\)", t) for t in texts]
    units = [m for m in units if m]
    if len(units) != 1:
        raise ParseError("NO_UNIQUE_STATEMENT_UNIT")
    current = []
    for text in texts:
        match = PERIOD.fullmatch(text)
        if match and match.group(2) == "2015":
            current.append((text, match))
    if len(current) != 1:
        raise ParseError("NO_UNIQUE_CURRENT_STATEMENT_PERIOD")
    period_text, match = current[0]
    label = compact(match.group(1))
    try:
        start = date(*map(int, match.groups()[1:4]))
        end = date(*map(int, match.groups()[4:7]))
    except ValueError:
        raise ParseError("INVALID_STATEMENT_PERIOD") from None
    expected = {"Q1": (date(2015, 3, 31), "1분기"), "Q2": (date(2015, 6, 30), "반기"), "Q3": (date(2015, 9, 30), "3분기")}[quarter]
    if start != date(2015, 1, 1) or end != expected[0] or not label.endswith(expected[1]):
        raise ParseError("STATEMENT_PERIOD_OUTSIDE_FIXED_SCOPE")
    return {"heading": rows[0]["cells"][0]["text"], "current_label": label,
            "period_text": period_text, "period_start": start.isoformat(), "period_end": end.isoformat(),
            "unit_raw": units[0].group(0), "unit_name": units[0].group(1),
            "unit_scale_to_krw": SCALES[units[0].group(1)], "anchor": table["anchor"]}


def numeric_amount(raw: str, scale: int) -> str:
    text = raw.strip()
    if len(text) > 100:
        raise ParseError("REVENUE_NUMBER_LENGTH_LIMIT")
    negative = text.startswith("(") and text.endswith(")")
    text = text[1:-1] if negative else text
    if not re.fullmatch(r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", text) or (negative and text.startswith("-")):
        raise ParseError("AMBIGUOUS_REVENUE_AMOUNT")
    with localcontext() as context:
        context.prec = len(text) + len(str(scale)) + 4
        value = Decimal(text.replace(",", "")) * scale * (-1 if negative else 1)
    return format(value, "f")


def table_revenue(table: dict, header: dict) -> list[dict]:
    grid = expand_grid(table)
    header_rows = [i for i, row in enumerate(table["rows"]) if row["header"]]
    if header_rows != [0, 1]:
        raise ParseError("UNSUPPORTED_STATEMENT_HEADER_DEPTH")
    current_columns = [i for i, cell in enumerate(grid[0]) if compact(cell["text"]) == header["current_label"]]
    if len(current_columns) != 2:
        raise ParseError("CURRENT_PERIOD_MUST_HAVE_EXACTLY_TWO_COLUMNS")
    choices = {}
    for col in current_columns:
        subheading = compact(grid[1][col]["text"])
        if subheading not in {"3개월", "누적"} or subheading in choices:
            raise ParseError("AMBIGUOUS_CURRENT_DURATION_COLUMNS")
        choices[subheading] = col
    if set(choices) != {"3개월", "누적"}:
        raise ParseError("MISSING_CURRENT_DURATION_COLUMN")
    matching_rows = [i for i, row in enumerate(grid[2:], 2) if revenue_label(row[0]["text"]) is not None]
    if len(matching_rows) != 1:
        raise ParseError("NO_UNIQUE_REVENUE_ROW")
    row_index = matching_rows[0]
    records = []
    for duration, column in choices.items():
        cell = grid[row_index][column]
        if cell["rowspan"] != 1 or cell["colspan"] != 1:
            raise ParseError("SPANNED_REVENUE_VALUE_UNSUPPORTED")
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


def parse_document(raw_bytes: bytes, quarter: str, expected_corp: str) -> dict:
    """Return evidence rows/rejections, never infer a missing CFS from failure.

    A document with only parsed OFS can be staged for inspection but MUST NOT be
    used as an OFS fallback while CFS remains UNRESOLVED. OFS-only publication
    requires independently verified, original-document CFS-not-applicable
    evidence and correction-lineage coverage. This version recognizes only
    frozen declarations observed in the source-shape diagnostic corpus.

    Both original and corrected filings with the same body format are parsed;
    receipt, publication time, correction links and first-vintage certification
    belong to the caller's independently validated immutable envelope.
    """
    result = {
        "schema_version": SCHEMA_VERSION, "parser_version": PARSER_VERSION,
        "parser_source_sha256": source_sha256(), "quarter": quarter,
        "rows": [], "rejections": [],
        "scope_status": {"CFS": "UNRESOLVED", "OFS": "UNRESOLVED"},
        "scope_details": {}, "publication_scope_gate": "BLOCKED_UNRESOLVED_SCOPE",
        "non_revenue_comprehensive_statements": [],
        "pit_certified": False, "first_publication_proven": False,
        "financial_available_at": None, "correction_lineage_checked": False,
        "cfs_absence_proven": False, "network_calls": 0, "database_calls": 0,
    }
    parser = None
    try:
        if not isinstance(raw_bytes, bytes):
            raise ParseError("DOCUMENT_MUST_BE_BYTES")
        result["xml_sha256"] = sha(raw_bytes)
        if quarter not in {"Q1", "Q2", "Q3"}:
            raise ParseError("UNSUPPORTED_QUARTER")
        if not isinstance(expected_corp, str) or not re.fullmatch(r"\d{8}", expected_corp):
            raise ParseError("EXPECTED_ISSUER_CODE_REQUIRED")
        text, decoding = decode_document(raw_bytes)
        result["decoding"] = decoding
        parser = StatementTables(text, decoding["strict_decoding"])
        parser.feed(text)
        parser.close()
        if parser.active is not None or parser.depth != 0 or parser.title is not None:
            raise ParseError("UNTERMINATED_DOCUMENT_STRUCTURE")
        result["xml_issuer_codes"] = parser.issuer_codes
        result["xml_document_form_codes"] = parser.document_types
        if parser.issuer_codes != [expected_corp]:
            raise ParseError("XML_ISSUER_IDENTITY_MISMATCH")
        # XML form 11013 covers both Q1 and Q3; reprt_code=11014 is API-only.
        expected_form = "11012" if quarter == "Q2" else "11013"
        if parser.document_types != [expected_form]:
            raise ParseError("XML_REPORT_FORM_MISMATCH")
    except (ParseError, UnicodeError) as exc:
        reason = str(exc) if isinstance(exc, ParseError) else "INVALID_DOCUMENT_TEXT"
        result["rejections"].append({"fs_type": None, "reason": reason, "scope": "DOCUMENT"})
        result["status"] = "REJECTED_DOCUMENT"
        return result

    candidates = {"CFS": [], "OFS": []}
    rejected = []
    pending = None
    for table in parser.tables:
        error_scope = table["scope"]
        try:
            header = heading_metadata(table, quarter)
            if header is not None:
                if pending is not None:
                    old_scope, old_header, old_section = pending
                    rejected.append({"fs_type": old_scope, "reason": "HEADER_WITHOUT_PAIRED_VALUE_TABLE",
                                     "table_anchor": old_header["anchor"]})
                pending = (table["scope"], header, table["section"])
                continue
            if pending is None:
                continue
            fs_type, header, section = pending
            pending = None
            error_scope = fs_type
            if table["scope"] != fs_type or table["section"] != section:
                raise ParseError("STATEMENT_HEADER_SCOPE_DRIFT")
            if table["anchor"]["table_ordinal_zero_based"] != header["anchor"]["table_ordinal_zero_based"] + 1:
                raise ParseError("NONADJACENT_STATEMENT_HEADER_VALUE_TABLE")
            # Do not turn an unsupported account label into a 'missing CFS'.
            if not any(revenue_label(cell["text"]) is not None for row in table["rows"] for cell in row["cells"]):
                if "포괄손익계산서" in compact(header["heading"]):
                    # Actual pilot reports may present income and OTHER
                    # comprehensive income as consecutive separate statements.
                    # The latter need not repeat revenue. It is never used as
                    # an alternate source or as evidence of scope absence.
                    result["non_revenue_comprehensive_statements"].append({
                        "fs_type": fs_type, "heading": header["heading"],
                        "header_table_anchor": header["anchor"],
                        "value_table_anchor": table["anchor"],
                    })
                    continue
                raise ParseError("NO_ALLOWLIST_REVENUE_IN_PAIRED_STATEMENT")
            candidates[fs_type].append(table_revenue(table, header))
        except ParseError as exc:
            rejected.append({"fs_type": error_scope, "reason": str(exc), "table_anchor": table["anchor"]})
            pending = None
    if pending is not None:
        fs_type, header, _ = pending
        rejected.append({"fs_type": fs_type, "reason": "HEADER_WITHOUT_PAIRED_VALUE_TABLE",
                         "table_anchor": header["anchor"]})

    for fs_type in ("CFS", "OFS"):
        sections = parser.scope_sections[fs_type]
        results = candidates[fs_type]
        if len(sections) != 1:
            rejected.append({"fs_type": fs_type, "reason": "NO_UNIQUE_MAIN_STATEMENT_SECTION"})
        scope_errors = [entry for entry in rejected if entry["fs_type"] == fs_type]
        if not scope_errors and len(results) == 1:
            rows = results[0]
            if len(rows) != 2 or {row["amount_role"] for row in rows} != {"CURRENT_QUARTER", "CURRENT_YTD"}:
                rejected.append({"fs_type": fs_type, "reason": "INCOMPLETE_CURRENT_REVENUE_ROLES"})
            else:
                result["rows"].extend(rows)
                result["scope_status"][fs_type] = "PARSED"
        elif not scope_errors:
            rejected.append({"fs_type": fs_type, "reason": "NO_UNIQUE_MAIN_REVENUE_STATEMENT"})
        result["scope_details"][fs_type] = {
            "recognized_main_sections": sections,
            "recognized_main_table_count": sum(table["scope"] == fs_type for table in parser.tables),
            "candidate_revenue_statement_count": len(results),
            "absence_proven": False,
        }
    absence = explicit_cfs_absence(parser, quarter, result["xml_sha256"])
    if (result["scope_status"]["CFS"] == "UNRESOLVED"
            and result["scope_status"]["OFS"] == "PARSED" and absence is not None
            and all(entry["reason"] == "NO_UNIQUE_MAIN_REVENUE_STATEMENT"
                    for entry in rejected if entry["fs_type"] == "CFS")):
        result["scope_status"]["CFS"] = "EXPLICITLY_ABSENT"
        result["scope_details"]["CFS"]["absence_proven"] = True
        result["scope_details"]["CFS"]["absence_evidence"] = [absence]
        result["cfs_absence_proven"] = True
        result["cfs_absence_evidence"] = [absence]
        rejected = [entry for entry in rejected if entry["fs_type"] != "CFS"]
    result["rejections"] = rejected
    if result["scope_status"] == {"CFS": "EXPLICITLY_ABSENT", "OFS": "PARSED"}:
        result["status"] = "PARSED_OFS_WITH_EXPLICIT_CFS_ABSENCE"
        result["publication_scope_gate"] = "PARSED_OFS_WITH_EXPLICIT_CFS_ABSENCE_LINEAGE_STILL_REQUIRED"
    elif all(status == "PARSED" for status in result["scope_status"].values()):
        result["status"] = "PARSED_BOTH_SCOPES"
        result["publication_scope_gate"] = "PARSED_BOTH_SCOPES_LINEAGE_STILL_REQUIRED"
    elif result["scope_status"]["OFS"] == "PARSED":
        result["status"] = "PARTIAL_OFS_ONLY"
        result["publication_scope_gate"] = "BLOCKED_CFS_ABSENCE_UNPROVEN"
    elif result["scope_status"]["CFS"] == "PARSED":
        result["status"] = "PARTIAL_CFS_ONLY"
    else:
        result["status"] = "UNSUPPORTED_OR_UNRESOLVED"
    return result
