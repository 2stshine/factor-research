import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from scripts import stage_dart_historical_revenue as stage


def source(quarter="Q2", amount="1,234", encoding="utf-8", duplicate=False, corp="00126380"):
    month, day, label = {"Q1": ("03", "31", "1분기"), "Q2": ("06", "30", "반기"), "Q3": ("09", "30", "3분기")}[quarter]
    def statement(fs):
        title = "연결 손익계산서" if fs == "CFS" else "손익계산서"
        return f'''<TABLE><TBODY><TR><TD>{title}</TD></TR>
<TR><TD>제 47 기 {label} 2015.01.01 부터 2015.{month}.{day} 까지</TD></TR>
<TR><TD>제 46 기 {label} 2014.01.01 부터 2014.{month}.{day} 까지</TD></TR>
<TR><TD>(단위 : 백만원)</TD></TR></TBODY></TABLE>
<TABLE><THEAD><TR><TH ROWSPAN="2"> </TH><TH COLSPAN="2">제 47 기 {label}</TH><TH COLSPAN="2">제 46 기 {label}</TH></TR>
<TR><TH>3개월</TH><TH>누적</TH><TH>3개월</TH><TH>누적</TH></TR></THEAD>
<TBODY><TR><TD>수익(매출액)</TD><TD>{amount}</TD><TD>2,000</TD><TD>900</TD><TD>1,800</TD></TR></TBODY></TABLE>'''
    form = "11012" if quarter == "Q2" else "11013"
    text = f'<?xml version="1.0" encoding="utf-8"?><DOCUMENT><DOCUMENT-NAME ACODE="{form}">보고서</DOCUMENT-NAME><COMPANY-NAME AREGCIK="{corp}">테스트</COMPANY-NAME><TITLE>III. 재무에 관한 사항</TITLE>'
    text += '<TITLE>1. 요약재무정보</TITLE>' + statement("CFS")
    text += '<TITLE>2. 연결재무제표</TITLE>' + statement("CFS")
    if duplicate:
        text += statement("CFS")
    text += '<TITLE>3. 연결재무제표 주석</TITLE>' + statement("CFS")
    text += '<TITLE>4. 재무제표</TITLE>' + statement("OFS")
    text += '<TITLE>5. 재무제표 주석</TITLE>' + statement("OFS")
    text += '<TITLE>IV. 감사인</TITLE>' + statement("CFS") + '</DOCUMENT>'
    return text.encode(encoding)


def test_only_main_statements_and_current_columns():
    result = stage.parse_statement_document(source(), "Q2")
    assert len(result["rows"]) == 4
    assert not result["rejections"]
    quarter = next(x for x in result["rows"] if x["fs_type"] == "CFS" and x["amount_role"] == "CURRENT_QUARTER")
    assert quarter["amount_krw_decimal"] == "1234000000"
    assert quarter["period_start"] == "2015-04-01"
    assert quarter["period_end"] == "2015-06-30"
    assert quarter["column_header_path"] == ["제 47 기 반기", "3개월"]
    assert len(quarter["value_table_anchor"]["table_sha256"]) == 64
    assert quarter["source_row_zero_based"] == 2


@pytest.mark.parametrize("quarter,start,end", [("Q1", "2015-01-01", "2015-03-31"), ("Q3", "2015-07-01", "2015-09-30")])
def test_quarter_and_ytd_dates_are_separate(quarter, start, end):
    result = stage.parse_statement_document(source(quarter), quarter)
    assert len(result["rows"]) == 4
    for row in result["rows"]:
        assert row["period_end"] == end
        assert row["period_start"] == (start if row["amount_role"] == "CURRENT_QUARTER" else "2015-01-01")


