"""Synthetic bounded-PIT overlay replay; no database or economic outcomes."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
import pytest

from engine import fundamental_contract as legacy
from engine import fundamentals
from engine import historical_fundamental_overlay as overlay
from engine.panel import Panel

RUN = "11111111-1111-4111-8111-111111111111"
BASE_RUN = "22222222-2222-4222-8222-222222222222"


def original(quarter, fs, *, value=None, filed=None, until="2023-08-01", revision=None):
    start, end, default_filed, default_value = {
        "Q1": ("2015-01-01", "2015-03-31", "2015-05-01", "10"),
        "Q2": ("2015-04-01", "2015-06-30", "2015-08-01", "20"),
        "Q3": ("2015-07-01", "2015-09-30", "2015-11-01", "30"),
    }[quarter]
    filed = filed or default_filed
    available = date.fromisoformat(filed) + timedelta(days=1)
    revision = revision or filed.replace("-", "") + "000001"
    out = {**overlay.DEFAULT_FIELDS, "asset_id": 1, "stock_code": "000001", "corp_code": "00000001",
        "period_start": start, "period_end": end, "fiscal_period": quarter, "fs_type": fs,
        "value": format(float(default_value if value is None else value), ".6f"),
        "filing_id": revision, "revision_key": revision, "filed": filed, "available_date": available.isoformat(),
        "available_at": datetime.combine(available, time.min, overlay.KST).isoformat(),
        "valid_until_exclusive": until, "evidence": {"scope_id": quarter}}
    out["observation_key"] = overlay.digest([out[k] for k in ("asset_id", "period_end", "fiscal_period", "fs_type", "revision_key", "metric")])
    out["payload_sha256"] = overlay.digest(out)
    return out


def bundle(rows=None, blocks=None, *, through="2023-07-31", mapping=True):
    rows = rows or [original(q, fs) for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    rows = sorted(deepcopy(rows), key=lambda row: row["observation_key"])
    scopes = [{"scope_id": q, "corp_code": "00000001", "stock_code": "000001", "quarter": q,
        "period_start": original(q, "CFS")["period_start"], "period_end": original(q, "CFS")["period_end"], "events": []}
        for q in ("Q1", "Q2", "Q3")]
    evidence = {"contract_version": overlay.PUBLISHER_VERSION, "scopes": scopes,
        "covered_through_by_corp": {"00000001": through},
        "verified_scope_identity_mappings": [{"scope_id": q, "asset_id": 1, "valid_from": "2010-01-01", "valid_until_exclusive": "2030-01-01"}
                                              for q in ("Q1", "Q2", "Q3")] if mapping else [],
        "review": {"decision": "ACCEPT"}, "certification_scope": "SOURCE_ROWS_WITH_BOUNDED_VALIDITY_ONLY",
        "reader_contract": "ASOF_WINDOW_REQUIRED_NO_UNBOUNDED_FORWARD_FILL", "full_history_certified": False}
    blocks = deepcopy(blocks or [])
    binding = overlay.digest({"rows": rows, "blocking_windows": blocks, "evidence": evidence})
    metadata = {"dataset_version": "synthetic-v1", "manifest_sha256": "a" * 64, "bundle_sha256": binding,
        "input_fingerprint": binding, "quality_run_id": RUN, "dq_status": "CERTIFIED", "evidence": evidence,
        "blocking_windows": blocks}
    db_rows = [{**row, "dataset_version": metadata["dataset_version"], "quality_run_id": RUN} for row in rows]
    return overlay.bundle_from_rows(db_rows, metadata)


def base_row(period="2015-12-31", label="FY", available="2016-03-01", metric="revenue", value="100"):
    return {"asset_id": 1, "period_end": pd.Timestamp(period), "fiscal_period": label, "fs_type": "CFS",
        "statement_type": "IS" if metric == "revenue" else "BS", "metric": metric, "value": value,
        "available_date": pd.Timestamp(available), "available_at": pd.Timestamp(available, tz=overlay.KST),
        "revision_key": available.replace("-", "") + "000009", "quality_run_id": BASE_RUN}


def base():
    return pd.DataFrame([base_row(), base_row(metric="total_assets", value="500")])


def asof(frame, when):
    return frame.loc[frame.available_date.le(pd.Timestamp(when))].iloc[-1]


def test_original_quarters_complete_ttm_only_after_known_fy_and_expire_at_horizon():
    original_base, b = base(), bundle()
    unchanged = original_base.copy(deep=True)
    materialized = overlay.materialize(original_base, b)
    assert np.isnan(asof(materialized, "2016-02-29").revenue_ttm)
    assert asof(materialized, "2016-03-01").revenue_ttm == 100
    assert asof(materialized, "2023-07-31").revenue_ttm == 100
    assert np.isnan(asof(materialized, "2023-08-01").revenue_ttm)
    assert asof(materialized, "2023-08-01").total_assets == 500
    pd.testing.assert_frame_equal(original_base, unchanged)
    receipt = materialized.attrs[overlay.RECEIPT_KEY]
    assert receipt["derived_control_rows"] == 6
    assert receipt["source_expiry_applies_to_fiscal_keys_not_entire_panel"]
    assert receipt["source"] != "RDS public.fundamental / CERTIFIED DART STANDARDIZED currency query"


def with_gap():
    rows = [original(q, fs) for q in ("Q1", "Q3") for fs in ("CFS", "OFS")]
    rows += [original("Q2", fs, until="2016-06-02") for fs in ("CFS", "OFS")]
    rows += [original("Q2", fs, value="25", filed="2016-08-01") for fs in ("CFS", "OFS")]
    blocks = [{"scope_id": "Q2", "valid_from": "2016-06-02", "valid_until_exclusive": "2016-08-02", "reason": "UNRESOLVED"}]
    return bundle(rows, blocks)


def test_unknown_correction_gap_blocks_old_value_then_approved_revision_restores():
    frame = overlay.materialize(base(), with_gap())
    assert asof(frame, "2016-06-01").revenue_ttm == 100
    assert np.isnan(asof(frame, "2016-06-02").revenue_ttm)
    assert np.isnan(asof(frame, "2016-08-01").revenue_ttm)
    assert asof(frame, "2016-08-02").revenue_ttm == 100
    assert asof(frame, "2016-08-02").revenue == 35


def test_contiguous_approved_revision_transition_has_no_same_day_nan_winner():
    rows = [original(q, fs) for q in ("Q1", "Q3") for fs in ("CFS", "OFS")]
    rows += [original("Q2", fs, until="2016-06-02") for fs in ("CFS", "OFS")]
    rows += [original("Q2", fs, filed="2016-06-01", value="25") for fs in ("CFS", "OFS")]
    frame = overlay.materialize(base(), bundle(rows))
    assert asof(frame, "2016-06-02").revenue_ttm == 100
    assert all(item["available_date"] != "2016-06-02" for item in frame.attrs[overlay.RECEIPT_KEY]["validity_controls"])


def test_2015_expiry_does_not_invalidate_later_2024_ttm_or_stocks():
    raw = pd.concat([base(), pd.DataFrame([
        base_row(f"2024-{month}", f"Q{q}", available=f"2025-0{q}-01", value="250")
        for q, month in enumerate(("03-31", "06-30", "09-30", "12-31"), 1)])], ignore_index=True)
    frame = overlay.materialize(raw, bundle())
    assert asof(frame, "2025-04-01").revenue_ttm == 1000
    assert asof(frame, "2025-04-01").total_assets == 500
    assert pd.Timestamp("2023-08-01") in set(frame.available_date)


def test_future_certification_expiry_does_not_change_past_values():
    a = overlay.materialize(base(), bundle())
    b_rows = [original(q, fs, until="2024-08-01") for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    b = overlay.materialize(base(), bundle(b_rows, through="2024-07-31"))
    pd.testing.assert_frame_equal(a.loc[a.available_date.le("2023-07-31")].reset_index(drop=True),
                                  b.loc[b.available_date.le("2023-07-31")].reset_index(drop=True), check_flags=False)


def reused_base():
    row = original("Q1", "CFS")
    added = {key: row[key] for key in legacy._LEDGER_REQUIRED if key != "quality_run_id"}
    added["quality_run_id"] = BASE_RUN
    added["period_end"], added["available_date"] = pd.Timestamp(added["period_end"]), pd.Timestamp(added["available_date"])
    added["available_at"] = pd.Timestamp(added["available_at"])
    return pd.concat([base(), pd.DataFrame([added])], ignore_index=True)


def test_exact_base_revision_reused_without_duplicate():
    compiled, receipt = overlay.compile_ledger(reused_base(), bundle())
    assert receipt["exact_base_observations_reused"] == 1
    assert receipt["new_source_observations"] == 5
    exact = compiled.loc[compiled.revision_key.eq(original("Q1", "CFS")["revision_key"]) & compiled.fs_type.eq("CFS")]
    assert len(exact) == 1


@pytest.mark.parametrize("field,value", [("value", "11"), ("available_date", pd.Timestamp("2015-05-03")),
    ("available_at", pd.Timestamp("2015-05-03", tz=overlay.KST)), ("statement_type", "CIS")])
def test_exact_revision_mismatch_fails_without_overwrite(field, value):
    raw = reused_base()
    raw.loc[2, field] = value
    with pytest.raises(ValueError, match="collision mismatch"):
        overlay.compile_ledger(raw, bundle())


def test_competing_base_revision_not_silently_prioritized():
    raw = reused_base()
    raw.loc[2, "revision_key"] = "20150501009999"
    with pytest.raises(ValueError, match="Competing base revision"):
        overlay.compile_ledger(raw, bundle())


def test_duplicate_base_revision_fails_closed():
    raw = reused_base()
    with pytest.raises(ValueError, match="Duplicate exact base"):
        overlay.compile_ledger(pd.concat([raw, raw.iloc[[2]]], ignore_index=True), bundle())


def test_scope_with_no_verified_identity_is_not_attached_to_guessed_asset():
    b = bundle(blocks=[{"scope_id": "Q2", "valid_from": "2015-07-01", "valid_until_exclusive": "2015-08-02", "reason": "UNRESOLVED"}], mapping=False)
    _, receipt = overlay.compile_ledger(base(), b)
    assert receipt["unbound_blocking_scopes_not_guessed"] == [{"scope_id": "Q2", "valid_from": "2015-07-01", "reason": "UNRESOLVED"}]


def test_block_before_first_approved_value_with_verified_identity_emits_barrier():
    b = bundle(blocks=[{"scope_id": "Q2", "valid_from": "2015-07-01", "valid_until_exclusive": "2015-08-02", "reason": "WITHDRAWAL"}])
    ledger, receipt = overlay.compile_ledger(base(), b)
    assert any(control["available_date"] == "2015-07-01" for control in receipt["validity_controls"])
    assert ledger.loc[ledger.available_date.eq("2015-07-01"), "value"].isna().all()


def test_block_and_approved_interval_cannot_overlap():
    b = bundle(blocks=[{"scope_id": "Q2", "valid_from": "2016-07-01", "valid_until_exclusive": "2016-08-01", "reason": "UNRESOLVED"}])
    with pytest.raises(ValueError, match="overlap"):
        overlay.compile_ledger(base(), b)


def test_ofs_only_interval_cannot_be_used_as_cfs_fallback():
    rows = [original(q, fs) for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS") if (q, fs) != ("Q2", "CFS")]
    with pytest.raises(ValueError, match="Both statement scopes"):
        overlay.compile_ledger(base(), bundle(rows))


def test_expiry_must_not_exceed_certified_horizon():
    rows = [original(q, fs, until="2024-08-01") for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    with pytest.raises(ValueError, match="validity interval"):
        overlay.compile_ledger(base(), bundle(rows))


@pytest.mark.parametrize("change", ["amount", "omit_row", "window", "query", "dq", "bundle"])
def test_changed_source_evidence_rejected(change):
    b = bundle()
    if change == "amount":
        b["rows"][0]["value"] = "999.000000"
    elif change == "omit_row":
        b["rows"].pop()
    elif change == "window":
        b["rows"][0]["valid_until_exclusive"] = "2025-08-01"
    elif change == "query":
        b["query_source_sha256"] = "f" * 64
    elif change == "dq":
        b["dq_status"] = "REJECTED"
    elif change == "bundle":
        b["bundle_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        overlay.compile_ledger(base(), b)


def financial_panel():
    raw, b = base(), bundle()
    frame = overlay.materialize(raw, b)
    months = pd.period_range("2016-03", "2016-05", freq="M")
    p = Panel(pd.DataFrame({"asset_id": 1, "ym": months, "trade_date": months.to_timestamp("M")}), pd.Series(dtype="datetime64[ns]"))
    p.monthly = fundamentals.attach(p.monthly, frame, sorted(fundamentals.PIT_FEATURES))
    overlay.bind(p, raw, b, materialized=frame)
    return p


def test_new_binding_is_separate_from_legacy_contract_and_detects_changed_panel():
    p = financial_panel()
    assert overlay.verify(p)["status"] == "VERIFIED_EXPIRY_AWARE_OVERLAY_REPLAY"
    assert legacy.META_KEY not in p.meta
    p.monthly.loc[0, "revenue_ttm"] = 900
    with pytest.raises(ValueError, match="content changed"):
        overlay.verify(p)


def test_stale_legacy_metadata_replaced_only_after_actual_replay_binding():
    p = financial_panel()
    p.meta[legacy.META_KEY] = {"stale": True}
    with pytest.raises(ValueError, match="Unambiguous"):
        overlay.verify(p)
    overlay.bind(p, base(), bundle())
    assert legacy.META_KEY not in p.meta
    assert overlay.verify(p)["status"] == "VERIFIED_EXPIRY_AWARE_OVERLAY_REPLAY"


def test_no_receipt_or_wrong_receipt_cannot_bless_materialized_values():
    p = financial_panel()
    frame = overlay.materialize(base(), bundle())
    frame.loc[frame.index[-1], "revenue_ttm"] = 100
    with pytest.raises(ValueError, match="provenance mismatch"):
        overlay.bind(p, base(), bundle(), materialized=frame)


def test_reader_requires_read_only_before_any_query():
    class Connection:
        read_only = False
        def cursor(self):
            raise AssertionError("No query on writable connection")
    with pytest.raises(ValueError, match="Read-only"):
        overlay.read_bundle(Connection(), "synthetic-v1")


def ofs_original(quarter, **kwargs):
    row = original(quarter, "OFS", **kwargs)
    row["evidence"].update({
        "statement_scope_status": {"CFS": "EXPLICITLY_ABSENT", "OFS": "PARSED"},
        "statement_scope_details": {"CFS": {"absence_proven": True, "absence_evidence": [{
            "claim": "REPORT_EXPLICITLY_DECLARES_CFS_NOT_APPLICABLE",
            "xml_sha256": "1" * 64, "source_slice_sha256": "2" * 64,
            "exact_text": "해당사항 없음", "evidence_rule": "SYNTHETIC_PUBLISHER_CERTIFIED_PROOF",
        }]}}})
    row["payload_sha256"] = overlay.digest({k: v for k, v in row.items() if k != "payload_sha256"})
    return row


def with_basis(row, basis):
    return {**row, "fs_type": basis}


@pytest.mark.parametrize("quarter_basis,fy_basis", [("OFS", "CFS"), ("CFS", "OFS")])
def test_fy_residual_never_mixes_quarter_and_fy_statement_basis(quarter_basis, fy_basis):
    rows = ([ofs_original(q) for q in ("Q1", "Q2", "Q3")] if quarter_basis == "OFS"
            else [original(q, fs) for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")])
    raw = pd.DataFrame([with_basis(base_row(), fy_basis), base_row(metric="total_assets", value="500")])
    ledger, _ = overlay.compile_ledger(raw, bundle(rows))
    assert asof(fundamentals.materialize_pit(ledger, verbose=False), "2016-03-01").revenue_ttm == 100
    frame = overlay.materialize(raw, bundle(rows))
    assert np.isnan(asof(frame, "2016-03-01").revenue)
    assert np.isnan(asof(frame, "2016-03-01").revenue_ttm)
    assert asof(frame, "2016-03-01").total_assets == 500


def test_proven_ofs_only_with_same_basis_fy_is_usable_but_expiry_still_blocks():
    raw = pd.DataFrame([with_basis(base_row(), "OFS")])
    b = bundle([ofs_original(q) for q in ("Q1", "Q2", "Q3")])
    frame = overlay.materialize(raw, b)
    assert asof(frame, "2016-03-01").revenue_ttm == 100
    assert np.isnan(asof(frame, "2023-08-01").revenue_ttm)


@pytest.mark.parametrize("change", ["status", "proven", "evidence", "hash"])
def test_ofs_only_missing_or_unresolved_basis_proof_rejected(change):
    rows = [ofs_original(q) for q in ("Q1", "Q2", "Q3")]
    evidence = rows[0]["evidence"]
    if change == "status":
        evidence["statement_scope_status"]["CFS"] = "UNRESOLVED"
    elif change == "proven":
        evidence["statement_scope_details"]["CFS"]["absence_proven"] = False
    elif change == "evidence":
        evidence["statement_scope_details"]["CFS"].pop("absence_evidence")
    else:
        evidence["statement_scope_details"]["CFS"]["absence_evidence"][0]["source_slice_sha256"] = "wrong"
    rows[0]["payload_sha256"] = overlay.digest({k: v for k, v in rows[0].items() if k != "payload_sha256"})
    with pytest.raises(ValueError, match="Both statement scopes"):
        overlay.compile_ledger(base(), bundle(rows))


def test_expired_cfs_does_not_permanently_hide_later_proven_ofs_revision():
    rows = [original(q, fs, until="2016-06-02") for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    rows += [ofs_original(q, filed="2016-08-01") for q in ("Q1", "Q2", "Q3")]
    raw = pd.DataFrame([with_basis(base_row(), "OFS")])
    frame = overlay.materialize(raw, bundle(rows))
    assert np.isnan(asof(frame, "2016-03-01").revenue_ttm)  # Earlier CFS vs OFS FY is invalid.
    assert np.isnan(asof(frame, "2016-06-02").revenue_ttm)
    assert asof(frame, "2016-08-02").revenue_ttm == 100
    assert asof(frame, "2016-08-02").revenue == 40
    assert np.isnan(asof(frame, "2023-08-01").revenue_ttm)


def test_contiguous_cfs_to_explicit_absent_ofs_revision_clears_stale_scope_priority():
    rows = [original(q, fs, until="2016-06-02") for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    rows += [ofs_original(q, filed="2016-06-01") for q in ("Q1", "Q2", "Q3")]
    raw = pd.DataFrame([with_basis(base_row(), "OFS")])
    frame = overlay.materialize(raw, bundle(rows))
    assert np.isnan(asof(frame, "2016-06-01").revenue_ttm)
    assert asof(frame, "2016-06-02").revenue_ttm == 100


def test_guard_applies_to_mixed_base_only_asset_and_recovers_after_four_same_basis_quarters():
    rows = []
    for quarter, endpoint in enumerate(("2019-03-31", "2019-06-30", "2019-09-30", "2019-12-31", "2020-03-31"), 1):
        row = base_row(endpoint, f"Q{(quarter - 1) % 4 + 1}", f"2020-0{quarter}-01", value="25")
        rows.append({**row, "asset_id": 2, "fs_type": "OFS" if quarter == 1 else "CFS"})
    raw = pd.concat([base(), pd.DataFrame(rows)], ignore_index=True)
    frame = overlay.materialize(raw, bundle())
    second = frame.loc[frame.asset_id.eq(2)]
    assert asof(second, "2020-04-01").revenue == 25
    assert np.isnan(asof(second, "2020-04-01").revenue_ttm)
    assert asof(second, "2020-05-01").revenue_ttm == 100
    assert "ALL_REVENUE_ALL_ASSETS" in frame.attrs[overlay.RECEIPT_KEY]["revenue_statement_basis_guard"]["scope"]


def test_unknown_base_scope_is_nan_not_a_usable_separate_statement():
    raw = base()
    raw.loc[raw.metric.eq("revenue"), "fs_type"] = "UNKNOWN"
    frame = overlay.materialize(raw, bundle())
    assert np.isnan(asof(frame, "2016-03-01").revenue_ttm)


def test_explicit_q4_retains_its_own_basis_and_does_not_require_unused_fy_basis():
    raw = pd.DataFrame([with_basis(base_row(), "OFS"),
                        base_row("2015-12-31", "Q4", "2016-03-01", value="40")])
    frame = overlay.materialize(raw, bundle())
    assert asof(frame, "2016-03-01").revenue_ttm == 100


def test_basis_guard_preserves_every_non_revenue_value_at_old_and_added_dates():
    rows = [original(q, fs, until="2016-06-02") for q in ("Q1", "Q2", "Q3") for fs in ("CFS", "OFS")]
    rows += [ofs_original(q, filed="2016-06-01") for q in ("Q1", "Q2", "Q3")]
    raw, b = base(), bundle(rows)
    ledger, _ = overlay.compile_ledger(raw, b)
    old = fundamentals.materialize_pit(ledger, verbose=False)
    new = overlay.materialize(raw, b)
    expected = pd.merge_asof(new[["asset_id", "available_date"]], old.drop(columns="asset_id"), on="available_date", direction="backward")
    cols = [col for col in old if col not in {"revenue", "revenue_ttm"}]
    pd.testing.assert_frame_equal(new[cols].reset_index(drop=True), expected[cols].reset_index(drop=True))


def test_future_basis_changes_leave_past_snapshot_values_unchanged():
    earlier = overlay.materialize(base(), bundle())
    future = with_basis(base_row("2016-03-31", "Q1", "2024-01-01", value="700"), "OFS")
    later = overlay.materialize(pd.concat([base(), pd.DataFrame([future])], ignore_index=True), bundle())
    pd.testing.assert_frame_equal(earlier.loc[earlier.available_date.lt("2024-01-01")].reset_index(drop=True),
                                  later.loc[later.available_date.lt("2024-01-01")].reset_index(drop=True))


def test_equal_priority_conflicting_base_values_are_not_order_dependent():
    a = {**base_row("2020-03-31", "Q1", "2020-05-01", value="30"), "asset_id": 2}
    b = {**a, "value": "31"}
    for values in ([a, b], [b, a]):
        raw = pd.concat([base(), pd.DataFrame(values)], ignore_index=True)
        frame = overlay.materialize(raw, bundle())
        assert np.isnan(asof(frame.loc[frame.asset_id.eq(2)], "2020-05-01").revenue)
