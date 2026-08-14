"""Fail-closed authentication of the Silver dividend total-return lineage."""
from __future__ import annotations

import json
from copy import deepcopy
from decimal import Decimal

import pandas as pd
import pytest

from engine import silver
from engine.panel import from_silver_frame


def _identity_rows() -> pd.DataFrame:
    return pd.DataFrame([{
        "asset_id": 1,
        "identifier": "005930",
        "valid_from": pd.Timestamp("1975-06-11"),
        "valid_to": pd.NaT,
    }])


def _evidence_frames() -> dict[str, pd.DataFrame]:
    identity = silver.total_return_asset_identity_evidence(_identity_rows())
    receipt_rows = [
        {
            "receipt_no": "20260102000001",
            "asset_id": 1,
            "ticker": "005930",
            "corp_cls": "Y",
            "report_name": "cash",
            "dart_rm": "",
            "announcement_date": pd.Timestamp("2026-01-02"),
            "revision_kind": "ORIGINAL_DECISION",
            "revision_root_receipt_no": "20260102000001",
            "previous_receipt_no": None,
            "terminal_receipt_no": "20260102000001",
            "terminal_announcement_date": pd.Timestamp("2026-01-02"),
            "is_terminal_economic_revision": True,
            "source_evidence_status": "VERIFIED_OPENDART_DOCUMENT",
            "cash_amount_status": "POSITIVE",
            "record_date": pd.Timestamp("2026-01-31"),
            "payment_date": None,
            "cash_amount": 100.0,
            "viewer_evidence_sha256": None,
            "economic_evidence_sha256": "1" * 64,
            "reviewed_correction_id": None,
            "payment_date_quality_status": None,
            "pit_event_date": pd.Timestamp("2026-01-31"),
            "mapping_status": "INCLUDED",
            "excluded_reason": None,
        },
        {
            "receipt_no": "20260202000002",
            "asset_id": 1,
            "ticker": "0008Z0",
            "corp_cls": "E",
            "report_name": "cash",
            "dart_rm": "",
            "announcement_date": pd.Timestamp("2026-02-02"),
            "revision_kind": "ORIGINAL_DECISION",
            "revision_root_receipt_no": "20260202000002",
            "previous_receipt_no": None,
            "terminal_receipt_no": "20260202000002",
            "terminal_announcement_date": pd.Timestamp("2026-02-02"),
            "is_terminal_economic_revision": True,
            "source_evidence_status": "VERIFIED_OPENDART_DOCUMENT",
            "cash_amount_status": "POSITIVE",
            "record_date": pd.Timestamp("2026-02-28"),
            "payment_date": None,
            "cash_amount": 200.0,
            "viewer_evidence_sha256": None,
            "economic_evidence_sha256": "2" * 64,
            "reviewed_correction_id": None,
            "payment_date_quality_status": None,
            "pit_event_date": pd.Timestamp("2026-02-28"),
            "mapping_status": "INCLUDED",
            "excluded_reason": None,
        },
        {
            "receipt_no": "20140102000003",
            "asset_id": None,
            "ticker": "123456",
            "corp_cls": "N",
            "report_name": "cash",
            "dart_rm": "",
            "announcement_date": pd.Timestamp("2014-01-02"),
            "revision_kind": "ORIGINAL_DECISION",
            "revision_root_receipt_no": "20140102000003",
            "previous_receipt_no": None,
            "terminal_receipt_no": "20140102000003",
            "terminal_announcement_date": pd.Timestamp("2014-01-02"),
            "is_terminal_economic_revision": True,
            "source_evidence_status": "VERIFIED_OPENDART_DOCUMENT",
            "cash_amount_status": "POSITIVE",
            "record_date": pd.Timestamp("2014-01-31"),
            "payment_date": None,
            "cash_amount": 50.0,
            "viewer_evidence_sha256": None,
            "economic_evidence_sha256": "3" * 64,
            "reviewed_correction_id": None,
            "payment_date_quality_status": None,
            "pit_event_date": pd.Timestamp("2014-01-31"),
            "mapping_status": "EXCLUDED",
            "excluded_reason": "BEFORE_CONTRACT",
        },
        {
            "receipt_no": "20260103000004",
            "asset_id": None,
            "ticker": "005930",
            "corp_cls": "Y",
            "report_name": "attachment correction",
            "dart_rm": "",
            "announcement_date": pd.Timestamp("2026-01-03"),
            "revision_kind": "ATTACHMENT_ONLY",
            "revision_root_receipt_no": "20260102000001",
            "previous_receipt_no": "20260102000001",
            "terminal_receipt_no": "20260102000001",
            "terminal_announcement_date": pd.Timestamp("2026-01-02"),
            "is_terminal_economic_revision": False,
            "source_evidence_status": "VERIFIED_ATTACHMENT_CORRECTION",
            "cash_amount_status": "ATTACHMENT_ONLY",
            "record_date": None,
            "payment_date": None,
            "cash_amount": None,
            "viewer_evidence_sha256": "4" * 64,
            "economic_evidence_sha256": "1" * 64,
            "reviewed_correction_id": None,
            "payment_date_quality_status": None,
            "pit_event_date": pd.Timestamp("2026-01-31"),
            "mapping_status": "EXCLUDED",
            "excluded_reason": (
                "NO_CERTIFIED_KOSPI_KOSDAQ_PRICE_EPISODE"
            ),
        },
    ]
    receipt_frame = pd.DataFrame(receipt_rows)
    action_defaults = {
        column: None for column in silver.PUBLISHED_ACTION_DIGEST_COLUMNS
    }
    action_rows = []
    for receipt in receipt_rows[:2]:
        action_rows.append({
            **action_defaults,
            "asset_id": receipt["asset_id"],
            "source": "DART_DISCLOSURE",
            "action_key": receipt["receipt_no"],
            "action_type": "cash_dividend",
            "announcement_date": receipt["announcement_date"],
            "record_date": receipt["record_date"],
            "payment_date": receipt["payment_date"],
            "cash_amount": receipt["cash_amount"],
            "currency": "KRW",
            "status": "announced",
            "report_name": receipt["report_name"],
            "dart_rm": receipt["dart_rm"],
            "corp_cls": receipt["corp_cls"],
            "action_scope": "ISSUER",
            "cash_amount_status": receipt["cash_amount_status"],
            "source_evidence_status": receipt["source_evidence_status"],
            "correction_of_action_key": receipt["previous_receipt_no"],
            "revision_root_action_key": receipt[
                "revision_root_receipt_no"
            ],
            "revision_kind": receipt["revision_kind"],
            "viewer_evidence_sha256": receipt["viewer_evidence_sha256"],
            "economic_evidence_sha256": receipt[
                "economic_evidence_sha256"
            ],
            "reviewed_correction_id": receipt["reviewed_correction_id"],
            "payment_date_quality_status": receipt[
                "payment_date_quality_status"
            ],
            "source_body_sha256": receipt["economic_evidence_sha256"],
        })
    action_rows.append({
        **action_defaults,
        "asset_id": 1,
        "source": "DART_DISCLOSURE",
        "action_key": "20260302000003",
        "action_type": "stock_dividend",
        "announcement_date": pd.Timestamp("2026-01-02"),
        "record_date": pd.Timestamp("2026-01-31"),
        "ratio_numerator": 1.0,
        "ratio_denominator": 10.0,
        "currency": "KRW",
        "status": "confirmed",
        "report_name": "주식배당결정",
        "corp_cls": "Y",
        "action_scope": "ISSUER",
        "source_body_sha256": "3" * 64,
    })
    action_frame = pd.DataFrame(action_rows)
    action_cash_parity = silver._action_cash_parity_frame(action_frame)
    cash_scale_support_frame = pd.DataFrame([{
        "action_snapshot_run_id": "action-run",
        "evidence_key": "scale-evidence-1",
        "support_action_source": "DART_DISCLOSURE",
        "support_action_key": "20260302000003",
        "support_action_type": "stock_dividend",
        "target_cash_receipt_no": "20260102000001",
        "target_adjustment_date": pd.Timestamp("2026-01-30"),
        "support_action_body_path": (
            "corporate_actions/dart/documents/year=2026/"
            "corp=005930/rcept=20260302000003.zip"
        ),
        "support_action_body_sha256": "3" * 64,
        "support_action_quality_run_id": "action-run",
        "support_announcement_date": pd.Timestamp("2026-01-02"),
        "support_ex_date": None,
        "support_record_date": pd.Timestamp("2026-01-31"),
        "support_ratio_numerator": 1.0,
        "support_ratio_denominator": 10.0,
        "support_entitlement_security_class": "COMMON",
        "support_distributed_security_class": "COMMON",
        "support_expected_price_factor": None,
        "support_reference_price": None,
        "support_reason": None,
        "support_report_name": "주식배당결정",
        "support_action_scope": "ISSUER",
        "support_semantic_group_keys": '["stock-dividend-1"]',
        "support_semantic_role": "ADJUSTMENT_COMPONENT",
        "manifest_support_row_sha256": None,
    }], columns=silver.CASH_SCALE_SUPPORT_ACTION_COLUMNS)
    cash_scale_support_frame.loc[0, "manifest_support_row_sha256"] = (
        silver._cash_scale_manifest_support_row_sha(
            cash_scale_support_frame.iloc[0]
        )
    )
    cash_scale_source_frame = pd.DataFrame([{
        "action_snapshot_run_id": "action-run",
        "evidence_key": "scale-evidence-1",
        "asset_id": 1,
        "ticker": "005930",
        "cash_receipt_no": "20260102000001",
        "cash_source_evidence_status": "VERIFIED_OPENDART_DOCUMENT",
        "cash_action_body_path": "cash/20260102000001.zip",
        "cash_action_body_sha256": "1" * 64,
        "cash_economic_body_path": "cash/20260102000001.zip",
        "cash_economic_body_schema": "OPENDART_DOCUMENT_ZIP_V1",
        "cash_economic_sha256": "1" * 64,
        "support_action_count": 1,
        "support_action_digest": (
            silver.cash_scale_support_manifest_digest(
                cash_scale_support_frame
            )
        ),
        "support_semantic_group_count": 1,
        "price_source": "KRX",
        "previous_price_source_object_key": "prices/2026-01-29.parquet",
        "previous_price_source_content_sha256": "4" * 64,
        "previous_price_source_etag": "5" * 32,
        "previous_price_source_schema": "marcap_parquet_v1",
        "adjustment_price_source_object_key": "prices/2026-01-30.parquet",
        "adjustment_price_source_content_sha256": "8" * 64,
        "adjustment_price_source_etag": "6" * 32,
        "adjustment_price_source_schema": "marcap_parquet_v1",
        "previous_trade_date": pd.Timestamp("2026-01-29"),
        "adjustment_trade_date": pd.Timestamp("2026-01-30"),
        "raw_previous_close": 100.0,
        "raw_applied_close": 95.0,
        "raw_reference_price": 94.0,
        "expected_price_factor": 0.94,
        "cash_scale_basis": "PRE_EVENT_PRICE_SCALE",
        "manifest_row_sha256": None,
    }], columns=silver.CASH_SCALE_SOURCE_EVIDENCE_COLUMNS)
    cash_scale_source_frame.loc[0, "manifest_row_sha256"] = (
        silver._cash_scale_manifest_row_sha(cash_scale_source_frame.iloc[0])
    )
    cash_scale_source_metadata = {
        "contract": silver.TOTAL_RETURN_CASH_SCALE_SOURCE_CONTRACT,
        "manifest_sha256": "e" * 64,
        "manifest_parent_row_count": 1,
        "manifest_parent_row_digest": (
            silver.cash_scale_source_manifest_digest(
                cash_scale_source_frame
            )
        ),
        "manifest_support_action_count": 1,
        "manifest_support_action_digest": (
            silver.cash_scale_support_manifest_digest(
                cash_scale_support_frame
            )
        ),
        "manifest_support_semantic_group_count": 1,
        "persisted_parent_row_count": 1,
        "persisted_parent_row_digest": silver.cash_scale_source_evidence_digest(
            cash_scale_source_frame
        ),
        "persisted_support_action_count": 1,
        "persisted_support_action_digest": silver.cash_scale_support_action_digest(
            cash_scale_support_frame
        ),
        "persisted_support_semantic_group_count": 1,
        "changed_scale_coverage_count": 1,
        "unresolved_count": 0,
    }
    cash_scale_resolution_frame = pd.DataFrame([{
        "asset_id": 1,
        "source": "DART_DISCLOSURE",
        "action_key": "20260102000001",
        "resolution_version": silver.TOTAL_RETURN_RESOLUTION_VERSION,
        "resolved_ex_date": pd.Timestamp("2026-01-30"),
        "applied_trade_date": pd.Timestamp("2026-01-30"),
        "previous_trade_date": pd.Timestamp("2026-01-29"),
        "raw_cash_amount": 100.0,
        "adjusted_cash_amount": 94.0,
        "previous_close": 100.0,
        "previous_adj_close": 94.0,
        "applied_close": 95.0,
        "applied_adj_close": 95.0,
        "previous_price_scale": 0.94,
        "applied_price_scale": 1.0,
        "selected_cash_scale": 0.94,
        "cash_adjustment_scale_basis": "PRE_EVENT_PRICE_SCALE",
        "scale_change_detected": True,
        "scale_evidence_action_snapshot_run_id": "action-run",
        "scale_evidence_key": "scale-evidence-1",
        "scale_price_factor_observed": 0.94,
        "scale_price_factor_reference": 0.94,
        "scale_price_factor_parity": True,
    }], columns=(
        *silver.CASH_SCALE_RESOLUTION_DIGEST_COLUMNS,
        "resolved_ex_date",
    ))
    cash_scale_resolution_metadata = {
        "contract": silver.TOTAL_RETURN_CASH_SCALE_RESOLUTION_CONTRACT,
        "row_count": 1,
        "row_digest": silver.cash_scale_resolution_evidence_digest(
            cash_scale_resolution_frame
        ),
        "applied_event_count": 1,
        "stable_scale_event_count": 0,
        "changed_scale_event_count": 1,
        "unresolved_count": 0,
        "resolution_parity_count": 1,
        "adjusted_cash_parity_count": 1,
        "first_listing_exclusion_count": 0,
        "explicit_exclusion_count": 1,
        "adj_close_decimal_places": 4,
        "cash_in_adj_close": False,
    }
    pit_scope = {
        "contract": silver.TOTAL_RETURN_PIT_SCOPE_CONTRACT,
        "input_action_count": 5,
        "included_action_count": 3,
        "excluded_action_count": 2,
        "included_by_corp_cls": {"Y": 2, "E": 1},
        "excluded_by_corp_cls": {"N": 1, "UNKNOWN": 1},
        "excluded_by_reason": {
            "NO_EVENT_DATE_PIT_IDENTITY": 1,
            "BEFORE_CONTRACT": 1,
        },
    }
    source_receipts = {
        "source_cash_receipt_count": 4,
        "economic_decision_count": 3,
        "attachment_correction_count": 1,
        "no_common_cash_dividend_count": 0,
        "withdrawn_or_cancelled_count": 0,
        "pending_record_date_count": 0,
        "unresolved_cash_receipt_count": 0,
        "included_cash_receipt_count": 2,
        "excluded_cash_receipt_count": 2,
        "included_cash_receipts_by_corp_cls": {"E": 1, "Y": 1},
        "excluded_cash_receipts_by_corp_cls": {"N": 1, "Y": 1},
        "cash_receipt_exclusion_reasons": {
            "BEFORE_CONTRACT": 1,
            "NO_CERTIFIED_KOSPI_KOSDAQ_PRICE_EPISODE": 1,
        },
        "source_receipt_row_digest": silver.source_receipt_digest(
            receipt_frame
        ),
        "terminal_economic_receipt_count": 3,
        "terminal_economic_receipt_digest": (
            silver.terminal_source_receipt_digest(receipt_frame)
        ),
    }
    published_actions = {
        "published_action_count": 3,
        "published_action_row_digest": silver.published_action_digest(
            action_frame
        ),
        "published_action_scope_contract": (
            "issuer_cash_ex_plus_manifest_scale_support_v1"
        ),
        "included_cash_action_parity_count": 2,
        "included_cash_action_parity_digest": (
            silver.included_cash_parity_digest(action_cash_parity)
        ),
    }
    disclosure_audit = {
        "contract": silver.TOTAL_RETURN_DISCLOSURE_OBSERVATION_CONTRACT,
        "observation_count": 3,
        "unique_receipt_count": 4,
        "mutable_conflict_digest": "c" * 64,
    }
    metadata = {
        "contract_release": silver.TOTAL_RETURN_CONTRACT_RELEASE,
        "certified_scope": {
            "source": "KRX",
            "asset_type": "stock",
            "instrument_type": "common_stock",
            "markets": ["KOSPI", "KOSDAQ"],
            "coverage_start": "2015-01-01",
        },
        "asset_count": 1,
        "price_row_count": 100,
        "cash_action_count": 2,
        "canonical_event_count": 2,
        "applied_event_count": 1,
        "excluded_event_count": 1,
        "resolution_version": silver.TOTAL_RETURN_RESOLUTION_VERSION,
        "action_snapshot_run_id": "action-run",
        "action_snapshot": {
            "manifest_sha256": "a" * 64,
            "body_digest": "b" * 64,
            "body_count": 97_486,
            "action_count": 3,
            "coverage_start": "2015-01-01",
            "coverage_end": "2026-08-10",
            "pit_scope": pit_scope,
            "source_receipts": source_receipts,
            "published_actions": published_actions,
            "disclosure_observation_audit": disclosure_audit,
            "cash_adjustment_scale_evidence": (
                cash_scale_source_metadata
            ),
        },
        "asset_identity": identity,
        "source_price_history_metadata_only": {
            "coverage_start": "1995-05-02",
            "coverage_end": "2026-08-06",
            "certified_as_total_return": False,
            "markets": ["KOSPI", "KOSDAQ"],
        },
        "per_row_run_parity": {
            "quality_field": "total_return_quality_run_id",
            "expected": 100,
            "actual": 100,
            "passed": True,
        },
        "input_scope": dict(silver.TOTAL_RETURN_INPUT_SCOPE),
        "research_role": dict(silver.TOTAL_RETURN_RESEARCH_ROLE),
        "cash_adjustment_scale_evidence": cash_scale_resolution_metadata,
    }
    return {
        "contract": pd.DataFrame([{
            "source": "KRX",
            "asset_type": "stock",
            "field_name": "total_return_close",
            "methodology_version": silver.TOTAL_RETURN_METHOD,
            "dividend_treatment": silver.TOTAL_RETURN_DIVIDEND_TREATMENT,
            "status": "CERTIFIED",
            "coverage_start": pd.Timestamp("2015-01-02"),
            "coverage_end": pd.Timestamp("2026-08-06"),
            "quality_run_id": "return-run",
            "metadata": metadata,
            "certified_at": pd.Timestamp("2026-08-11"),
        }]),
        "schema": pd.DataFrame([{
            "has_total_return_lineage": True,
            "has_dividend_resolution": True,
            "has_action_snapshot_contract": True,
            "has_dividend_source_receipt": True,
            "has_cash_scale_source_evidence": True,
            "has_cash_scale_support_action": True,
            "cash_scale_source_columns": [
                *silver.CASH_SCALE_SOURCE_EVIDENCE_COLUMNS,
                "recorded_at",
            ],
            "cash_scale_support_columns": [
                *silver.CASH_SCALE_SUPPORT_ACTION_COLUMNS,
                "recorded_at",
            ],
            "has_resolution_scale_columns": True,
            "has_resolution_v2_scale_check": True,
            "has_action_corp_cls_provenance": True,
            "has_cash_scale_support_source_type_check": True,
            "has_cash_scale_support_role_semantics_check": True,
            "resolution_pk_columns": [
                "quality_run_id", "asset_id", "source", "action_key",
                "resolution_version",
            ],
            "source_receipt_pk_columns": [
                "quality_run_id", "receipt_no",
            ],
            "cash_scale_source_pk_columns": [
                "action_snapshot_run_id", "evidence_key",
            ],
            "cash_scale_source_unique_columns": [
                "action_snapshot_run_id", "asset_id", "cash_receipt_no",
                "adjustment_trade_date",
            ],
            "cash_scale_source_parent_identity_unique_columns": [
                "action_snapshot_run_id", "evidence_key",
                "cash_receipt_no", "adjustment_trade_date",
            ],
            "cash_scale_source_snapshot_fk_columns": [
                "action_snapshot_run_id",
            ],
            "cash_scale_source_receipt_fk_columns": [
                "action_snapshot_run_id", "cash_receipt_no",
            ],
            "cash_scale_support_pk_columns": [
                "action_snapshot_run_id", "evidence_key",
                "support_action_source", "support_action_key",
                "support_action_type",
            ],
            "cash_scale_support_parent_fk_columns": [
                "action_snapshot_run_id", "evidence_key",
            ],
            "cash_scale_support_parent_identity_fk_columns": [
                "action_snapshot_run_id", "evidence_key",
                "target_cash_receipt_no", "target_adjustment_date",
            ],
            "cash_scale_support_parent_identity_fk_target_columns": [
                "action_snapshot_run_id", "evidence_key",
                "cash_receipt_no", "adjustment_trade_date",
            ],
            "cash_scale_support_quality_fk_columns": [
                "support_action_quality_run_id",
            ],
            "resolution_scale_fk_columns": [
                "scale_evidence_action_snapshot_run_id",
                "scale_evidence_key",
            ],
        }]),
        "scope": pd.DataFrame([{
            "price_row_count": 100,
            "asset_count": 1,
            "coverage_start": pd.Timestamp("2015-01-02"),
            "coverage_end": pd.Timestamp("2026-08-06"),
            "raw_certified_row_count": 100,
            "total_return_run_row_count": 100,
            "positive_total_return_row_count": 100,
            "total_return_run_count": 1,
            "total_return_run_status": "CERTIFIED",
            "total_return_run_mode": silver.TOTAL_RETURN_REBUILD_MODE,
            "source_history_start": pd.Timestamp("1995-05-02"),
            "source_history_end": pd.Timestamp("2026-08-06"),
        }]),
        "action": pd.DataFrame([{
            "quality_run_id": "action-run",
            "schema_version": silver.TOTAL_RETURN_ACTION_SNAPSHOT_SCHEMA,
            "manifest_sha256": "a" * 64,
            "body_digest": "b" * 64,
            "body_count": 97_486,
            "coverage_start": pd.Timestamp("2015-01-01"),
            "coverage_end": pd.Timestamp("2026-08-10"),
            "action_count": 3,
            "snapshot_metadata": {
                "total_return_actions_only": True,
                "markets": ["KOSPI", "KOSDAQ"],
                "pit_scope": deepcopy(pit_scope),
                "source_receipts": deepcopy(source_receipts),
                "published_actions": deepcopy(published_actions),
                "disclosure_observation_audit": deepcopy(disclosure_audit),
                "cash_adjustment_scale_evidence": deepcopy(
                    cash_scale_source_metadata
                ),
            },
            "quality_run_status": "CERTIFIED",
            "quality_run_mode": silver.TOTAL_RETURN_ACTION_SNAPSHOT_MODE,
            "persisted_action_count": 3,
            "persisted_cash_action_count": 2,
        }]),
        "resolution": pd.DataFrame([{
            "resolution_row_count": 2,
            "expected_version_row_count": 2,
            "applied_canonical_row_count": 1,
            "excluded_row_count": 1,
            "unresolved_source_row_count": 0,
            "unknown_exclusion_row_count": 0,
        }]),
        "identity": _identity_rows(),
        "source_receipts": receipt_frame,
        "published_actions": action_frame,
        "cash_scale_source": cash_scale_source_frame,
        "cash_scale_support": cash_scale_support_frame,
        "cash_scale_resolution": cash_scale_resolution_frame,
    }