def test_cp949_strict_fallback_and_original_sha():
    raw = source(encoding="cp949")
    result = stage.parse_statement_document(raw, "Q2")
    assert result["decoding"]["strict_decoding"] == "cp949"
    assert result["decoding"]["encoding_declaration_mismatch"]
    assert result["xml_sha256"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(stage.StagingError, match="ENCODING"):
        stage.decode_document(b"\xff\xff")


def test_dart_cr_and_bare_ampersand_are_not_executed():
    raw = source().replace(b"<DOCUMENT>", b"<DOCUMENT><P>A & B &cr; C</P>")
    assert len(stage.parse_statement_document(raw, "Q2")["rows"]) == 4


@pytest.mark.parametrize("bad", ["", "-", "1 234", "1,23", "1.2.3", "(-5)"])
def test_ambiguous_numbers_fail_closed(bad):
    result = stage.parse_statement_document(source(amount=bad), "Q2")
    assert not result["rows"]
    assert all(x["reason"] == "AMBIGUOUS_REVENUE_AMOUNT" for x in result["rejections"])


def test_negative_amount_is_exact_not_float():
    result = stage.parse_statement_document(source(amount="(1,234.5)"), "Q2")
    row = next(x for x in result["rows"] if x["amount_role"] == "CURRENT_QUARTER")
    assert row["amount_krw_decimal"] == "-1234500000.0"


def test_duplicate_statement_blocks_only_ambiguous_scope():
    result = stage.parse_statement_document(source(duplicate=True), "Q2")
    assert len(result["rows"]) == 2
    assert {x["fs_type"] for x in result["rows"]} == {"OFS"}
    assert result["rejections"][0]["reason"] == "NO_UNIQUE_MAIN_REVENUE_STATEMENT"


@pytest.mark.parametrize("old,new", [
    (b'COLSPAN="2"', b'COLSPAN="3"'),
    ("3개월".encode(), "누적".encode()),
    ("백만원".encode(), "USD".encode()),
    (b"2015.06.30", b"2015.09.30"),
])
def test_span_unit_period_and_header_fail_closed(old, new):
    result = stage.parse_statement_document(source().replace(old, new), "Q2")
    assert not result["rows"]
    assert result["rejections"]


def pilot_fixture(root: Path):
    root.mkdir()
    for ticker, corp in stage.ISSUERS:
        for window in stage.WINDOWS:
            q, begin, end, title, period = window
            scope = f"{ticker}-{q}"
            receipt = begin + "000001"
            row = {"stock_code": ticker, "corp_code": corp, "rcept_no": receipt, "rcept_dt": begin,
                   "report_nm": f"{title} ({period})"}
            body = json.dumps({"status": "000", "total_page": 1, "list": [row]}).encode()
            params = {"corp_code": corp, "bgn_de": begin, "end_de": end, "last_reprt_at": "N", "pblntf_ty": "A",
                      "sort": "date", "sort_mth": "asc", "page_no": "1", "page_count": "100"}
            list_path = f"raw/{scope}.json"
            xml = source(q, encoding="cp949", corp=corp)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(f"/{receipt}.xml", xml)
            archive_bytes = buffer.getvalue()
            zip_path = f"raw/{scope}.zip"
            list_meta = {"endpoint": "list.json", "params": params, "bytes": len(body), "sha256": stage.sha(body), "body_path": list_path}
            document_meta = {"endpoint": "document.xml", "params": {"rcept_no": receipt}, "bytes": len(archive_bytes),
                             "sha256": stage.sha(archive_bytes), "body_path": zip_path, "received_at": "2026-10-02T00:00:00+00:00"}
            meta = {"receipt_no": receipt, "official_rcept_dt": begin, "list_sha256": stage.sha(body),
                    "document": document_meta, "members": stage.validate_zip(archive_bytes, expected_receipt=receipt)}
            for path, value in ((list_path, body), (zip_path, archive_bytes),
                                (f"objects/list-{scope}.json", json.dumps(list_meta).encode()),
                                (f"documents/{scope}.json", json.dumps(meta).encode())):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)


def test_nine_scope_staging_is_not_certification(tmp_path, monkeypatch):
    root = tmp_path / "pilot"
    pilot_fixture(root)
    def forbidden(*args, **kwargs):
        raise AssertionError("No ZIP extraction")
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    report = stage.stage(root)
    assert report["status"] == "STAGED_PIT_UNVERIFIED"
    assert report["staged_row_count"] == 36
    assert report["api_calls"] == 0 and not report["official_input_connected"]
    assert all(r["financial_available_at"] is None for r in report["rows"])
    assert all(r["xml_sha256"] and r["zip_sha256"] and r["list_sha256"] for r in report["rows"])


def test_tampered_raw_zip_rejects_scope(tmp_path):
    root = tmp_path / "pilot"
    pilot_fixture(root)
    (root / "raw/005930-Q1.zip").write_bytes(b"tampered")
    report = stage.stage(root)
    failed = next(x for x in report["documents"] if x["scope"] == "005930-Q1")
    assert failed["status"] == "REJECTED"
    assert failed["rejections"][0]["reason"] == "PROVENANCE_SHA_OR_SIZE_MISMATCH"
    assert report["staged_row_count"] == 32


def test_correction_selected_instead_of_original_is_rejected(tmp_path):
    root = tmp_path / "pilot"
    pilot_fixture(root)
    path = root / "documents/005930-Q1.json"
    meta = json.loads(path.read_text())
    meta["receipt_no"] = "20150601000001"
    path.write_text(json.dumps(meta))
    failed = stage.stage(root)["documents"][0]
    assert failed["status"] == "REJECTED"
    assert failed["rejections"][0]["reason"] == "ORIGINAL_SELECTION_PROVENANCE_MISMATCH"


def test_output_is_immutable(tmp_path, monkeypatch):
    target = tmp_path / "existing.json"
    target.write_text("keep")
    monkeypatch.setattr("sys.argv", ["stage", "--input", str(tmp_path), "--output", str(target)])
    with pytest.raises(SystemExit) as exc:
        stage.main()
    assert exc.value.code == 2
    assert target.read_text() == "keep"


def test_xml_identity_and_report_form_checked():
    with pytest.raises(stage.StagingError, match="ISSUER_IDENTITY"):
        stage.parse_statement_document(source(), "Q2", expected_corp="00164779")
    with pytest.raises(stage.StagingError, match="REPORT_FORM"):
        stage.parse_statement_document(source().replace(b'ACODE="11012"', b'ACODE="11011"'), "Q2", expected_corp="00126380")
    assert len(stage.parse_statement_document(source("Q3"), "Q3", expected_corp="00126380")["rows"]) == 4


def test_decimal_scaling_does_not_round_at_default_precision():
    raw = "12345678901234567890123456789"
    assert stage.numeric_amount(raw, 1000000) == raw + "000000"
