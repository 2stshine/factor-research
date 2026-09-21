from copy import deepcopy
import json

import pytest

from scripts.verify_fmp_remaining import COT_FIELDS, compare_cot, quality, load_exact_macro
from scripts.verify_fmp_cpi_releases import list_links, parse_release
from scripts.verify_fmp_etf_sources import historical_nav, latest_close


def row(payload):
    return {"payload": payload, "audit_source_uri": "test://raw", "source_row_index": 0}


def cot_pair():
    p = {f: 0 for f in COT_FIELDS}
    p.update(date="2015-01-06 00:00:00", cftcContractMarketCode="085692",
             openInterestAll=100, noncommPositionsLongAll=30, noncommPositionsShortAll=20,
             noncommPositionsSpreadAll=10, commPositionsLongAll=40, commPositionsShortAll=50,
             totReptPositionsLongAll=80, totReptPositionsShortAll=80,
             nonreptPositionsLongAll=20, nonreptPositionsShortAll=20)
    official = {v: str(p[k]) for k, v in COT_FIELDS.items()}
    official.update(cftc_contract_market_code="085692", report_date_as_yyyy_mm_dd="2015-01-06T00:00:00.000")
    return p, official


def test_cot_exact_full_value_agreement_is_not_vintage_approval():
    p, other = cot_pair()
    r = compare_cot("HG", [row(p)], [other])
    assert r["status"] == "PASS" and r["compared_values"] == 10
    assert r["first_vintage_proven"] is False
    q = quality("HG", [row(p)], "cot")
    assert q["basic_quality"] == "PASS" and q["new_approval_issued"] is False


@pytest.mark.parametrize("change", ["duplicate", "code", "missing_field"])
def test_bad_official_cot_source_fails_closed(change):
    p, other = cot_pair()
    sources = [other]
    if change == "duplicate":
        sources.append(deepcopy(other))
    elif change == "code":
        other["cftc_contract_market_code"] = "85692"
    else:
        del other["open_interest_all"]
    with pytest.raises(ValueError):
        compare_cot("HG", [row(p)], sources)


def test_cot_value_difference_and_missing_date_are_not_conflated():
    p, other = cot_pair()
    other["open_interest_all"] = "101"
    second = deepcopy(other)
    second["report_date_as_yyyy_mm_dd"] = "2015-01-13T00:00:00"
    r = compare_cot("HG", [row(p)], [other, second])
    assert r["different_rows"] == 1
    assert r["official_dates_missing_fmp"] == ["2015-01-13"]


def test_cot_accounting_identity_failure():
    p, _ = cot_pair()
    p["nonreptPositionsLongAll"] = 21
    r = quality("HG", [row(p)], "cot")
    assert r["quality_issue_rows"] == 1
    assert "POSITION_IDENTITY:Long" in r["quality_issues"][0]["reasons"]


def test_null_is_not_zero_and_duplicate_retained():
    rows = [row({"date": "2015-01-01", "actual": None}), row({"date": "2015-01-01", "actual": 0})]
    r = quality("X", rows, "macro")
    assert r["field_null_counts"]["actual"] == 1
    assert r["quality_issue_rows"] == 1 and r["duplicate_excess"] == 1


def test_fx_sunday_is_not_automatic_error():
    p = {"date": "2020-03-01", "open": 1, "high": 2, "low": 1, "close": 1.5, "volume": 0}
    r = quality("EURUSD", [row(p)], "fx")
    assert r["weekday_counts"]["Sunday"] == 1 and r["basic_quality"] == "PASS"


def test_ohlc_range_violation():
    p = {"date": "2020-03-02", "open": 1, "high": 2, "low": 1, "close": 3, "volume": 0}
    assert quality("EWY", [row(p)], "etf")["quality_issue_rows"] == 1


def test_utc_month_boundary_does_not_grant_publication_approval():
    r = quality("KR_CPI_YOY", [row({"date": "2015-03-31 23:00:00", "actual": 0.4})], "macro")
    assert r["provider_utc_to_kst_changes_month"] == 1
    assert r["historical_pit"] == "EVIDENCE_INCOMPLETE"


@pytest.mark.parametrize("words,expected", [
    ("전월대비 변동이 없으며, 전년동월대비 0.5% 상승", (0, .5)),
    ("전월대비 0.2%, 전년동월대비 0.3% 각각 하락", (-.2, -.3)),
    ("전월대비 0.2% 하락, 전년동월대비 0.3% 상승", (-.2, .3)),
    ("전월대비 0.1%, 전년동월대비 2.9% 각각 상승", (.1, 2.9)),
])
def test_cpi_headline_sign_and_zero(words, expected):
    b = f'<span>게시일 2015-02-03</span><div class="board_content">소비자물가지수는 {words} 농산물및석유류제외지수는 전월대비 9.9% 상승</div>'.encode()
    r = parse_release(b)
    assert (r["mom"], r["yoy"]) == expected
    assert r["publication_date"] == "2015-02-03"


def test_cpi_missing_headline_not_filled_from_core():
    r = parse_release('<div class="board_content">소비자물가 농산물및석유류제외지수는 전월대비 1.2% 상승</div>'.encode())
    assert r["mom"] is None


def test_cpi_revision_notice_not_lost():
    r = parse_release('<div class="board_content">소비자물가는 전월대비 0.4% 상승. 일부 변경되어 게시합니다.</div>'.encode())
    assert r["revision_notice"] is True


def test_cpi_list_skips_rebase_and_preserves_december():
    b = '''<a class="board_link" href="?list_no=1"><span>2025년 12월 및 연간 소비자물가동향</span></a>
    <a class="board_link" href="?list_no=2">2025년 소비자물가지수 개편 실시</a>'''.encode()
    r = list_links(b)
    assert len(r) == 1 and r[0]["reference_month"] == "2025-12"


def test_issuer_nav_is_distinct_from_close_and_bad_xml_link_does_not_change_numbers():
    b = b'''<?xml version="1.0"?><ss:Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
    <ss:Worksheet ss:Name="Historical"><ss:Table>
    <ss:Row><ss:Cell><ss:Data>As Of</ss:Data></ss:Cell><ss:Cell><ss:Data>NAV per Share</ss:Data></ss:Cell></ss:Row>
    <ss:Row><ss:Cell ss:HRef="https://test/?a=1&b=2"><ss:Data>Jan 02, 2015</ss:Data></ss:Cell><ss:Cell><ss:Data>100</ss:Data></ss:Cell></ss:Row>
    </ss:Table></ss:Worksheet></ss:Workbook>'''
    assert historical_nav(b) == {"2015-01-02": 100}
    page = json.dumps({"closingPrice": {"name": "closingPrice", "formattedAsOfDate": "Jan 02, 2015", "formattedValue": "99.50"}}).encode()
    # Whitespace-free source form, as in the issuer's hydration payload.
    page = json.dumps(json.loads(page), separators=(",", ":")).encode()
    assert latest_close(page) == ("2015-01-02", 99.5)
    with pytest.raises(ValueError):
        latest_close(b'<div> NAV 100 </div>')
