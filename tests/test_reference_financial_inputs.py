from copy import deepcopy
import hashlib
import json

import pandas as pd
import pytest

from engine.reference_financial_inputs import (
    ANCHOR_SQL, CORE_SQL, EXACT_SQL, VERSION, attach_annual_features,
    capture_annual_ledger, verify_capture,
)


def base(dates=("2020-03-31", "2020-04-30")):
    return pd.DataFrame({"asset_id": [1] * len(dates), "date": pd.to_datetime(dates),
                         "stock_code": ["005930"] * len(dates), "market": ["KOSPI"] * len(dates)})


def row(metric="total_assets", amount="100", *, period="2019-12-31", filing="20200320000001",
        available="2020-03-21T00:00:00+09:00", fs="CFS", kind="EXACT_ACCOUNT_ID", **kw):
    return {"asset_id": 1, "source_kind": kind, "source": "DART", "period_end": period,
            "fiscal_period": "FY", "fs_type": fs, "statement_type": "BS", "filing_id": filing,
            "filed": str(pd.Timestamp(available).date() - pd.Timedelta(days=1)),
            "available_at": available, "currency": "KRW", "revision_key": filing,
            "quality_run_id": "certified-id", "metric": metric, "amount": amount,
            "cumulative_amount": None, "account_id": "ifrs-full_Assets", "line_key": metric,
            "mapping_version": "exact-v1", "report_code": "11011", **kw}


def attach(rows, panel=None, **kwargs):
    return attach_annual_features(base() if panel is None else panel, pd.DataFrame(rows), **kwargs)


def test_actual_disclosure_clock_no_future_revision():
    rows = [row(), row(amount="200", filing="20200401000001", available="2020-04-02T00:00:00+09:00")]
    frame, evidence = attach(rows)
    assert frame.fy_total_assets.tolist() == [100., 200.]
    assert evidence["pit_status"] == "PIT_ASSUMED"
    assert evidence["first_vintage_verified"] is False
    assert frame.stock_code.tolist() == ["005930", "005930"]


def test_newer_missing_filing_anchor_blocks_older_values():
    rows = [row(), row(metric=None, amount=None, kind="FILING_ANCHOR", filing="20200401000001",
                       available="2020-04-02T00:00:00+09:00")]
    frame, _ = attach(rows)
    assert frame.fy_total_assets.iloc[0] == 100
    assert pd.isna(frame.fy_total_assets.iloc[1])
    assert frame.fy_filing_id.iloc[1] == "20200401000001"


def test_newer_null_correction_never_uses_old_nonnull():
    rows = [row(), row(amount=None, filing="20200401000001", available="2020-04-02T00:00:00+09:00")]
    frame, evidence = attach(rows)
    assert frame.fy_total_assets.iloc[0] == 100
    assert pd.isna(frame.fy_total_assets.iloc[1])
    assert "fy_total_assets:MISSING_OR_NONFINITE_AMOUNT" in evidence["metric_rejections"]


def test_broken_filing_identity_cannot_hide_a_revision():
    with pytest.raises(ValueError, match="filing identity"):
        attach([row(), row(filing=None)])


def test_cfs_presence_never_backfills_from_ofs():
    frame, _ = attach([row(metric=None, amount=None, kind="FILING_ANCHOR"), row(fs="OFS")])
    assert frame.fy_total_assets.isna().all()
    assert frame.fy_fs_type.eq("CFS").all()


def test_same_filing_sources_must_agree_exactly():
    frame, evidence = attach([row(), row(amount="100.000001", kind="STANDARDIZED_NAME")])
    assert frame.fy_total_assets.isna().all()
    assert "fy_total_assets:CONFLICTING_METRIC_AMOUNTS" in evidence["metric_rejections"]


def test_core_utc_raw_kst_same_filing_uses_later_clock():
    frame, _ = attach([row(), row(kind="STANDARDIZED_NAME", available="2020-03-21T00:00:00Z")])
    assert frame.fy_total_assets.eq(100).all()
    assert frame.fy_available_at.eq(pd.Timestamp("2020-03-21T00:00:00Z")).all()


def test_equal_is_cis_duplicate_accepted_but_different_rejected():
    rows = [row("net_income", "25", statement_type="IS"), row("net_income", "25", statement_type="CIS")]
    frame, _ = attach(rows)
    assert frame.fy_net_income.eq(25).all()
    rows[1]["amount"] = "24"
    assert attach(rows)[0].fy_net_income.isna().all()