def _validate(frames: dict[str, pd.DataFrame]):
    return silver._validate_total_return_contract(
        frames["contract"],
        frames["schema"],
        frames["scope"],
        frames["action"],
        frames["resolution"],
        frames["identity"],
        frames["source_receipts"],
        frames["published_actions"],
        frames["cash_scale_source"],
        frames["cash_scale_support"],
        frames["cash_scale_resolution"],
    )


def _refresh_cash_scale_source_contract(
    frames: dict[str, pd.DataFrame],
) -> None:
    support = frames["cash_scale_support"]
    for index, row in support.iterrows():
        support.loc[index, "manifest_support_row_sha256"] = (
            silver._cash_scale_manifest_support_row_sha(row)
        )
    parents = frames["cash_scale_source"]
    for index, row in parents.iterrows():
        children = support[
            support["action_snapshot_run_id"].astype(str).eq(
                str(row["action_snapshot_run_id"])
            )
            & support["evidence_key"].astype(str).eq(
                str(row["evidence_key"])
            )
        ]
        parents.loc[index, "support_action_count"] = len(children)
        parents.loc[index, "support_action_digest"] = (
            silver.cash_scale_support_manifest_digest(children)
        )
        try:
            group_count = silver._cash_scale_support_group_count(children)
        except ValueError:
            group_count = int(row["support_semantic_group_count"])
        parents.loc[index, "support_semantic_group_count"] = group_count
        parents.loc[index, "manifest_row_sha256"] = (
            silver._cash_scale_manifest_row_sha(parents.loc[index])
        )
    try:
        global_group_count = silver._cash_scale_support_group_count(support)
    except ValueError:
        global_group_count = int(
            parents["support_semantic_group_count"].sum()
        )
    metadata = frames["contract"].at[0, "metadata"][
        "action_snapshot"
    ]["cash_adjustment_scale_evidence"]
    metadata.update({
        "manifest_parent_row_count": len(parents),
        "manifest_parent_row_digest": (
            silver.cash_scale_source_manifest_digest(parents)
        ),
        "manifest_support_action_count": len(support),
        "manifest_support_action_digest": (
            silver.cash_scale_support_manifest_digest(support)
        ),
        "manifest_support_semantic_group_count": global_group_count,
        "persisted_parent_row_count": len(parents),
        "persisted_parent_row_digest": silver.cash_scale_source_evidence_digest(
            parents
        ),
        "persisted_support_action_count": len(support),
        "persisted_support_action_digest": silver.cash_scale_support_action_digest(
            support
        ),
        "persisted_support_semantic_group_count": global_group_count,
        "changed_scale_coverage_count": len(parents),
    })
    frames["action"].at[0, "snapshot_metadata"][
        "cash_adjustment_scale_evidence"
    ] = deepcopy(metadata)


