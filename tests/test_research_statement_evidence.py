"""Synthetic contract tests only; no empirical coverage or PIT certification."""
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from engine.research_statement_evidence import pair_annual_cfo_assets


def line(metric="operating_cash_flow", **changes):
    row = dict(asset_id=1, source="DART", fiscal_period="FY", business_year=2023,
               period_end=date(2023, 12, 31), report_code="11011", fs_type="CFS",
               filing_id="202403010001", revision_key="202403010001", filed=date(2024, 3, 1),
               available_at=datetime(2024, 3, 2, tzinfo=timezone.utc), currency="KRW",
               metric=metric, statement_type="CF" if metric == "operating_cash_flow" else "BS",
               current_amount=Decimal("10" if metric == "operating_cash_flow" else "100"),
               current_cumulative_amount=None, metric_candidate_count=1,
               quality_run_id="certified-run-fixture", mapping_version="dart-exact-id-v1",
               account_id="ifrs-full_fixture", line_key=metric)
    row.update(changes)
    return row


def annual(**changes):
    return [line(**changes), line("total_assets", **changes)]


def run(rows=None, **changes):
    args = dict(business_year=2023, as_of="2024-04-01T00:00:00+00:00",
                eligible_asset_ids=[1], scope_ref="synthetic-contract-fixtures")
    args.update(changes)
    return pair_annual_cfo_assets(annual() if rows is None else rows, **args)


def reasons(result):
    return result["rejects"][0]["reasons"]


def test_exact_pair_and_lineage_preserved_without_factor_or_certification():
    rows = annual()
    before = deepcopy(rows)
    result = run(rows)
    assert rows == before
    assert result["pairs"][0]["operating_cash_flow"] == "10"
    assert result["pairs"][0]["total_assets"] == "100"
    for key in ("filed", "revision_key", "quality_run_id", "mapping_version", "line_key"):
        assert result["pairs"][0]["cfo_lineage"][key] == str(rows[0][key])
    assert result["purpose"] == "DIAGNOSTIC_ONLY"
    assert result["pit_certified"] is False
    assert result["factor_admission"] == "NOT_ASSESSED"


def test_future_restatement_does_not_change_any_output_even_when_ambiguous():
    future = annual(filing_id="future", available_at="2024-05-01T00:00:00Z",
                    revision_key="future", metric_candidate_count=2, current_amount="NaN")
    assert run(annual() + future) == run()
    assert run(list(reversed(annual() + future))) == run()


def test_availability_exact_boundary_and_timezone_aware_cutoff():
    rows = annual(available_at="2024-03-02T00:00:00+09:00")
    assert run(rows, as_of="2024-03-01T14:59:59Z")["pairs"] == []
    assert len(run(rows, as_of="2024-03-01T15:00:00Z")["pairs"]) == 1
    utc_rows = annual(available_at="2024-03-01T15:00:00Z")
    assert len(run(utc_rows, as_of="2024-03-01T15:00:00Z")["pairs"]) == 1
    with pytest.raises(ValueError, match="timezone-aware"):
        run(as_of="2024-04-01")


def test_latest_missing_both_targets_never_falls_back():
    newest = line("inventories", filing_id="new", revision_key="new",
                  available_at="2024-03-20T00:00:00Z")
    result = run(annual() + [newest])
    assert result["pairs"] == []
    assert reasons(result) == ["MISSING_OPERATING_CASH_FLOW", "MISSING_TOTAL_ASSETS"]


def test_prefer_cfs_in_latest_filing_and_never_splice_or_fallback():
    assert run(annual() + annual(fs_type="OFS"))["pairs"][0]["fs_type"] == "CFS"
    assert run(annual(fs_type="OFS"))["pairs"][0]["fs_type"] == "OFS"
    rows = [line("total_assets")] + annual(fs_type="OFS")
    assert reasons(run(rows)) == ["MISSING_OPERATING_CASH_FLOW"]
    assert reasons(run([line(), line("total_assets", fs_type="OFS")])) == ["MISSING_TOTAL_ASSETS"]
    latest = annual(fs_type="OFS", filing_id="new", revision_key="new",
                    available_at="2024-03-20T00:00:00Z")
    assert run(annual() + latest)["pairs"][0]["fs_type"] == "OFS"