def test_prior_exact_fy_not_observation_lag():
    rows = [row(), row(amount="80", period="2018-12-31", filing="20190301000001", available="2019-03-02T00:00:00+09:00")]
    assert attach(rows)[0].prev_fy_total_assets.eq(80).all()
    rows[1]["period_end"] = "2017-12-31"
    assert attach(rows)[0].prev_fy_total_assets.isna().all()


def test_prior_fy_leap_year_month_end_preserved():
    rows = [row(period="2021-02-28", filing="20210501000001", available="2021-05-02T00:00:00+09:00"),
            row(amount="80", period="2020-02-29", filing="20200501000001", available="2020-05-02T00:00:00+09:00")]
    frame, _ = attach(rows, base(("2021-05-31",)))
    assert frame.prev_fy_total_assets.iloc[0] == 80


def test_prior_scope_change_no_synthetic_comparison():
    rows = [row(), row(amount="80", period="2018-12-31", filing="20190301000001", available="2019-03-02T00:00:00+09:00", fs="OFS")]
    frame, _ = attach(rows)
    assert frame.prev_fy_total_assets.isna().all()
    assert frame.prior_financial_status.eq("PRIOR_FS_SCOPE_MISMATCH").all()


@pytest.mark.parametrize("update", [
    {"currency": "USD"}, {"currency": None}, {"filed": "2020-03-21"},
    {"quality_run_id": None}, {"report_code": "11012"}, {"revision_key": None},
])
def test_invalid_bundle_no_data(update):
    frame, _ = attach([row(**update)])
    assert frame.fy_total_assets.isna().all()


def test_quarters_and_unknown_availability_rejected():
    with pytest.raises(ValueError, match="Quarterly"):
        attach([row(fiscal_period="Q1")])
    with pytest.raises(ValueError, match="availability"):
        attach([row(available_at="2020-03-21")])


def test_fy_current_cumulative_conflict():
    frame, _ = attach([row("operating_cash_flow", "100", cumulative_amount="150")])
    assert frame.fy_operating_cash_flow.isna().all()


def test_stale_annual_and_pit_assumption_permission():
    frame, _ = attach([row()], base(("2021-07-31",)))
    assert frame.fy_total_assets.isna().all()
    assert frame.financial_status.eq("STALE_FY").all()
    with pytest.raises(ValueError, match="PIT_ASSUMED"):
        attach([row()], allow_pit_assumed=False)


def test_invalid_identity_and_duplicate_grid():
    panel = base()
    panel["stock_code"] = 5930
    with pytest.raises(ValueError, match="identity"):
        attach([row()], panel)
    with pytest.raises(ValueError, match="identity"):
        attach([row()], pd.concat([base(), base()]))


def test_krx_alphanumeric_code_and_string_asset_ids_preserved():
    panel = base()
    panel["stock_code"] = "00593K"
    panel["asset_id"] = "1"
    frame, _ = attach([row()], panel)
    assert frame.stock_code.eq("00593K").all()
    assert frame.asset_id.eq(1).all()
    assert frame.fy_total_assets.eq(100).all()
    for bad in (1.5, True, None, 0):
        panel["asset_id"] = bad
        with pytest.raises(ValueError, match="identity"):
            attach([row()], panel)


def test_no_filing_is_unknown_not_zero():
    frame, evidence = attach([])
    assert frame.fy_total_assets.isna().all()
    assert evidence["status_counts"] == {"NO_AVAILABLE_FY_FILING": 2}


def test_queries_preserve_vintages_and_unmapped_filing_anchors():
    for sql in (CORE_SQL, EXACT_SQL, ANCHOR_SQL):
        assert "CERTIFIED" in sql and "available_at <=" in sql
        assert not any(word in sql.lower() for word in ("gold", "_current", "forward", "return_"))
    assert "dart_account_metric_map" not in ANCHOR_SQL
    assert "current_amount" in EXACT_SQL and "prior_amount" not in EXACT_SQL


def test_capture_hash_tampering_rejected(tmp_path):
    (tmp_path / "mapping.json").write_text("[]")
    manifest = {"version": VERSION, "status": "COMPLETE", "pit_status": "PIT_ASSUMED",
                "first_vintage_verified": False, "files": [{"path": "mapping.json",
                  "sha256": hashlib.sha256(b"[]").hexdigest()}]}
    raw = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    manifest["manifest_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    verify_capture(tmp_path)
    (tmp_path / "mapping.json").write_text("[1]")
    with pytest.raises(ValueError, match="artifact hash"):
        verify_capture(tmp_path)


def test_readwrite_transaction_refused(tmp_path):
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql): self.sql = sql
        def fetchone(self): return ("off" if "read_only" in self.sql else "repeatable read",)
    class Connection:
        def cursor(self): return Cursor()
    with pytest.raises(ValueError, match="READ ONLY"):
        capture_annual_ledger(Connection(), [1], "2014-01-01", "2026-10-01T00:00:00Z", tmp_path)