def test_complete_total_return_lineage_is_content_addressed():
    _contract, evidence = _validate(_evidence_frames())

    assert evidence["validation_status"] == "VERIFIED"
    assert evidence["certified_scope_start"] == "2015-01-01"
    assert evidence["coverage_start"] == "2015-01-02"
    assert evidence["price_row_count"] == 100
    assert evidence["contract_release"] == silver.TOTAL_RETURN_CONTRACT_RELEASE
    assert evidence["cash_action_count"] == 2
    assert evidence["applied_event_count"] == 1
    assert evidence["excluded_event_count"] == 1
    assert evidence["source_receipt_row_count"] == 4
    assert evidence["published_action_count"] == 3
    assert evidence["included_cash_action_parity_count"] == 2
    assert evidence["cash_scale_source_evidence_count"] == 1
    assert evidence["cash_scale_support_action_count"] == 1
    assert evidence["cash_scale_support_semantic_group_count"] == 1
    assert evidence["cash_scale_resolution_row_count"] == 1
    assert evidence["cash_scale_changed_event_count"] == 1
    assert evidence["cash_scale_evidence_match_count"] == 1
    assert silver.verify_total_return_validation_evidence(evidence) == evidence


@pytest.mark.parametrize(
    ("previous_close", "previous_adj_close", "raw_cash", "adjusted_cash"),
    [
        (131_500.0, 124_000.0, 1_450.0, 1_367.30038023),
        (10_200.0, 4_960.0, 100.0, 48.62745098),
    ],
)
def test_changed_scale_cash_uses_pre_event_scale(
    previous_close: float,
    previous_adj_close: float,
    raw_cash: float,
    adjusted_cash: float,
):
    scale = previous_adj_close / previous_close
    frame = pd.DataFrame([{
        "asset_id": 1,
        "source": "DART_DISCLOSURE",
        "action_key": "20260102000001",
        "resolution_version": silver.TOTAL_RETURN_RESOLUTION_VERSION,
        "resolved_ex_date": pd.Timestamp("2026-01-30"),
        "applied_trade_date": pd.Timestamp("2026-01-30"),
        "previous_trade_date": pd.Timestamp("2026-01-29"),
        "raw_cash_amount": raw_cash,
        "adjusted_cash_amount": adjusted_cash,
        "previous_close": previous_close,
        "previous_adj_close": previous_adj_close,
        "applied_close": previous_adj_close,
        "applied_adj_close": previous_adj_close,
        "previous_price_scale": scale,
        "applied_price_scale": 1.0,
        "selected_cash_scale": scale,
        "cash_adjustment_scale_basis": "PRE_EVENT_PRICE_SCALE",
        "scale_change_detected": True,
        "scale_evidence_action_snapshot_run_id": "action-run",
        "scale_evidence_key": "scale-evidence-1",
        "scale_price_factor_observed": scale,
        "scale_price_factor_reference": scale,
        "scale_price_factor_parity": True,
    }])

    checks = silver._cash_scale_resolution_semantic_checks(frame)

    assert all(checks.values()), checks


def test_adjusted_cash_uses_numeric_scale_then_half_up_cash_rounding():
    assert silver._cash_scale_adjusted_cash(
        1_450,
        "0.942965779468",
    ) == Decimal("1367.30038023")
    assert silver._cash_scale_adjusted_cash(
        "0.5",
        "1.000000010000",
    ) == Decimal("0.50000001")
    assert silver._cash_scale_adjusted_cash(
        "100000000",
        "0.1234567890125",
    ) == Decimal("12345678.90130000")


def test_four_decimal_intervals_do_not_hide_a_small_real_scale_reset():
    previous = silver._cash_scale_stored_scale_interval(
        close=100.0, adjusted_close=100.0,
    )
    applied = silver._cash_scale_stored_scale_interval(
        close=100.0, adjusted_close=99.99981,
    )

    assert abs(1.0 - (99.99981 / 100.0)) < 0.000002
    assert previous[0] > applied[1]


def test_composite_collision_supports_multiple_actions_and_groups():
    frames = _evidence_frames()
    template = frames["cash_scale_support"].iloc[0].to_dict()
    support = pd.DataFrame([
        {
            **template,
            "support_action_source": "DART_STRUCTURED",
            "support_action_key": "20260102000010",
            "support_action_type": "bonus_issue",
            "support_ratio_numerator": 1.0,
            "support_ratio_denominator": 4.0,
            "support_expected_price_factor": 0.8,
            "support_entitlement_security_class": "COMMON",
            "support_distributed_security_class": "COMMON",
            "support_report_name": "무상증자",
            "support_semantic_group_keys": '["bonus-group"]',
            "support_semantic_role": "ADJUSTMENT_COMPONENT",
        },
        {
            **template,
            "support_action_source": "KRX_KIND",
            "support_action_key": "20260102000012",
            "support_action_type": "stock_dividend",
            "support_action_body_path": (
                "corporate_actions/krx/kind/body_objects/"
                f"sha256={'3' * 64}.html"
            ),
            "support_record_date": pd.Timestamp("2026-01-31"),
            "support_ratio_numerator": 1.0,
            "support_ratio_denominator": 10.0,
            "support_entitlement_security_class": (
                "COMMON_AND_PREFERRED"
            ),
            "support_distributed_security_class": "NEW_PREFERRED",
            "support_report_name": "주식배당 결정",
            "support_semantic_group_keys": '["stock-group"]',
            "support_semantic_role": "ADJUSTMENT_COMPONENT",
        },
        {
            **template,
            "support_action_source": "DART_DISCLOSURE",
            "support_action_key": "20260102000011",
            "support_action_type": "combined_detachment",
            "support_ex_date": pd.Timestamp("2026-01-30"),
            "support_ratio_numerator": None,
            "support_ratio_denominator": None,
            "support_entitlement_security_class": None,
            "support_distributed_security_class": None,
            "support_expected_price_factor": None,
            "support_reference_price": 94.0,
            "support_reason": "무상증자 및 주식배당",
            "support_report_name": "권배락",
            "support_semantic_group_keys": (
                '["bonus-group","stock-group"]'
            ),
            "support_semantic_role": "CORROBORATION",
        },
    ], columns=silver.CASH_SCALE_SUPPORT_ACTION_COLUMNS)
    for index, row in support.iterrows():
        support.loc[index, "manifest_support_row_sha256"] = (
            silver._cash_scale_manifest_support_row_sha(row)
        )
    parent = frames["cash_scale_source"].copy()
    parent.loc[0, "support_action_count"] = 3
    parent.loc[0, "support_action_digest"] = (
        silver.cash_scale_support_manifest_digest(support)
    )
    parent.loc[0, "support_semantic_group_count"] = 2

    group_count, parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )
    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )

    assert group_count == 2
    assert parity is True
    assert all(semantic.values()), semantic

    inconsistent_bonus = support.copy()
    inconsistent_bonus.loc[0, "support_ratio_denominator"] = 5.0
    inconsistent_bonus.loc[0, "manifest_support_row_sha256"] = (
        silver._cash_scale_manifest_support_row_sha(
            inconsistent_bonus.loc[0]
        )
    )
    inconsistent_semantic = silver._cash_scale_support_semantic_checks(
        inconsistent_bonus,
        action_snapshot_run_id="action-run",
    )
    assert inconsistent_semantic["semantic_roles"] is False

    cancelled = support.copy()
    cancelled.loc[1, "support_report_name"] = "주식배당결정 취소"
    cancelled.loc[1, "manifest_support_row_sha256"] = (
        silver._cash_scale_manifest_support_row_sha(cancelled.loc[1])
    )
    cancelled_semantic = silver._cash_scale_support_semantic_checks(
        cancelled,
        action_snapshot_run_id="action-run",
    )
    assert cancelled_semantic["snapshot_fields"] is False

    noncanonical_kind_report = support.copy()
    noncanonical_kind_report.loc[1, "support_report_name"] = "주식배당결정"
    noncanonical_kind_report.loc[1, "manifest_support_row_sha256"] = (
        silver._cash_scale_manifest_support_row_sha(
            noncanonical_kind_report.loc[1]
        )
    )
    kind_report_semantic = silver._cash_scale_support_semantic_checks(
        noncanonical_kind_report,
        action_snapshot_run_id="action-run",
    )
    assert kind_report_semantic["semantic_roles"] is False

    wrong_adjustment_date = support.copy()
    wrong_adjustment_date.loc[
        2, "support_ex_date"
    ] = pd.Timestamp("2026-01-29")
    wrong_adjustment_date.loc[2, "manifest_support_row_sha256"] = (
        silver._cash_scale_manifest_support_row_sha(
            wrong_adjustment_date.loc[2]
        )
    )
    _group_count, wrong_date_parity = (
        silver._cash_scale_parent_support_parity(
            parent,
            wrong_adjustment_date,
        )
    )
    assert wrong_date_parity is False


