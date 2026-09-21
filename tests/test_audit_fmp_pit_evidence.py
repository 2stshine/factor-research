import json

import pytest

from scripts.audit_fmp_pit_evidence import (
    cpi_supplement, inspect_legacy, new_series_review, verify_hash, write_once,
)


def test_current_cot_agreement_never_implies_historical_approval():
    row = dict(series_id="HG", kind="cot", rows=611, first="2015-01-06", latest="2026-09-15",
               source_integrity="PASS", independent_value_check="PASS", remaining_requirements=["FIRST_VINTAGE_VALUES"])
    result = new_series_review(row)
    assert result["status"] == "HISTORICAL_PIT_EVIDENCE_INCOMPLETE"
    assert result["raw_series_historical_backtest_approved"] is False
    assert result["not_approved_is_not_proven_contamination"] is True


def test_policy_raw_not_approved_by_derived_context():
    row = dict(series_id="KR_POLICY_RATE", kind="macro", rows=105, first="2015", latest="2026",
               source_integrity="PASS", independent_value_check="NOT_PERFORMED", remaining_requirements=[])
    result = new_series_review(row)
    assert result["derived_context_exists"] is True
    assert result["raw_series_historical_backtest_approved"] is False


def test_cpi_preserves_current_difference_and_limits_briefing_finding():
    row = dict(series_id="KR_CPI_MOM", reference_month="2024-04", fmp_actual=0.0, official_value=0.1,
               official_url="https://mods.go.kr/example")
    result = cpi_supplement([row])
    assert result["dated_briefing_actual"] == result["fmp_actual"]
    assert result["current_mods_headline_actual"] != result["fmp_actual"]
    assert result["new_pit_approval"] is False
    assert result["raw_http_body_saved"] is False
    assert result["briefing_contains_other_field_correction_notice"] is True
    with pytest.raises(ValueError):
        cpi_supplement([row, row])
    with pytest.raises(ValueError):
        cpi_supplement([{**row, "fmp_actual": 0.1}])


def test_changed_evidence_rejected(tmp_path):
    path = tmp_path / "proof.json"
    path.write_text(json.dumps({"actual": 0.0}))
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_hash(path, "0" * 64)


def test_no_overwrite(tmp_path):
    path = tmp_path / "proof.json"
    write_once(path, b"first")
    write_once(path, b"first")
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        write_once(path, b"second")
    assert path.read_bytes() == b"first"


def test_static_contract_missing_cutoff_fails():
    source = "SYMBOLS = {'^VIX': 'index'}\nMATURITIES = ('month3',)\n"
    with pytest.raises(ValueError, match="contract changed"):
        inspect_legacy(source, "CREATE FUNCTION example()")