@pytest.mark.parametrize("asset", [1.5, True, "1.0", 0, -1])
def test_capture_does_not_truncate_or_coerce_invalid_asset_identity(tmp_path, asset):
    with pytest.raises(ValueError, match="asset IDs"):
        capture_annual_ledger(None, [asset], "2014-01-01", "2026-10-01T00:00:00Z", tmp_path)


def balance_rows(assets="100", liabilities="60", equity="40", **kwargs):
    return [row("total_assets", assets, **kwargs), row("total_liabilities", liabilities, **kwargs),
            row("total_equity", equity, **kwargs), row("revenue", "200", **kwargs)]


def test_balance_mismatch_quarantines_whole_fy_and_preserves_metadata():
    frame, evidence = attach(balance_rows(equity="42"))
    assert frame.fy_total_assets.isna().all()
    assert frame.fy_revenue.isna().all()  # Not only the offending balance values.
    assert frame.financial_status.eq("BALANCE_EQUATION_UNCERTAINTY").all()
    assert frame.fy_filing_id.eq("20200320000001").all()
    assert frame.fy_fs_type.eq("CFS").all()
    assert frame.fy_available_at.notna().all()
    assert "UNCERTAINTY_NOT_CONFIRMED_ERROR" in evidence["policy"]["balance_equation"]


@pytest.mark.parametrize("assets,liabilities,equity", [
    ("100", "120", "-20"),  # Negative equity is not an equation failure.
    ("100", "60", "40"),
    ("100", "60", "41"),  # Absolute 1 KRW boundary accepted.
    ("2000000", "1000000", "1000002"),  # Relative 1e-6 boundary accepted.
])
def test_balance_valid_and_exact_tolerance_boundary(assets, liabilities, equity):
    frame, _ = attach(balance_rows(assets, liabilities, equity))
    assert frame.fy_total_assets.notna().all()
    assert frame.fy_revenue.eq(200).all()


def test_balance_just_above_tolerance_is_quarantined_using_exact_decimal():
    frame, _ = attach(balance_rows("2000000", "1000000", "1000002.000001"))
    assert frame.fy_revenue.isna().all()
    assert frame.financial_status.eq("BALANCE_EQUATION_UNCERTAINTY").all()


def test_balance_missing_or_conflicting_triplet_does_not_quarantine_other_fields():
    rows = balance_rows(equity=None)
    frame, _ = attach(rows)
    assert frame.fy_revenue.eq(200).all()
    assert frame.fy_total_equity.isna().all()
    rows = balance_rows() + [row("total_equity", "999", kind="STANDARDIZED_NAME")]
    frame, _ = attach(rows)
    assert frame.fy_revenue.eq(200).all()
    assert frame.fy_total_equity.isna().all()


def test_prior_balance_mismatch_blocks_prior_fields_but_keeps_current():
    rows = balance_rows() + balance_rows(
        equity="45", period="2018-12-31", filing="20190301000001", available="2019-03-02T00:00:00+09:00")
    frame, _ = attach(rows)
    assert frame.fy_revenue.eq(200).all()
    assert frame.prev_fy_revenue.isna().all()
    assert frame.prev_fy_total_assets.isna().all()
    assert frame.prev_fy_filing_id.eq("20190301000001").all()
    assert frame.prior_financial_status.eq("BALANCE_EQUATION_UNCERTAINTY").all()


def test_balance_mismatch_never_falls_back_to_old_filing_or_valid_ofs():
    rows = balance_rows() + balance_rows(equity="43", filing="20200401000001",
                                         available="2020-04-02T00:00:00+09:00")
    rows += balance_rows(fs="OFS", filing="20200401000001", available="2020-04-02T00:00:00+09:00")
    frame, _ = attach(rows)
    assert frame.fy_revenue.iloc[0] == 200
    assert pd.isna(frame.fy_revenue.iloc[1])
    assert frame.fy_fs_type.iloc[1] == "CFS"
    assert frame.fy_filing_id.iloc[1] == "20200401000001"
