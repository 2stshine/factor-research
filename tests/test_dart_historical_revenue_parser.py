"""Strict revenue document parsing; synthetic cases and immutable pilot parity."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from engine import dart_historical_revenue_parser as parser
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


def parse(raw=None, quarter="Q2"):
    return parser.parse_document(source(quarter) if raw is None else raw, quarter, expected_corp="00126380")


@pytest.mark.parametrize("quarter,start,end", [("Q1", "2015-01-01", "2015-03-31"),
    ("Q2", "2015-04-01", "2015-06-30"), ("Q3", "2015-07-01", "2015-09-30")])
def test_main_scope_roles_exact_amounts_and_dates(quarter, start, end):
    result = parse(quarter=quarter)
    assert result["status"] == "PARSED_BOTH_SCOPES"
    assert result["scope_status"] == {"CFS": "PARSED", "OFS": "PARSED"}
    assert len(result["rows"]) == 4 and result["rejections"] == []
    for row in result["rows"]:
        assert row["period_end"] == end
        assert row["period_start"] == (start if row["amount_role"] == "CURRENT_QUARTER" else "2015-01-01")
        assert row["amount_krw_decimal"] == ("1234000000" if row["amount_role"] == "CURRENT_QUARTER" else "2000000000")
        assert len(row["value_table_anchor"]["table_sha256"]) == 64
        assert row["currency"] == "KRW"
    assert result["financial_available_at"] is None
    assert not result["pit_certified"] and not result["first_publication_proven"]


def test_correction_body_parses_but_does_not_certify_lineage_or_backdate():
    result = parse(source(correction=True))
    assert len(result["rows"]) == 4
    assert not result["correction_lineage_checked"]
    assert result["financial_available_at"] is None


def test_all_original_anchor_fields_preserved_exactly_against_immutable_pilot_parser():
    raw = source()
    old = pilot.parse_statement_document(raw, "Q2", expected_corp="00126380")
    new = parse(raw)
    assert new["rows"] == old["rows"]
    assert new["xml_sha256"] == old["xml_sha256"]


@pytest.mark.parametrize("account", ["수익", "영업수익", "매출", "이자수익", "총매출액", "부문매출액"])
def test_semantic_account_allowlist_not_broadened(account):
    result = parse(source(cfs=statement("CFS", account=account)))
    assert result["scope_status"] == {"CFS": "UNRESOLVED", "OFS": "PARSED"}
    assert {row["fs_type"] for row in result["rows"]} == {"OFS"}
    assert result["publication_scope_gate"] == "BLOCKED_CFS_ABSENCE_UNPROVEN"


def test_separate_other_comprehensive_statement_does_not_replace_income_statement():
    cfs = statement("CFS") + statement("CFS", heading="연결 포괄손익계산서", account="당기순이익")
    result = parse(source(cfs=cfs))
    assert len(result["rows"]) == 4
    assert len(result["non_revenue_comprehensive_statements"]) == 1


def test_only_comprehensive_without_revenue_is_unresolved_not_absent():
    result = parse(source(cfs=statement("CFS", heading="연결 포괄손익계산서", account="당기순이익")))
    assert result["scope_status"]["CFS"] == "UNRESOLVED"
    assert not result["cfs_absence_proven"]


@pytest.mark.parametrize("cfs", ["", "<P>해당사항 없음</P>", "<P>당사는 연결재무제표를 작성하지 않습니다.</P>"])
def test_ofs_only_needs_independent_explicit_absence_evidence(cfs):
    result = parse(source(cfs=cfs))
    assert result["status"] == "PARTIAL_OFS_ONLY"
    assert len(result["rows"]) == 2
    assert not result["cfs_absence_proven"]
    assert result["publication_scope_gate"] == "BLOCKED_CFS_ABSENCE_UNPROVEN"


@pytest.mark.parametrize("bad", ["", "-", "1,23", "(-5)", "1 234", "NaN", "1e12"])
def test_bad_amount_blocks_only_affected_scope(bad):
    result = parse(source(cfs=statement("CFS", amount=bad)))
    assert result["scope_status"] == {"CFS": "UNRESOLVED", "OFS": "PARSED"}
    assert any(item["reason"] == "AMBIGUOUS_REVENUE_AMOUNT" for item in result["rejections"])


@pytest.mark.parametrize("unit,amount,expected", [("원", "(1,234.5)", "-1234.5"),
    ("천원", "1,234", "1234000"), ("백만원", "12345678901234567890123456789", "12345678901234567890123456789000000")])
def test_exact_decimal_scaling_without_float(unit, amount, expected):
    result = parse(source(cfs=statement("CFS", unit=unit, amount=amount)))
    row = next(row for row in result["rows"] if row["fs_type"] == "CFS" and row["amount_role"] == "CURRENT_QUARTER")
    assert row["amount_krw_decimal"] == expected
    assert row["amount_raw"] == amount


@pytest.mark.parametrize("unit", ["USD", "억원", "원, 주당이익: 원"])
def test_unapproved_units_not_guessed(unit):
    result = parse(source(cfs=statement("CFS", unit=unit)))
    assert result["scope_status"]["CFS"] == "UNRESOLVED"


def test_duplicate_revenue_tables_reject_one_scope():
    result = parse(source(cfs=statement("CFS") * 2))
    assert result["scope_status"] == {"CFS": "UNRESOLVED", "OFS": "PARSED"}


@pytest.mark.parametrize("old,new", [(b"2015.06.30", b"2015.09.30"),
    (b"2015.01.01", b"2015.04.01"), (b'COLSPAN="2"', b'COLSPAN="3"'),
    ("3개월".encode(), "누적".encode())])
def test_period_span_duration_ambiguity_fails_closed(old, new):
    result = parse(source().replace(old, new))
    assert not result["rows"]
    assert result["rejections"]


def test_document_identity_missing_duplicate_and_wrong_form_reject_all_scopes():
    bads = [source(corp="00164779"), source().replace(b'ACODE="11012"', b'ACODE="11011"'),
        source().replace(b"</DOCUMENT>", b'<COMPANY-NAME AREGCIK="00126380">duplicate</COMPANY-NAME></DOCUMENT>')]
    for raw in bads:
        result = parse(raw)
        assert result["status"] == "REJECTED_DOCUMENT" and not result["rows"]


@pytest.mark.parametrize("corp", [None, 126380, "126380", "00126380x"])
def test_expected_issuer_must_be_explicit_eight_digit_string(corp):
    result = parser.parse_document(source(), "Q2", corp)
    assert result["rejections"][0]["reason"] == "EXPECTED_ISSUER_CODE_REQUIRED"


def test_cp949_roundtrip_and_document_hash():
    raw = source(encoding="cp949")
    result = parse(raw)
    assert result["decoding"]["strict_decoding"] == "cp949"
    assert result["xml_sha256"] == hashlib.sha256(raw).hexdigest()
    assert len(result["rows"]) == 4


def test_unknown_entity_and_unclosed_table_reject_without_network():
    for raw in (source().replace("수익(매출액)".encode(), b"&external;"), source()[:-30]):
        result = parse(raw)
        assert result["status"] == "REJECTED_DOCUMENT"
        assert not result["rows"] and result["network_calls"] == 0


def test_parser_hash_covers_entire_module_and_allowlist_is_frozen():
    assert parser.source_sha256() == hashlib.sha256(Path(parser.__file__).read_bytes()).hexdigest()
    assert parse()["parser_source_sha256"] == parser.source_sha256()
    assert parser.LABELS == frozenset({"매출액", "수익(매출액)"})


def test_duplicate_main_section_is_not_merged():
    raw = source().replace(b"</DOCUMENT>", ('<TITLE>III. 재무에 관한 사항</TITLE><TITLE>2. 연결재무제표</TITLE>' + statement("CFS") + '</DOCUMENT>').encode())
    result = parse(raw)
    assert result["scope_status"]["CFS"] == "UNRESOLVED"


def test_fixed_nine_original_documents_preserve_all_36_rows_if_local_corpus_present():
    root = Path(__file__).resolve().parents[1] / "output/dart-historical-2015-pilot-20261002"
    if not root.is_dir():
        pytest.skip("Local immutable nine-document pilot corpus not installed")
    staged = json.loads((root / "staged-revenue-v1.json").read_text())
    assert staged["staged_row_count"] == 36
    checked = 0
    for stock, corp in pilot.ISSUERS:
        for quarter in ("Q1", "Q2", "Q3"):
            metadata = json.loads((root / f"documents/{stock}-{quarter}.json").read_text())
            zipped = pilot.read_object(root, metadata["document"], "document.xml", {"rcept_no": metadata["receipt_no"]})
            members = pilot.validate_zip(zipped, expected_receipt=metadata["receipt_no"])
            assert members == metadata["members"] and len(members) == 1
            with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
                raw = archive.read(members[0]["name"])
            old = pilot.parse_statement_document(raw, quarter, expected_corp=corp)
            new = parser.parse_document(raw, quarter, expected_corp=corp)
            assert new["scope_status"] == {"CFS": "PARSED", "OFS": "PARSED"}
            assert old["rows"] == new["rows"] and not new["rejections"]
            for row in new["rows"]:
                original = [prior for prior in staged["rows"] if prior["stock_code"] == stock
                            and prior["quarter"] == quarter and prior["fs_type"] == row["fs_type"]
                            and prior["amount_role"] == row["amount_role"]]
                assert len(original) == 1
                assert all(original[0][key] == value for key, value in row.items())
                assert original[0]["xml_sha256"] == new["xml_sha256"]
                checked += 1
    assert checked == 36
