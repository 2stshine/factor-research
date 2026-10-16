"""Observed source-format support, not wider financial account semantics."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from engine import dart_historical_revenue_parser as v1
from engine import dart_historical_revenue_parser_v2 as v2
from scripts import stage_dart_historical_revenue as pilot


def statement(fs, quarter="Q2", *, amount="1,234", account="수익(매출액)", unit="백만원", heading=None):
    month, day, label = {"Q1": ("03", "31", "1분기"), "Q2": ("06", "30", "반기"), "Q3": ("09", "30", "3분기")}[quarter]
    heading = heading or ("연결 손익계산서" if fs == "CFS" else "손익계산서")
    return f'''<TABLE><TBODY><TR><TD>{heading}</TD></TR>
<TR><TD>제 47 기 {label} 2015.01.01 부터 2015.{month}.{day} 까지</TD></TR>
<TR><TD>제 46 기 {label} 2014.01.01 부터 2014.{month}.{day} 까지</TD></TR>
<TR><TD>(단위 : {unit})</TD></TR></TBODY></TABLE>
<TABLE><THEAD><TR><TH ROWSPAN="2"> </TH><TH COLSPAN="2">제 47 기 {label}</TH><TH COLSPAN="2">제 46 기 {label}</TH></TR>
<TR><TH>3개월</TH><TH>누적</TH><TH>3개월</TH><TH>누적</TH></TR></THEAD>
<TBODY><TR><TD>{account}</TD><TD>{amount}</TD><TD>2,000</TD><TD>900</TD><TD>1,800</TD></TR></TBODY></TABLE>'''


def source(quarter="Q2", *, cfs=None, ofs=None, encoding="utf-8", corp="00126380", correction=False):
    form = "11012" if quarter == "Q2" else "11013"
    text = f'<?xml version="1.0" encoding="utf-8"?><DOCUMENT><DOCUMENT-NAME ACODE="{form}">보고서</DOCUMENT-NAME><COMPANY-NAME AREGCIK="{corp}">테스트</COMPANY-NAME>'
    if correction:
        text += '<TITLE>기재정정</TITLE><P>정정 제출일과 원 보고서 제출일은 외부 lineage 검증 대상</P>'
    text += '<TITLE>III. 재무에 관한 사항</TITLE><TITLE>1. 요약재무정보</TITLE>' + statement("CFS", quarter)
    text += '<TITLE>2. 연결재무제표</TITLE>' + (statement("CFS", quarter) if cfs is None else cfs)
    text += '<TITLE>3. 연결재무제표 주석</TITLE>' + statement("CFS", quarter)
    text += '<TITLE>4. 재무제표</TITLE>' + (statement("OFS", quarter) if ofs is None else ofs)
    text += '<TITLE>5. 재무제표 주석</TITLE>' + statement("OFS", quarter)
    text += '<TITLE>IV. 감사인</TITLE>' + statement("CFS", quarter) + '</DOCUMENT>'
    return text.encode(encoding)




def parse(raw):
    return v2.parse_document(raw, "Q2", "00126380")


@pytest.mark.parametrize("label", [
    "매출액", "수익(매출액)", "Ⅰ.매출액", "I.수익(매출액)",
    "매출액 (주5,26)", "Ⅰ.매출액 (주5,33)", "수익(매출액) (주22)",
])
def test_only_observed_presentation_is_removed(label):
    result = parse(source(cfs=statement("CFS", account=label)))
    assert result["scope_status"]["CFS"] == "PARSED"
    row = next(row for row in result["rows"] if row["fs_type"] == "CFS")
    assert row["account_label_raw"] == label
    assert row["amount_krw_decimal"] == "1234000000"


@pytest.mark.parametrize("label", [
    "매출", "영업수익", "이자수익", "총매출액", "순매출액", "매출액성장률",
    "Ⅱ.매출액", "1.매출액", "매출액(해외)", "매출액(주5,)", "매출액(주석5)",
    "재화의판매로인한수익(매출액)", "(1)수익(매출액)",
])
def test_unreviewed_financial_alias_or_annotation_is_rejected(label):
    assert v2.revenue_label(label) is None
    result = parse(source(cfs=statement("CFS", account=label)))
    assert result["scope_status"]["CFS"] == "UNRESOLVED"


@pytest.mark.parametrize("text", [
    "해당사항 없습니다.", "- 해당사항 없음.", '" 해당사항없음"',
    "당사는 연결재무제표 작성대상 법인이 아니므로 해당사항 없습니다.",
    "회사는 한국채택국제회계기준에 의한 연결대상이 없어 연결재무제표를 작성하지 않습니다.",
])
def test_explicit_absence_requires_unique_named_main_section_without_tables(text):
    raw = source(cfs="<P>" + text + "</P>")
    result = parse(raw)
    assert result["scope_status"] == {"CFS": "EXPLICITLY_ABSENT", "OFS": "PARSED"}
    assert result["cfs_absence_evidence"] == result["scope_details"]["CFS"]["absence_evidence"]
    assert {row["fs_type"] for row in result["rows"]} == {"OFS"}
    assert result["scope_details"]["CFS"]["absence_proven"] is True
    evidence = result["scope_details"]["CFS"]["absence_evidence"][0]
    decoded, dec = v2.decode_document(raw)
    body = decoded[evidence["body_start_character_offset"]:evidence["body_end_character_offset_exclusive"]]
    assert hashlib.sha256(body.encode(dec["strict_decoding"])).hexdigest() == evidence["source_slice_sha256"]
    assert evidence["xml_sha256"] == hashlib.sha256(raw).hexdigest()
    assert evidence["exact_text"] == text
    assert result["financial_available_at"] is None and not result["pit_certified"]
    assert v1.parse_document(raw, "Q2", "00126380")["scope_status"]["CFS"] == "UNRESOLVED"


@pytest.mark.parametrize("body", [
    "", "<P>현재 자료가 없습니다.</P>", "<P>해당사항 없음. 추후 작성 예정입니다.</P>",
    "<P>해당사항 없음이 아닙니다.</P>", "<P>해당사항 없음</P><TABLE><TR><TD>매출액</TD></TR></TABLE>",
    "<P>해당사항 없음</P><P>일부 자회사 제외</P>",
])
def test_blank_unknown_qualified_or_table_bearing_sections_do_not_prove_absence(body):
    assert parse(source(cfs=body))["scope_status"]["CFS"] == "UNRESOLVED"


def test_absence_text_in_notes_or_another_major_section_not_accepted():
    raw = source(cfs="").replace("</DOCUMENT>".encode(), "<P>해당사항 없음</P></DOCUMENT>".encode())
    assert parse(raw)["scope_status"]["CFS"] == "UNRESOLVED"


def test_absence_requires_ofs_current_statement_success():
    raw = source(cfs="<P>해당사항 없음</P>", ofs=statement("OFS", unit="USD"))
    result = parse(raw)
    assert result["scope_status"] == {"CFS": "UNRESOLVED", "OFS": "UNRESOLVED"}


def test_duplicate_main_section_cannot_certify_absence():
    raw = source(cfs="<P>해당사항 없음</P>").replace(
        b"</DOCUMENT>", '<TITLE>III. 재무에 관한 사항</TITLE><TITLE>2. 연결재무제표</TITLE><P>해당사항 없음</P></DOCUMENT>'.encode())
    assert parse(raw)["scope_status"]["CFS"] == "UNRESOLVED"


def test_wrong_half_year_specific_claim_does_not_certify_quarter_report():
    raw = source("Q1", cfs="<P>당사는 당반기말과 전반기말 현재 연결재무제표 작성대상에 해당하지 않습니다.</P>")
    assert v2.parse_document(raw, "Q1", "00126380")["scope_status"]["CFS"] == "UNRESOLVED"


def test_v1_supported_rows_are_unchanged():
    for quarter in ("Q1", "Q2", "Q3"):
        raw = source(quarter)
        assert v1.parse_document(raw, quarter, "00126380")["rows"] == v2.parse_document(raw, quarter, "00126380")["rows"]


@pytest.mark.parametrize("attempt,quarter,corp", [
    ("002016", "Q1", "00108649"), ("001799", "Q1", "00101488"),
    ("002129", "Q1", "00112022"), ("001892", "Q1", "00104722"),
    ("002049", "Q1", "00109587"), ("002314", "Q1", "00117966"),
])
def test_observed_corpus_presentation_examples_if_installed(attempt, quarter, corp):
    path = Path(__file__).resolve().parents[1] / f"output/dart-historical-statement-corpus-20261002-v1/attempts/{attempt}/response.zip"
    if not path.exists():
        pytest.skip("Local immutable source-format example unavailable")
    with zipfile.ZipFile(path) as archive:
        raw = archive.read(archive.namelist()[0])
    result = v2.parse_document(raw, quarter, corp)
    assert result["scope_status"]["OFS"] == "PARSED"
    assert result["scope_status"]["CFS"] in {"PARSED", "EXPLICITLY_ABSENT"}
    assert not result["rejections"]


def test_pilot_all_36_original_rows_preserved_if_installed():
    root = Path(__file__).resolve().parents[1] / "output/dart-historical-2015-pilot-20261002"
    if not root.exists():
        pytest.skip("Local pilot unavailable")
    count = 0
    for stock, corp in pilot.ISSUERS:
        for quarter in ("Q1", "Q2", "Q3"):
            meta = json.loads((root / f"documents/{stock}-{quarter}.json").read_text())
            zipped = pilot.read_object(root, meta["document"], "document.xml", {"rcept_no": meta["receipt_no"]})
            with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
                raw = archive.read(meta["members"][0]["name"])
            old, new = v1.parse_document(raw, quarter, corp), v2.parse_document(raw, quarter, corp)
            assert old["rows"] == new["rows"] and not new["rejections"]
            count += len(new["rows"])
    assert count == 36