def _dart_viewer_bonus_parity_frames(
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the actual 001060 viewer-backed bonus support shape."""
    frames = _evidence_frames()
    parent = frames["cash_scale_source"].copy()
    parent.loc[0, "ticker"] = "001060"

    body_sha = "b" * 64
    receipt = "20161216000097"
    support = frames["cash_scale_support"].copy()
    support.loc[0, [
        "support_action_source", "support_action_key",
        "support_action_type", "support_action_body_path",
        "support_action_body_sha256", "support_announcement_date",
        "support_ex_date", "support_record_date",
        "support_ratio_numerator", "support_ratio_denominator",
        "support_entitlement_security_class",
        "support_distributed_security_class",
        "support_expected_price_factor", "support_reference_price",
        "support_reason", "support_report_name",
        "support_semantic_group_keys", "support_semantic_role",
    ]] = [
        "DART_VIEWER", receipt, "bonus_issue",
        (
            "corporate_actions/dart/support_action_families/objects/"
            f"sha256={body_sha}.html"
        ),
        body_sha, pd.Timestamp("2016-12-16"),
        pd.Timestamp("2017-01-01"), None, 0.02, 1.0,
        "COMMON", "COMMON", 1.0 / 1.02, None, None,
        "주요사항보고서(무상증자결정)",
        '["001060|2017-01-01|BONUS_ISSUE|0.02"]',
        "ADJUSTMENT_COMPONENT",
    ]
    support.loc[0, "manifest_support_row_sha256"] = (
        silver._cash_scale_manifest_support_row_sha(support.loc[0])
    )
    parent.loc[0, "support_action_digest"] = (
        silver.cash_scale_support_manifest_digest(support)
    )
    parent.loc[0, "manifest_row_sha256"] = (
        silver._cash_scale_manifest_row_sha(parent.loc[0])
    )

    defaults = {
        column: None for column in silver.PUBLISHED_ACTION_DIGEST_COLUMNS
    }
    cash_action = frames["published_actions"].iloc[0].to_dict()
    viewer_action = {
        **defaults,
        "asset_id": int(parent.loc[0, "asset_id"]),
        "source": "DART_VIEWER",
        "action_key": receipt,
        "action_type": "bonus_issue",
        "announcement_date": pd.Timestamp("2016-12-16"),
        "ex_date": pd.Timestamp("2017-01-01"),
        "record_date": None,
        "ratio_numerator": 0.02,
        "ratio_denominator": 1.0,
        "expected_price_factor": 1.0 / 1.02,
        "report_name": "주요사항보고서(무상증자결정)",
        "action_scope": "ISSUER",
        "source_body_sha256": body_sha,
    }
    actions = pd.DataFrame(
        [cash_action, viewer_action],
        columns=silver.PUBLISHED_ACTION_DIGEST_COLUMNS,
    )
    return parent, support, actions, frames["source_receipts"].copy()


def _rehash_support_parent(
    parent: pd.DataFrame,
    support: pd.DataFrame,
) -> None:
    support.loc[0, "manifest_support_row_sha256"] = (
        silver._cash_scale_manifest_support_row_sha(support.loc[0])
    )
    parent.loc[0, "support_action_digest"] = (
        silver.cash_scale_support_manifest_digest(support)
    )
    parent.loc[0, "manifest_row_sha256"] = (
        silver._cash_scale_manifest_row_sha(parent.loc[0])
    )


def test_dart_viewer_bonus_common_component_exact_contract():
    parent, support, actions, receipts = _dart_viewer_bonus_parity_frames()

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )
    group_count, parent_parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )

    assert all(semantic.values()), semantic
    assert (group_count, parent_parity) == (1, True)
    assert silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    ) is True


@pytest.mark.parametrize(
    ("field", "value", "failed_semantic", "fails_action_parity"),
    [
        (
            "support_action_body_path",
            "corporate_actions/dart/support_action_families/objects/"
            + "sha256=" + "c" * 64 + ".html",
            "source_body",
            True,
        ),
        (
            "support_entitlement_security_class", "PREFERRED",
            "semantic_roles", False,
        ),
        (
            "support_distributed_security_class", "PREFERRED",
            "semantic_roles", False,
        ),
        ("support_ratio_numerator", 0.0, "snapshot_fields", True),
        ("support_expected_price_factor", 0.0, "snapshot_fields", True),
        ("support_expected_price_factor", 0.99, "semantic_roles", True),
    ],
)
def test_dart_viewer_bonus_tamper_fails_closed(
    field: str,
    value: object,
    failed_semantic: str,
    fails_action_parity: bool,
):
    parent, support, actions, receipts = _dart_viewer_bonus_parity_frames()
    support.loc[0, field] = value
    _rehash_support_parent(parent, support)

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )

    assert semantic[failed_semantic] is False
    action_parity = silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    )
    assert action_parity is (not fails_action_parity)


@pytest.mark.parametrize(
    ("support_field", "action_field", "value"),
    [
        ("support_report_name", "report_name", "무상증자결정"),
        (
            "support_report_name", "report_name",
            "[첨부정정]주요사항보고서(무상증자결정)",
        ),
        ("support_ex_date", "ex_date", None),
        (
            "support_record_date", "record_date",
            pd.Timestamp("2017-01-01"),
        ),
    ],
)
def test_dart_viewer_bonus_synchronized_semantic_drift_fails_closed(
    support_field: str, action_field: str, value: object,
):
    parent, support, actions, receipts = _dart_viewer_bonus_parity_frames()
    support.loc[0, support_field] = value
    _rehash_support_parent(parent, support)
    viewer = actions["source"].eq("DART_VIEWER")
    actions.loc[viewer, action_field] = value

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )

    assert semantic["semantic_roles"] is False
    # The synchronized persisted action and all manifest hashes still agree;
    # the viewer-only producer semantics are the independent fail-closed gate.
    assert silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    ) is True


def test_dart_viewer_bonus_synchronized_effective_date_drift_fails_closed():
    parent, support, actions, receipts = _dart_viewer_bonus_parity_frames()
    changed_date = pd.Timestamp("2017-01-02")
    support.loc[0, "support_ex_date"] = changed_date
    _rehash_support_parent(parent, support)
    viewer = actions["source"].eq("DART_VIEWER")
    actions.loc[viewer, "ex_date"] = changed_date

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )
    _group_count, parent_parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )

    assert all(semantic.values()), semantic
    assert parent_parity is False
    assert silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    ) is True


@pytest.mark.parametrize(
    "group",
    [
        "000660|2017-01-01|BONUS_ISSUE|0.02",
        "001060|2017-01-01|BONUS_ISSUE|0.020000000001",
        "001060|2017-01-01|bonus_issue|0.02",
        "bonus-common",
    ],
)
def test_dart_viewer_bonus_group_identity_drift_fails_closed(group: str):
    parent, support, _actions, _receipts = _dart_viewer_bonus_parity_frames()
    support.loc[0, "support_semantic_group_keys"] = json.dumps(
        [group], separators=(",", ":"),
    )
    _rehash_support_parent(parent, support)

    _group_count, parent_parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )

    assert parent_parity is False


def test_dart_viewer_bonus_corporate_action_drift_fails_closed():
    parent, support, actions, receipts = _dart_viewer_bonus_parity_frames()
    viewer = actions["source"].eq("DART_VIEWER")
    actions.loc[viewer, "expected_price_factor"] = 0.99

    assert silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    ) is False


def _dart_viewer_stock_dividend_parity_frames(
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build a viewer stock family whose own date differs from cash."""
    parent, support, actions, receipts = (
        _dart_viewer_bonus_parity_frames()
    )
    parent.loc[0, "ticker"] = "018670"
    body_sha = "d" * 64
    receipt = "20260115000001"
    record = pd.Timestamp("2026-02-02")
    support.loc[0, [
        "support_action_key", "support_action_type",
        "support_action_body_path", "support_action_body_sha256",
        "support_announcement_date", "support_ex_date",
        "support_record_date", "support_ratio_numerator",
        "support_ratio_denominator",
        "support_entitlement_security_class",
        "support_distributed_security_class",
        "support_expected_price_factor", "support_reference_price",
        "support_reason", "support_report_name",
        "support_semantic_group_keys",
    ]] = [
        receipt, "stock_dividend",
        (
            "corporate_actions/dart/support_action_families/objects/"
            f"sha256={body_sha}.html"
        ),
        body_sha, pd.Timestamp("2026-01-15"), None, record,
        0.01, 1.0, "COMMON", "COMMON", None, None, None,
        "[기재정정]주식배당결정   ",
        '["018670|2026-02-02|STOCK_DIVIDEND|0.01"]',
    ]
    _rehash_support_parent(parent, support)

    viewer = actions["source"].eq("DART_VIEWER")
    actions.loc[viewer, [
        "action_key", "action_type", "announcement_date", "ex_date",
        "record_date", "ratio_numerator", "ratio_denominator",
        "expected_price_factor", "report_name", "source_body_sha256",
    ]] = [
        receipt, "stock_dividend", pd.Timestamp("2026-01-15"), None,
        record, 0.01, 1.0, None, "[기재정정]주식배당결정   ", body_sha,
    ]
    assert receipts.loc[0, "record_date"] != record
    return parent, support, actions, receipts


def _kind_paid_increase_parity_frames(
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the sole reviewed 183190 KIND paid-rights component."""
    parent, support, actions, receipts = (
        _dart_viewer_bonus_parity_frames()
    )
    cash_receipt = "20180226800579"
    parent.loc[0, [
        "evidence_key", "ticker", "cash_receipt_no",
        "previous_trade_date", "adjustment_trade_date",
        "raw_previous_close", "raw_applied_close", "raw_reference_price",
        "expected_price_factor",
    ]] = [
        "183190:20180226800579:2017-12-27", "183190", cash_receipt,
        pd.Timestamp("2017-12-26"), pd.Timestamp("2017-12-27"),
        118_500.0, 111_500.0, 116_500.0, 116_500.0 / 118_500.0,
    ]
    body_sha = (
        "cf15168b7b9f16f7808252be7dc2a81a06dc23b30d0d14e41cebf8674ebf35c9"
    )
    support.loc[0, [
        "evidence_key", "support_action_source", "support_action_key",
        "support_action_type", "target_cash_receipt_no",
        "target_adjustment_date", "support_action_body_path",
        "support_action_body_sha256", "support_announcement_date",
        "support_ex_date", "support_record_date",
        "support_ratio_numerator", "support_ratio_denominator",
        "support_entitlement_security_class",
        "support_distributed_security_class",
        "support_expected_price_factor", "support_reference_price",
        "support_reason", "support_report_name",
        "support_semantic_group_keys",
    ]] = [
        "183190:20180226800579:2017-12-27", "KRX_KIND",
        "20180201000086", "paid_increase", cash_receipt,
        pd.Timestamp("2017-12-27"),
        (
            "corporate_actions/krx/kind/body_objects/"
            f"sha256={body_sha}.html"
        ),
        body_sha, pd.Timestamp("2018-02-01"), None,
        pd.Timestamp("2017-12-31"), 0.1456981704, 1.0,
        "COMMON", "COMMON", None, None, None, "유상증자 결정",
        '["183190|2017-12-31|PAID_INCREASE|0.1456981704"]',
    ]
    _rehash_support_parent(parent, support)

    cash = actions["source"].eq("DART_DISCLOSURE")
    actions.loc[cash, "action_key"] = cash_receipt
    paid = actions["source"].eq("DART_VIEWER")
    actions.loc[paid, [
        "source", "action_key", "action_type", "announcement_date",
        "ex_date", "record_date", "ratio_numerator",
        "ratio_denominator", "expected_price_factor", "report_name",
        "source_body_sha256",
    ]] = [
        "KRX_KIND", "20180201000086", "paid_increase",
        pd.Timestamp("2018-02-01"), None, pd.Timestamp("2017-12-31"),
        0.1456981704, 1.0, None, "유상증자 결정", body_sha,
    ]
    receipts.loc[0, ["receipt_no", "ticker", "record_date"]] = [
        cash_receipt, "183190", pd.Timestamp("2017-12-31"),
    ]
    return parent, support, actions, receipts


def test_dart_viewer_stock_dividend_uses_verified_family_record_date():
    parent, support, actions, receipts = (
        _dart_viewer_stock_dividend_parity_frames()
    )

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )
    group_count, parent_parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )

    assert all(semantic.values()), semantic
    assert (group_count, parent_parity) == (1, True)
    assert support.loc[0, "support_record_date"] != receipts.loc[
        0, "record_date"
    ]
    assert silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    ) is True


@pytest.mark.parametrize(
    ("field", "value", "failed_layer"),
    [
        ("support_report_name", "주식배당", "semantic"),
        (
            "support_entitlement_security_class", "PREFERRED",
            "semantic",
        ),
        ("support_expected_price_factor", 0.99, "semantic"),
        (
            "support_record_date", pd.Timestamp("2026-02-03"),
            "parent",
        ),
        (
            "support_semantic_group_keys",
            '["000000|2026-02-02|STOCK_DIVIDEND|0.01"]',
            "parent",
        ),
    ],
)
def test_dart_viewer_stock_dividend_drift_fails_closed(
    field: str,
    value: object,
    failed_layer: str,
):
    parent, support, _actions, _receipts = (
        _dart_viewer_stock_dividend_parity_frames()
    )
    support.loc[0, field] = value
    _rehash_support_parent(parent, support)

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )
    _group_count, parent_parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )

    if failed_layer == "semantic":
        assert not all(semantic.values()), semantic
    else:
        assert parent_parity is False


@pytest.mark.parametrize("record", ["2026-01-30", "2026-02-07"])
def test_dart_viewer_stock_dividend_record_window_is_directional(
    record: str,
):
    parent, support, _actions, _receipts = (
        _dart_viewer_stock_dividend_parity_frames()
    )
    parsed = pd.Timestamp(record)
    support.loc[0, "support_record_date"] = parsed
    support.loc[0, "support_semantic_group_keys"] = json.dumps([
        f"018670|{parsed.date().isoformat()}|STOCK_DIVIDEND|0.01"
    ], separators=(",", ":"))
    _rehash_support_parent(parent, support)

    assert silver._cash_scale_parent_support_parity(
        parent, support,
    )[1] is False


def test_dart_viewer_stock_dividend_duplicate_component_is_rejected():
    parent, support, _actions, _receipts = (
        _dart_viewer_stock_dividend_parity_frames()
    )
    duplicated = pd.concat([support, support], ignore_index=True)

    semantic = silver._cash_scale_support_semantic_checks(
        duplicated, action_snapshot_run_id="action-run",
    )

    assert semantic["unique_identity"] is False
    assert silver._cash_scale_parent_support_parity(
        parent, duplicated,
    )[1] is False


def test_kind_paid_increase_exact_closed_contract():
    parent, support, actions, receipts = _kind_paid_increase_parity_frames()

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )
    group_count, parent_parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )

    assert all(semantic.values()), semantic
    assert (group_count, parent_parity) == (1, True)
    assert silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    ) is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("support_action_key", "20180201000087"),
        ("support_action_body_sha256", "e" * 64),
        ("support_report_name", "유상증자"),
        ("support_record_date", pd.Timestamp("2018-01-01")),
        ("support_ratio_numerator", 0.1456981705),
        ("support_distributed_security_class", "PREFERRED"),
        ("support_expected_price_factor", 0.8729),
        (
            "support_semantic_group_keys",
            '["183190|2017-12-31|PAID_INCREASE|0.1456981705"]',
        ),
    ],
)
def test_kind_paid_increase_component_drift_fails_closed(
    field: str,
    value: object,
):
    parent, support, _actions, _receipts = (
        _kind_paid_increase_parity_frames()
    )
    support.loc[0, field] = value
    _rehash_support_parent(parent, support)

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )
    _group_count, parent_parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )

    assert not all(semantic.values()) or parent_parity is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ticker", "183191"),
        ("cash_receipt_no", "20180226800578"),
        ("adjustment_trade_date", pd.Timestamp("2017-12-28")),
        ("price_source", "UNVERIFIED"),
        ("expected_price_factor", 0.9),
    ],
)
def test_kind_paid_increase_parent_or_krx_factor_drift_fails_closed(
    field: str,
    value: object,
):
    parent, support, _actions, _receipts = (
        _kind_paid_increase_parity_frames()
    )
    parent.loc[0, field] = value
    parent.loc[0, "manifest_row_sha256"] = (
        silver._cash_scale_manifest_row_sha(parent.loc[0])
    )

    assert silver._cash_scale_parent_support_parity(
        parent, support,
    )[1] is False


def test_kind_paid_increase_published_action_drift_fails_closed():
    parent, support, actions, receipts = _kind_paid_increase_parity_frames()
    paid = actions["source"].eq("KRX_KIND")
    actions.loc[paid, "source_body_sha256"] = "e" * 64

    assert silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    ) is False


def test_live_contract_accepts_viewer_stock_family_without_cash_date_alias(
    monkeypatch,
):
    frames = _evidence_frames()
    parent, support, actions, receipts = (
        _dart_viewer_stock_dividend_parity_frames()
    )
    actions = pd.concat([
        actions,
        frames["published_actions"].iloc[[1]],
    ], ignore_index=True)
    actions.loc[actions["source"].eq("DART_VIEWER"), "corp_cls"] = "Y"
    parent.loc[0, "ticker"] = "005930"
    support.loc[0, "support_semantic_group_keys"] = (
        '["005930|2026-02-02|STOCK_DIVIDEND|0.01"]'
    )
    _rehash_support_parent(parent, support)
    frames["cash_scale_source"] = parent
    frames["cash_scale_support"] = support
    frames["published_actions"] = actions
    frames["source_receipts"] = receipts
    _refresh_cash_scale_source_contract(frames)
    published = frames["contract"].at[0, "metadata"][
        "action_snapshot"
    ]["published_actions"]
    published["published_action_row_digest"] = (
        silver.published_action_digest(actions)
    )
    frames["action"].at[0, "snapshot_metadata"][
        "published_actions"
    ] = deepcopy(published)

    contract, evidence = _validate(frames)
    monkeypatch.setattr(
        silver,
        "_load_validated_total_return_contract",
        lambda conn: (contract, dict(evidence)),
    )

    assert silver.verify_live_total_return_contract(
        object(), evidence,
    ) == evidence


def _kind_corroboration_parity_frames(
    action_type: str = "ex_dividend",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the persisted shape of the reviewed 006800 KIND evidence."""
    frames = _evidence_frames()
    parent = frames["cash_scale_source"].copy()
    parent.loc[0, [
        "evidence_key", "asset_id", "ticker", "cash_receipt_no",
    ]] = ["006800-scale-evidence", 6800, "006800", "20260316800587"]
    parent.loc[0, "previous_trade_date"] = pd.Timestamp("2026-03-13")
    parent.loc[0, "adjustment_trade_date"] = pd.Timestamp("2026-03-16")
    parent.loc[0, "raw_previous_close"] = 69_500.0
    parent.loc[0, "raw_applied_close"] = 70_900.0
    parent.loc[0, "raw_reference_price"] = 69_200.0
    parent.loc[0, "expected_price_factor"] = 69_200.0 / 69_500.0

    template = frames["cash_scale_support"].iloc[0].to_dict()
    group = (
        "006800-stock-common"
        if action_type == "ex_dividend" else "006800-bonus-common"
    )
    if action_type == "ex_dividend":
        component = {
            **template,
            "evidence_key": "006800-scale-evidence",
            "support_action_key": "20260313800897",
            "target_cash_receipt_no": "20260316800587",
            "target_adjustment_date": pd.Timestamp("2026-03-16"),
            "support_action_body_path": (
                "corporate_actions/dart/documents/year=2026/corp=006800/"
                "rcept=20260313800897.zip"
            ),
            "support_action_body_sha256": "6" * 64,
            "support_announcement_date": pd.Timestamp("2026-03-13"),
            "support_record_date": pd.Timestamp("2026-03-17"),
            "support_ratio_numerator": 0.0073206,
            "support_ratio_denominator": 1.0,
            "support_report_name": "[기재정정]주식배당결정",
            "support_semantic_group_keys": f'["{group}"]',
        }
    else:
        component = {
            **template,
            "evidence_key": "006800-scale-evidence",
            "support_action_source": "DART_STRUCTURED",
            "support_action_key": "20260313800898",
            "support_action_type": "bonus_issue",
            "target_cash_receipt_no": "20260316800587",
            "target_adjustment_date": pd.Timestamp("2026-03-16"),
            "support_action_body_path": (
                "corporate_actions/dart/structured/event=bonus_issue/"
                "year=2026/corp=006800/rcept=20260313800898.json"
            ),
            "support_action_body_sha256": "8" * 64,
            "support_announcement_date": pd.Timestamp("2026-03-13"),
            "support_ex_date": None,
            "support_record_date": pd.Timestamp("2026-03-17"),
            "support_ratio_numerator": 1.0,
            "support_ratio_denominator": 4.0,
            "support_expected_price_factor": 0.8,
            "support_report_name": "무상증자",
            "support_semantic_group_keys": f'["{group}"]',
        }
    reason = {
        "ex_dividend": "주식배당",
        "rights_detachment": "무상증자",
        "combined_detachment": "무상증자 및 주식배당",
    }[action_type]
    kind_sha = (
        "6d24251bbabc1ca2b7f6dba7639d6b448e9a7df6a1ac2ebed44f7139578e6d02"
    )
    corroboration = {
        **template,
        "evidence_key": "006800-scale-evidence",
        "support_action_source": "KRX_KIND",
        "support_action_key": "20260313001262",
        "support_action_type": action_type,
        "target_cash_receipt_no": "20260316800587",
        "target_adjustment_date": pd.Timestamp("2026-03-16"),
        "support_action_body_path": (
            "corporate_actions/krx/kind/body_objects/"
            f"sha256={kind_sha}.html"
        ),
        "support_action_body_sha256": kind_sha,
        "support_announcement_date": pd.Timestamp("2026-03-13"),
        "support_ex_date": pd.Timestamp("2026-03-16"),
        "support_record_date": None,
        "support_ratio_numerator": None,
        "support_ratio_denominator": None,
        "support_entitlement_security_class": "COMMON",
        "support_distributed_security_class": None,
        "support_expected_price_factor": None,
        "support_reference_price": 69_200.0,
        "support_reason": reason,
        "support_report_name": "배당락 기준가격 안내",
        "support_semantic_group_keys": f'["{group}"]',
        "support_semantic_role": "CORROBORATION",
    }
    support = pd.DataFrame(
        [component, corroboration],
        columns=silver.CASH_SCALE_SUPPORT_ACTION_COLUMNS,
    )
    for index, row in support.iterrows():
        support.loc[index, "manifest_support_row_sha256"] = (
            silver._cash_scale_manifest_support_row_sha(row)
        )
    parent.loc[0, "support_action_count"] = len(support)
    parent.loc[0, "support_action_digest"] = (
        silver.cash_scale_support_manifest_digest(support)
    )
    parent.loc[0, "support_semantic_group_count"] = 1
    parent.loc[0, "manifest_row_sha256"] = (
        silver._cash_scale_manifest_row_sha(parent.iloc[0])
    )

    defaults = {
        column: None for column in silver.PUBLISHED_ACTION_DIGEST_COLUMNS
    }
    action_rows = [{
        **defaults,
        "asset_id": 6800,
        "source": "DART_DISCLOSURE",
        "action_key": "20260316800587",
        "action_type": "cash_dividend",
        "source_body_sha256": parent.loc[0, "cash_action_body_sha256"],
    }]
    action_rows.append({
        **defaults,
        "asset_id": 6800,
        "source": component["support_action_source"],
        "action_key": component["support_action_key"],
        "action_type": component["support_action_type"],
        "announcement_date": component["support_announcement_date"],
        "ex_date": component["support_ex_date"],
        "record_date": component["support_record_date"],
        "ratio_numerator": component["support_ratio_numerator"],
        "ratio_denominator": component["support_ratio_denominator"],
        "expected_price_factor": component["support_expected_price_factor"],
        "report_name": component["support_report_name"],
        "action_scope": "ISSUER",
        "source_body_sha256": component["support_action_body_sha256"],
    })
    action_rows.append({
        **defaults,
        "asset_id": 6800,
        "source": "KRX_KIND",
        "action_key": "20260313001262",
        "action_type": action_type,
        "announcement_date": pd.Timestamp("2026-03-13"),
        "ex_date": pd.Timestamp("2026-03-16"),
        "report_name": "배당락 기준가격 안내",
        "action_scope": "ISSUER",
        "source_body_sha256": kind_sha,
    })
    actions = pd.DataFrame(action_rows)
    receipts = pd.DataFrame([{
        "receipt_no": "20260316800587",
        "record_date": pd.Timestamp("2026-03-17"),
    }])
    return parent, support, actions, receipts


@pytest.mark.parametrize(
    "action_type",
    ["ex_dividend", "rights_detachment", "combined_detachment"],
)
def test_kind_corroboration_exact_parent_and_action_parity(action_type: str):
    parent, support, actions, receipts = (
        _kind_corroboration_parity_frames(action_type)
    )

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )
    group_count, parent_parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )

    assert all(semantic.values()), semantic
    assert (group_count, parent_parity) == (1, True)
    assert silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    ) is True