@pytest.mark.parametrize("changes,reason", [
    ({"metric_candidate_count": 2}, "AMBIGUOUS_OPERATING_CASH_FLOW"),
    ({"metric_candidate_count": True}, "AMBIGUOUS_OPERATING_CASH_FLOW"),
    ({"currency": "USD"}, "CURRENCY_MISMATCH"),
    ({"currency": " "}, "MISSING_CURRENCY"),
    ({"current_amount": "NaN"}, "INVALID_CURRENT_CFO"),
    ({"current_amount": None, "current_cumulative_amount": "10"}, "INVALID_CURRENT_CFO"),
    ({"current_cumulative_amount": "11"}, "FY_CFO_AMOUNT_CONTRADICTION"),
    ({"current_cumulative_amount": "Infinity"}, "FY_CFO_AMOUNT_CONTRADICTION"),
    ({"period_end": date(2023, 6, 30)}, "PERIOD_END_MISMATCH"),
    ({"report_code": "11012"}, "FY_REPORT_CODE_MISMATCH"),
    ({"quality_run_id": None}, "MISSING_LINEAGE"),
    ({"statement_type": "BS"}, "STATEMENT_TYPE_MISMATCH"),
])
def test_invalid_latest_pair_never_revives_earlier_valid_filing(changes, reason):
    latest = annual(filing_id="new", revision_key="new", available_at="2024-03-20T00:00:00Z")
    latest[0].update(changes)
    result = run(annual() + latest)
    assert result["pairs"] == [] and reason in reasons(result)


def test_duplicate_rows_fail_even_if_declared_candidate_count_is_one():
    assert "AMBIGUOUS_OPERATING_CASH_FLOW" in reasons(run(annual() + [line(line_key="duplicate")]))


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "Infinity", None])
def test_positive_finite_assets_required(amount):
    assert "INVALID_POSITIVE_CURRENT_ASSETS" in reasons(run([line(), line("total_assets", current_amount=amount)]))


@pytest.mark.parametrize("amount", ["0", "-10", "12.345678"])
def test_fy_current_and_cumulative_equal_accept_zero_and_negative_cfo(amount):
    assert run([line(current_amount=amount, current_cumulative_amount=amount), line("total_assets")])["pairs"]


def test_denominator_includes_absent_assets_and_empty_universe_is_undefined():
    result = run(eligible_asset_ids=[1, 2, 3])
    assert result["coverage"]["eligible_assets"] == 3
    assert result["coverage"]["matched_fraction"] == 1 / 3
    assert [row["asset_id"] for row in result["rejects"]] == [2, 3]
    assert run([], eligible_asset_ids=[])["coverage"]["matched_fraction"] is None


def test_other_year_quarter_source_and_ineligible_asset_cannot_supply_pair():
    ignored = (annual(business_year=2022, available_at="2024-03-25T00:00:00Z")
               + annual(fiscal_period="Q2") + annual(source="OTHER") + annual(asset_id=9))
    assert run(ignored + annual()) == run()
    assert run(ignored)["pairs"] == []


def test_invalid_available_time_blocks_unorderable_filing():
    assert reasons(run(annual() + annual(available_at="2024-03-20"))) == ["INVALID_AVAILABILITY"]


def test_non_december_fy_and_revision_tie_policy():
    rows = annual(period_end=date(2023, 6, 30))
    newest = annual(period_end=date(2023, 6, 30), filing_id="z", revision_key="z")
    assert run(rows + newest)["pairs"][0]["filing_id"] == "z"


def test_actual_driver_uuid_and_utc_timestamp_types_are_supported():
    rows = annual(quality_run_id=UUID("00000000-0000-0000-0000-000000000001"),
                  available_at=datetime(2024, 3, 1, 15, tzinfo=timezone.utc))
    assert run(rows)["pairs"][0]["cfo_lineage"]["quality_run_id"] == str(rows[0]["quality_run_id"])


def test_missing_financial_scope_is_rejected_without_exception():
    rows = annual()
    del rows[0]["fs_type"]
    assert "INVALID_FS_TYPE" in reasons(run(rows))
