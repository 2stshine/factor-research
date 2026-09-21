from datetime import date
from pathlib import Path
import pytest

from scripts.audit_dart_pit_evidence import analyze_rows, source_helpers


SOURCE = Path(__file__).resolve().parents[2] / "TeamAlpha-data/pipeline/silver/financials.py"
pytestmark = pytest.mark.skipif(not SOURCE.exists(), reason="Upstream code not installed")


def row(**overrides):
    result = dict(rcept_no="20240329000123", account_nm="자산총계",
                  stock_code="005930", reprt_code="11011", bsns_year="2023",
                  thstrm_amount="1,000", thstrm_dt="2023.12.31 현재")
    result.update(overrides)
    return result


def test_receipt_date_does_not_imply_vintage_proof():
    d = analyze_rows([row()], Path("/data/year=2023/corp=005930/11011.json"), source_helpers(SOURCE))
    assert d["counts"]["mapped_numeric_rows_before_silver_quality_filter"] == 1
    assert not d["counts"].get("mapped_numeric_assumed_deadline_availability_rows")
    assert "pit_approved" not in d


def test_missing_receipt_exposes_assumed_deadline():
    helpers = source_helpers(SOURCE)
    d = analyze_rows([row(rcept_no="")], Path("/data/year=2023/corp=005930/11011.json"), helpers)
    assert d["counts"]["mapped_numeric_assumed_deadline_availability_rows"] == 1
    assert d["counts"]["mapped_numeric_fallback_revision_key_rows"] == 1
    assert helpers["_available_date"](date(2023, 12, 31), "FY", None) == date(2024, 4, 2)


def test_invalid_receipt_is_not_valid_date():
    d = analyze_rows([row(rcept_no="20241329000123")], Path("/data/year=2023/corp=005930/11011.json"), source_helpers(SOURCE))
    assert d["counts"]["mapped_numeric_assumed_deadline_availability_rows"] == 1
    assert not d["counts"].get("raw_rows_without_14_digit_receipt")


def test_missing_amount_excluded_not_replaced_with_zero():
    d = analyze_rows([row(thstrm_amount="-")], Path("/data/year=2023/corp=005930/11011.json"), source_helpers(SOURCE))
    assert d["counts"]["mapped_missing_or_invalid_amount_rows"] == 1
    assert not d["counts"].get("mapped_numeric_rows_before_silver_quality_filter")


def test_period_end_fallback_separate_from_publication_fallback():
    d = analyze_rows([row(thstrm_dt="")], Path("/data/year=2023/corp=005930/11011.json"), source_helpers(SOURCE))
    assert d["counts"]["mapped_numeric_period_end_fallback_rows"] == 1
    assert not d["counts"].get("mapped_numeric_assumed_deadline_availability_rows")