@pytest.mark.parametrize(
    ("field", "value", "failed_semantic"),
    [
        ("support_entitlement_security_class", "PREFERRED", "semantic_roles"),
        ("support_ex_date", pd.Timestamp("2026-03-17"), None),
        ("support_reference_price", 69_100.0, None),
        ("support_reason", "현금배당", "semantic_roles"),
        ("support_report_name", "배당락 기준가격 공지", "semantic_roles"),
        ("support_report_name", "배당락  기준가격 안내", "semantic_roles"),
        ("target_cash_receipt_no", "20260316800588", None),
        ("target_adjustment_date", pd.Timestamp("2026-03-17"), None),
        (
            "support_action_body_path",
            "corporate_actions/krx/kind/body_objects/sha256=" + "f" * 64
            + ".html",
            "source_body",
        ),
    ],
)
def test_kind_corroboration_tamper_fails_closed(
    field: str, value: object, failed_semantic: str | None,
):
    parent, support, actions, receipts = _kind_corroboration_parity_frames()
    support.loc[1, field] = value
    support.loc[1, "manifest_support_row_sha256"] = (
        silver._cash_scale_manifest_support_row_sha(support.loc[1])
    )
    parent.loc[0, "support_action_digest"] = (
        silver.cash_scale_support_manifest_digest(support)
    )
    parent.loc[0, "manifest_row_sha256"] = (
        silver._cash_scale_manifest_row_sha(parent.iloc[0])
    )

    semantic = silver._cash_scale_support_semantic_checks(
        support, action_snapshot_run_id="action-run",
    )
    _group_count, parent_parity = silver._cash_scale_parent_support_parity(
        parent, support,
    )

    if failed_semantic is not None:
        assert semantic[failed_semantic] is False
    assert parent_parity is False or failed_semantic is not None
    assert silver._cash_scale_support_action_parity(
        parent, support, actions, receipts,
    ) is False or parent_parity is False


def test_support_rows_cannot_be_swapped_across_parents_after_rehashing():
    frames = _evidence_frames()
    parent_a = frames["cash_scale_source"].iloc[0].to_dict()
    child_a = frames["cash_scale_support"].iloc[0].to_dict()
    parent_b = {
        **parent_a,
        "evidence_key": "scale-evidence-2",
        "asset_id": 2,
        "ticker": "0008Z0",
        "cash_receipt_no": "20260202000002",
        "previous_trade_date": pd.Timestamp("2026-02-26"),
        "adjustment_trade_date": pd.Timestamp("2026-02-27"),
    }
    child_b = {
        **child_a,
        "evidence_key": "scale-evidence-2",
        "support_action_key": "20260302000004",
        "target_cash_receipt_no": "20260202000002",
        "target_adjustment_date": pd.Timestamp("2026-02-27"),
        "support_action_body_path": (
            "corporate_actions/dart/documents/year=2026/"
            "corp=0008Z0/rcept=20260302000004.zip"
        ),
        "support_semantic_group_keys": '["stock-dividend-2"]',
    }
    parents = pd.DataFrame(
        [parent_a, parent_b], columns=silver.CASH_SCALE_SOURCE_EVIDENCE_COLUMNS,
    )
    support = pd.DataFrame(
        [child_a, child_b], columns=silver.CASH_SCALE_SUPPORT_ACTION_COLUMNS,
    )

    def rehash(
        parent_rows: pd.DataFrame, child_rows: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        parent_rows = parent_rows.copy()
        child_rows = child_rows.copy()
        for index, row in child_rows.iterrows():
            child_rows.loc[index, "manifest_support_row_sha256"] = (
                silver._cash_scale_manifest_support_row_sha(row)
            )
        for index, row in parent_rows.iterrows():
            children = child_rows[
                child_rows["action_snapshot_run_id"].astype(str).eq(
                    str(row["action_snapshot_run_id"])
                )
                & child_rows["evidence_key"].astype(str).eq(
                    str(row["evidence_key"])
                )
            ]
            parent_rows.loc[index, "support_action_count"] = len(children)
            parent_rows.loc[index, "support_action_digest"] = (
                silver.cash_scale_support_manifest_digest(children)
            )
            parent_rows.loc[index, "support_semantic_group_count"] = (
                silver._cash_scale_support_group_count(children)
            )
            parent_rows.loc[index, "manifest_row_sha256"] = (
                silver._cash_scale_manifest_row_sha(parent_rows.loc[index])
            )
        return parent_rows, child_rows

    parents, support = rehash(parents, support)
    assert silver._cash_scale_parent_support_parity(
        parents, support,
    )[1] is True

    swapped = support.copy()
    swapped["evidence_key"] = list(reversed(swapped["evidence_key"].tolist()))
    swapped_parents, swapped = rehash(parents, swapped)

    assert silver._cash_scale_parent_support_parity(
        swapped_parents, swapped,
    )[1] is False


def test_cash_scale_support_query_binds_security_class_semantics_in_order():
    columns = list(silver.CASH_SCALE_SUPPORT_ACTION_COLUMNS)
    action_type = columns.index("support_action_type")
    denominator = columns.index("support_ratio_denominator")

    assert columns[action_type + 1:action_type + 3] == [
        "target_cash_receipt_no", "target_adjustment_date",
    ]
    assert columns[denominator + 1:denominator + 4] == [
        "support_entitlement_security_class",
        "support_distributed_security_class",
        "support_expected_price_factor",
    ]
    assert (
        ",".join(columns)
        in silver.TOTAL_RETURN_CASH_SCALE_SUPPORT_ACTION_SQL
    )


def test_action_snapshot_count_reads_support_rows_not_parent_only_columns():
    sql = silver.TOTAL_RETURN_ACTION_SNAPSHOT_AUDIT_SQL

    assert "cash_adjustment_scale_support_action support" in sql
    assert "cash_adjustment_scale_source_evidence evidence" in sql
    assert "e.support_action_source" not in sql
    assert "support.support_action_source = ca.source" in sql
    assert "evidence.asset_id = ca.asset_id" in sql


def test_schema_audit_checks_both_sides_of_support_parent_identity_fk():
    sql = silver.TOTAL_RETURN_SCHEMA_AUDIT_SQL

    assert "unnest(c.conkey)" in sql
    assert "unnest(c.confkey)" in sql
    assert "cash_scale_support_parent_identity_fk_target_columns" in sql


def test_corp_cls_is_provenance_only_and_alphanumeric_ticker_is_valid():
    frames = _evidence_frames()
    assert "E" in set(frames["source_receipts"]["corp_cls"])
    assert "0008Z0" in set(frames["source_receipts"]["ticker"])

    _validate(frames)


@pytest.mark.parametrize(
    "updates,expected_invalid",
    [
        ({}, False),
        ({"viewer_evidence_sha256": "1" * 64}, True),
        ({
            "source_evidence_status": "VERIFIED_REVIEWED_SOURCE_ERRATUM",
            "reviewed_correction_id": "review-1",
        }, False),
        ({
            "source_evidence_status": "VERIFIED_REVIEWED_SOURCE_ERRATUM",
            "reviewed_correction_id": "review-1",
            "viewer_evidence_sha256": "1" * 64,
        }, True),
        ({
            "source_evidence_status": "VERIFIED_DART_VIEWER_BODY",
            "viewer_evidence_sha256": "1" * 64,
        }, False),
        ({
            "source_evidence_status": "VERIFIED_DART_VIEWER_BODY",
            "viewer_evidence_sha256": "2" * 64,
        }, True),
        ({
            "source_evidence_status": "VERIFIED_ATTACHMENT_CORRECTION",
            "cash_amount_status": "ATTACHMENT_ONLY",
            "revision_kind": "ATTACHMENT_ONLY",
            "previous_receipt_no": "20251231000000",
            "viewer_evidence_sha256": "1" * 64,
            "cash_amount": None,
        }, True),
        ({
            "source_evidence_status": "VERIFIED_ATTACHMENT_CORRECTION",
            "cash_amount_status": "ATTACHMENT_ONLY",
            "revision_kind": "ATTACHMENT_ONLY",
            "previous_receipt_no": "20251231000000",
            "viewer_evidence_sha256": "2" * 64,
            "cash_amount": None,
        }, False),
    ],
    ids=[
        "opendart-blank-viewer",
        "opendart-rejects-viewer",
        "reviewed-blank-viewer",
        "reviewed-rejects-viewer",
        "viewer-body-equal-sha",
        "viewer-body-rejects-sha-mismatch",
        "attachment-rejects-equal-sha",
        "attachment-unequal-sha",
    ],
)
def test_source_evidence_sha_shape_is_exact(
    updates: dict[str, object], expected_invalid: bool,
):
    row = _evidence_frames()["source_receipts"].iloc[[0]].copy()
    for column, value in updates.items():
        row.loc[row.index[0], column] = value

    invalid = silver._invalid_cash_evidence_mask(
        row,
        key_column="receipt_no",
        root_key_column="revision_root_receipt_no",
        correction_key_column="previous_receipt_no",
    )

    assert bool(invalid.iloc[0]) is expected_invalid


@pytest.mark.parametrize(
    "corruption",
    [
        "equal_sha",
        "null_previous",
        "missing_previous",
        "different_root",
        "different_ticker",
    ],
)
def test_attachment_requires_same_family_previous_receipt(corruption: str):
    receipts = _evidence_frames()["source_receipts"].copy()
    attachment_index = receipts.index[
        receipts["source_evidence_status"].eq(
            "VERIFIED_ATTACHMENT_CORRECTION"
        )
    ].item()
    assert not silver._source_receipt_semantic_failures(receipts).any()

    if corruption == "equal_sha":
        receipts.loc[attachment_index, "viewer_evidence_sha256"] = "1" * 64
    elif corruption == "null_previous":
        receipts.loc[attachment_index, "previous_receipt_no"] = None
    elif corruption == "missing_previous":
        receipts.loc[
            attachment_index, "previous_receipt_no"
        ] = "20990101000000"
    elif corruption == "different_root":
        receipts.loc[
            attachment_index, "revision_root_receipt_no"
        ] = "20260202000002"
    elif corruption == "different_ticker":
        receipts.loc[attachment_index, "ticker"] = "0008Z0"

    failures = silver._source_receipt_semantic_failures(receipts)
    assert bool(failures.loc[attachment_index]) is True


@pytest.mark.parametrize("corruption", [
    "legacy_schema",
    "konex_scope",
    "stale_price_run",
    "wrong_return_run_mode",
    "action_body_mismatch",
    "legacy_action_schema",
    "missing_source_receipt_table",
    "source_receipt_pk_gap",
    "missing_cash_scale_source_table",
    "missing_cash_scale_support_table",
    "cash_scale_source_column_gap",
    "cash_scale_support_column_gap",
    "missing_resolution_scale_columns",
    "missing_resolution_scale_check",
    "cash_scale_source_pk_gap",
    "cash_scale_source_unique_gap",
    "cash_scale_source_parent_identity_unique_gap",
    "cash_scale_source_snapshot_fk_gap",
    "cash_scale_source_receipt_fk_gap",
    "cash_scale_support_pk_gap",
    "cash_scale_support_fk_gap",
    "cash_scale_support_parent_identity_fk_gap",
    "cash_scale_support_parent_identity_fk_target_gap",
    "cash_scale_support_quality_fk_gap",
    "cash_scale_support_source_type_check_gap",
    "cash_scale_support_role_semantics_check_gap",
    "resolution_scale_fk_gap",
    "contract_release_gap",
    "input_scope_gap",
    "research_role_gap",
    "snapshot_pit_binding_gap",
    "pit_partition_gap",
    "source_receipt_digest_gap",
    "terminal_receipt_gap",
    "published_action_digest_gap",
    "cash_parity_digest_gap",
    "source_metadata_binding_gap",
    "disclosure_binding_gap",
    "cash_scale_source_metadata_binding_gap",
    "cash_scale_source_metadata_extra",
    "cash_scale_source_digest_gap",
    "cash_scale_price_etag_gap",
    "cash_scale_manifest_row_gap",
    "cash_scale_receipt_binding_gap",
    "cash_scale_support_binding_gap",
    "cash_scale_support_digest_gap",
    "cash_scale_support_manifest_row_gap",
    "cash_scale_support_noncanonical_groups",
    "cash_scale_support_component_gap",
    "cash_scale_support_security_class_gap",
    "cash_scale_support_snapshot_field_gap",
    "cash_scale_support_body_path_gap",
    "cash_scale_cash_action_body_gap",
    "cash_scale_source_unresolved",
    "invalid_alphanumeric_ticker",
    "resolution_gap",
    "unresolved_cash_receipt",
    "unknown_resolution_exclusion",
    "cash_scale_resolution_digest_gap",
    "cash_scale_resolution_count_gap",
    "cash_scale_resolution_unresolved",
    "cash_scale_resolution_metadata_extra",
    "cash_scale_adjusted_parity_count_gap",
    "cash_scale_explicit_exclusion_gap",
    "cash_scale_stored_price_contract_gap",
    "cash_scale_evidence_link_gap",
    "cash_scale_source_price_lineage_gap",
    "cash_scale_price_scale_gap",
    "cash_scale_factor_parity_gap",
    "cash_scale_basis_gap",
    "cash_scale_post_event_selected_gap",
    "cash_scale_adjusted_cash_gap",
    "cash_scale_raw_cash_action_gap",
    "raw_history_metadata_lie",
    "asset_identity_remap",
])
def test_any_total_return_lineage_break_fails_closed(corruption: str):
    frames = deepcopy(_evidence_frames())
    if corruption == "legacy_schema":
        frames["schema"].at[0, "resolution_pk_columns"] = ["asset_id"]
    elif corruption == "konex_scope":
        frames["contract"].at[0, "metadata"]["certified_scope"][
            "markets"
        ] = ["KOSPI", "KOSDAQ", "KONEX"]
    elif corruption == "stale_price_run":
        frames["scope"].loc[0, "total_return_run_row_count"] = 99
    elif corruption == "wrong_return_run_mode":
        frames["scope"].loc[0, "total_return_run_mode"] = "manual_patch"
    elif corruption == "action_body_mismatch":
        frames["action"].loc[0, "body_digest"] = "d" * 64
    elif corruption == "legacy_action_schema":
        frames["action"].loc[0, "schema_version"] = "dart_action_snapshot_v1"
    elif corruption == "missing_source_receipt_table":
        frames["schema"].loc[0, "has_dividend_source_receipt"] = False
    elif corruption == "source_receipt_pk_gap":
        frames["schema"].at[0, "source_receipt_pk_columns"] = ["receipt_no"]
    elif corruption == "missing_cash_scale_source_table":
        frames["schema"].loc[0, "has_cash_scale_source_evidence"] = False
    elif corruption == "missing_cash_scale_support_table":
        frames["schema"].loc[0, "has_cash_scale_support_action"] = False
    elif corruption == "cash_scale_source_column_gap":
        frames["schema"].at[0, "cash_scale_source_columns"] = [
            "action_snapshot_run_id", "evidence_key",
        ]
    elif corruption == "cash_scale_support_column_gap":
        frames["schema"].at[0, "cash_scale_support_columns"] = [
            "action_snapshot_run_id", "evidence_key",
        ]
    elif corruption == "missing_resolution_scale_columns":
        frames["schema"].loc[0, "has_resolution_scale_columns"] = False
    elif corruption == "missing_resolution_scale_check":
        frames["schema"].loc[0, "has_resolution_v2_scale_check"] = False
    elif corruption == "cash_scale_source_pk_gap":
        frames["schema"].at[0, "cash_scale_source_pk_columns"] = [
            "evidence_key",
        ]
    elif corruption == "cash_scale_source_unique_gap":
        frames["schema"].at[0, "cash_scale_source_unique_columns"] = [
            "action_snapshot_run_id", "evidence_key",
        ]
    elif corruption == "cash_scale_source_parent_identity_unique_gap":
        frames["schema"].at[
            0, "cash_scale_source_parent_identity_unique_columns"
        ] = ["action_snapshot_run_id", "evidence_key"]
    elif corruption == "cash_scale_source_snapshot_fk_gap":
        frames["schema"].at[
            0, "cash_scale_source_snapshot_fk_columns"
        ] = []
    elif corruption == "cash_scale_source_receipt_fk_gap":
        frames["schema"].at[
            0, "cash_scale_source_receipt_fk_columns"
        ] = ["cash_receipt_no"]
    elif corruption == "cash_scale_support_pk_gap":
        frames["schema"].at[0, "cash_scale_support_pk_columns"] = [
            "action_snapshot_run_id", "evidence_key",
        ]
    elif corruption == "cash_scale_support_fk_gap":
        frames["schema"].at[
            0, "cash_scale_support_parent_fk_columns"
        ] = ["evidence_key"]
    elif corruption == "cash_scale_support_parent_identity_fk_gap":
        frames["schema"].at[
            0, "cash_scale_support_parent_identity_fk_columns"
        ] = ["action_snapshot_run_id", "evidence_key"]
    elif corruption == "cash_scale_support_parent_identity_fk_target_gap":
        frames["schema"].at[
            0, "cash_scale_support_parent_identity_fk_target_columns"
        ] = [
            "action_snapshot_run_id", "evidence_key", "cash_receipt_no",
            "previous_trade_date",
        ]
    elif corruption == "cash_scale_support_quality_fk_gap":
        frames["schema"].at[
            0, "cash_scale_support_quality_fk_columns"
        ] = []
    elif corruption == "cash_scale_support_source_type_check_gap":
        frames["schema"].loc[
            0, "has_cash_scale_support_source_type_check"
        ] = False
    elif corruption == "cash_scale_support_role_semantics_check_gap":
        frames["schema"].loc[
            0, "has_cash_scale_support_role_semantics_check"
        ] = False
    elif corruption == "resolution_scale_fk_gap":
        frames["schema"].at[0, "resolution_scale_fk_columns"] = [
            "scale_evidence_key",
        ]
    elif corruption == "contract_release_gap":
        frames["contract"].at[0, "metadata"]["contract_release"] = "legacy"
    elif corruption == "input_scope_gap":
        frames["contract"].at[0, "metadata"]["input_scope"][
            "actions"
        ] = "corp_cls whitelist"
    elif corruption == "research_role_gap":
        frames["contract"].at[0, "metadata"]["research_role"][
            "feature_pit_safe"
        ] = True
    elif corruption == "snapshot_pit_binding_gap":
        frames["action"].at[0, "snapshot_metadata"]["pit_scope"][
            "excluded_action_count"
        ] = 1
    elif corruption == "pit_partition_gap":
        frames["contract"].at[0, "metadata"]["action_snapshot"][
            "pit_scope"
        ]["input_action_count"] = 4
    elif corruption == "source_receipt_digest_gap":
        frames["source_receipts"].loc[0, "cash_amount"] = 101.0
    elif corruption == "terminal_receipt_gap":
        frames["source_receipts"].loc[
            0, "is_terminal_economic_revision"
        ] = False
    elif corruption == "published_action_digest_gap":
        frames["published_actions"].loc[0, "status"] = "changed"
    elif corruption == "cash_parity_digest_gap":
        replacement = "9" * 64
        frames["contract"].at[0, "metadata"]["action_snapshot"][
            "published_actions"
        ]["included_cash_action_parity_digest"] = replacement
        frames["action"].at[0, "snapshot_metadata"]["published_actions"][
            "included_cash_action_parity_digest"
        ] = replacement
    elif corruption == "source_metadata_binding_gap":
        frames["action"].at[0, "snapshot_metadata"]["source_receipts"][
            "source_cash_receipt_count"
        ] = 5
    elif corruption == "disclosure_binding_gap":
        frames["action"].at[0, "snapshot_metadata"][
            "disclosure_observation_audit"
        ]["mutable_conflict_digest"] = "d" * 64
    elif corruption == "cash_scale_source_metadata_binding_gap":
        frames["action"].at[0, "snapshot_metadata"][
            "cash_adjustment_scale_evidence"
        ]["persisted_parent_row_count"] = 0
    elif corruption == "cash_scale_source_metadata_extra":
        for location in (
            frames["contract"].at[0, "metadata"]["action_snapshot"][
                "cash_adjustment_scale_evidence"
            ],
            frames["action"].at[0, "snapshot_metadata"][
                "cash_adjustment_scale_evidence"
            ],
        ):
            location["unexpected"] = 0
    elif corruption == "cash_scale_source_digest_gap":
        frames["cash_scale_source"].loc[0, "raw_reference_price"] = 93.0
    elif corruption == "cash_scale_price_etag_gap":
        frames["cash_scale_source"].loc[
            0, "previous_price_source_etag"
        ] = '"' + ("5" * 32) + '"'
        _refresh_cash_scale_source_contract(frames)
    elif corruption == "cash_scale_manifest_row_gap":
        frames["cash_scale_source"].loc[0, "manifest_row_sha256"] = "9" * 64
        digest = silver.cash_scale_source_evidence_digest(
            frames["cash_scale_source"]
        )
        frames["contract"].at[0, "metadata"]["action_snapshot"][
            "cash_adjustment_scale_evidence"
        ]["persisted_parent_row_digest"] = digest
        frames["action"].at[0, "snapshot_metadata"][
            "cash_adjustment_scale_evidence"
        ]["persisted_parent_row_digest"] = digest
    elif corruption == "cash_scale_receipt_binding_gap":
        frames["cash_scale_source"].loc[0, "cash_economic_sha256"] = "9" * 64
    elif corruption == "cash_scale_support_binding_gap":
        frames["cash_scale_support"].loc[0, "support_action_key"] = (
            "20990101000000"
        )
    elif corruption == "cash_scale_support_digest_gap":
        for location in (
            frames["contract"].at[0, "metadata"]["action_snapshot"][
                "cash_adjustment_scale_evidence"
            ],
            frames["action"].at[0, "snapshot_metadata"][
                "cash_adjustment_scale_evidence"
            ],
        ):
            location["persisted_support_action_digest"] = "9" * 64
    elif corruption == "cash_scale_support_manifest_row_gap":
        frames["cash_scale_support"].loc[
            0, "manifest_support_row_sha256"
        ] = "9" * 64
        persisted_digest = silver.cash_scale_support_action_digest(
            frames["cash_scale_support"]
        )
        for location in (
            frames["contract"].at[0, "metadata"]["action_snapshot"][
                "cash_adjustment_scale_evidence"
            ],
            frames["action"].at[0, "snapshot_metadata"][
                "cash_adjustment_scale_evidence"
            ],
        ):
            location["persisted_support_action_digest"] = persisted_digest
    elif corruption == "cash_scale_support_noncanonical_groups":
        frames["cash_scale_support"].loc[
            0, "support_semantic_group_keys"
        ] = '["z-group","a-group"]'
        _refresh_cash_scale_source_contract(frames)
    elif corruption == "cash_scale_support_component_gap":
        frames["cash_scale_support"].loc[
            0, "support_semantic_role"
        ] = "CORROBORATION"
        _refresh_cash_scale_source_contract(frames)
    elif corruption == "cash_scale_support_security_class_gap":
        frames["cash_scale_support"].loc[
            0, "support_distributed_security_class"
        ] = "NEW_PREFERRED"
        _refresh_cash_scale_source_contract(frames)
    elif corruption == "cash_scale_support_snapshot_field_gap":
        frames["cash_scale_support"].loc[
            0, "support_report_name"
        ] = "changed report"
        _refresh_cash_scale_source_contract(frames)
    elif corruption == "cash_scale_support_body_path_gap":
        frames["cash_scale_support"].loc[
            0, "support_action_body_path"
        ] = "support/20260302000003.zip"
        _refresh_cash_scale_source_contract(frames)
    elif corruption == "cash_scale_cash_action_body_gap":
        frames["cash_scale_source"].loc[
            0, "cash_action_body_sha256"
        ] = "9" * 64
        _refresh_cash_scale_source_contract(frames)
    elif corruption == "cash_scale_source_unresolved":
        for location in (
            frames["contract"].at[0, "metadata"]["action_snapshot"][
                "cash_adjustment_scale_evidence"
            ],
            frames["action"].at[0, "snapshot_metadata"][
                "cash_adjustment_scale_evidence"
            ],
        ):
            location["unresolved_count"] = 1
    elif corruption == "invalid_alphanumeric_ticker":
        frames["source_receipts"].loc[1, "ticker"] = "0008z0"
    elif corruption == "resolution_gap":
        frames["resolution"].loc[0, "resolution_row_count"] = 1
    elif corruption == "unresolved_cash_receipt":
        frames["resolution"].loc[0, "unresolved_source_row_count"] = 1
    elif corruption == "unknown_resolution_exclusion":
        frames["resolution"].loc[0, "unknown_exclusion_row_count"] = 1
    elif corruption == "cash_scale_resolution_digest_gap":
        frames["cash_scale_resolution"].loc[0, "selected_cash_scale"] = 0.93
    elif corruption == "cash_scale_resolution_count_gap":
        frames["contract"].at[0, "metadata"][
            "cash_adjustment_scale_evidence"
        ]["row_count"] = 2
    elif corruption == "cash_scale_resolution_unresolved":
        frames["contract"].at[0, "metadata"][
            "cash_adjustment_scale_evidence"
        ]["unresolved_count"] = 1
    elif corruption == "cash_scale_resolution_metadata_extra":
        frames["contract"].at[0, "metadata"][
            "cash_adjustment_scale_evidence"
        ]["unexpected"] = 0
    elif corruption == "cash_scale_adjusted_parity_count_gap":
        frames["contract"].at[0, "metadata"][
            "cash_adjustment_scale_evidence"
        ]["adjusted_cash_parity_count"] = 0
    elif corruption == "cash_scale_explicit_exclusion_gap":
        frames["contract"].at[0, "metadata"][
            "cash_adjustment_scale_evidence"
        ]["explicit_exclusion_count"] = 0
    elif corruption == "cash_scale_stored_price_contract_gap":
        frames["contract"].at[0, "metadata"][
            "cash_adjustment_scale_evidence"
        ]["cash_in_adj_close"] = True
    elif corruption == "cash_scale_evidence_link_gap":
        frames["cash_scale_resolution"].loc[
            0, "scale_evidence_key"
        ] = "missing"
    elif corruption == "cash_scale_source_price_lineage_gap":
        frames["cash_scale_source"].loc[0, "raw_applied_close"] = 96.0
        _refresh_cash_scale_source_contract(frames)
    elif corruption == "cash_scale_price_scale_gap":
        frames["cash_scale_resolution"].loc[
            0, "previous_price_scale"
        ] = 0.93
    elif corruption == "cash_scale_factor_parity_gap":
        frames["cash_scale_resolution"].loc[
            0, "scale_price_factor_parity"
        ] = False
    elif corruption == "cash_scale_basis_gap":
        frames["cash_scale_resolution"].loc[
            0, "cash_adjustment_scale_basis"
        ] = "STABLE_PRICE_SCALE"
    elif corruption == "cash_scale_post_event_selected_gap":
        frames["cash_scale_resolution"].loc[0, "selected_cash_scale"] = 1.0
        frames["contract"].at[0, "metadata"][
            "cash_adjustment_scale_evidence"
        ]["row_digest"] = silver.cash_scale_resolution_evidence_digest(
            frames["cash_scale_resolution"]
        )
    elif corruption == "cash_scale_adjusted_cash_gap":
        frames["cash_scale_resolution"].loc[
            0, "adjusted_cash_amount"
        ] = 100.0
    elif corruption == "cash_scale_raw_cash_action_gap":
        frames["cash_scale_resolution"].loc[0, "raw_cash_amount"] = 101.0
        frames["cash_scale_resolution"].loc[
            0, "adjusted_cash_amount"
        ] = 94.94
        frames["contract"].at[0, "metadata"][
            "cash_adjustment_scale_evidence"
        ]["row_digest"] = silver.cash_scale_resolution_evidence_digest(
            frames["cash_scale_resolution"]
        )
    elif corruption == "raw_history_metadata_lie":
        frames["contract"].at[0, "metadata"][
            "source_price_history_metadata_only"
        ]["coverage_start"] = "2015-01-01"
    elif corruption == "asset_identity_remap":
        frames["identity"].loc[0, "identifier"] = "000001"

    with pytest.raises(RuntimeError):
        _validate(frames)


def test_cached_evidence_digest_detects_metadata_tampering():
    _contract, evidence = _validate(_evidence_frames())
    evidence["price_row_count"] = 99

    with pytest.raises(RuntimeError, match="변조되었거나 구형"):
        silver.verify_total_return_validation_evidence(evidence)


def test_legacy_v1_evidence_is_rejected_even_with_a_recomputed_digest():
    _contract, evidence = _validate(_evidence_frames())
    evidence["methodology_version"] = "krx_gross_dividend_reinvested_v1"
    evidence["evidence_sha256"] = silver.total_return_evidence_sha256(evidence)

    with pytest.raises(RuntimeError, match="변조되었거나 구형"):
        silver.verify_total_return_validation_evidence(evidence)


@pytest.mark.parametrize(
    "field,value",
    [
        ("action_snapshot_schema_version", "dart_total_return_action_snapshot_v4"),
        ("cash_scale_source_contract", "legacy"),
        ("cash_scale_resolution_contract", "legacy"),
        ("cash_scale_source_evidence_count", 0),
        ("cash_scale_support_action_count", 0),
        ("cash_scale_support_semantic_group_count", 0),
        ("cash_scale_resolution_row_count", 2),
        ("cash_scale_changed_event_count", 0),
        ("cash_scale_evidence_match_count", 0),
        ("cash_scale_adjusted_cash_parity_count", 2),
        ("cash_scale_adj_close_decimal_places", 3),
    ],
)
def test_cached_cash_scale_contract_rejects_recomputed_tampering(
    field: str,
    value: object,
):
    _contract, evidence = _validate(_evidence_frames())
    evidence[field] = value
    evidence["evidence_sha256"] = silver.total_return_evidence_sha256(
        evidence
    )

    with pytest.raises(RuntimeError, match="변조되었거나 구형"):
        silver.verify_total_return_validation_evidence(evidence)


def test_live_contract_must_match_cached_lineage(monkeypatch):
    contract, evidence = _validate(_evidence_frames())
    monkeypatch.setattr(
        silver,
        "_load_validated_total_return_contract",
        lambda conn: (contract, dict(evidence)),
    )
    assert silver.verify_live_total_return_contract(object(), evidence) == evidence

    rebuilt = dict(evidence)
    rebuilt["quality_run_id"] = "new-return-run"
    rebuilt["evidence_sha256"] = silver.total_return_evidence_sha256(rebuilt)
    monkeypatch.setattr(
        silver,
        "_load_validated_total_return_contract",
        lambda conn: (contract, rebuilt),
    )
    with pytest.raises(RuntimeError, match="현재 RDS 총수익 lineage"):
        silver.verify_live_total_return_contract(object(), evidence)


def test_raw_cache_keeps_pre2015_and_preferred_identity_but_masks_returns():
    contract, evidence = _validate(_evidence_frames())
    rows = pd.DataFrame({
        "asset_id": [1, 1, 2],
        "Code": ["005930", "005930", "005935"],
        "Name": ["삼성전자", "삼성전자", "삼성전자우"],
        "instrument_type": [
            "common_stock", "common_stock", "preferred_stock",
        ],
        "listed_from": [None, None, None],
        "listed_to": [None, None, None],
        "trade_date": pd.to_datetime([
            "1995-05-31", "2015-01-30", "2015-01-30",
        ]),
        "close": [10.0, 100.0, 80.0],
        "adj_close": [10.0, 100.0, 80.0],
        "total_return_close": [10.0, 101.0, 80.0],
        "trading_value": [1e8, 1e9, 1e8],
        "market_cap": [1e10, 1e11, 1e10],
        "shares": [1e6, 1e6, 1e6],
        "market": ["KOSPI", "KOSPI", "KOSPI"],
        "adv20": [1e8, 1e9, 1e8],
        "age_days": [1, 5_000, 1],
        "first_seen": pd.to_datetime([
            "1995-05-31", "1995-05-31", "2015-01-30",
        ]),
        "dataset_start": pd.to_datetime([
            "1995-05-31", "1995-05-31", "1995-05-31",
        ]),
        "quality_run_id": ["raw", "raw", "raw"],
        "total_return_quality_run_id": [None, "return-run", None],
        "amihud_illiquidity_1m": [None, 1e-12, None],
        "amihud_observations_1m": [0, 20, 0],
        "daily_volatility_252d": [None, .01, None],
        "daily_return_observations_252d": [0, 252, 0],
        "max_daily_return_1m": [None, .02, None],
        "max_daily_return_observations_1m": [0, 20, 0],
        "price_high_252d": [10.0, 110.0, 80.0],
        "price_high_observations_252d": [1, 252, 1],
    })
    rows.attrs["return_contract"] = silver._contract_attrs(contract, evidence)
    rows.attrs["return_roles"] = silver.return_role_contract()

    panel = from_silver_frame(rows, verbose=False)

    assert len(panel.monthly) == 3
    assert panel.monthly["trade_date"].min() == pd.Timestamp("1995-05-31")
    eligible = (
        panel.monthly["instrument_type"].eq("common_stock")
        & panel.monthly["trade_date"].ge("2015-01-01")
    )
    assert panel.monthly.loc[eligible, "total_return_close"].notna().all()
    assert panel.monthly.loc[~eligible, "total_return_close"].isna().all()
    assert panel.monthly["adj_close"].notna().all()
    assert "return_close" not in panel.monthly
