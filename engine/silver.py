"""RDS Silver read-only access.

Research is downstream of Silver.  This module is the only place that knows the
physical public schema; the rest of the engine works on immutable pandas
snapshots.  Every source row must belong to a CERTIFIED data-quality run.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from dotenv import load_dotenv


TOTAL_RETURN_METHOD = "krx_gross_dividend_reinvested_v3"
TOTAL_RETURN_DIVIDEND_TREATMENT = (
    "gross_cash_dividend_reinvested_on_ex_date"
)
TOTAL_RETURN_SCOPE_START = date(2015, 1, 1)
TOTAL_RETURN_RESOLUTION_VERSION = "krx_dividend_resolution_v2"
TOTAL_RETURN_CONTRACT_RELEASE = (
    "krx_total_return_v3_cash_scale_evidence_2026_08"
)
TOTAL_RETURN_ASSET_IDENTITY_CONTRACT = (
    "krx_pit_ticker_asset_v3_price_scoped"
)
TOTAL_RETURN_ACTION_SNAPSHOT_MODE = "dart_dividend_action_backfill"
TOTAL_RETURN_ACTION_SNAPSHOT_SCHEMA = "dart_total_return_action_snapshot_v5"
RESEARCH_WORK_MEM = "64MB"
TOTAL_RETURN_CASH_SCALE_SOURCE_CONTRACT = (
    "krx_cash_adjustment_scale_source_evidence_v1"
)
TOTAL_RETURN_CASH_SCALE_RESOLUTION_CONTRACT = (
    "krx_cash_adjustment_scale_resolution_v1"
)
TOTAL_RETURN_CASH_SCALE_SOURCE_METADATA_KEYS = frozenset({
    "contract", "manifest_sha256", "manifest_parent_row_count",
    "manifest_parent_row_digest", "manifest_support_action_count",
    "manifest_support_action_digest",
    "manifest_support_semantic_group_count",
    "persisted_parent_row_count", "persisted_parent_row_digest",
    "persisted_support_action_count", "persisted_support_action_digest",
    "persisted_support_semantic_group_count", "changed_scale_coverage_count",
    "unresolved_count",
})
TOTAL_RETURN_CASH_SCALE_RESOLUTION_METADATA_KEYS = frozenset({
    "contract", "row_count", "row_digest", "applied_event_count",
    "stable_scale_event_count", "changed_scale_event_count",
    "unresolved_count", "resolution_parity_count",
    "adjusted_cash_parity_count", "first_listing_exclusion_count",
    "explicit_exclusion_count", "adj_close_decimal_places",
    "cash_in_adj_close",
})
TOTAL_RETURN_REBUILD_MODE = "krx_total_return_rebuild"
TOTAL_RETURN_PIT_SCOPE_CONTRACT = (
    "event_date_identity_common_stock_certified_kospi_kosdaq_price_episode"
)
TOTAL_RETURN_DISCLOSURE_OBSERVATION_CONTRACT = (
    "latest_manifest_coverage_end_mutable_list_fields_v1"
)
TOTAL_RETURN_INPUT_SCOPE = {
    "prices": "CERTIFIED KRX common_stock KOSPI/KOSDAQ",
    "actions": (
        "CERTIFIED issuer DART cash/ex actions plus exact referenced "
        "scale-support corporate_action rows, bound by event-date "
        "PIT identity and source-body digest"
    ),
    "cash_scale_source_evidence": (
        "append-only content-addressed cash/action and separate "
        "previous/adjustment KRX source objects; changed scale exact "
        "1:1 parent, stable scale no parent"
    ),
}
TOTAL_RETURN_RESEARCH_ROLE = {
    "role": "ex_post_realized_forward_return_label",
    "feature_pit_safe": False,
    "action_vintage": "latest_corrected_action_snapshot",
    "feature_guidance": (
        "use adj_close price returns for return-based features until "
        "a bitemporal action-vintage contract exists"
    ),
}

VERIFIED_DIVIDEND_SOURCE_STATUSES = frozenset({
    "VERIFIED_OPENDART_DOCUMENT",
    "VERIFIED_DART_VIEWER_BODY",
    "VERIFIED_ATTACHMENT_CORRECTION",
    "VERIFIED_REVIEWED_SOURCE_ERRATUM",
})
SUPPORTED_DIVIDEND_CASH_STATUSES = frozenset({
    "POSITIVE",
    "POSITIVE_PENDING_RECORD_DATE",
    "NO_COMMON_CASH_DIVIDEND",
    "NO_ECONOMIC_EVENT",
    "ATTACHMENT_ONLY",
})
SOURCE_RECEIPT_DIGEST_COLUMNS = (
    "receipt_no", "asset_id", "ticker", "corp_cls", "report_name",
    "dart_rm", "announcement_date", "revision_kind",
    "revision_root_receipt_no", "previous_receipt_no",
    "terminal_receipt_no", "terminal_announcement_date",
    "is_terminal_economic_revision", "source_evidence_status",
    "cash_amount_status", "record_date", "payment_date", "cash_amount",
    "viewer_evidence_sha256", "economic_evidence_sha256",
    "reviewed_correction_id", "payment_date_quality_status",
    "pit_event_date", "mapping_status", "excluded_reason",
)
PUBLISHED_ACTION_DIGEST_COLUMNS = (
    "asset_id", "source", "action_key", "action_type",
    "announcement_date", "ex_date", "record_date", "payment_date",
    "cash_amount", "adjusted_cash_amount", "currency", "frequency",
    "ratio_numerator", "ratio_denominator", "expected_price_factor",
    "share_count_factor", "status", "confidence", "filing_id",
    "report_name", "dart_rm", "corp_cls", "action_scope",
    "cash_amount_status", "source_evidence_status",
    "correction_of_action_key", "revision_root_action_key",
    "revision_kind", "viewer_evidence_sha256",
    "economic_evidence_sha256", "reviewed_correction_id",
    "payment_date_quality_status", "source_body_sha256",
)
INCLUDED_CASH_PARITY_COLUMNS = (
    "asset_id", "receipt_no", "announcement_date", "record_date",
    "payment_date", "cash_amount", "cash_amount_status",
    "source_evidence_status", "previous_receipt_no",
    "revision_root_receipt_no", "revision_kind",
    "viewer_evidence_sha256", "economic_evidence_sha256",
    "reviewed_correction_id", "payment_date_quality_status",
)
CASH_SCALE_SOURCE_EVIDENCE_COLUMNS = (
    "action_snapshot_run_id", "evidence_key", "asset_id", "ticker",
    "cash_receipt_no", "cash_source_evidence_status",
    "cash_action_body_path", "cash_action_body_sha256",
    "cash_economic_body_path", "cash_economic_body_schema",
    "cash_economic_sha256", "support_action_count",
    "support_action_digest", "support_semantic_group_count",
    "price_source",
    "previous_price_source_object_key",
    "previous_price_source_content_sha256", "previous_price_source_etag",
    "previous_price_source_schema", "adjustment_price_source_object_key",
    "adjustment_price_source_content_sha256",
    "adjustment_price_source_etag", "adjustment_price_source_schema",
    "previous_trade_date", "adjustment_trade_date", "raw_previous_close",
    "raw_applied_close", "raw_reference_price", "expected_price_factor",
    "cash_scale_basis", "manifest_row_sha256",
)
CASH_SCALE_SUPPORT_ACTION_COLUMNS = (
    "action_snapshot_run_id", "evidence_key", "support_action_source",
    "support_action_key", "support_action_type",
    "target_cash_receipt_no", "target_adjustment_date",
    "support_action_body_path", "support_action_body_sha256",
    "support_action_quality_run_id", "support_announcement_date",
    "support_ex_date", "support_record_date", "support_ratio_numerator",
    "support_ratio_denominator", "support_entitlement_security_class",
    "support_distributed_security_class", "support_expected_price_factor",
    "support_reference_price", "support_reason", "support_report_name",
    "support_action_scope", "support_semantic_group_keys",
    "support_semantic_role", "manifest_support_row_sha256",
)
CASH_SCALE_RESOLUTION_DIGEST_COLUMNS = (
    "asset_id", "source", "action_key", "resolution_version",
    "applied_trade_date", "raw_cash_amount", "adjusted_cash_amount",
    "previous_trade_date", "previous_close",
    "previous_adj_close", "applied_close", "applied_adj_close",
    "previous_price_scale", "applied_price_scale", "selected_cash_scale",
    "cash_adjustment_scale_basis", "scale_change_detected",
    "scale_evidence_action_snapshot_run_id", "scale_evidence_key",
    "scale_price_factor_observed", "scale_price_factor_reference",
    "scale_price_factor_parity",
)
CASH_SCALE_MANIFEST_ROW_COLUMNS = tuple(
    column for column in CASH_SCALE_SOURCE_EVIDENCE_COLUMNS
    if column not in {
        "action_snapshot_run_id", "asset_id", "manifest_row_sha256",
    }
)
CASH_SCALE_MANIFEST_SUPPORT_ACTION_COLUMNS = tuple(
    column for column in CASH_SCALE_SUPPORT_ACTION_COLUMNS
    if column not in {
        "action_snapshot_run_id", "support_action_quality_run_id",
        "manifest_support_row_sha256",
    }
)
CASH_SCALE_BASES = frozenset({
    "STABLE_PRICE_SCALE",
    "PRE_EVENT_PRICE_SCALE",
})
_DIVIDEND_DIGEST_DATE_COLUMNS = frozenset({
    "announcement_date", "terminal_announcement_date", "ex_date",
    "record_date", "payment_date", "pit_event_date",
})
_DIVIDEND_DIGEST_DECIMAL_PLACES = {
    "cash_amount": 8,
    "adjusted_cash_amount": 8,
    "ratio_numerator": 8,
    "ratio_denominator": 8,
    "expected_price_factor": 12,
    "share_count_factor": 12,
}
_CASH_SCALE_DATE_COLUMNS = frozenset({
    "previous_trade_date", "adjustment_trade_date", "applied_trade_date",
    "target_adjustment_date", "support_announcement_date",
    "support_ex_date", "support_record_date",
})
_CASH_SCALE_INTEGER_COLUMNS = frozenset({
    "asset_id", "support_action_count", "support_semantic_group_count",
})
_CASH_SCALE_BOOLEAN_COLUMNS = frozenset({
    "scale_change_detected", "scale_price_factor_parity",
})
_CASH_SCALE_DECIMAL_PLACES = {
    "raw_previous_close": 8,
    "raw_applied_close": 8,
    "raw_reference_price": 8,
    "raw_cash_amount": 8,
    "adjusted_cash_amount": 8,
    "previous_close": 8,
    "previous_adj_close": 8,
    "applied_close": 8,
    "applied_adj_close": 8,
    "expected_price_factor": 12,
    "support_ratio_numerator": 8,
    "support_ratio_denominator": 8,
    "support_expected_price_factor": 12,
    "support_reference_price": 8,
    "previous_price_scale": 12,
    "applied_price_scale": 12,
    "selected_cash_scale": 12,
    "scale_price_factor_observed": 12,
    "scale_price_factor_reference": 12,
}
RETURN_ROLE_CONTRACT = "krx_feature_label_isolation_v1"
FEATURE_PRICE_FIELD = "adj_close"
FEATURE_RETURN_METHOD = "krx_split_adjusted_price_return_v1"
FEATURE_RETURN_USAGE = "historical_candidate_features_only"
LABEL_RETURN_FIELD = "total_return_close"
LABEL_RETURN_USAGE = "forward_return_labels_only"
LABEL_REVISION_SEMANTICS = "latest_revision_ex_post_realized"
DIVIDEND_PIT_AVAILABILITY_CONTRACT = (
    "canonical_latest_terminal_announcement_plus_one_day_v1"
)
RETURN_ROLE_META_KEYS = (
    "return_role_contract",
    "feature_price_field",
    "feature_return_methodology",
    "feature_return_usage",
    "label_return_field",
    "label_return_methodology",
    "label_return_usage",
    "label_revision_semantics",
    "label_candidate_access",
)
ASSET_IDENTITY_CONTRACT = "krx_month_end_asset_ticker_v1"
ASSET_IDENTITY_META_KEYS = (
    "asset_identity_contract",
    "asset_identity_digest",
    "asset_identity_row_count",
    "asset_identity_asset_count",
    "asset_identity_month_count",
    "asset_identity_cutoff",
)


def return_role_contract() -> dict[str, Any]:
    """The immutable feature/label separation carried by every panel cache."""
    return {
        "return_role_contract": RETURN_ROLE_CONTRACT,
        "feature_price_field": FEATURE_PRICE_FIELD,
        "feature_return_methodology": FEATURE_RETURN_METHOD,
        "feature_return_usage": FEATURE_RETURN_USAGE,
        "label_return_field": LABEL_RETURN_FIELD,
        "label_return_methodology": TOTAL_RETURN_METHOD,
        "label_return_usage": LABEL_RETURN_USAGE,
        "label_revision_semantics": LABEL_REVISION_SEMANTICS,
        "label_candidate_access": False,
    }


TOTAL_RETURN_CONTRACT_SQL = """
SELECT source, asset_type, field_name, methodology_version,
       dividend_treatment, status, coverage_start, coverage_end,
       quality_run_id, metadata, certified_at
FROM public.price_return_contract
WHERE source = 'KRX'
  AND asset_type = 'stock'
  AND field_name = 'total_return_close'
"""


RESEARCH_GENERATION_SQL = """
SELECT
    p.quality_run_id::text AS quality_run_id,
    p.status AS contract_status,
    p.methodology_version,
    p.dividend_treatment,
    p.coverage_start,
    p.coverage_end,
    (p.metadata->>'action_snapshot_run_id') AS action_snapshot_run_id,
    (p.metadata->'action_snapshot'->>'manifest_sha256') AS action_manifest_sha256,
    (p.metadata->'action_snapshot'->>'body_digest') AS action_body_digest,
    return_q.status AS return_quality_status,
    action_q.status AS action_quality_status,
    action.schema_version AS action_schema_version,
    action.manifest_sha256 AS persisted_action_manifest_sha256,
    action.body_digest AS persisted_action_body_digest
FROM public.price_return_contract p
JOIN public.dq_run return_q ON return_q.run_id = p.quality_run_id
JOIN public.dart_action_snapshot_contract action
  ON action.quality_run_id =
     (p.metadata->>'action_snapshot_run_id')::uuid
JOIN public.dq_run action_q ON action_q.run_id = action.quality_run_id
WHERE p.source = 'KRX'
  AND p.asset_type = 'stock'
  AND p.field_name = 'total_return_close'
"""


TOTAL_RETURN_SCHEMA_AUDIT_SQL = """
SELECT
    EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'price_daily'
          AND column_name = 'total_return_quality_run_id'
    ) AS has_total_return_lineage,
    EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'dividend_event_resolution'
    ) AS has_dividend_resolution,
    EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'dart_action_snapshot_contract'
    ) AS has_action_snapshot_contract,
    EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'dividend_source_receipt'
    ) AS has_dividend_source_receipt,
    EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'cash_adjustment_scale_source_evidence'
    ) AS has_cash_scale_source_evidence,
    EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'cash_adjustment_scale_support_action'
    ) AS has_cash_scale_support_action,
    coalesce((
        SELECT array_agg(column_name::text ORDER BY ordinal_position)
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'cash_adjustment_scale_source_evidence'
    ), ARRAY[]::text[]) AS cash_scale_source_columns,
    coalesce((
        SELECT array_agg(column_name::text ORDER BY ordinal_position)
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'cash_adjustment_scale_support_action'
    ), ARRAY[]::text[]) AS cash_scale_support_columns,
    NOT EXISTS (
        SELECT 1
        FROM unnest(ARRAY[
            'previous_trade_date', 'previous_close', 'previous_adj_close',
            'applied_close', 'applied_adj_close', 'previous_price_scale',
            'applied_price_scale', 'selected_cash_scale',
            'cash_adjustment_scale_basis', 'scale_change_detected',
            'scale_evidence_action_snapshot_run_id', 'scale_evidence_key',
            'scale_price_factor_observed', 'scale_price_factor_reference',
            'scale_price_factor_parity'
        ]) AS expected(column_name)
        LEFT JOIN information_schema.columns observed
          ON observed.table_schema = 'public'
         AND observed.table_name = 'dividend_event_resolution'
         AND observed.column_name = expected.column_name
        WHERE observed.column_name IS NULL
    ) AS has_resolution_scale_columns,
    EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = 'dividend_event_resolution'
          AND c.conname = 'dividend_resolution_v2_scale_contract_check'
          AND c.contype = 'c'
    ) AS has_resolution_v2_scale_check,
    EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'corporate_action'
          AND column_name = 'corp_cls'
    ) AS has_action_corp_cls_provenance,
    EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_support_action'
          AND c.conname = 'cash_scale_support_source_type_check'
          AND c.contype = 'c'
    ) AS has_cash_scale_support_source_type_check,
    EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_support_action'
          AND c.conname = 'cash_scale_support_role_semantics_check'
          AND c.contype = 'c'
    ) AS has_cash_scale_support_role_semantics_check,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'dividend_event_resolution'
          AND c.contype = 'p'
    ), ARRAY[]::text[]) AS resolution_pk_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'dividend_source_receipt'
          AND c.contype = 'p'
    ), ARRAY[]::text[]) AS source_receipt_pk_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_source_evidence'
          AND c.contype = 'p'
    ), ARRAY[]::text[]) AS cash_scale_source_pk_columns,
    coalesce((
        SELECT constraint_columns
        FROM (
            SELECT c.oid,
                   array_agg(
                       a.attname ORDER BY key_column.ordinality
                   ) AS constraint_columns
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            CROSS JOIN LATERAL unnest(c.conkey)
                WITH ORDINALITY AS key_column(attnum, ordinality)
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid
             AND a.attnum = key_column.attnum
            WHERE n.nspname = 'public'
              AND t.relname = 'cash_adjustment_scale_source_evidence'
              AND c.contype = 'u'
            GROUP BY c.oid
        ) observed
        WHERE constraint_columns = ARRAY[
            'action_snapshot_run_id','asset_id','cash_receipt_no',
            'adjustment_trade_date'
        ]::name[]
        LIMIT 1
    ), ARRAY[]::name[]) AS cash_scale_source_unique_columns,
    coalesce((
        SELECT constraint_columns
        FROM (
            SELECT c.oid,
                   array_agg(
                       a.attname ORDER BY key_column.ordinality
                   ) AS constraint_columns
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            CROSS JOIN LATERAL unnest(c.conkey)
                WITH ORDINALITY AS key_column(attnum, ordinality)
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid
             AND a.attnum = key_column.attnum
            WHERE n.nspname = 'public'
              AND t.relname = 'cash_adjustment_scale_source_evidence'
              AND c.contype = 'u'
            GROUP BY c.oid
        ) observed
        WHERE constraint_columns = ARRAY[
            'action_snapshot_run_id','evidence_key','cash_receipt_no',
            'adjustment_trade_date'
        ]::name[]
        LIMIT 1
    ), ARRAY[]::name[]) AS cash_scale_source_parent_identity_unique_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_class target ON target.oid = c.confrelid
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_source_evidence'
          AND target.relname = 'dart_action_snapshot_contract'
          AND c.contype = 'f'
    ), ARRAY[]::text[]) AS cash_scale_source_snapshot_fk_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_class target ON target.oid = c.confrelid
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_source_evidence'
          AND target.relname = 'dividend_source_receipt'
          AND c.contype = 'f'
    ), ARRAY[]::text[]) AS cash_scale_source_receipt_fk_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_support_action'
          AND c.contype = 'p'
    ), ARRAY[]::text[]) AS cash_scale_support_pk_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_class target ON target.oid = c.confrelid
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_support_action'
          AND target.relname = 'cash_adjustment_scale_source_evidence'
          AND c.contype = 'f'
          AND c.conname <> 'cash_scale_support_parent_identity_fk'
    ), ARRAY[]::text[]) AS cash_scale_support_parent_fk_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_class target ON target.oid = c.confrelid
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_support_action'
          AND target.relname = 'cash_adjustment_scale_source_evidence'
          AND c.conname = 'cash_scale_support_parent_identity_fk'
          AND c.contype = 'f'
    ), ARRAY[]::text[]) AS cash_scale_support_parent_identity_fk_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_class target ON target.oid = c.confrelid
        CROSS JOIN LATERAL unnest(c.confkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.confrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_support_action'
          AND target.relname = 'cash_adjustment_scale_source_evidence'
          AND c.conname = 'cash_scale_support_parent_identity_fk'
          AND c.contype = 'f'
    ), ARRAY[]::text[])
        AS cash_scale_support_parent_identity_fk_target_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_class target ON target.oid = c.confrelid
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'cash_adjustment_scale_support_action'
          AND target.relname = 'dq_run'
          AND c.contype = 'f'
    ), ARRAY[]::text[]) AS cash_scale_support_quality_fk_columns,
    coalesce((
        SELECT array_agg(a.attname ORDER BY key_column.ordinality)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        CROSS JOIN LATERAL unnest(c.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = key_column.attnum
        WHERE n.nspname = 'public'
          AND t.relname = 'dividend_event_resolution'
          AND c.conname = 'dividend_resolution_scale_evidence_fk'
          AND c.contype = 'f'
    ), ARRAY[]::text[]) AS resolution_scale_fk_columns
"""


TOTAL_RETURN_SCOPE_AUDIT_SQL = """
WITH target AS (
    SELECT %s::uuid AS quality_run_id
), scoped AS (
    SELECT p.*, q.status AS raw_quality_status
    FROM public.price_daily p
    JOIN public.asset a ON a.asset_id = p.asset_id
    LEFT JOIN public.dq_run q ON q.run_id = p.quality_run_id
    WHERE p.source = 'KRX'
      AND a.exchange = 'KRX'
      AND a.asset_type = 'stock'
      AND a.instrument_type = 'common_stock'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND p.trade_date >= DATE '2015-01-01'
), source_history AS (
    SELECT min(p.trade_date) AS coverage_start,
           max(p.trade_date) AS coverage_end
    FROM public.price_daily p
    JOIN public.asset a ON a.asset_id = p.asset_id
    JOIN public.dq_run q ON q.run_id = p.quality_run_id
    WHERE p.source = 'KRX'
      AND a.exchange = 'KRX'
      AND a.asset_type = 'stock'
      AND a.instrument_type = 'common_stock'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND q.status = 'CERTIFIED'
)
SELECT
    count(*) AS price_row_count,
    count(DISTINCT asset_id) AS asset_count,
    min(trade_date) AS coverage_start,
    max(trade_date) AS coverage_end,
    count(*) FILTER (
        WHERE raw_quality_status = 'CERTIFIED'
    ) AS raw_certified_row_count,
    count(*) FILTER (
        WHERE total_return_quality_run_id = target.quality_run_id
    ) AS total_return_run_row_count,
    count(*) FILTER (
        WHERE total_return_close IS NOT NULL
          AND total_return_close > 0
    ) AS positive_total_return_row_count,
    count(DISTINCT total_return_quality_run_id) AS total_return_run_count,
    (
        SELECT status FROM public.dq_run
        WHERE run_id = target.quality_run_id
    ) AS total_return_run_status,
    (
        SELECT mode FROM public.dq_run
        WHERE run_id = target.quality_run_id
    ) AS total_return_run_mode,
    (SELECT coverage_start FROM source_history) AS source_history_start,
    (SELECT coverage_end FROM source_history) AS source_history_end
FROM scoped
CROSS JOIN target
GROUP BY target.quality_run_id
"""


TOTAL_RETURN_ACTION_SNAPSHOT_AUDIT_SQL = """
SELECT
    s.quality_run_id,
    s.schema_version,
    s.manifest_sha256,
    s.body_digest,
    s.body_count,
    s.coverage_start,
    s.coverage_end,
    s.action_count,
    s.metadata AS snapshot_metadata,
    q.status AS quality_run_status,
    q.mode AS quality_run_mode,
    (
        SELECT count(*)
        FROM public.corporate_action ca
        JOIN public.asset a ON a.asset_id = ca.asset_id
        WHERE ca.quality_run_id = s.quality_run_id
          AND ca.action_scope = 'ISSUER'
          AND (
              (
                  ca.source = 'DART_DISCLOSURE'
                  AND ca.action_type IN ('cash_dividend', 'ex_dividend')
              )
              OR EXISTS (
                  SELECT 1
                  FROM public.cash_adjustment_scale_support_action support
                  JOIN public.cash_adjustment_scale_source_evidence evidence
                    ON evidence.action_snapshot_run_id =
                       support.action_snapshot_run_id
                   AND evidence.evidence_key = support.evidence_key
                  WHERE support.action_snapshot_run_id = s.quality_run_id
                    AND evidence.asset_id = ca.asset_id
                    AND support.support_action_source = ca.source
                    AND support.support_action_key = ca.action_key
                    AND support.support_action_type = ca.action_type
              )
          )
          AND a.asset_type = 'stock'
          AND a.instrument_type = 'common_stock'
          AND a.exchange = 'KRX'
    ) AS persisted_action_count,
    (
        SELECT count(*)
        FROM public.corporate_action ca
        JOIN public.asset a ON a.asset_id = ca.asset_id
        WHERE ca.quality_run_id = s.quality_run_id
          AND ca.source = 'DART_DISCLOSURE'
          AND ca.action_scope = 'ISSUER'
          AND ca.action_type = 'cash_dividend'
          AND a.asset_type = 'stock'
          AND a.instrument_type = 'common_stock'
          AND a.exchange = 'KRX'
    ) AS persisted_cash_action_count
FROM public.dart_action_snapshot_contract s
JOIN public.dq_run q ON q.run_id = s.quality_run_id
WHERE s.quality_run_id = %s::uuid
"""


TOTAL_RETURN_SOURCE_RECEIPT_SQL = f"""
SELECT {','.join(SOURCE_RECEIPT_DIGEST_COLUMNS)}
FROM public.dividend_source_receipt
WHERE quality_run_id = %s::uuid
ORDER BY receipt_no
"""


TOTAL_RETURN_CASH_SCALE_SOURCE_EVIDENCE_SQL = f"""
SELECT {','.join(CASH_SCALE_SOURCE_EVIDENCE_COLUMNS)}
FROM public.cash_adjustment_scale_source_evidence
WHERE action_snapshot_run_id = %s::uuid
ORDER BY evidence_key
"""


TOTAL_RETURN_CASH_SCALE_SUPPORT_ACTION_SQL = f"""
SELECT {','.join(CASH_SCALE_SUPPORT_ACTION_COLUMNS)}
FROM public.cash_adjustment_scale_support_action
WHERE action_snapshot_run_id = %s::uuid
ORDER BY evidence_key, support_action_source, support_action_key,
         support_action_type
"""


TOTAL_RETURN_PUBLISHED_ACTION_SQL = f"""
SELECT {','.join('ca.' + column for column in PUBLISHED_ACTION_DIGEST_COLUMNS)}
FROM public.corporate_action ca
JOIN public.asset a ON a.asset_id = ca.asset_id
WHERE ca.quality_run_id = %s::uuid
  AND ca.action_scope = 'ISSUER'
  AND (
      (
          ca.source = 'DART_DISCLOSURE'
          AND ca.action_type IN ('cash_dividend', 'ex_dividend')
      )
      OR EXISTS (
          SELECT 1
          FROM public.cash_adjustment_scale_support_action support
          JOIN public.cash_adjustment_scale_source_evidence evidence
            ON evidence.action_snapshot_run_id =
               support.action_snapshot_run_id
           AND evidence.evidence_key = support.evidence_key
          WHERE support.action_snapshot_run_id = ca.quality_run_id
            AND evidence.asset_id = ca.asset_id
            AND support.support_action_source = ca.source
            AND support.support_action_key = ca.action_key
            AND support.support_action_type = ca.action_type
      )
  )
  AND a.asset_type = 'stock'
  AND a.instrument_type = 'common_stock'
  AND a.exchange = 'KRX'
ORDER BY ca.asset_id, ca.source, ca.action_key
"""


TOTAL_RETURN_RESOLUTION_AUDIT_SQL = """
SELECT
    count(*) AS resolution_row_count,
    count(*) FILTER (
        WHERE resolution_version = 'krx_dividend_resolution_v2'
    ) AS expected_version_row_count,
    count(*) FILTER (
        WHERE is_canonical IS TRUE
          AND excluded_reason IS NULL
          AND resolved_ex_date IS NOT NULL
          AND ex_date_basis IN ('KRX_NOTICE', 'KRX_T2_INFERRED')
          AND applied_trade_date IS NOT NULL
          AND raw_cash_amount > 0
          AND adjusted_cash_amount > 0
    ) AS applied_canonical_row_count,
    count(*) FILTER (
        WHERE is_canonical IS FALSE
          AND excluded_reason IS NOT NULL
          AND applied_trade_date IS NULL
          AND adjusted_cash_amount IS NULL
    ) AS excluded_row_count,
    count(*) FILTER (
        WHERE excluded_reason IN (
            'MISSING_RECORD_DATE', 'INVALID_CASH_AMOUNT'
        )
    ) AS unresolved_source_row_count,
    count(*) FILTER (
        WHERE is_canonical IS FALSE
          AND excluded_reason NOT IN (
              'ATTACHMENT_CORRECTION',
              'SUPERSEDED_REVISION',
              'NO_COMMON_CASH_DIVIDEND',
              'NO_ECONOMIC_EVENT',
              'BEFORE_MARKET_COVERAGE',
              'PENDING_FUTURE_TRADE',
              'BEFORE_LISTING_OR_EPISODE_START',
              'LISTING_EPISODE_GAP'
          )
    ) AS unknown_exclusion_row_count
FROM public.dividend_event_resolution
WHERE quality_run_id = %s::uuid
"""


TOTAL_RETURN_CASH_SCALE_RESOLUTION_SQL = f"""
SELECT {','.join(CASH_SCALE_RESOLUTION_DIGEST_COLUMNS)}, resolved_ex_date
FROM public.dividend_event_resolution
WHERE quality_run_id = %s::uuid
  AND resolution_version = 'krx_dividend_resolution_v2'
  AND is_canonical IS TRUE
  AND excluded_reason IS NULL
  AND applied_trade_date IS NOT NULL
ORDER BY asset_id, source, action_key
"""


TOTAL_RETURN_ASSET_IDENTITY_SQL = """
SELECT ai.asset_id, ai.identifier, ai.valid_from, ai.valid_to
FROM public.asset_identifier ai
JOIN public.asset a ON a.asset_id = ai.asset_id
WHERE ai.source = 'KRX'
  AND ai.identifier_type = 'ticker'
  AND a.asset_type = 'stock'
  AND a.instrument_type = 'common_stock'
  AND a.exchange = 'KRX'
  AND ai.valid_from <= %s::date
  AND (ai.valid_to IS NULL OR ai.valid_to >= DATE '2015-01-01')
  AND EXISTS (
      SELECT 1
      FROM public.price_daily p
      JOIN public.dq_run q ON q.run_id = p.quality_run_id
      WHERE p.asset_id = ai.asset_id
        AND p.source = 'KRX'
        AND p.market IN ('KOSPI', 'KOSDAQ')
        AND q.status = 'CERTIFIED'
        AND p.trade_date BETWEEN DATE '2015-01-01' AND %s::date
  )
ORDER BY ai.asset_id, ai.identifier, ai.valid_from, ai.valid_to
"""


PRICE_SNAPSHOT_SQL = """
WITH certified AS (
    SELECT
        p.asset_id,
        i.identifier AS "Code",
        a.name AS "Name",
        a.instrument_type,
        a.listed_from,
        a.listed_to,
        p.trade_date,
        p.close,
        p.adj_close,
        p.total_return_close,
        p.trading_value,
        p.market_cap,
        p.shares,
        p.market,
        p.quality_run_id,
        p.total_return_quality_run_id,
        i.ticker_match_count,
        avg(CASE
                WHEN p.trade_date >= DATE '2015-01-01'
                THEN p.trading_value
            END) OVER (
            PARTITION BY p.asset_id ORDER BY p.trade_date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS adv20,
        row_number() OVER (
            PARTITION BY p.asset_id ORDER BY p.trade_date
        ) AS age_days,
        min(p.trade_date) OVER (PARTITION BY p.asset_id) AS first_seen
    FROM public.price_daily p
    JOIN public.asset a ON a.asset_id = p.asset_id
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id AND q.status = 'CERTIFIED'
    JOIN LATERAL (
        SELECT min(ai.identifier) AS identifier,
               count(*) AS ticker_match_count
        FROM public.asset_identifier ai
        WHERE ai.asset_id = p.asset_id
          AND ai.source = 'KRX'
          AND ai.identifier_type = 'ticker'
          AND ai.valid_from <= p.trade_date
          AND (ai.valid_to IS NULL OR ai.valid_to >= p.trade_date)
    ) i ON true
    WHERE p.source = 'KRX'
      AND a.exchange = 'KRX'
      AND a.asset_type = 'stock'
      AND p.market IN ('KOSPI', 'KOSDAQ')
), feature_inputs AS (
    SELECT certified.*,
           CASE
               WHEN instrument_type = 'common_stock'
                    AND market IN ('KOSPI', 'KOSDAQ')
                    AND trade_date >= DATE '2015-01-01'
               THEN adj_close
           END AS certified_feature_price
    FROM certified
), daily_returns AS (
    SELECT feature_inputs.*,
           CASE
               WHEN lag(certified_feature_price) OVER (
                        PARTITION BY asset_id ORDER BY trade_date
                    ) > 0
                    AND certified_feature_price > 0
               THEN certified_feature_price / lag(
                        certified_feature_price
                    ) OVER (
                        PARTITION BY asset_id ORDER BY trade_date
                    ) - 1
           END AS daily_price_return
    FROM feature_inputs
), daily_features AS (
    SELECT daily_returns.*,
           avg(abs(daily_price_return) / trading_value) FILTER (
               WHERE daily_price_return IS NOT NULL
                 AND trading_value > 0
           ) OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
           ) AS amihud_illiquidity_1m,
           count(daily_price_return) FILTER (
               WHERE trading_value > 0
           ) OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
           ) AS amihud_observations_1m,
           stddev_samp(daily_price_return) OVER (
               PARTITION BY asset_id ORDER BY trade_date
               ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
           ) AS daily_volatility_252d,
           count(daily_price_return) OVER (
               PARTITION BY asset_id ORDER BY trade_date
               ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
           ) AS daily_return_observations_252d,
           max(daily_price_return) OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
           ) AS max_daily_return_1m,
           count(daily_price_return) OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
           ) AS max_daily_return_observations_1m,
           max(certified_feature_price) OVER (
               PARTITION BY asset_id ORDER BY trade_date
               ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
           ) AS price_high_252d,
           count(certified_feature_price) OVER (
               PARTITION BY asset_id ORDER BY trade_date
               ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
           ) AS price_high_observations_252d
    FROM daily_returns
), monthly AS (
    SELECT daily_features.*,
           min(trade_date) OVER () AS dataset_start,
           row_number() OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
               ORDER BY trade_date DESC
           ) AS month_rank
    FROM daily_features
)
SELECT asset_id, "Code", "Name", instrument_type, listed_from, listed_to,
       trade_date, close, adj_close, total_return_close, trading_value,
       market_cap, shares, market, adv20, age_days, first_seen, dataset_start,
       quality_run_id, total_return_quality_run_id, ticker_match_count,
       amihud_illiquidity_1m, amihud_observations_1m,
       daily_volatility_252d, daily_return_observations_252d,
       max_daily_return_1m, max_daily_return_observations_1m,
       price_high_252d, price_high_observations_252d
FROM monthly
WHERE month_rank = 1
ORDER BY asset_id, trade_date
"""


ASSET_IDENTITY_SQL = """
WITH monthly AS (
    SELECT p.asset_id,
           p.trade_date,
           row_number() OVER (
               PARTITION BY p.asset_id, date_trunc('month', p.trade_date)
               ORDER BY p.trade_date DESC
           ) AS month_rank
    FROM public.price_daily p
    JOIN public.asset a ON a.asset_id = p.asset_id
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id AND q.status = 'CERTIFIED'
    WHERE p.source = 'KRX'
      AND a.exchange = 'KRX'
      AND a.asset_type = 'stock'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND (%s::date IS NULL OR p.trade_date <= %s::date)
), month_end AS (
    SELECT asset_id, trade_date
    FROM monthly
    WHERE month_rank = 1
), identified AS (
    SELECT m.asset_id,
           m.trade_date,
           min(ai.identifier) AS "Code",
           count(ai.identifier) AS ticker_match_count
    FROM month_end m
    LEFT JOIN public.asset_identifier ai
      ON ai.asset_id = m.asset_id
     AND ai.source = 'KRX'
     AND ai.identifier_type = 'ticker'
     AND ai.valid_from <= m.trade_date
     AND (ai.valid_to IS NULL OR ai.valid_to >= m.trade_date)
    GROUP BY m.asset_id, m.trade_date
)
SELECT asset_id, "Code", trade_date, ticker_match_count
FROM identified
ORDER BY trade_date, asset_id, "Code"
"""


FUNDAMENTAL_SQL = """
SELECT f.asset_id, f.period_end, f.fiscal_period, f.fs_type,
       f.statement_type, f.available_date, f.available_at,
       f.metric, f.value, f.revision_key, f.quality_run_id
FROM public.fundamental f
JOIN public.asset a ON a.asset_id = f.asset_id
JOIN public.dq_run q
  ON q.run_id = f.quality_run_id AND q.status = 'CERTIFIED'
WHERE f.source = 'DART'
  AND a.exchange = 'KRX'
  AND a.asset_type = 'stock'
  AND f.data_basis = 'STANDARDIZED'
  AND f.unit_type = 'currency'
  AND f.available_date IS NOT NULL
  AND f.metric = ANY(%s)
"""


DIVIDEND_HISTORY_SQL = """
WITH current_contract AS (
    SELECT quality_run_id, coverage_start, coverage_end,
           metadata->>'resolution_version' AS resolution_version,
           (metadata->>'action_snapshot_run_id')::uuid AS action_snapshot_run_id
    FROM public.price_return_contract
    WHERE source = 'KRX'
      AND asset_type = 'stock'
      AND field_name = 'total_return_close'
      AND methodology_version = 'krx_gross_dividend_reinvested_v3'
      AND status = 'CERTIFIED'
      AND certified_at IS NOT NULL
      AND metadata->>'resolution_version' IS NOT NULL
      AND metadata->>'action_snapshot_run_id' IS NOT NULL
)
SELECT r.asset_id, r.source, r.action_key, r.resolution_version,
       ca.announcement_date, r.applied_trade_date,
       r.adjusted_cash_amount, r.quality_run_id
FROM current_contract c
JOIN public.dividend_event_resolution r
  ON r.quality_run_id = c.quality_run_id
 AND r.resolution_version = c.resolution_version
JOIN public.corporate_action ca
  ON ca.asset_id = r.asset_id
 AND ca.source = r.source
 AND ca.action_key = r.action_key
 AND ca.quality_run_id = c.action_snapshot_run_id
JOIN public.asset a ON a.asset_id = r.asset_id
JOIN public.dq_run resolution_q
  ON resolution_q.run_id = r.quality_run_id
 AND resolution_q.status = 'CERTIFIED'
JOIN public.dq_run action_q
  ON action_q.run_id = ca.quality_run_id
 AND action_q.status = 'CERTIFIED'
WHERE r.is_canonical IS TRUE
  AND r.excluded_reason IS NULL
  AND r.applied_trade_date IS NOT NULL
  AND r.applied_trade_date BETWEEN c.coverage_start AND c.coverage_end
  AND r.adjusted_cash_amount > 0
  AND ca.announcement_date IS NOT NULL
  AND ca.source = 'DART_DISCLOSURE'
  AND ca.action_type = 'cash_dividend'
  AND ca.action_scope = 'ISSUER'
  AND a.exchange = 'KRX'
  AND a.asset_type = 'stock'
  AND a.instrument_type = 'common_stock'
ORDER BY r.asset_id, r.applied_trade_date, r.action_key
"""


APPROVED_VALUES_SQL = """
WITH ranked AS (
    SELECT f.factor_key, v.asset_id, v.as_of_date,
           v.value * coalesce((f.config->>'predicted_sign')::integer, 1) AS value,
           row_number() OVER (
               PARTITION BY f.factor_id, v.asset_id,
                            date_trunc('month', v.as_of_date)
               ORDER BY v.as_of_date DESC
           ) AS month_rank
    FROM gold.factor f
    JOIN gold.factor_value v ON v.factor_id = f.factor_id
    WHERE f.status = 'APPROVED'
)
SELECT factor_key, asset_id, as_of_date, value
FROM ranked
WHERE month_rank = 1
ORDER BY factor_key, asset_id, as_of_date
"""


APPROVED_FACTOR_KEYS_SQL = """
SELECT DISTINCT factor_key
FROM gold.factor
WHERE status = 'APPROVED'
ORDER BY factor_key
"""


GOLD_GENERATION_SQL = """
SELECT count(*)::bigint AS approved_factor_count,
       count(DISTINCT nullif(config->>'gold_generation_digest', ''))::integer
           AS generation_digest_count,
       min(nullif(config->>'gold_generation_digest', ''))
           AS gold_generation_digest,
       array_agg(factor_key ORDER BY factor_key) AS approved_factor_keys
FROM gold.factor
WHERE status = 'APPROVED'
"""


GOLD_TRIAL_HISTORY_SQL = """
SELECT coalesce(
           nullif(btrim(config->>'research_definition_hash'), ''),
           implementation_hash
       ) AS definition_hash,
       CASE WHEN (evaluation->'metrics'->>'net_ir') ~ '^-?[0-9]+([.][0-9]+)?$'
            THEN (evaluation->'metrics'->>'net_ir')::double precision END AS net_ir,
       CASE WHEN (evaluation->'metrics'->>'hac_pvalue') ~ '^[0-9]+([.][0-9]+)?([eE]-?[0-9]+)?$'
            THEN (evaluation->'metrics'->>'hac_pvalue')::double precision END AS hac_pvalue
FROM gold.factor
WHERE coalesce(
          nullif(btrim(config->>'research_definition_hash'), ''),
          implementation_hash
      ) IS NOT NULL
ORDER BY factor_id
"""


def _load_environment() -> None:
    """Load local configuration without overriding injected production secrets."""
    load_dotenv(override=False)
    configured = os.environ.get("TEAMALPHA_DATA_DIR")
    if configured:
        data_repo = Path(configured).expanduser()
    else:
        data_repo = Path(__file__).resolve().parents[2] / "TeamAlpha-data"
    load_dotenv(data_repo / ".env", override=False)


def database_url() -> str:
    _load_environment()
    secret_id = os.environ.get("SILVER_DB_SECRET_ID")
    if secret_id:
        import boto3

        profile = os.environ.get("AWS_PROFILE")
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        secret = session.client("secretsmanager").get_secret_value(SecretId=secret_id)
        payload = json.loads(secret["SecretString"])
        url = payload.get("SILVER_DB_URL")
        if not url:
            raise SystemExit(f"Secrets Manager {secret_id!r}에 SILVER_DB_URL이 없습니다")
        return url
    url = os.environ.get("SILVER_DB_URL")
    if not url:
        raise SystemExit(
            "SILVER_DB_URL이 필요합니다. RDS가 터널 뒤에 있으면 먼저 터널을 여세요."
        )
    return url


def connect(*, read_only: bool = True):
    """Connect with bounded network waits; research never mutates public Silver."""
    conninfo = database_url()
    host_override = os.environ.get("SILVER_DB_HOST_OVERRIDE")
    port_override = os.environ.get("SILVER_DB_PORT_OVERRIDE")
    if host_override or port_override:
        overrides = {}
        if host_override:
            overrides["host"] = host_override
        if port_override:
            overrides["port"] = int(port_override)
        conninfo = psycopg.conninfo.make_conninfo(conninfo, **overrides)
    connection_options = psycopg.conninfo.conninfo_to_dict(conninfo).get(
        "options", ""
    )
    work_mem_option = f"-c work_mem={RESEARCH_WORK_MEM}"
    conninfo = psycopg.conninfo.make_conninfo(
        conninfo,
        options=" ".join(
            part for part in (connection_options, work_mem_option) if part
        ),
    )
    conn = psycopg.connect(
        conninfo,
        connect_timeout=15,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
        tcp_user_timeout=60_000,
    )
    if read_only:
        # Identity validation and every dependent query must observe one RDS
        # snapshot even if Silver is rebuilt concurrently.
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
    conn.read_only = read_only
    return conn


def read_frame(conn, sql: str, params: Any = None, *, chunk_size: int = 50_000) -> pd.DataFrame:
    """Read a query in bounded chunks without relying on pandas' DBAPI adapter."""
    frames: list[pd.DataFrame] = []
    with conn.cursor() as cur:
        cur.execute(sql, params)
        columns = [d.name for d in cur.description]
        while rows := cur.fetchmany(chunk_size):
            frames.append(pd.DataFrame.from_records(rows, columns=columns))
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


def _identity_cutoff(value: Any) -> pd.Timestamp:
    try:
        cutoff = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"asset identity cutoff 날짜가 잘못되었습니다: {value!r}") from exc
    if pd.isna(cutoff):
        raise ValueError("asset identity cutoff은 비어 있을 수 없습니다")
    if cutoff.tzinfo is not None:
        cutoff = cutoff.tz_convert("UTC").tz_localize(None)
    return cutoff.normalize()


def asset_identity_evidence(
    frame: pd.DataFrame, *, cutoff: Any | None = None,
) -> dict[str, Any]:
    """Return the canonical PIT month-end ``asset_id``/ticker identity digest.

    The digest hashes only JSON rows of ``[date ISO, asset_id integer, Code
    exact text]`` in deterministic order.  No numeric conversion, padding, or
    trimming is permitted for ``Code`` because those transformations can hide
    an asset remap.
    """
    required = {"asset_id", "Code", "trade_date"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            f"asset identity 필수 컬럼 누락: {sorted(missing)}"
        )

    scoped = frame.loc[:, ["asset_id", "Code", "trade_date"]].copy()
    if scoped.empty:
        raise RuntimeError("asset identity 월말 스냅샷 행이 없습니다")
    dates = pd.to_datetime(scoped["trade_date"], errors="coerce")
    if dates.isna().any():
        raise RuntimeError(
            "asset identity trade_date가 비었거나 날짜가 아닙니다: "
            f"{int(dates.isna().sum()):,}행"
        )
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_convert("UTC").dt.tz_localize(None)
    scoped["trade_date"] = dates.dt.normalize()

    requested_cutoff = (
        _identity_cutoff(cutoff)
        if cutoff is not None
        else scoped["trade_date"].max()
    )
    scoped = scoped.loc[scoped["trade_date"] <= requested_cutoff].copy()
    if scoped.empty:
        raise RuntimeError(
            "asset identity cutoff 이내의 월말 스냅샷 행이 없습니다: "
            f"cutoff={requested_cutoff.date().isoformat()}"
        )

    raw_codes = scoped["Code"]
    bad_code = raw_codes.map(
        lambda value: (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or "\x00" in value
        )
    )
    if bad_code.any():
        sample = raw_codes.loc[bad_code].head(3).tolist()
        raise RuntimeError(
            "asset identity Code는 공백 없는 정확한 문자열이어야 합니다; "
            f"숫자 변환·zero-padding은 허용하지 않습니다: sample={sample!r}"
        )

    numeric_ids = pd.to_numeric(scoped["asset_id"], errors="coerce")
    finite_ids = numeric_ids.map(
        lambda value: False if pd.isna(value) else math.isfinite(float(value))
    )
    bad_id = (
        numeric_ids.isna()
        | ~finite_ids
        | numeric_ids.mod(1).ne(0)
        | numeric_ids.lt(0)
    )
    if bad_id.any():
        sample = scoped.loc[bad_id, "asset_id"].head(3).tolist()
        raise RuntimeError(
            "asset identity asset_id는 0 이상의 정수여야 합니다: "
            f"sample={sample!r}"
        )
    scoped["asset_id"] = numeric_ids.astype("int64")
    scoped["ym"] = scoped["trade_date"].dt.to_period("M")

    duplicated_asset = scoped.duplicated(["asset_id", "ym"], keep=False)
    if duplicated_asset.any():
        sample = scoped.loc[
            duplicated_asset, ["asset_id", "trade_date", "Code"]
        ].head(4).to_dict("records")
        raise RuntimeError(
            "asset identity (asset_id, month)가 중복되었습니다: "
            f"sample={sample}"
        )
    duplicated_code = scoped.duplicated(["Code", "ym"], keep=False)
    if duplicated_code.any():
        sample = scoped.loc[
            duplicated_code, ["asset_id", "trade_date", "Code"]
        ].head(4).to_dict("records")
        raise RuntimeError(
            "asset identity (Code, month)가 중복되었습니다: "
            f"sample={sample}"
        )

    scoped = scoped.sort_values(
        ["trade_date", "asset_id", "Code"], kind="mergesort"
    )
    digest = hashlib.sha256()
    for row in scoped.itertuples(index=False):
        digest.update(json.dumps(
            [row.trade_date.date().isoformat(), int(row.asset_id), row.Code],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"))
        digest.update(b"\n")

    return {
        "asset_identity_contract": ASSET_IDENTITY_CONTRACT,
        "asset_identity_digest": digest.hexdigest(),
        "asset_identity_row_count": int(len(scoped)),
        "asset_identity_asset_count": int(scoped["asset_id"].nunique()),
        "asset_identity_month_count": int(scoped["ym"].nunique()),
        "asset_identity_cutoff": requested_cutoff.date().isoformat(),
    }


def _check_ticker_match_counts(frame: pd.DataFrame) -> None:
    if "ticker_match_count" not in frame.columns:
        return
    counts = pd.to_numeric(frame["ticker_match_count"], errors="coerce")
    invalid = counts.ne(1) | counts.isna()
    if invalid.any():
        columns = [
            column for column in
            ("asset_id", "trade_date", "Code", "ticker_match_count")
            if column in frame.columns
        ]
        sample = frame.loc[invalid, columns].head(5).to_dict("records")
        raise RuntimeError(
            "Silver PIT ticker는 각 (asset_id, trade_date)에 정확히 하나여야 "
            f"합니다. 누락 또는 유효기간 중첩: sample={sample}"
        )


def load_asset_identity_snapshot(
    conn, *, cutoff: Any | None = None,
) -> pd.DataFrame:
    """Load and validate the live RDS month-end PIT identity at ``cutoff``."""
    normalized = _identity_cutoff(cutoff) if cutoff is not None else None
    parameter = None if normalized is None else normalized.date().isoformat()
    frame = read_frame(conn, ASSET_IDENTITY_SQL, (parameter, parameter))
    _check_ticker_match_counts(frame)
    evidence = asset_identity_evidence(frame, cutoff=normalized)
    frame.attrs["asset_identity"] = evidence
    return frame


def verify_live_asset_identity(
    conn, expected: dict[str, Any], *, cutoff: Any | None = None,
) -> dict[str, Any]:
    """Fail closed when live RDS identity differs from bound panel evidence."""
    missing = [key for key in ASSET_IDENTITY_META_KEYS if key not in expected]
    if missing:
        raise RuntimeError(
            f"예상 asset identity 계약 메타데이터가 없습니다: {missing}"
        )
    expected_cutoff = _identity_cutoff(expected["asset_identity_cutoff"])
    if cutoff is not None and _identity_cutoff(cutoff) != expected_cutoff:
        raise RuntimeError(
            "asset identity 검증 cutoff와 패널 계약 cutoff가 다릅니다: "
            f"requested={_identity_cutoff(cutoff).date().isoformat()}, "
            f"bound={expected_cutoff.date().isoformat()}"
        )
    live = load_asset_identity_snapshot(conn, cutoff=expected_cutoff)
    actual = live.attrs["asset_identity"]
    mismatches = {
        key: {"expected": expected[key], "actual": actual[key]}
        for key in ASSET_IDENTITY_META_KEYS
        if str(expected[key]) != str(actual[key])
    }
    if mismatches:
        raise RuntimeError(
            "현재 RDS의 asset_id↔ticker PIT identity가 패널 계약과 "
            f"다릅니다: {mismatches}"
        )
    return actual


def _one_row(frame: pd.DataFrame, *, label: str) -> pd.Series:
    if len(frame) != 1:
        raise RuntimeError(f"{label}은 정확히 한 행이어야 합니다: rows={len(frame)}")
    return frame.iloc[0]


def _date_value(value: Any, *, label: str) -> date:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise RuntimeError(f"{label} 날짜가 비어 있거나 잘못되었습니다: {value!r}")
    return pd.Timestamp(parsed).date()


def _positive_metadata_int(payload: dict, key: str, *, label: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool):
        raise RuntimeError(f"{label}.{key}는 양의 정수여야 합니다: {value!r}")
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"{label}.{key}는 양의 정수여야 합니다: {value!r}"
        ) from exc
    if integer < 1 or value != integer:
        raise RuntimeError(f"{label}.{key}는 양의 정수여야 합니다: {value!r}")
    return integer


def _nonnegative_metadata_int(payload: dict, key: str, *, label: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool):
        raise RuntimeError(
            f"{label}.{key}는 0 이상의 정수여야 합니다: {value!r}"
        )
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"{label}.{key}는 0 이상의 정수여야 합니다: {value!r}"
        ) from exc
    if integer < 0 or value != integer:
        raise RuntimeError(
            f"{label}.{key}는 0 이상의 정수여야 합니다: {value!r}"
        )
    return integer


def _sha256_text(value: Any, *, label: str) -> str:
    rendered = str(value or "")
    if len(rendered) != 64 or any(
        character not in "0123456789abcdef" for character in rendered
    ):
        raise RuntimeError(f"{label}은 소문자 SHA-256이어야 합니다")
    return rendered


def total_return_evidence_sha256(evidence: dict[str, Any]) -> str:
    """Hash canonical validation evidence (excluding its digest field)."""
    payload = {
        key: value for key, value in evidence.items()
        if key != "evidence_sha256"
    }
    return hashlib.sha256(json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _cash_scale_canonical_value(column: str, value: object) -> object:
    """Mirror TeamAlpha's public cash-scale row rendering contract."""
    if value is None or pd.isna(value):
        return None
    if column in _CASH_SCALE_DATE_COLUMNS:
        if isinstance(value, (date, datetime, pd.Timestamp)):
            return value.isoformat()[:10]
        return pd.Timestamp(value).date().isoformat()
    if column in _CASH_SCALE_INTEGER_COLUMNS:
        return int(value)
    if column in _CASH_SCALE_BOOLEAN_COLUMNS:
        return bool(value)
    if column in _CASH_SCALE_DECIMAL_PLACES:
        try:
            quantum = Decimal(1).scaleb(-_CASH_SCALE_DECIMAL_PLACES[column])
            return format(Decimal(str(value)).quantize(quantum), "f")
        except (InvalidOperation, ValueError) as exc:
            raise RuntimeError(
                f"현금배당 스케일 증거 숫자값이 잘못되었습니다: "
                f"{column}={value!r}"
            ) from exc
    return str(value)


def _cash_scale_rows_digest(
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...],
    order_by: tuple[str, ...],
) -> str:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise RuntimeError(
            f"현금배당 스케일 digest 컬럼 누락: {missing}"
        )
    ordered = frame.sort_values(list(order_by), kind="stable")
    payload = [
        {
            column: _cash_scale_canonical_value(
                column, getattr(row, column),
            )
            for column in columns
        }
        for row in ordered[list(columns)].itertuples(index=False)
    ]
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def cash_scale_source_evidence_digest(frame: pd.DataFrame) -> str:
    """Digest persisted evidence, including both certified run identities."""
    return _cash_scale_rows_digest(
        frame,
        columns=CASH_SCALE_SOURCE_EVIDENCE_COLUMNS,
        order_by=("action_snapshot_run_id", "evidence_key"),
    )


def cash_scale_source_manifest_digest(frame: pd.DataFrame) -> str:
    """Digest database-neutral parent rows from the immutable manifest."""
    return _cash_scale_rows_digest(
        frame,
        columns=CASH_SCALE_MANIFEST_ROW_COLUMNS,
        order_by=("evidence_key",),
    )


def cash_scale_support_action_digest(frame: pd.DataFrame) -> str:
    """Digest persisted support-action rows, including both run identities."""
    return _cash_scale_rows_digest(
        frame,
        columns=CASH_SCALE_SUPPORT_ACTION_COLUMNS,
        order_by=(
            "action_snapshot_run_id", "evidence_key",
            "support_action_source", "support_action_key",
            "support_action_type",
        ),
    )


def cash_scale_support_manifest_digest(frame: pd.DataFrame) -> str:
    """Digest database-neutral support-action rows from the manifest."""
    return _cash_scale_rows_digest(
        frame,
        columns=CASH_SCALE_MANIFEST_SUPPORT_ACTION_COLUMNS,
        order_by=(
            "evidence_key", "support_action_source", "support_action_key",
            "support_action_type",
        ),
    )


def cash_scale_resolution_evidence_digest(frame: pd.DataFrame) -> str:
    """Digest every applied-event cash-scale decision in resolution-v2."""
    return _cash_scale_rows_digest(
        frame,
        columns=CASH_SCALE_RESOLUTION_DIGEST_COLUMNS,
        order_by=("asset_id", "source", "action_key"),
    )


def _cash_scale_manifest_row_sha(row: pd.Series) -> str:
    missing = sorted(
        set(CASH_SCALE_MANIFEST_ROW_COLUMNS) - set(row.index)
    )
    if missing:
        raise RuntimeError(
            f"현금배당 스케일 manifest 컬럼 누락: {missing}"
        )
    payload = {
        column: _cash_scale_canonical_value(column, row[column])
        for column in CASH_SCALE_MANIFEST_ROW_COLUMNS
    }
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def _cash_scale_manifest_support_row_sha(row: pd.Series) -> str:
    missing = sorted(
        set(CASH_SCALE_MANIFEST_SUPPORT_ACTION_COLUMNS) - set(row.index)
    )
    if missing:
        raise RuntimeError(
            f"현금배당 스케일 support manifest 컬럼 누락: {missing}"
        )
    payload = {
        column: _cash_scale_canonical_value(column, row[column])
        for column in CASH_SCALE_MANIFEST_SUPPORT_ACTION_COLUMNS
    }
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def _dividend_digest_value(column: str, value: object) -> object:
    """Render one TeamAlpha dividend-evidence field canonically."""
    if value is None or pd.isna(value):
        return None
    if column in _DIVIDEND_DIGEST_DATE_COLUMNS:
        if isinstance(value, (date, datetime, pd.Timestamp)):
            return value.isoformat()[:10]
        return pd.Timestamp(value).date().isoformat()
    if column == "asset_id":
        return int(value)
    if column == "is_terminal_economic_revision":
        return bool(value)
    if column in _DIVIDEND_DIGEST_DECIMAL_PLACES:
        try:
            places = _DIVIDEND_DIGEST_DECIMAL_PLACES[column]
            quantum = Decimal(1).scaleb(-places)
            return format(Decimal(str(value)).quantize(quantum), "f")
        except (InvalidOperation, ValueError) as exc:
            raise RuntimeError(
                f"배당 증거 숫자값이 잘못되었습니다: {column}={value!r}"
            ) from exc
    return str(value)


def _dividend_frame_digest(
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...],
    order_by: tuple[str, ...],
) -> str:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise RuntimeError(f"배당 digest 컬럼이 없습니다: {missing}")
    ordered = frame.sort_values(list(order_by), kind="stable")
    payload = [
        {
            column: _dividend_digest_value(column, getattr(row, column))
            for column in columns
        }
        for row in ordered[list(columns)].itertuples(index=False)
    ]
    rendered = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def source_receipt_digest(frame: pd.DataFrame) -> str:
    """Hash the complete immutable DART source-receipt ledger."""
    if (
        "receipt_no" in frame
        and frame["receipt_no"].astype(str).duplicated().any()
    ):
        raise RuntimeError("배당 source receipt가 중복되었습니다")
    return _dividend_frame_digest(
        frame,
        columns=SOURCE_RECEIPT_DIGEST_COLUMNS,
        order_by=("receipt_no",),
    )


def terminal_source_receipt_digest(frame: pd.DataFrame) -> str:
    terminal = frame[
        frame["is_terminal_economic_revision"].fillna(False).astype(bool)
    ]
    return source_receipt_digest(terminal)


def published_action_digest(frame: pd.DataFrame) -> str:
    keys = ["asset_id", "source", "action_key"]
    if all(column in frame for column in keys) and frame.duplicated(keys).any():
        raise RuntimeError("게시 배당 action key가 중복되었습니다")
    return _dividend_frame_digest(
        frame,
        columns=PUBLISHED_ACTION_DIGEST_COLUMNS,
        order_by=("asset_id", "source", "action_key"),
    )


def included_cash_parity_digest(frame: pd.DataFrame) -> str:
    if (
        "receipt_no" in frame
        and frame["receipt_no"].astype(str).duplicated().any()
    ):
        raise RuntimeError("포함 배당 parity receipt가 중복되었습니다")
    return _dividend_frame_digest(
        frame,
        columns=INCLUDED_CASH_PARITY_COLUMNS,
        order_by=("asset_id", "receipt_no"),
    )


def _dividend_series(frame: pd.DataFrame, name: str) -> pd.Series:
    return frame.get(name, pd.Series(None, index=frame.index, dtype="object"))


def _invalid_cash_evidence_mask(
    frame: pd.DataFrame,
    *,
    key_column: str,
    root_key_column: str,
    correction_key_column: str,
) -> pd.Series:
    """Mirror TeamAlpha's exact source/economic evidence shape."""
    key = _dividend_series(frame, key_column).fillna("").astype(str).str.strip()
    root = (
        _dividend_series(frame, root_key_column)
        .fillna("").astype(str).str.strip()
    )
    correction_key = (
        _dividend_series(frame, correction_key_column)
        .fillna("").astype(str).str.strip()
    )
    source_status = (
        _dividend_series(frame, "source_evidence_status")
        .fillna("").astype(str)
    )
    cash_status = (
        _dividend_series(frame, "cash_amount_status")
        .fillna("").astype(str)
    )
    revision_kind = (
        _dividend_series(frame, "revision_kind").fillna("").astype(str)
    )
    viewer_sha = (
        _dividend_series(frame, "viewer_evidence_sha256")
        .fillna("").astype(str)
    )
    economic_sha = (
        _dividend_series(frame, "economic_evidence_sha256")
        .fillna("").astype(str)
    )
    reviewed_id = (
        _dividend_series(frame, "reviewed_correction_id")
        .fillna("").astype(str).str.strip()
    )
    receipt_pattern = r"^[0-9]{14}$"
    sha_pattern = r"^[0-9a-f]{64}$"
    source_shape = (
        source_status.eq("VERIFIED_OPENDART_DOCUMENT")
        & viewer_sha.eq("")
        & economic_sha.str.fullmatch(sha_pattern)
    ) | (
        source_status.eq("VERIFIED_DART_VIEWER_BODY")
        & viewer_sha.str.fullmatch(sha_pattern)
        & economic_sha.str.fullmatch(sha_pattern)
        & viewer_sha.eq(economic_sha)
    ) | (
        source_status.eq("VERIFIED_ATTACHMENT_CORRECTION")
        & viewer_sha.str.fullmatch(sha_pattern)
        & economic_sha.str.fullmatch(sha_pattern)
        & viewer_sha.ne(economic_sha)
        & cash_status.eq("ATTACHMENT_ONLY")
        & revision_kind.eq("ATTACHMENT_ONLY")
        & correction_key.ne("")
    ) | (
        source_status.eq("VERIFIED_REVIEWED_SOURCE_ERRATUM")
        & viewer_sha.eq("")
        & economic_sha.str.fullmatch(sha_pattern)
        & reviewed_id.ne("")
    )
    record_date = pd.to_datetime(
        _dividend_series(frame, "record_date"), errors="coerce",
    )
    cash_amount = pd.to_numeric(
        _dividend_series(frame, "cash_amount"), errors="coerce",
    )
    economic_shape = (
        cash_status.eq("POSITIVE") & record_date.notna() & cash_amount.gt(0)
    ) | (
        cash_status.eq("POSITIVE_PENDING_RECORD_DATE")
        & record_date.isna()
        & cash_amount.gt(0)
    ) | (
        cash_status.isin({
            "NO_COMMON_CASH_DIVIDEND", "NO_ECONOMIC_EVENT",
            "ATTACHMENT_ONLY",
        })
        & cash_amount.isna()
    )
    return (
        ~key.str.fullmatch(receipt_pattern)
        | ~root.str.fullmatch(receipt_pattern)
        | ~(correction_key.eq("") | correction_key.str.fullmatch(receipt_pattern))
        | ~source_status.isin(VERIFIED_DIVIDEND_SOURCE_STATUSES)
        | ~cash_status.isin(SUPPORTED_DIVIDEND_CASH_STATUSES)
        | ~source_shape
        | ~economic_shape
    )


def _corp_cls_counts(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty:
        return {}
    normalized = frame["corp_cls"].map(
        lambda value: (
            "UNKNOWN"
            if value is None or pd.isna(value) or not str(value).strip()
            else str(value).strip()
        )
    )
    return {
        str(key): int(value)
        for key, value in normalized.value_counts().sort_index().items()
    }


def _reason_counts(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty:
        return {}
    return {
        str(key): int(value)
        for key, value in frame["excluded_reason"].value_counts(
            dropna=False,
        ).sort_index().items()
    }


def _valid_count_map(value: Any) -> bool:
    return isinstance(value, dict) and all(
        isinstance(count, int)
        and not isinstance(count, bool)
        and count >= 0
        and isinstance(key, str)
        and bool(key)
        for key, count in value.items()
    )


def _source_receipt_semantic_failures(frame: pd.DataFrame) -> pd.Series:
    invalid = _invalid_cash_evidence_mask(
        frame,
        key_column="receipt_no",
        root_key_column="revision_root_receipt_no",
        correction_key_column="previous_receipt_no",
    )
    receipt = frame["receipt_no"].fillna("").astype(str)
    terminal_receipt = frame["terminal_receipt_no"].fillna("").astype(str)
    previous = frame["previous_receipt_no"].fillna("").astype(str)
    ticker = frame["ticker"].fillna("").astype(str)
    mapping = frame["mapping_status"].fillna("").astype(str)
    terminal_flag = frame["is_terminal_economic_revision"]
    expected_terminal = receipt.eq(terminal_receipt)
    source_status = frame["source_evidence_status"].fillna("").astype(str)
    roots = frame["revision_root_receipt_no"].fillna("").astype(str)
    prior_keys = set(zip(receipt, ticker, roots))
    attachment_has_same_family_previous = pd.Series(
        [
            (str(previous_key), str(row_ticker), str(root)) in prior_keys
            for previous_key, row_ticker, root in zip(previous, ticker, roots)
        ],
        index=frame.index,
        dtype="bool",
    )
    attachment_missing_previous = (
        source_status.eq("VERIFIED_ATTACHMENT_CORRECTION")
        & ~attachment_has_same_family_previous
    )
    return invalid | attachment_missing_previous | (
        ~terminal_receipt.str.fullmatch(r"^[0-9]{14}$")
        | frame["terminal_announcement_date"].isna()
        | terminal_flag.isna()
        | terminal_flag.fillna(False).astype(bool).ne(expected_terminal)
        | ~(previous.eq("") | previous.str.fullmatch(r"^[0-9]{14}$"))
        | ~ticker.str.fullmatch(r"^[0-9A-Z]{6}$")
        | frame["pit_event_date"].isna()
        | ~mapping.isin({"INCLUDED", "EXCLUDED"})
        | (
            mapping.eq("INCLUDED")
            & (frame["asset_id"].isna() | frame["excluded_reason"].notna())
        )
        | (mapping.eq("EXCLUDED") & frame["excluded_reason"].isna())
    )


def _action_cash_parity_frame(actions: pd.DataFrame) -> pd.DataFrame:
    return actions[actions["action_type"].eq("cash_dividend")].rename(
        columns={
            "action_key": "receipt_no",
            "correction_of_action_key": "previous_receipt_no",
            "revision_root_action_key": "revision_root_receipt_no",
        }
    )[list(INCLUDED_CASH_PARITY_COLUMNS)].copy()


def _cash_scale_source_semantic_checks(
    frame: pd.DataFrame,
    *,
    action_snapshot_run_id: str,
) -> dict[str, bool]:
    """Validate persisted source rows without trusting producer metadata."""
    required = set(CASH_SCALE_SOURCE_EVIDENCE_COLUMNS)
    if not required.issubset(frame.columns):
        return {"required_columns": False}
    if frame.empty:
        return {
            "required_columns": True,
            "run_binding": True,
            "unique_keys": True,
            "unique_cash_date": True,
            "identities": True,
            "source_bodies": True,
            "support_summary": True,
            "price_evidence": True,
            "date_order": True,
            "positive_prices": True,
            "reference_factor": True,
            "basis": True,
            "manifest_row_digest": True,
        }

    run_ids = frame["action_snapshot_run_id"].astype("string")
    evidence_keys = frame["evidence_key"].astype("string")
    tickers = frame["ticker"].astype("string")
    receipts = frame["cash_receipt_no"].astype("string")
    asset_ids = pd.to_numeric(frame["asset_id"], errors="coerce")
    previous_dates = pd.to_datetime(
        frame["previous_trade_date"], errors="coerce",
    )
    adjustment_dates = pd.to_datetime(
        frame["adjustment_trade_date"], errors="coerce",
    )
    prices = {
        column: pd.to_numeric(frame[column], errors="coerce")
        for column in (
            "raw_previous_close", "raw_applied_close",
            "raw_reference_price", "expected_price_factor",
        )
    }
    support_action_count = pd.to_numeric(
        frame["support_action_count"], errors="coerce",
    )
    support_group_count = pd.to_numeric(
        frame["support_semantic_group_count"], errors="coerce",
    )
    sha_fields = (
        "cash_action_body_sha256", "cash_economic_sha256",
        "support_action_digest",
        "previous_price_source_content_sha256",
        "adjustment_price_source_content_sha256", "manifest_row_sha256",
    )
    valid_sha = pd.Series(True, index=frame.index)
    for column in sha_fields:
        valid_sha &= frame[column].astype("string").str.fullmatch(
            r"[0-9a-f]{64}", na=False,
        )
    body_paths = (
        "cash_action_body_path", "cash_economic_body_path",
        "previous_price_source_object_key",
        "adjustment_price_source_object_key",
    )
    nonempty_paths = pd.Series(True, index=frame.index)
    for column in body_paths:
        rendered = frame[column].astype("string")
        nonempty_paths &= rendered.notna() & rendered.str.strip().ne("")

    previous_etag = frame[
        "previous_price_source_etag"
    ].astype("string")
    adjustment_etag = frame[
        "adjustment_price_source_etag"
    ].astype("string")
    cash_status = frame["cash_source_evidence_status"].astype("string")
    cash_schema = frame["cash_economic_body_schema"].astype("string")
    cash_body_contract = (
        cash_status.eq("VERIFIED_OPENDART_DOCUMENT")
        & cash_schema.eq("OPENDART_DOCUMENT_ZIP_V1")
        & frame["cash_action_body_path"].eq(
            frame["cash_economic_body_path"]
        )
        & frame["cash_action_body_sha256"].eq(
            frame["cash_economic_sha256"]
        )
    ) | (
        cash_status.eq("VERIFIED_DART_VIEWER_BODY")
        & cash_schema.eq("DART_VIEWER_HTML_V1")
    ) | (
        cash_status.eq("VERIFIED_REVIEWED_SOURCE_ERRATUM")
        & cash_schema.eq("REVIEWED_PERIODIC_JSON_V1")
    )
    positive_prices = pd.Series(True, index=frame.index)
    for values in prices.values():
        positive_prices &= values.notna() & values.gt(0) & values.map(
            math.isfinite
        )
    observed_factor = prices["raw_reference_price"] / prices[
        "raw_previous_close"
    ]
    factor_parity = (
        observed_factor - prices["expected_price_factor"]
    ).abs().le(5e-13)
    manifest_parity = pd.Series(
        [
            _cash_scale_manifest_row_sha(row)
            == str(row["manifest_row_sha256"])
            for _, row in frame.iterrows()
        ],
        index=frame.index,
    )
    return {
        "required_columns": True,
        "run_binding": bool(run_ids.eq(action_snapshot_run_id).all()),
        "unique_keys": bool(
            evidence_keys.notna().all()
            and evidence_keys.str.len().between(1, 300).all()
            and not frame.duplicated([
                "action_snapshot_run_id", "evidence_key",
            ]).any()
        ),
        "unique_cash_date": not frame.duplicated([
            "action_snapshot_run_id", "asset_id", "cash_receipt_no",
            "adjustment_trade_date",
        ]).any(),
        "identities": bool(
            asset_ids.notna().all()
            and asset_ids.mod(1).eq(0).all()
            and asset_ids.gt(0).all()
            and tickers.str.fullmatch(r"[0-9A-Z]{6}", na=False).all()
            and receipts.str.fullmatch(r"[0-9]{14}", na=False).all()
        ),
        "source_bodies": bool(
            valid_sha.all() and nonempty_paths.all()
            and cash_body_contract.all()
        ),
        "support_summary": bool(
            support_action_count.notna().all()
            and support_action_count.mod(1).eq(0).all()
            and support_action_count.gt(0).all()
            and support_group_count.notna().all()
            and support_group_count.mod(1).eq(0).all()
            and support_group_count.gt(0).all()
            and support_group_count.le(support_action_count).all()
        ),
        "price_evidence": bool(
            frame["price_source"].eq("KRX").all()
            and frame["previous_price_source_schema"].isin({
                "marcap_parquet_v1", "krxapi_stock_parquet_v1",
            }).all()
            and frame["adjustment_price_source_schema"].isin({
                "marcap_parquet_v1", "krxapi_stock_parquet_v1",
            }).all()
            and previous_etag.str.fullmatch(
                r"[0-9a-f]{32}(?:-[0-9]+)?", na=False,
            ).all()
            and adjustment_etag.str.fullmatch(
                r"[0-9a-f]{32}(?:-[0-9]+)?", na=False,
            ).all()
        ),
        "date_order": bool(
            previous_dates.notna().all()
            and adjustment_dates.notna().all()
            and previous_dates.lt(adjustment_dates).all()
        ),
        "positive_prices": bool(positive_prices.all()),
        "reference_factor": bool(factor_parity.fillna(False).all()),
        "basis": bool(
            frame["cash_scale_basis"].eq("PRE_EVENT_PRICE_SCALE").all()
        ),
        "manifest_row_digest": bool(manifest_parity.all()),
    }


def _cash_scale_receipt_parity(
    evidence: pd.DataFrame,
    receipts: pd.DataFrame,
) -> bool:
    if evidence.empty:
        return True
    required = {
        "receipt_no", "asset_id", "ticker", "economic_evidence_sha256",
        "source_evidence_status", "mapping_status",
        "is_terminal_economic_revision",
    }
    if not required.issubset(receipts.columns):
        return False
    terminal = receipts[
        receipts["mapping_status"].eq("INCLUDED")
        & receipts["is_terminal_economic_revision"].fillna(False).astype(bool)
    ].copy()
    keys = terminal["receipt_no"].astype(str)
    if keys.duplicated().any():
        return False
    by_key = terminal.assign(_receipt_key=keys).set_index("_receipt_key")
    for row in evidence.itertuples(index=False):
        receipt_no = str(row.cash_receipt_no)
        if receipt_no not in by_key.index:
            return False
        receipt = by_key.loc[receipt_no]
        if isinstance(receipt, pd.DataFrame):
            return False
        try:
            same_asset = int(receipt["asset_id"]) == int(row.asset_id)
        except (TypeError, ValueError):
            return False
        if not (
            same_asset
            and str(receipt["ticker"]) == str(row.ticker)
            and str(receipt["source_evidence_status"])
            == str(row.cash_source_evidence_status)
            and str(receipt["economic_evidence_sha256"])
            == str(row.cash_economic_sha256)
        ):
            return False
    return True


def _cash_scale_support_groups(value: object) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise ValueError("support semantic groups must be JSON text")
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("support semantic groups are not JSON") from exc
    if (
        not isinstance(decoded, list)
        or not decoded
        or any(
            not isinstance(item, str) or not item.strip()
            for item in decoded
        )
    ):
        raise ValueError("support semantic group list is invalid")
    canonical = sorted(set(item.strip() for item in decoded))
    if (
        decoded != canonical
        or any(len(item) > 300 for item in canonical)
        or value != json.dumps(
            canonical, ensure_ascii=False, separators=(",", ":"),
        )
    ):
        raise ValueError("support semantic group list is not canonical")
    return tuple(canonical)


def _cash_scale_support_group_count(frame: pd.DataFrame) -> int:
    groups: set[str] = set()
    for value in frame.get(
        "support_semantic_group_keys", pd.Series(dtype="object"),
    ):
        groups.update(_cash_scale_support_groups(value))
    return len(groups)


_VIEWER_BONUS_GROUP_PATTERN = re.compile(
    r"^(?P<ticker>[0-9A-Z]{6})\|"
    r"(?P<effective>[0-9]{4}-[0-9]{2}-[0-9]{2})\|"
    r"BONUS_ISSUE\|"
    r"(?P<ratio>[0-9]+(?:\.[0-9]+)?(?:e[+-][0-9]+)?)$"
)

_PAID_INCREASE_IDENTITY = (
    "183190", "20180226800579", "2017-12-27",
    "20180201000086", "2017-12-31", "0.1456981704",
)
_PAID_INCREASE_BODY_SHA256 = (
    "cf15168b7b9f16f7808252be7dc2a81a06dc23b30d0d14e41cebf8674ebf35c9"
)
_PAID_INCREASE_REPORT_NAME = "유상증자 결정"


def _cash_scale_viewer_bonus_group_parity(
    parent: object,
    child: pd.Series,
    groups: tuple[str, ...],
) -> bool:
    """Bind the producer's sole bonus group to parent and economics."""
    if len(groups) != 1:
        return False
    match = _VIEWER_BONUS_GROUP_PATTERN.fullmatch(groups[0])
    if match is None:
        return False
    try:
        ticker = str(getattr(parent, "ticker"))
        effective = pd.Timestamp(child["support_ex_date"]).date()
        ratio = (
            float(child["support_ratio_numerator"])
            / float(child["support_ratio_denominator"])
        )
        if not math.isfinite(ratio) or ratio <= 0:
            return False
        parsed_effective = date.fromisoformat(match.group("effective"))
    except (AttributeError, TypeError, ValueError, ZeroDivisionError):
        return False
    expected_ratio = format(ratio, ".12g")
    return (
        match.group("ticker") == ticker
        and parsed_effective == effective
        and match.group("effective") == effective.isoformat()
        and match.group("ratio") == expected_ratio
    )


def _cash_scale_viewer_stock_dividend_group_parity(
    parent: object,
    child: pd.Series,
    groups: tuple[str, ...],
) -> bool:
    """Bind a verified viewer stock family to its own record-date group."""
    if len(groups) != 1:
        return False
    try:
        numerator = float(child["support_ratio_numerator"])
        denominator = float(child["support_ratio_denominator"])
        ratio = numerator / denominator
        record = pd.Timestamp(child["support_record_date"]).date()
        adjustment = pd.Timestamp(parent.adjustment_trade_date).date()
        ticker = str(getattr(parent, "ticker"))
    except (
        AttributeError, TypeError, ValueError, ZeroDivisionError,
    ):
        return False
    if not math.isfinite(ratio) or ratio <= 0:
        return False
    expected = (
        f"{ticker}|{record.isoformat()}|STOCK_DIVIDEND|"
        f"{format(ratio, '.12g')}"
    )
    return bool(
        1 <= (record - adjustment).days <= 7
        and groups == (expected,)
    )


def _cash_scale_paid_increase_group_parity(
    parent: object,
    child: pd.Series,
    groups: tuple[str, ...],
) -> bool:
    """Admit only the independently reviewed paid-rights identity."""
    if len(groups) != 1:
        return False
    try:
        numerator = float(child["support_ratio_numerator"])
        denominator = float(child["support_ratio_denominator"])
        ratio = numerator / denominator
        adjustment = pd.Timestamp(parent.adjustment_trade_date).date()
        record = pd.Timestamp(child["support_record_date"]).date()
        identity = (
            str(parent.ticker).zfill(6),
            str(parent.cash_receipt_no),
            adjustment.isoformat(),
            str(child["support_action_key"]),
            record.isoformat(),
            format(ratio, ".12g"),
        )
        raw_previous = float(parent.raw_previous_close)
        raw_reference = float(parent.raw_reference_price)
        expected_factor = float(parent.expected_price_factor)
    except (
        AttributeError, TypeError, ValueError, ZeroDivisionError,
    ):
        return False
    expected_group = (
        f"{identity[0]}|{identity[4]}|PAID_INCREASE|{identity[5]}"
    )
    return bool(
        math.isfinite(ratio)
        and ratio > 0
        and 1 <= (record - adjustment).days <= 7
        and identity == _PAID_INCREASE_IDENTITY
        and groups == (expected_group,)
        and str(parent.price_source) == "KRX"
        and math.isfinite(raw_previous)
        and raw_previous > 0
        and math.isfinite(raw_reference)
        and raw_reference > 0
        and math.isfinite(expected_factor)
        and _cash_scale_decimal_equal(
            expected_factor, raw_reference / raw_previous,
        )
    )


def _cash_scale_support_semantic_checks(
    frame: pd.DataFrame,
    *,
    action_snapshot_run_id: str,
) -> dict[str, bool]:
    required = set(CASH_SCALE_SUPPORT_ACTION_COLUMNS)
    if not required.issubset(frame.columns):
        return {"required_columns": False}
    if frame.empty:
        return {
            "required_columns": True,
            "run_binding": True,
            "unique_identity": True,
            "supported_identity": True,
            "target_identity": True,
            "source_body": True,
            "snapshot_fields": True,
            "security_classes": True,
            "canonical_groups": True,
            "semantic_roles": True,
            "manifest_row_digest": True,
        }

    run_ids = frame["action_snapshot_run_id"].astype("string")
    quality_run_ids = frame["support_action_quality_run_id"].astype(
        "string"
    )
    sources = frame["support_action_source"].astype("string")
    keys = frame["support_action_key"].astype("string")
    action_types = frame["support_action_type"].astype("string")
    target_receipts = frame["target_cash_receipt_no"].astype("string")
    target_dates = pd.to_datetime(
        frame["target_adjustment_date"], errors="coerce",
    )
    supported_identity = (
        (
            sources.eq("DART_DISCLOSURE")
            & action_types.isin({
                "ex_dividend", "rights_detachment", "stock_dividend",
                "combined_detachment",
            })
            & keys.str.fullmatch(r"[0-9]{14}", na=False)
        )
        | (
            sources.eq("DART_STRUCTURED")
            & action_types.eq("bonus_issue")
            & keys.str.fullmatch(r"[0-9]{14}", na=False)
        )
        | (
            sources.eq("DART_VIEWER")
            & action_types.isin({"bonus_issue", "stock_dividend"})
            & keys.str.fullmatch(r"[0-9]{14}", na=False)
        )
        | (
            sources.eq("KRX_KIND")
            & action_types.isin({
                "stock_dividend", "ex_dividend", "rights_detachment",
                "combined_detachment", "paid_increase",
            })
            & keys.str.fullmatch(r"[0-9]{14}", na=False)
        )
    )
    body_sha = frame["support_action_body_sha256"].astype(
        "string"
    ).str.fullmatch(r"[0-9a-f]{64}", na=False)
    body_path = frame["support_action_body_path"].astype("string")
    kind_body_path = (
        "corporate_actions/krx/kind/body_objects/sha256="
        + frame["support_action_body_sha256"].astype("string")
        + ".html"
    )
    viewer_bonus_body_path = (
        "corporate_actions/dart/support_action_families/objects/sha256="
        + frame["support_action_body_sha256"].astype("string")
        + ".html"
    )
    report_name = frame["support_report_name"].astype("string")
    compact_report = report_name.str.replace(r"\s+", "", regex=True)
    reason = frame["support_reason"].astype("string")
    compact_reason = reason.str.replace(r"\s+", "", regex=True)
    admissible_report = (
        report_name.notna()
        & report_name.str.strip().ne("")
        & ~report_name.str.contains("철회|취소|부결", regex=True, na=False)
    )
    ratio_numerator = pd.to_numeric(
        frame["support_ratio_numerator"], errors="coerce",
    )
    ratio_denominator = pd.to_numeric(
        frame["support_ratio_denominator"], errors="coerce",
    )
    entitlement = frame[
        "support_entitlement_security_class"
    ].astype("string")
    distributed = frame[
        "support_distributed_security_class"
    ].astype("string")
    expected_factor = pd.to_numeric(
        frame["support_expected_price_factor"], errors="coerce",
    )
    reference_price = pd.to_numeric(
        frame["support_reference_price"], errors="coerce",
    )
    ratio_pair = (
        ratio_numerator.isna().eq(ratio_denominator.isna())
        & (ratio_numerator.isna() | ratio_numerator.gt(0))
        & (ratio_denominator.isna() | ratio_denominator.gt(0))
    )
    optional_positive = (
        (expected_factor.isna() | expected_factor.gt(0))
        & (reference_price.isna() | reference_price.gt(0))
    )
    bonus_expected_factor = 1.0 / (
        1.0 + (ratio_numerator / ratio_denominator)
    )
    bonus_expected_factor_parity = (
        expected_factor - bonus_expected_factor
    ).abs().le(5e-13).fillna(False)
    parsed_groups: list[tuple[str, ...] | None] = []
    for value in frame["support_semantic_group_keys"]:
        try:
            parsed_groups.append(_cash_scale_support_groups(value))
        except ValueError:
            parsed_groups.append(None)
    roles = frame["support_semantic_role"].astype("string")
    role_contract = roles.isin({
        "ADJUSTMENT_COMPONENT", "CORROBORATION",
    })
    allowed_security_classes = (
        (entitlement.isna() | entitlement.isin({
            "COMMON", "PREFERRED", "COMMON_AND_PREFERRED",
        }))
        & (distributed.isna() | distributed.isin({
            "COMMON", "PREFERRED", "NEW_PREFERRED",
        }))
    )
    common_stock_component = (
        entitlement.eq("COMMON").fillna(False)
        & distributed.eq("COMMON").fillna(False)
    )
    new_preferred_stock_component = (
        entitlement.eq("COMMON_AND_PREFERRED").fillna(False)
        & distributed.eq("NEW_PREFERRED").fillna(False)
    )
    kind_corroboration = (
        roles.eq("CORROBORATION")
        & sources.eq("KRX_KIND")
        & action_types.isin({
            "ex_dividend", "rights_detachment", "combined_detachment",
        })
    )
    kind_reason_contract = (
        (
            action_types.eq("ex_dividend")
            & compact_reason.str.contains("주식배당", regex=False, na=False)
            & ~compact_reason.str.contains("무상증자", regex=False, na=False)
        )
        | (
            action_types.eq("rights_detachment")
            & compact_reason.str.contains("무상증자", regex=False, na=False)
            & ~compact_reason.str.contains("주식배당", regex=False, na=False)
        )
        | (
            action_types.eq("combined_detachment")
            & compact_reason.str.contains("주식배당", regex=False, na=False)
            & compact_reason.str.contains("무상증자", regex=False, na=False)
        )
    )
    kind_corroboration_contract = (
        kind_corroboration
        & ratio_numerator.isna()
        & ratio_denominator.isna()
        & expected_factor.isna()
        & reference_price.notna()
        # Producer evidence may also retain preferred-share notices.  This
        # consumer certifies a common-stock-only research universe, while the
        # published action row has no security-class column to disambiguate a
        # swap, so selected corroboration must fail closed to COMMON.
        & entitlement.eq("COMMON").fillna(False)
        & distributed.isna()
        & pd.to_datetime(
            frame["support_ex_date"], errors="coerce",
        ).notna()
        & pd.to_datetime(
            frame["support_record_date"], errors="coerce",
        ).isna()
        & report_name.isin({"배당락 기준가격 안내", "배당락"})
        & kind_reason_contract
    )
    kind_stock_component_contract = (
        roles.eq("ADJUSTMENT_COMPONENT")
        & sources.eq("KRX_KIND")
        & action_types.eq("stock_dividend")
        & ratio_numerator.notna()
        & expected_factor.isna()
        & reference_price.isna()
        & pd.to_datetime(
            frame["support_ex_date"], errors="coerce",
        ).isna()
        & pd.to_datetime(
            frame["support_record_date"], errors="coerce",
        ).notna()
        & report_name.eq("주식배당 결정")
        & (common_stock_component | new_preferred_stock_component)
    )
    viewer_bonus_component_contract = (
        roles.eq("ADJUSTMENT_COMPONENT")
        & sources.eq("DART_VIEWER")
        & action_types.eq("bonus_issue")
        & ratio_numerator.notna()
        & bonus_expected_factor_parity
        & common_stock_component
        & pd.to_datetime(
            frame["support_ex_date"], errors="coerce",
        ).notna()
        & pd.to_datetime(
            frame["support_record_date"], errors="coerce",
        ).isna()
        & report_name.str.fullmatch(
            r"(?:\[기재정정\])?주요사항보고서\(무상증자결정\)",
            na=False,
        )
    )
    viewer_stock_dividend_component_contract = (
        roles.eq("ADJUSTMENT_COMPONENT")
        & sources.eq("DART_VIEWER")
        & action_types.eq("stock_dividend")
        & ratio_numerator.notna()
        & ratio_denominator.notna()
        & ratio_numerator.map(math.isfinite)
        & ratio_denominator.map(math.isfinite)
        & expected_factor.isna()
        & reference_price.isna()
        & common_stock_component
        & pd.to_datetime(
            frame["support_ex_date"], errors="coerce",
        ).isna()
        & pd.to_datetime(
            frame["support_record_date"], errors="coerce",
        ).notna()
        & compact_report.str.fullmatch(
            r"(?:\[기재정정\])?주식배당결정", na=False,
        )
    )
    paid_increase_component_contract = (
        roles.eq("ADJUSTMENT_COMPONENT")
        & sources.eq("KRX_KIND")
        & action_types.eq("paid_increase")
        & keys.eq(_PAID_INCREASE_IDENTITY[3])
        & target_receipts.eq(_PAID_INCREASE_IDENTITY[1])
        & target_dates.eq(pd.Timestamp(_PAID_INCREASE_IDENTITY[2]))
        & frame["support_action_body_sha256"].astype("string").eq(
            _PAID_INCREASE_BODY_SHA256
        )
        & ratio_numerator.notna()
        & ratio_denominator.notna()
        & ratio_numerator.map(math.isfinite)
        & ratio_denominator.map(math.isfinite)
        & expected_factor.isna()
        & reference_price.isna()
        & common_stock_component
        & pd.to_datetime(
            frame["support_ex_date"], errors="coerce",
        ).isna()
        & pd.to_datetime(
            frame["support_record_date"], errors="coerce",
        ).eq(pd.Timestamp(_PAID_INCREASE_IDENTITY[4]))
        & report_name.eq(_PAID_INCREASE_REPORT_NAME)
    )
    component_role_contract = (
        (
            roles.eq("ADJUSTMENT_COMPONENT")
            & sources.eq("DART_STRUCTURED")
            & action_types.eq("bonus_issue")
            & ratio_numerator.notna()
            & bonus_expected_factor_parity
            & common_stock_component
        )
        | viewer_bonus_component_contract
        | viewer_stock_dividend_component_contract
        | (
            roles.eq("ADJUSTMENT_COMPONENT")
            & sources.eq("DART_DISCLOSURE")
            & action_types.eq("stock_dividend")
            & ratio_numerator.notna()
            & (common_stock_component | new_preferred_stock_component)
        )
        | kind_stock_component_contract
        | paid_increase_component_contract
        | (
            roles.eq("CORROBORATION")
            & sources.eq("DART_DISCLOSURE")
            & action_types.isin({
                "ex_dividend", "rights_detachment", "combined_detachment",
            })
        )
        | kind_corroboration_contract
    )
    component_group_contract = all(
        groups is not None
        and (role != "ADJUSTMENT_COMPONENT" or len(groups) == 1)
        for groups, role in zip(parsed_groups, roles, strict=True)
    )
    action_specific = (
        (~(
            sources.eq("DART_DISCLOSURE")
            & action_types.eq("combined_detachment")
        ) | (
            reference_price.notna()
            & frame["support_reason"].astype("string").str.contains(
                "무상증자", regex=False, na=False,
            )
            & frame["support_reason"].astype("string").str.contains(
                "배당", regex=False, na=False,
            )
        ))
        & (
            ~(
                sources.isin({"DART_STRUCTURED", "DART_VIEWER"})
                & action_types.eq("bonus_issue")
            )
            | expected_factor.notna()
        )
    )
    manifest_parity = pd.Series([
        _cash_scale_manifest_support_row_sha(row)
        == str(row["manifest_support_row_sha256"])
        for _, row in frame.iterrows()
    ], index=frame.index)
    return {
        "required_columns": True,
        "run_binding": bool(
            run_ids.eq(action_snapshot_run_id).all()
            and quality_run_ids.eq(action_snapshot_run_id).all()
        ),
        "unique_identity": not frame.duplicated([
            "action_snapshot_run_id", "evidence_key",
            "support_action_source", "support_action_key",
            "support_action_type",
        ]).any(),
        "supported_identity": bool(supported_identity.all()),
        "target_identity": bool(
            target_receipts.str.fullmatch(r"[0-9]{14}", na=False).all()
            and target_dates.notna().all()
        ),
        "source_body": bool(
            body_sha.all()
            and body_path.notna().all()
            and body_path.str.strip().ne("").all()
            and (
                ~sources.eq("KRX_KIND") | body_path.eq(kind_body_path)
            ).all()
            and (
                ~sources.eq("DART_VIEWER")
                | body_path.eq(viewer_bonus_body_path)
            ).all()
        ),
        "snapshot_fields": bool(
            ratio_pair.all()
            and optional_positive.all()
            and admissible_report.all()
            and frame["support_action_scope"].eq("ISSUER").all()
            and action_specific.all()
        ),
        "security_classes": bool(allowed_security_classes.all()),
        "canonical_groups": all(groups is not None for groups in parsed_groups),
        "semantic_roles": bool(
            role_contract.all()
            and component_role_contract.all()
            and component_group_contract
        ),
        "manifest_row_digest": bool(manifest_parity.all()),
    }


def _cash_scale_parent_support_parity(
    evidence: pd.DataFrame,
    support: pd.DataFrame,
) -> tuple[int, bool]:
    if evidence.empty:
        return 0, support.empty
    required_parent = set(CASH_SCALE_SOURCE_EVIDENCE_COLUMNS)
    required_support = set(CASH_SCALE_SUPPORT_ACTION_COLUMNS)
    if (
        not required_parent.issubset(evidence.columns)
        or not required_support.issubset(support.columns)
        or support.empty
    ):
        return 0, False
    parent_keys = {
        (str(row.action_snapshot_run_id), str(row.evidence_key))
        for row in evidence.itertuples(index=False)
    }
    observed_child_keys = set(zip(
        support["action_snapshot_run_id"].astype(str),
        support["evidence_key"].astype(str),
        strict=True,
    ))
    if not observed_child_keys.issubset(parent_keys):
        return 0, False
    all_groups: set[str] = set()
    for parent in evidence.itertuples(index=False):
        children = support[
            support["action_snapshot_run_id"].astype(str).eq(
                str(parent.action_snapshot_run_id)
            )
            & support["evidence_key"].astype(str).eq(
                str(parent.evidence_key)
            )
        ]
        try:
            memberships: dict[str, list[int]] = {}
            child_lineage_contract = True
            for index, child in children.iterrows():
                groups = _cash_scale_support_groups(
                    child["support_semantic_group_keys"]
                )
                if (
                    str(child["target_cash_receipt_no"])
                    != str(parent.cash_receipt_no)
                    or _cash_scale_canonical_value(
                        "target_adjustment_date",
                        child["target_adjustment_date"],
                    )
                    != _cash_scale_canonical_value(
                        "target_adjustment_date",
                        parent.adjustment_trade_date,
                    )
                ):
                    child_lineage_contract = False
                source_type = (
                    str(child["support_action_source"]),
                    str(child["support_action_type"]),
                )
                if source_type == (
                    "DART_VIEWER", "bonus_issue"
                ) and not _cash_scale_viewer_bonus_group_parity(
                    parent, child, groups,
                ):
                    child_lineage_contract = False
                if source_type == (
                    "DART_VIEWER", "stock_dividend"
                ) and not _cash_scale_viewer_stock_dividend_group_parity(
                    parent, child, groups,
                ):
                    child_lineage_contract = False
                if source_type == (
                    "KRX_KIND", "paid_increase"
                ) and not _cash_scale_paid_increase_group_parity(
                    parent, child, groups,
                ):
                    child_lineage_contract = False
                if source_type in {
                    ("DART_DISCLOSURE", "ex_dividend"),
                    ("DART_DISCLOSURE", "rights_detachment"),
                    ("DART_DISCLOSURE", "combined_detachment"),
                    ("KRX_KIND", "ex_dividend"),
                    ("KRX_KIND", "rights_detachment"),
                    ("KRX_KIND", "combined_detachment"),
                } and (
                    _cash_scale_canonical_value(
                        "support_ex_date", child["support_ex_date"],
                    )
                    != _cash_scale_canonical_value(
                        "adjustment_trade_date",
                        parent.adjustment_trade_date,
                    )
                ):
                    child_lineage_contract = False
                if source_type == (
                    "DART_DISCLOSURE", "combined_detachment"
                ) and (
                    not _cash_scale_decimal_equal(
                        child["support_reference_price"],
                        parent.raw_reference_price,
                        places=8,
                    )
                    or "무상증자" not in str(child["support_reason"] or "")
                    or "배당" not in str(child["support_reason"] or "")
                ):
                    child_lineage_contract = False
                if source_type in {
                    ("KRX_KIND", "ex_dividend"),
                    ("KRX_KIND", "rights_detachment"),
                    ("KRX_KIND", "combined_detachment"),
                }:
                    compact_reason = re.sub(
                        r"\s+", "", str(child["support_reason"] or ""),
                    )
                    action_type = source_type[1]
                    reason_contract = (
                        (
                            action_type == "ex_dividend"
                            and "주식배당" in compact_reason
                            and "무상증자" not in compact_reason
                        )
                        or (
                            action_type == "rights_detachment"
                            and "무상증자" in compact_reason
                            and "주식배당" not in compact_reason
                        )
                        or (
                            action_type == "combined_detachment"
                            and "무상증자" in compact_reason
                            and "주식배당" in compact_reason
                        )
                    )
                    if (
                        child["support_semantic_role"] != "CORROBORATION"
                        or child[
                            "support_entitlement_security_class"
                        ] != "COMMON"
                        or not pd.isna(
                            child["support_distributed_security_class"]
                        )
                        or not _cash_scale_decimal_equal(
                            child["support_reference_price"],
                            parent.raw_reference_price,
                            places=8,
                        )
                        or not reason_contract
                    ):
                        child_lineage_contract = False
                if (
                    child["support_semantic_role"]
                    == "ADJUSTMENT_COMPONENT"
                    and len(groups) != 1
                ):
                    return 0, False
                for group in groups:
                    memberships.setdefault(group, []).append(index)
                    all_groups.add(group)
            group_contract = bool(memberships) and all(
                int(children.loc[indices, "support_semantic_role"].eq(
                    "ADJUSTMENT_COMPONENT"
                ).sum()) == 1
                for indices in memberships.values()
            )
            parent_contract = (
                int(parent.support_action_count) == len(children)
                and int(parent.support_semantic_group_count)
                == len(memberships)
                and str(parent.support_action_digest)
                == cash_scale_support_manifest_digest(children)
                and group_contract
                and child_lineage_contract
            )
        except (TypeError, ValueError, RuntimeError):
            return 0, False
        if not parent_contract:
            return 0, False
    return len(all_groups), True


def _cash_scale_support_action_parity(
    evidence: pd.DataFrame,
    support_rows: pd.DataFrame,
    actions: pd.DataFrame,
    receipts: pd.DataFrame,
) -> bool:
    if evidence.empty:
        return support_rows.empty
    required = {
        "asset_id", "source", "action_key", "action_type",
        "source_body_sha256",
    }
    if (
        not required.issubset(actions.columns)
        or not set(CASH_SCALE_SUPPORT_ACTION_COLUMNS).issubset(
            support_rows.columns
        )
        or not {"receipt_no", "record_date"}.issubset(receipts.columns)
    ):
        return False
    keys = ["asset_id", "source", "action_key", "action_type"]
    if actions.duplicated(keys).any():
        return False
    action_index = actions.set_index(keys, drop=False)
    parent_index = evidence.assign(
        _run=evidence["action_snapshot_run_id"].astype(str),
        _key=evidence["evidence_key"].astype(str),
    ).set_index(["_run", "_key"])
    receipt_index = receipts.assign(
        _receipt=receipts["receipt_no"].astype(str),
    ).set_index("_receipt")
    for row in evidence.itertuples(index=False):
        cash_key = (
            int(row.asset_id),
            "DART_DISCLOSURE",
            str(row.cash_receipt_no),
            "cash_dividend",
        )
        if cash_key not in action_index.index:
            return False
        cash = action_index.loc[cash_key]
        if isinstance(cash, pd.DataFrame):
            return False
        if str(cash["source_body_sha256"]) != str(row.cash_action_body_sha256):
            return False
    for row in support_rows.itertuples(index=False):
        parent_key = (
            str(row.action_snapshot_run_id), str(row.evidence_key),
        )
        if parent_key not in parent_index.index:
            return False
        parent = parent_index.loc[parent_key]
        if isinstance(parent, pd.DataFrame):
            return False
        if (
            str(row.target_cash_receipt_no)
            != str(parent["cash_receipt_no"])
            or _cash_scale_canonical_value(
                "target_adjustment_date", row.target_adjustment_date,
            )
            != _cash_scale_canonical_value(
                "target_adjustment_date", parent["adjustment_trade_date"],
            )
        ):
            return False
        body_path = str(row.support_action_body_path)
        receipt = str(row.support_action_key)
        ticker = str(parent["ticker"])
        if row.support_action_source == "DART_DISCLOSURE":
            expected_body_path = (
                "corporate_actions/dart/documents/"
                f"year={receipt[:4]}/corp={ticker}/rcept={receipt}.zip"
            )
            if body_path != expected_body_path:
                return False
        elif row.support_action_source == "DART_STRUCTURED":
            expected_body_path = (
                "corporate_actions/dart/structured/event=bonus_issue/"
                f"year={receipt[:4]}/corp={ticker}/rcept={receipt}.json"
            )
            if body_path != expected_body_path:
                return False
        elif row.support_action_source == "DART_VIEWER":
            expected_body_path = (
                "corporate_actions/dart/support_action_families/objects/"
                f"sha256={row.support_action_body_sha256}.html"
            )
            if body_path != expected_body_path:
                return False
        elif row.support_action_source == "KRX_KIND":
            expected_body_path = (
                "corporate_actions/krx/kind/body_objects/sha256="
                f"{row.support_action_body_sha256}.html"
            )
            if body_path != expected_body_path:
                return False
        else:
            return False
        support_key = (
            int(parent["asset_id"]), str(row.support_action_source),
            str(row.support_action_key), str(row.support_action_type),
        )
        if support_key not in action_index.index:
            return False
        action = action_index.loc[support_key]
        if isinstance(action, pd.DataFrame):
            return False
        if str(action["source_body_sha256"]) != str(
            row.support_action_body_sha256
        ):
            return False
        for evidence_field, action_field in (
            ("support_announcement_date", "announcement_date"),
            ("support_ex_date", "ex_date"),
            ("support_record_date", "record_date"),
            ("support_ratio_numerator", "ratio_numerator"),
            ("support_ratio_denominator", "ratio_denominator"),
            ("support_expected_price_factor", "expected_price_factor"),
            ("support_report_name", "report_name"),
            ("support_action_scope", "action_scope"),
        ):
            if _cash_scale_canonical_value(
                evidence_field, getattr(row, evidence_field)
            ) != _cash_scale_canonical_value(
                evidence_field, action[action_field]
            ):
                return False
        if (
            row.support_action_type == "stock_dividend"
            and row.support_action_source != "DART_VIEWER"
        ):
            receipt_no = str(parent["cash_receipt_no"])
            if receipt_no not in receipt_index.index:
                return False
            receipt = receipt_index.loc[receipt_no]
            if isinstance(receipt, pd.DataFrame) or (
                _cash_scale_canonical_value(
                    "support_record_date", row.support_record_date,
                )
                != _cash_scale_canonical_value(
                    "support_record_date", receipt["record_date"],
                )
            ):
                return False
        if row.support_action_type == "combined_detachment" and not (
            _cash_scale_decimal_equal(
                row.support_reference_price, parent["raw_reference_price"],
                places=8,
            )
        ):
            return False
    return True


def _cash_scale_decimal_equal(
    left: object,
    right: object,
    *,
    places: int = 12,
) -> bool:
    try:
        quantum = Decimal(1).scaleb(-places)
        return Decimal(str(left)).quantize(
            quantum, rounding=ROUND_HALF_UP,
        ) == Decimal(
            str(right)
        ).quantize(quantum, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return False


def _cash_scale_adjusted_cash(
    raw_cash_amount: object,
    selected_cash_scale: object,
) -> Decimal:
    """Mirror PostgreSQL NUMERIC(28,12) scale then NUMERIC(28,8) cash."""
    try:
        raw_cash = Decimal(str(raw_cash_amount))
        selected_scale = Decimal(str(selected_cash_scale)).quantize(
            Decimal("0.000000000001"), rounding=ROUND_HALF_UP,
        )
        adjusted_cash = (raw_cash * selected_scale).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid cash-scale adjusted-cash inputs") from exc
    if not raw_cash.is_finite() or not selected_scale.is_finite():
        raise ValueError("cash-scale adjusted-cash inputs must be finite")
    return adjusted_cash


def _cash_scale_ratio_equal(
    scale: object,
    adjusted: object,
    raw: object,
) -> bool:
    try:
        denominator = Decimal(str(raw))
        if denominator <= 0:
            return False
        ratio = Decimal(str(adjusted)) / denominator
    except (ArithmeticError, TypeError, ValueError):
        return False
    return _cash_scale_decimal_equal(scale, ratio)


def _cash_scale_stored_scale_interval(
    *, close: float, adjusted_close: float,
) -> tuple[float, float]:
    """Return the exact scale interval implied by a 4dp stored adj_close."""
    if not all(
        math.isfinite(value) and value > 0
        for value in (close, adjusted_close)
    ):
        raise ValueError("stored price scale inputs must be positive")
    low = (adjusted_close - 0.00005) / close
    high = (adjusted_close + 0.00005) / close
    ulp = max(math.ulp(low), math.ulp(high))
    return low - ulp, high + ulp


def _cash_scale_stored_scale_parity(
    scale: object,
    adjusted: object,
    raw: object,
) -> bool:
    """Bind NUMERIC(28,12) scale to the interval implied by 4dp price data."""
    try:
        observed = float(scale)
        low, high = _cash_scale_stored_scale_interval(
            close=float(raw), adjusted_close=float(adjusted),
        )
    except (ArithmeticError, TypeError, ValueError):
        return False
    return math.isfinite(observed) and low <= observed <= high


def _cash_scale_stored_factor_interval(
    *,
    previous_close: float,
    previous_adj_close: float,
    applied_close: float,
    applied_adj_close: float,
) -> tuple[float, float]:
    previous_low, previous_high = _cash_scale_stored_scale_interval(
        close=previous_close, adjusted_close=previous_adj_close,
    )
    applied_low, applied_high = _cash_scale_stored_scale_interval(
        close=applied_close, adjusted_close=applied_adj_close,
    )
    low = previous_low / applied_high
    high = previous_high / applied_low
    ulp = max(math.ulp(low), math.ulp(high))
    return low - ulp, high + ulp


def _cash_scale_resolution_source_parity(
    resolutions: pd.DataFrame,
    sources: pd.DataFrame,
) -> tuple[int, bool]:
    required_resolution = set(CASH_SCALE_RESOLUTION_DIGEST_COLUMNS)
    required_source = set(CASH_SCALE_SOURCE_EVIDENCE_COLUMNS)
    if (
        not required_resolution.issubset(resolutions.columns)
        or not required_source.issubset(sources.columns)
    ):
        return 0, False
    stable = resolutions[~resolutions["scale_change_detected"].fillna(False)]
    stable_has_evidence = (
        stable["scale_evidence_action_snapshot_run_id"].notna().any()
        or stable["scale_evidence_key"].notna().any()
    )
    changed = resolutions[
        resolutions["scale_change_detected"].fillna(False).astype(bool)
    ]
    if changed.empty:
        return 0, bool(sources.empty and not stable_has_evidence)
    if stable_has_evidence or sources.empty:
        return 0, False
    source_keys = ["action_snapshot_run_id", "evidence_key"]
    if sources.duplicated(source_keys).any():
        return 0, False
    source_index = sources.assign(
        _run=sources["action_snapshot_run_id"].astype(str),
        _key=sources["evidence_key"].astype(str),
    ).set_index(["_run", "_key"])
    consumed: list[tuple[str, str]] = []
    matched = 0
    for row in changed.itertuples(index=False):
        if (
            pd.isna(row.scale_evidence_action_snapshot_run_id)
            or pd.isna(row.scale_evidence_key)
        ):
            continue
        key = (
            str(row.scale_evidence_action_snapshot_run_id),
            str(row.scale_evidence_key),
        )
        if key not in source_index.index:
            continue
        source = source_index.loc[key]
        if isinstance(source, pd.DataFrame):
            continue
        try:
            identity_matches = (
                int(source["asset_id"]) == int(row.asset_id)
                and str(source["cash_receipt_no"]) == str(row.action_key)
                and pd.Timestamp(source["previous_trade_date"]).date()
                == pd.Timestamp(row.previous_trade_date).date()
                and pd.Timestamp(source["adjustment_trade_date"]).date()
                == pd.Timestamp(row.applied_trade_date).date()
            )
        except (TypeError, ValueError):
            identity_matches = False
        value_matches = (
            str(source["cash_scale_basis"])
            == str(row.cash_adjustment_scale_basis)
            == "PRE_EVENT_PRICE_SCALE"
            and _cash_scale_decimal_equal(
                source["raw_previous_close"], row.previous_close, places=8,
            )
            and _cash_scale_decimal_equal(
                source["raw_applied_close"], row.applied_close, places=8,
            )
            and _cash_scale_decimal_equal(
                source["expected_price_factor"],
                row.scale_price_factor_reference,
            )
        )
        if identity_matches and value_matches:
            consumed.append(key)
            matched += 1
    return matched, bool(
        matched == len(changed) == len(sources)
        and len(set(consumed)) == len(consumed)
        and set(consumed) == set(source_index.index.tolist())
    )


def _cash_scale_resolution_cash_action_parity(
    resolutions: pd.DataFrame,
    actions: pd.DataFrame,
) -> bool:
    required_actions = {
        "asset_id", "source", "action_key", "action_type", "cash_amount",
    }
    if (
        resolutions.empty
        or not set(CASH_SCALE_RESOLUTION_DIGEST_COLUMNS).issubset(
            resolutions.columns
        )
        or not required_actions.issubset(actions.columns)
    ):
        return False
    cash = actions[actions["action_type"].eq("cash_dividend")]
    keys = ["asset_id", "source", "action_key"]
    if cash.duplicated(keys).any():
        return False
    cash_index = cash.set_index(keys, drop=False)
    for row in resolutions.itertuples(index=False):
        key = (int(row.asset_id), str(row.source), str(row.action_key))
        if key not in cash_index.index:
            return False
        action = cash_index.loc[key]
        if isinstance(action, pd.DataFrame) or not _cash_scale_decimal_equal(
            row.raw_cash_amount, action["cash_amount"], places=8,
        ):
            return False
    return True


def _cash_scale_resolution_semantic_checks(
    frame: pd.DataFrame,
) -> dict[str, bool]:
    required = set(CASH_SCALE_RESOLUTION_DIGEST_COLUMNS) | {
        "resolved_ex_date", "raw_cash_amount", "adjusted_cash_amount",
    }
    if not required.issubset(frame.columns) or frame.empty:
        return {"required_nonempty_rows": False}
    asset_ids = pd.to_numeric(frame["asset_id"], errors="coerce")
    previous_dates = pd.to_datetime(
        frame["previous_trade_date"], errors="coerce",
    )
    applied_dates = pd.to_datetime(
        frame["applied_trade_date"], errors="coerce",
    )
    resolved_dates = pd.to_datetime(
        frame["resolved_ex_date"], errors="coerce",
    )
    numeric_columns = (
        "raw_cash_amount", "adjusted_cash_amount",
        "previous_close", "previous_adj_close", "applied_close",
        "applied_adj_close", "previous_price_scale",
        "applied_price_scale", "selected_cash_scale",
        "scale_price_factor_observed", "scale_price_factor_reference",
    )
    numeric = {
        column: pd.to_numeric(frame[column], errors="coerce")
        for column in numeric_columns
    }
    positive = pd.Series(True, index=frame.index)
    for values in numeric.values():
        positive &= values.notna() & values.gt(0) & values.map(math.isfinite)
    previous_scale_parity = pd.Series([
        _cash_scale_stored_scale_parity(
            row.previous_price_scale,
            row.previous_adj_close,
            row.previous_close,
        )
        for row in frame.itertuples(index=False)
    ], index=frame.index)
    applied_scale_parity = pd.Series([
        _cash_scale_stored_scale_parity(
            row.applied_price_scale,
            row.applied_adj_close,
            row.applied_close,
        )
        for row in frame.itertuples(index=False)
    ], index=frame.index)
    changed = frame["scale_change_detected"].fillna(False).astype(bool)
    stable = ~changed
    classification_parity: list[bool] = []
    selected_scale_parity: list[bool] = []
    observed_factor_parity: list[bool] = []
    reference_factor_parity: list[bool] = []
    adjusted_cash_parity: list[bool] = []
    for row in frame.itertuples(index=False):
        try:
            previous_close = float(row.previous_close)
            applied_close = float(row.applied_close)
            previous_scale = float(row.previous_adj_close) / previous_close
            applied_scale = float(row.applied_adj_close) / applied_close
            previous_low, previous_high = (
                _cash_scale_stored_scale_interval(
                    close=previous_close,
                    adjusted_close=float(row.previous_adj_close),
                )
            )
            applied_low, applied_high = _cash_scale_stored_scale_interval(
                close=applied_close,
                adjusted_close=float(row.applied_adj_close),
            )
            expected_changed = not (
                previous_low <= applied_high
                and applied_low <= previous_high
            )
            observed = previous_scale / applied_scale
            factor_low, factor_high = _cash_scale_stored_factor_interval(
                previous_close=previous_close,
                previous_adj_close=float(row.previous_adj_close),
                applied_close=applied_close,
                applied_adj_close=float(row.applied_adj_close),
            )
            exact_applied_ex_date = (
                pd.Timestamp(row.applied_trade_date).normalize()
                == pd.Timestamp(row.resolved_ex_date).normalize()
            )
            selected = (
                previous_scale
                if expected_changed or not exact_applied_ex_date
                else applied_scale
            )
            expected_adjusted_cash = _cash_scale_adjusted_cash(
                row.raw_cash_amount,
                row.selected_cash_scale,
            )
            reference_ok = (
                abs(float(row.scale_price_factor_reference) - 1.0)
                <= 5e-13
                if not expected_changed
                else factor_low
                <= float(row.scale_price_factor_reference)
                <= factor_high
            )
        except (ArithmeticError, TypeError, ValueError):
            classification_parity.append(False)
            selected_scale_parity.append(False)
            observed_factor_parity.append(False)
            reference_factor_parity.append(False)
            adjusted_cash_parity.append(False)
            continue
        classification_parity.append(
            bool(row.scale_change_detected) == bool(expected_changed)
        )
        selected_scale_parity.append(
            _cash_scale_decimal_equal(row.selected_cash_scale, selected)
        )
        observed_factor_parity.append(
            _cash_scale_decimal_equal(row.scale_price_factor_observed, observed)
        )
        reference_factor_parity.append(reference_ok)
        try:
            actual_adjusted_cash = Decimal(
                str(row.adjusted_cash_amount)
            ).quantize(
                Decimal("0.00000001"), rounding=ROUND_HALF_UP,
            )
        except (InvalidOperation, TypeError, ValueError):
            actual_adjusted_cash = None
        adjusted_cash_parity.append(
            actual_adjusted_cash == expected_adjusted_cash
        )
    stable_contract = (
        frame.loc[stable, "cash_adjustment_scale_basis"]
        .eq("STABLE_PRICE_SCALE").all()
        and frame.loc[
            stable, "scale_evidence_action_snapshot_run_id"
        ].isna().all()
        and frame.loc[stable, "scale_evidence_key"].isna().all()
    )
    changed_contract = (
        frame.loc[changed, "cash_adjustment_scale_basis"]
        .eq("PRE_EVENT_PRICE_SCALE").all()
        and frame.loc[
            changed, "scale_evidence_action_snapshot_run_id"
        ].notna().all()
        and frame.loc[changed, "scale_evidence_key"].notna().all()
        and all(
            _cash_scale_decimal_equal(selected, previous)
            for selected, previous in zip(
                frame.loc[changed, "selected_cash_scale"],
                frame.loc[changed, "previous_price_scale"],
                strict=True,
            )
        )
    )
    return {
        "required_nonempty_rows": True,
        "identity": bool(
            asset_ids.notna().all()
            and asset_ids.mod(1).eq(0).all()
            and asset_ids.gt(0).all()
            and frame["source"].astype("string").str.strip().ne("").all()
            and frame["action_key"].astype("string").str.strip().ne("").all()
            and not frame.duplicated([
                "asset_id", "source", "action_key",
            ]).any()
        ),
        "resolution_version": bool(
            frame["resolution_version"].eq(
                TOTAL_RETURN_RESOLUTION_VERSION
            ).all()
        ),
        "date_order": bool(
            previous_dates.notna().all()
            and applied_dates.notna().all()
            and resolved_dates.notna().all()
            and previous_dates.lt(applied_dates).all()
        ),
        "positive_numeric_fields": bool(positive.all()),
        "stored_price_scale_parity": bool(
            previous_scale_parity.all() and applied_scale_parity.all()
        ),
        "scale_change_classification": all(classification_parity),
        "selected_cash_scale": all(selected_scale_parity),
        "observed_price_factor": all(observed_factor_parity),
        "reference_price_factor": all(reference_factor_parity),
        "adjusted_cash_uses_selected_scale": all(adjusted_cash_parity),
        "boolean_decisions": bool(
            frame["scale_change_detected"].notna().all()
            and frame["scale_price_factor_parity"].notna().all()
            and frame["scale_price_factor_parity"].astype(bool).all()
        ),
        "stable_basis_contract": bool(stable_contract),
        "changed_basis_contract": bool(changed_contract),
    }


def total_return_asset_identity_evidence(frame: pd.DataFrame) -> dict[str, Any]:
    """Recompute TeamAlpha's PIT ticker-episode digest independently."""
    required = {"asset_id", "identifier", "valid_from", "valid_to"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(
            f"총수익 asset identity 필수 컬럼 누락: {sorted(missing)}"
        )
    if frame.empty:
        raise RuntimeError("총수익 asset identity episode가 없습니다")
    scoped = frame.loc[:, [
        "asset_id", "identifier", "valid_from", "valid_to",
    ]].copy()
    scoped["asset_id"] = pd.to_numeric(scoped["asset_id"], errors="coerce")
    if (
        scoped["asset_id"].isna().any()
        or scoped["asset_id"].mod(1).ne(0).any()
        or scoped["asset_id"].lt(0).any()
    ):
        raise RuntimeError("총수익 asset identity의 asset_id가 잘못되었습니다")
    scoped["asset_id"] = scoped["asset_id"].astype("int64")
    invalid_identifier = scoped["identifier"].map(
        lambda value: not isinstance(value, str) or not value
    )
    if invalid_identifier.any():
        raise RuntimeError("총수익 asset identity의 ticker가 비었습니다")
    scoped["valid_from"] = pd.to_datetime(
        scoped["valid_from"], errors="coerce",
    )
    scoped["valid_to"] = pd.to_datetime(scoped["valid_to"], errors="coerce")
    if scoped["valid_from"].isna().any():
        raise RuntimeError("총수익 asset identity의 valid_from이 잘못되었습니다")
    if scoped.duplicated([
        "asset_id", "identifier", "valid_from", "valid_to",
    ]).any():
        raise RuntimeError("총수익 asset identity episode가 중복되었습니다")
    scoped = scoped.sort_values(
        ["asset_id", "identifier", "valid_from", "valid_to"],
        kind="mergesort", na_position="last",
    )
    digest = hashlib.sha256()
    for row in scoped.itertuples(index=False):
        canonical = [
            int(row.asset_id),
            str(row.identifier),
            pd.Timestamp(row.valid_from).date().isoformat(),
            (
                None
                if pd.isna(row.valid_to)
                else pd.Timestamp(row.valid_to).date().isoformat()
            ),
        ]
        digest.update(json.dumps(
            canonical,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"))
        digest.update(b"\n")
    return {
        "contract": TOTAL_RETURN_ASSET_IDENTITY_CONTRACT,
        "digest": digest.hexdigest(),
        "row_count": int(len(scoped)),
        "asset_count": int(scoped["asset_id"].nunique()),
    }


def _validate_total_return_contract(
    contract: pd.DataFrame,
    schema_audit: pd.DataFrame,
    scope_audit: pd.DataFrame,
    action_audit: pd.DataFrame,
    resolution_audit: pd.DataFrame,
    identity_rows: pd.DataFrame,
    source_receipt_rows: pd.DataFrame,
    published_action_rows: pd.DataFrame,
    cash_scale_source_rows: pd.DataFrame,
    cash_scale_support_rows: pd.DataFrame,
    cash_scale_resolution_rows: pd.DataFrame,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Authenticate the complete derived-return lineage or fail closed."""
    row = _one_row(contract, label="KRX total_return_close 계약")
    schema = _one_row(schema_audit, label="총수익 schema audit")
    scope = _one_row(scope_audit, label="총수익 price scope audit")
    action = _one_row(action_audit, label="DART action snapshot audit")
    resolution = _one_row(
        resolution_audit, label="배당 resolution audit",
    )

    expected_header = {
        "source": "KRX",
        "asset_type": "stock",
        "field_name": "total_return_close",
        "methodology_version": TOTAL_RETURN_METHOD,
        "dividend_treatment": TOTAL_RETURN_DIVIDEND_TREATMENT,
        "status": "CERTIFIED",
    }
    header_mismatches = {
        key: {"expected": expected, "actual": row.get(key)}
        for key, expected in expected_header.items()
        if row.get(key) != expected
    }
    if header_mismatches or pd.isna(row.get("certified_at")):
        raise RuntimeError(
            "Silver 총수익 계약 header가 인증 기준과 다릅니다: "
            f"{header_mismatches or {'certified_at': row.get('certified_at')}}"
        )
    run_id = str(row.get("quality_run_id") or "")
    if not run_id:
        raise RuntimeError("Silver 총수익 계약 quality_run_id가 없습니다")
    coverage_start = _date_value(
        row.get("coverage_start"), label="총수익 coverage_start",
    )
    coverage_end = _date_value(
        row.get("coverage_end"), label="총수익 coverage_end",
    )
    if coverage_end < coverage_start:
        raise RuntimeError("Silver 총수익 계약 coverage가 역전되었습니다")
    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("Silver 총수익 계약 metadata가 JSON object가 아닙니다")

    schema_checks = {
        key: bool(schema.get(key))
        for key in (
            "has_total_return_lineage",
            "has_dividend_resolution",
            "has_action_snapshot_contract",
            "has_dividend_source_receipt",
            "has_cash_scale_source_evidence",
            "has_cash_scale_support_action",
            "has_resolution_scale_columns",
            "has_resolution_v2_scale_check",
            "has_action_corp_cls_provenance",
            "has_cash_scale_support_source_type_check",
            "has_cash_scale_support_role_semantics_check",
        )
    }
    resolution_pk_columns = schema.get("resolution_pk_columns")
    if isinstance(resolution_pk_columns, tuple):
        resolution_pk_columns = list(resolution_pk_columns)
    schema_checks["append_only_resolution_pk"] = resolution_pk_columns == [
        "quality_run_id", "asset_id", "source", "action_key",
        "resolution_version",
    ]
    source_receipt_pk_columns = schema.get("source_receipt_pk_columns")
    if isinstance(source_receipt_pk_columns, tuple):
        source_receipt_pk_columns = list(source_receipt_pk_columns)
    schema_checks["append_only_source_receipt_pk"] = (
        source_receipt_pk_columns == ["quality_run_id", "receipt_no"]
    )
    cash_scale_source_pk_columns = schema.get(
        "cash_scale_source_pk_columns"
    )
    if isinstance(cash_scale_source_pk_columns, tuple):
        cash_scale_source_pk_columns = list(cash_scale_source_pk_columns)
    schema_checks["append_only_cash_scale_source_pk"] = (
        cash_scale_source_pk_columns
        == ["action_snapshot_run_id", "evidence_key"]
    )
    cash_scale_source_unique_columns = schema.get(
        "cash_scale_source_unique_columns"
    )
    if isinstance(cash_scale_source_unique_columns, tuple):
        cash_scale_source_unique_columns = list(
            cash_scale_source_unique_columns
        )
    schema_checks["cash_scale_source_unique_cash_date"] = (
        cash_scale_source_unique_columns == [
            "action_snapshot_run_id", "asset_id", "cash_receipt_no",
            "adjustment_trade_date",
        ]
    )
    source_parent_identity_unique = schema.get(
        "cash_scale_source_parent_identity_unique_columns"
    )
    if isinstance(source_parent_identity_unique, tuple):
        source_parent_identity_unique = list(source_parent_identity_unique)
    schema_checks["cash_scale_source_parent_identity_unique"] = (
        source_parent_identity_unique == [
            "action_snapshot_run_id", "evidence_key", "cash_receipt_no",
            "adjustment_trade_date",
        ]
    )
    source_snapshot_fk = schema.get(
        "cash_scale_source_snapshot_fk_columns"
    )
    if isinstance(source_snapshot_fk, tuple):
        source_snapshot_fk = list(source_snapshot_fk)
    schema_checks["cash_scale_source_snapshot_fk"] = (
        source_snapshot_fk == ["action_snapshot_run_id"]
    )
    source_receipt_fk = schema.get(
        "cash_scale_source_receipt_fk_columns"
    )
    if isinstance(source_receipt_fk, tuple):
        source_receipt_fk = list(source_receipt_fk)
    schema_checks["cash_scale_source_receipt_fk"] = (
        source_receipt_fk
        == ["action_snapshot_run_id", "cash_receipt_no"]
    )
    cash_scale_source_columns = schema.get("cash_scale_source_columns")
    if isinstance(cash_scale_source_columns, tuple):
        cash_scale_source_columns = list(cash_scale_source_columns)
    schema_checks["cash_scale_source_exact_columns"] = (
        cash_scale_source_columns
        == [*CASH_SCALE_SOURCE_EVIDENCE_COLUMNS, "recorded_at"]
    )
    cash_scale_support_columns = schema.get("cash_scale_support_columns")
    if isinstance(cash_scale_support_columns, tuple):
        cash_scale_support_columns = list(cash_scale_support_columns)
    schema_checks["cash_scale_support_exact_columns"] = (
        cash_scale_support_columns
        == [*CASH_SCALE_SUPPORT_ACTION_COLUMNS, "recorded_at"]
    )
    cash_scale_support_pk_columns = schema.get(
        "cash_scale_support_pk_columns"
    )
    if isinstance(cash_scale_support_pk_columns, tuple):
        cash_scale_support_pk_columns = list(
            cash_scale_support_pk_columns
        )
    schema_checks["append_only_cash_scale_support_pk"] = (
        cash_scale_support_pk_columns == [
            "action_snapshot_run_id", "evidence_key",
            "support_action_source", "support_action_key",
            "support_action_type",
        ]
    )
    cash_scale_support_parent_fk_columns = schema.get(
        "cash_scale_support_parent_fk_columns"
    )
    if isinstance(cash_scale_support_parent_fk_columns, tuple):
        cash_scale_support_parent_fk_columns = list(
            cash_scale_support_parent_fk_columns
        )
    schema_checks["cash_scale_support_parent_fk"] = (
        cash_scale_support_parent_fk_columns
        == ["action_snapshot_run_id", "evidence_key"]
    )
    support_parent_identity_fk = schema.get(
        "cash_scale_support_parent_identity_fk_columns"
    )
    if isinstance(support_parent_identity_fk, tuple):
        support_parent_identity_fk = list(support_parent_identity_fk)
    schema_checks["cash_scale_support_parent_identity_fk"] = (
        support_parent_identity_fk == [
            "action_snapshot_run_id", "evidence_key",
            "target_cash_receipt_no", "target_adjustment_date",
        ]
    )
    support_parent_identity_fk_target = schema.get(
        "cash_scale_support_parent_identity_fk_target_columns"
    )
    if isinstance(support_parent_identity_fk_target, tuple):
        support_parent_identity_fk_target = list(
            support_parent_identity_fk_target
        )
    schema_checks["cash_scale_support_parent_identity_fk_target"] = (
        support_parent_identity_fk_target == [
            "action_snapshot_run_id", "evidence_key", "cash_receipt_no",
            "adjustment_trade_date",
        ]
    )
    support_quality_fk = schema.get(
        "cash_scale_support_quality_fk_columns"
    )
    if isinstance(support_quality_fk, tuple):
        support_quality_fk = list(support_quality_fk)
    schema_checks["cash_scale_support_quality_fk"] = (
        support_quality_fk == ["support_action_quality_run_id"]
    )
    resolution_scale_fk_columns = schema.get("resolution_scale_fk_columns")
    if isinstance(resolution_scale_fk_columns, tuple):
        resolution_scale_fk_columns = list(resolution_scale_fk_columns)
    schema_checks["resolution_scale_source_fk"] = (
        resolution_scale_fk_columns == [
            "scale_evidence_action_snapshot_run_id", "scale_evidence_key",
        ]
    )
    if not all(schema_checks.values()):
        raise RuntimeError(
            f"Silver 총수익 schema가 append-only 계약을 충족하지 않습니다: {schema_checks}"
        )

    certified_scope = metadata.get("certified_scope")
    expected_scope = {
        "source": "KRX",
        "asset_type": "stock",
        "instrument_type": "common_stock",
        "markets": ["KOSPI", "KOSDAQ"],
        "coverage_start": TOTAL_RETURN_SCOPE_START.isoformat(),
    }
    if certified_scope != expected_scope:
        raise RuntimeError(
            "Silver 총수익 certified_scope가 2015+ KRX common_stock 계약과 "
            f"다릅니다: {certified_scope!r}"
        )
    if metadata.get("contract_release") != TOTAL_RETURN_CONTRACT_RELEASE:
        raise RuntimeError(
            "Silver 총수익 contract_release가 현재 계약과 다릅니다: "
            f"{metadata.get('contract_release')!r}"
        )
    if metadata.get("input_scope") != TOTAL_RETURN_INPUT_SCOPE:
        raise RuntimeError(
            f"Silver 총수익 input_scope가 다릅니다: {metadata.get('input_scope')!r}"
        )
    if metadata.get("research_role") != TOTAL_RETURN_RESEARCH_ROLE:
        raise RuntimeError(
            "Silver 총수익 research_role이 label-only 계약과 다릅니다: "
            f"{metadata.get('research_role')!r}"
        )

    observed_price_rows = int(scope.get("price_row_count") or 0)
    observed_assets = int(scope.get("asset_count") or 0)
    if observed_price_rows < 1 or observed_assets < 1:
        raise RuntimeError("2015+ KRX common_stock 총수익 scope가 비었습니다")
    scope_start = _date_value(
        scope.get("coverage_start"), label="관측 총수익 coverage_start",
    )
    scope_end = _date_value(
        scope.get("coverage_end"), label="관측 총수익 coverage_end",
    )
    price_checks = {
        "contract_starts_at_first_trade": coverage_start == scope_start,
        "contract_reaches_latest_price": coverage_end == scope_end,
        "raw_price_lineage_certified": (
            int(scope.get("raw_certified_row_count") or 0)
            == observed_price_rows
        ),
        "total_return_run_parity": (
            int(scope.get("total_return_run_row_count") or 0)
            == observed_price_rows
        ),
        "positive_total_return_parity": (
            int(scope.get("positive_total_return_row_count") or 0)
            == observed_price_rows
        ),
        "one_total_return_run": int(scope.get("total_return_run_count") or 0) == 1,
        "total_return_run_certified": scope.get("total_return_run_status") == "CERTIFIED",
        "total_return_run_mode": (
            scope.get("total_return_run_mode") == TOTAL_RETURN_REBUILD_MODE
        ),
        "metadata_price_rows": (
            _positive_metadata_int(metadata, "price_row_count", label="metadata")
            == observed_price_rows
        ),
        "metadata_assets": (
            _positive_metadata_int(metadata, "asset_count", label="metadata")
            == observed_assets
        ),
    }
    parity = metadata.get("per_row_run_parity")
    price_checks["declared_per_row_parity"] = (
        isinstance(parity, dict)
        and parity.get("quality_field") == "total_return_quality_run_id"
        and parity.get("passed") is True
        and parity.get("expected") == observed_price_rows
        and parity.get("actual") == observed_price_rows
    )
    if not all(price_checks.values()):
        raise RuntimeError(
            f"Silver 총수익 price lineage parity가 깨졌습니다: {price_checks}"
        )

    action_snapshot_run_id = str(metadata.get("action_snapshot_run_id") or "")
    action_metadata = metadata.get("action_snapshot")
    if not action_snapshot_run_id or not isinstance(action_metadata, dict):
        raise RuntimeError("Silver 총수익 계약의 DART snapshot binding이 없습니다")
    action_manifest = _sha256_text(
        action_metadata.get("manifest_sha256"),
        label="action_snapshot.manifest_sha256",
    )
    action_digest = _sha256_text(
        action_metadata.get("body_digest"),
        label="action_snapshot.body_digest",
    )
    action_body_count = _positive_metadata_int(
        action_metadata, "body_count", label="action_snapshot",
    )
    action_count = _positive_metadata_int(
        action_metadata, "action_count", label="action_snapshot",
    )
    snapshot_metadata = action.get("snapshot_metadata")
    if not isinstance(snapshot_metadata, dict):
        raise RuntimeError("Silver DART snapshot metadata가 JSON object가 아닙니다")

    action_pit_scope = action_metadata.get("pit_scope")
    snapshot_pit_scope = snapshot_metadata.get("pit_scope")
    if not isinstance(action_pit_scope, dict):
        raise RuntimeError("Silver DART snapshot PIT scope 증거가 없습니다")
    pit_input_count = _positive_metadata_int(
        action_pit_scope, "input_action_count", label="action_snapshot.pit_scope",
    )
    pit_included_count = _positive_metadata_int(
        action_pit_scope, "included_action_count", label="action_snapshot.pit_scope",
    )
    pit_excluded_count = _nonnegative_metadata_int(
        action_pit_scope, "excluded_action_count", label="action_snapshot.pit_scope",
    )
    pit_included_classes = action_pit_scope.get("included_by_corp_cls")
    pit_excluded_classes = action_pit_scope.get("excluded_by_corp_cls")
    pit_excluded_reasons = action_pit_scope.get("excluded_by_reason")

    action_source_receipts = action_metadata.get("source_receipts")
    snapshot_source_receipts = snapshot_metadata.get("source_receipts")
    action_published_actions = action_metadata.get("published_actions")
    snapshot_published_actions = snapshot_metadata.get("published_actions")
    action_cash_scale_source = action_metadata.get(
        "cash_adjustment_scale_evidence"
    )
    snapshot_cash_scale_source = snapshot_metadata.get(
        "cash_adjustment_scale_evidence"
    )
    action_disclosure_audit = action_metadata.get(
        "disclosure_observation_audit"
    )
    snapshot_disclosure_audit = snapshot_metadata.get(
        "disclosure_observation_audit"
    )
    if not all(isinstance(value, dict) for value in (
        action_source_receipts,
        action_published_actions,
        action_disclosure_audit,
        action_cash_scale_source,
    )):
        raise RuntimeError("Silver DART v5 source/action 증거 metadata가 없습니다")

    source_digest = source_receipt_digest(source_receipt_rows)
    terminal_digest = terminal_source_receipt_digest(source_receipt_rows)
    published_digest = published_action_digest(published_action_rows)
    cash_scale_source_digest = cash_scale_source_evidence_digest(
        cash_scale_source_rows
    )
    cash_scale_source_manifest_digest_value = (
        cash_scale_source_manifest_digest(cash_scale_source_rows)
    )
    cash_scale_support_digest = cash_scale_support_action_digest(
        cash_scale_support_rows
    )
    cash_scale_support_manifest_digest_value = (
        cash_scale_support_manifest_digest(cash_scale_support_rows)
    )
    source_failures = _source_receipt_semantic_failures(source_receipt_rows)
    included_receipts = source_receipt_rows.loc[
        source_receipt_rows["mapping_status"].eq("INCLUDED")
    ].copy()
    excluded_receipts = source_receipt_rows.loc[
        source_receipt_rows["mapping_status"].eq("EXCLUDED")
    ].copy()
    action_cash_parity = _action_cash_parity_frame(published_action_rows)
    receipt_parity_digest = included_cash_parity_digest(included_receipts)
    action_parity_digest = included_cash_parity_digest(action_cash_parity)

    source_total = len(source_receipt_rows)
    source_included = len(included_receipts)
    source_excluded = len(excluded_receipts)
    source_terminal = int(
        source_receipt_rows["is_terminal_economic_revision"]
        .fillna(False).astype(bool).sum()
    )
    source_terminal_pending = int((
        source_receipt_rows["is_terminal_economic_revision"]
        .fillna(False).astype(bool)
        & source_receipt_rows["cash_amount_status"].eq(
            "POSITIVE_PENDING_RECORD_DATE"
        )
    ).sum())
    source_included_classes = _corp_cls_counts(included_receipts)
    source_excluded_classes = _corp_cls_counts(excluded_receipts)
    source_exclusion_reasons = _reason_counts(excluded_receipts)
    persisted_cash_count = len(action_cash_parity)

    source_checks = {
        "metadata_binding": action_source_receipts == snapshot_source_receipts,
        "source_count": _positive_metadata_int(
            action_source_receipts,
            "source_cash_receipt_count",
            label="action_snapshot.source_receipts",
        ) == source_total,
        "unique_receipts": (
            source_receipt_rows["receipt_no"].astype(str).nunique()
            == source_total
        ),
        "partition": (
            source_total == source_included + source_excluded
            and _positive_metadata_int(
                action_source_receipts,
                "included_cash_receipt_count",
                label="action_snapshot.source_receipts",
            ) == source_included == persisted_cash_count
            and _nonnegative_metadata_int(
                action_source_receipts,
                "excluded_cash_receipt_count",
                label="action_snapshot.source_receipts",
            ) == source_excluded
        ),
        "semantic_rows": not source_failures.any(),
        "attachment_count": _nonnegative_metadata_int(
            action_source_receipts,
            "attachment_correction_count",
            label="action_snapshot.source_receipts",
        ) == int(source_receipt_rows["cash_amount_status"].eq(
            "ATTACHMENT_ONLY"
        ).sum()),
        "no_common_count": _nonnegative_metadata_int(
            action_source_receipts,
            "no_common_cash_dividend_count",
            label="action_snapshot.source_receipts",
        ) == int(source_receipt_rows["cash_amount_status"].eq(
            "NO_COMMON_CASH_DIVIDEND"
        ).sum()),
        "cancelled_count": _nonnegative_metadata_int(
            action_source_receipts,
            "withdrawn_or_cancelled_count",
            label="action_snapshot.source_receipts",
        ) == int(source_receipt_rows["cash_amount_status"].eq(
            "NO_ECONOMIC_EVENT"
        ).sum()),
        "pending_count": _nonnegative_metadata_int(
            action_source_receipts,
            "pending_record_date_count",
            label="action_snapshot.source_receipts",
        ) == int(source_receipt_rows["cash_amount_status"].eq(
            "POSITIVE_PENDING_RECORD_DATE"
        ).sum()),
        "unresolved_count": _nonnegative_metadata_int(
            action_source_receipts,
            "unresolved_cash_receipt_count",
            label="action_snapshot.source_receipts",
        ) == int(source_failures.sum()) == 0,
        "terminal_count": (
            _positive_metadata_int(
                action_source_receipts,
                "economic_decision_count",
                label="action_snapshot.source_receipts",
            ) == source_terminal
            and _positive_metadata_int(
                action_source_receipts,
                "terminal_economic_receipt_count",
                label="action_snapshot.source_receipts",
            ) == source_terminal
            and source_terminal_pending == 0
        ),
        "source_digest": (
            action_source_receipts.get("source_receipt_row_digest")
            == source_digest
        ),
        "terminal_digest": (
            action_source_receipts.get("terminal_economic_receipt_digest")
            == terminal_digest
        ),
        "corp_cls_provenance": (
            action_source_receipts.get("included_cash_receipts_by_corp_cls")
            == source_included_classes
            and action_source_receipts.get(
                "excluded_cash_receipts_by_corp_cls"
            ) == source_excluded_classes
        ),
        "exclusion_reasons": (
            action_source_receipts.get("cash_receipt_exclusion_reasons")
            == source_exclusion_reasons
            and sum(source_exclusion_reasons.values()) == source_excluded
        ),
    }
    published_checks = {
        "metadata_binding": (
            action_published_actions == snapshot_published_actions
        ),
        "published_count": _positive_metadata_int(
            action_published_actions,
            "published_action_count",
            label="action_snapshot.published_actions",
        ) == len(published_action_rows) == action_count,
        "published_digest": (
            action_published_actions.get("published_action_row_digest")
            == published_digest
        ),
        "published_scope": (
            action_published_actions.get("published_action_scope_contract")
            == "issuer_cash_ex_plus_manifest_scale_support_v1"
        ),
        "cash_parity_count": _positive_metadata_int(
            action_published_actions,
            "included_cash_action_parity_count",
            label="action_snapshot.published_actions",
        ) == persisted_cash_count,
        "cash_parity_digest": (
            receipt_parity_digest
            == action_parity_digest
            == action_published_actions.get(
                "included_cash_action_parity_digest"
            )
        ),
    }
    cash_scale_source_count = _nonnegative_metadata_int(
        action_cash_scale_source,
        "persisted_parent_row_count",
        label="action_snapshot.cash_adjustment_scale_evidence",
    )
    cash_scale_support_count = _nonnegative_metadata_int(
        action_cash_scale_source,
        "persisted_support_action_count",
        label="action_snapshot.cash_adjustment_scale_evidence",
    )
    cash_scale_support_group_count, parent_support_parity = (
        _cash_scale_parent_support_parity(
            cash_scale_source_rows, cash_scale_support_rows,
        )
    )
    cash_scale_source_semantics = _cash_scale_source_semantic_checks(
        cash_scale_source_rows,
        action_snapshot_run_id=action_snapshot_run_id,
    )
    cash_scale_support_semantics = _cash_scale_support_semantic_checks(
        cash_scale_support_rows,
        action_snapshot_run_id=action_snapshot_run_id,
    )
    cash_scale_source_checks = {
        "metadata_binding": (
            action_cash_scale_source == snapshot_cash_scale_source
        ),
        "metadata_fields": (
            set(action_cash_scale_source)
            == TOTAL_RETURN_CASH_SCALE_SOURCE_METADATA_KEYS
        ),
        "contract": (
            action_cash_scale_source.get("contract")
            == TOTAL_RETURN_CASH_SCALE_SOURCE_CONTRACT
        ),
        "manifest_sha256": (
            _sha256_text(
                action_cash_scale_source.get("manifest_sha256"),
                label=(
                    "action_snapshot.cash_adjustment_scale_evidence."
                    "manifest_sha256"
                ),
            )
            == action_cash_scale_source.get("manifest_sha256")
        ),
        "manifest_parent_count": (
            _nonnegative_metadata_int(
                action_cash_scale_source,
                "manifest_parent_row_count",
                label="action_snapshot.cash_adjustment_scale_evidence",
            )
            == len(cash_scale_source_rows)
        ),
        "manifest_parent_digest": (
            _sha256_text(
                action_cash_scale_source.get(
                    "manifest_parent_row_digest"
                ),
                label=(
                    "action_snapshot.cash_adjustment_scale_evidence."
                    "manifest_parent_row_digest"
                ),
            )
            == cash_scale_source_manifest_digest_value
        ),
        "manifest_support_count": (
            _nonnegative_metadata_int(
                action_cash_scale_source,
                "manifest_support_action_count",
                label="action_snapshot.cash_adjustment_scale_evidence",
            )
            == len(cash_scale_support_rows)
        ),
        "manifest_support_digest": (
            _sha256_text(
                action_cash_scale_source.get(
                    "manifest_support_action_digest"
                ),
                label=(
                    "action_snapshot.cash_adjustment_scale_evidence."
                    "manifest_support_action_digest"
                ),
            )
            == cash_scale_support_manifest_digest_value
        ),
        "manifest_support_groups": (
            _nonnegative_metadata_int(
                action_cash_scale_source,
                "manifest_support_semantic_group_count",
                label="action_snapshot.cash_adjustment_scale_evidence",
            )
            == cash_scale_support_group_count
        ),
        "persisted_parent_row_count": (
            cash_scale_source_count == len(cash_scale_source_rows)
        ),
        "persisted_parent_row_digest": (
            _sha256_text(
                action_cash_scale_source.get("persisted_parent_row_digest"),
                label=(
                    "action_snapshot.cash_adjustment_scale_evidence."
                    "persisted_parent_row_digest"
                ),
            )
            == cash_scale_source_digest
        ),
        "persisted_support_action_count": (
            cash_scale_support_count == len(cash_scale_support_rows)
        ),
        "persisted_support_action_digest": (
            _sha256_text(
                action_cash_scale_source.get(
                    "persisted_support_action_digest"
                ),
                label=(
                    "action_snapshot.cash_adjustment_scale_evidence."
                    "persisted_support_action_digest"
                ),
            )
            == cash_scale_support_digest
        ),
        "persisted_support_semantic_group_count": (
            _nonnegative_metadata_int(
                action_cash_scale_source,
                "persisted_support_semantic_group_count",
                label="action_snapshot.cash_adjustment_scale_evidence",
            )
            == cash_scale_support_group_count
        ),
        "changed_scale_coverage": (
            _nonnegative_metadata_int(
                action_cash_scale_source,
                "changed_scale_coverage_count",
                label="action_snapshot.cash_adjustment_scale_evidence",
            )
            == cash_scale_source_count
        ),
        "no_unresolved": (
            _nonnegative_metadata_int(
                action_cash_scale_source,
                "unresolved_count",
                label="action_snapshot.cash_adjustment_scale_evidence",
            )
            == 0
        ),
        "semantic_rows": all(cash_scale_source_semantics.values()),
        "semantic_support_rows": all(
            cash_scale_support_semantics.values()
        ),
        "parent_support_parity": parent_support_parity,
        "cash_receipt_parity": _cash_scale_receipt_parity(
            cash_scale_source_rows, source_receipt_rows,
        ),
        "support_action_parity": _cash_scale_support_action_parity(
            cash_scale_source_rows, cash_scale_support_rows,
            published_action_rows, source_receipt_rows,
        ),
    }
    action_checks = {
        "run_id": str(action.get("quality_run_id") or "") == action_snapshot_run_id,
        "schema_version": action.get("schema_version") == TOTAL_RETURN_ACTION_SNAPSHOT_SCHEMA,
        "manifest_sha256": str(action.get("manifest_sha256") or "") == action_manifest,
        "body_digest": str(action.get("body_digest") or "") == action_digest,
        "body_count": int(action.get("body_count") or 0) == action_body_count,
        "action_count": int(action.get("action_count") or 0) == action_count,
        "persisted_action_count": int(action.get("persisted_action_count") or 0) == action_count,
        "persisted_cash_action_count": int(
            action.get("persisted_cash_action_count") or 0
        ) == persisted_cash_count,
        "coverage_start": (
            _date_value(action.get("coverage_start"), label="DART snapshot coverage_start")
            == TOTAL_RETURN_SCOPE_START
            and action_metadata.get("coverage_start")
            == TOTAL_RETURN_SCOPE_START.isoformat()
        ),
        "coverage_end": (
            _date_value(action.get("coverage_end"), label="DART snapshot coverage_end")
            == _date_value(
                action_metadata.get("coverage_end"),
                label="metadata DART snapshot coverage_end",
            )
            and _date_value(action.get("coverage_end"), label="DART snapshot coverage_end")
            >= coverage_end
        ),
        "quality_run_certified": action.get("quality_run_status") == "CERTIFIED",
        "quality_run_mode": action.get("quality_run_mode") == TOTAL_RETURN_ACTION_SNAPSHOT_MODE,
        "snapshot_markets": snapshot_metadata.get("markets") == [
            "KOSPI", "KOSDAQ",
        ],
        "pit_metadata_binding": action_pit_scope == snapshot_pit_scope,
        "pit_contract": (
            action_pit_scope.get("contract")
            == TOTAL_RETURN_PIT_SCOPE_CONTRACT
        ),
        "pit_partition": (
            pit_input_count == pit_included_count + pit_excluded_count
            and pit_included_count == action_count
        ),
        "pit_corp_cls_provenance": (
            _valid_count_map(pit_included_classes)
            and _valid_count_map(pit_excluded_classes)
            and pit_included_classes
            == _corp_cls_counts(published_action_rows)
            and sum(pit_included_classes.values()) == pit_included_count
            and sum(pit_excluded_classes.values()) == pit_excluded_count
        ),
        "pit_exclusion_reasons": (
            _valid_count_map(pit_excluded_reasons)
            and sum(pit_excluded_reasons.values()) == pit_excluded_count
        ),
        "source_receipt_exact_parity": all(source_checks.values()),
        "published_action_exact_parity": all(published_checks.values()),
        "cash_scale_source_exact_parity": all(
            cash_scale_source_checks.values()
        ),
        "disclosure_observation_binding": (
            action_disclosure_audit == snapshot_disclosure_audit
            and action_disclosure_audit.get("contract")
            == TOTAL_RETURN_DISCLOSURE_OBSERVATION_CONTRACT
            and _sha256_text(
                action_disclosure_audit.get("mutable_conflict_digest"),
                label="disclosure_observation_audit.mutable_conflict_digest",
            )
            == action_disclosure_audit.get("mutable_conflict_digest")
        ),
    }
    if not all(action_checks.values()):
        raise RuntimeError(
            "Silver DART action snapshot lineage가 깨졌습니다: "
            f"action={action_checks}, source={source_checks}, "
            f"published={published_checks}, "
            f"cash_scale_source={cash_scale_source_checks}, "
            f"cash_scale_semantics={cash_scale_source_semantics}, "
            f"cash_scale_support_semantics={cash_scale_support_semantics}"
        )

    cash_action_count = _positive_metadata_int(
        metadata, "cash_action_count", label="metadata",
    )
    if cash_action_count != persisted_cash_count:
        raise RuntimeError(
            "Silver 게시 cash action과 resolution 입력 수가 다릅니다: "
            f"published={persisted_cash_count}, resolution={cash_action_count}"
        )
    applied_event_count = _positive_metadata_int(
        metadata, "applied_event_count", label="metadata",
    )
    excluded_event_count = _nonnegative_metadata_int(
        metadata, "excluded_event_count", label="metadata",
    )
    canonical_event_count = _positive_metadata_int(
        metadata, "canonical_event_count", label="metadata",
    )
    resolution_rows = int(resolution.get("resolution_row_count") or 0)
    resolution_checks = {
        "resolution_version": metadata.get("resolution_version") == TOTAL_RETURN_RESOLUTION_VERSION,
        "row_parity": resolution_rows == cash_action_count,
        "version_row_parity": int(resolution.get("expected_version_row_count") or 0) == resolution_rows,
        "applied_row_parity": int(resolution.get("applied_canonical_row_count") or 0) == applied_event_count,
        "excluded_row_parity": int(resolution.get("excluded_row_count") or 0) == excluded_event_count,
        "decision_row_parity": applied_event_count + excluded_event_count == cash_action_count,
        "no_unresolved_source_rows": int(
            resolution.get("unresolved_source_row_count") or 0
        ) == 0,
        "known_exclusion_reasons_only": int(
            resolution.get("unknown_exclusion_row_count") or 0
        ) == 0,
        "source_canonical_bounds": (
            applied_event_count <= canonical_event_count <= cash_action_count
        ),
    }
    if not all(resolution_checks.values()):
        raise RuntimeError(
            f"Silver 배당 resolution lineage가 깨졌습니다: {resolution_checks}"
        )

    cash_scale_metadata = metadata.get("cash_adjustment_scale_evidence")
    if not isinstance(cash_scale_metadata, dict):
        raise RuntimeError(
            "Silver 현금배당 스케일 resolution 증거 metadata가 없습니다"
        )
    cash_scale_resolution_digest = cash_scale_resolution_evidence_digest(
        cash_scale_resolution_rows
    )
    cash_scale_resolution_semantics = (
        _cash_scale_resolution_semantic_checks(
            cash_scale_resolution_rows
        )
    )
    scale_changed = cash_scale_resolution_rows[
        "scale_change_detected"
    ].fillna(False).astype(bool)
    cash_scale_changed_count = int(scale_changed.sum())
    cash_scale_stable_count = int((~scale_changed).sum())
    cash_scale_evidence_match_count, cash_scale_source_parity = (
        _cash_scale_resolution_source_parity(
            cash_scale_resolution_rows,
            cash_scale_source_rows,
        )
    )
    cash_scale_row_count = _positive_metadata_int(
        cash_scale_metadata,
        "row_count",
        label="metadata.cash_adjustment_scale_evidence",
    )
    cash_scale_resolution_checks = {
        "metadata_fields": (
            set(cash_scale_metadata)
            == TOTAL_RETURN_CASH_SCALE_RESOLUTION_METADATA_KEYS
        ),
        "contract": (
            cash_scale_metadata.get("contract")
            == TOTAL_RETURN_CASH_SCALE_RESOLUTION_CONTRACT
        ),
        "row_count": (
            cash_scale_row_count == len(cash_scale_resolution_rows)
            == applied_event_count
        ),
        "row_digest": (
            _sha256_text(
                cash_scale_metadata.get("row_digest"),
                label="metadata.cash_adjustment_scale_evidence.row_digest",
            )
            == cash_scale_resolution_digest
        ),
        "applied_event_count": (
            _positive_metadata_int(
                cash_scale_metadata,
                "applied_event_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
            == applied_event_count
        ),
        "stable_scale_event_count": (
            _nonnegative_metadata_int(
                cash_scale_metadata,
                "stable_scale_event_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
            == cash_scale_stable_count
        ),
        "changed_scale_event_count": (
            _nonnegative_metadata_int(
                cash_scale_metadata,
                "changed_scale_event_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
            == cash_scale_changed_count
        ),
        "partition": (
            cash_scale_stable_count + cash_scale_changed_count
            == cash_scale_row_count
        ),
        "source_coverage": (
            cash_scale_changed_count == cash_scale_source_count
        ),
        "evidence_match_count": (
            cash_scale_evidence_match_count == cash_scale_changed_count
        ),
        "no_unresolved": (
            _nonnegative_metadata_int(
                cash_scale_metadata,
                "unresolved_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
            == 0
        ),
        "resolution_parity_count": (
            _positive_metadata_int(
                cash_scale_metadata,
                "resolution_parity_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
            == cash_scale_row_count
        ),
        "adjusted_cash_parity_count": (
            _positive_metadata_int(
                cash_scale_metadata,
                "adjusted_cash_parity_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
            == cash_scale_row_count
        ),
        "explicit_exclusion_count": (
            _nonnegative_metadata_int(
                cash_scale_metadata,
                "explicit_exclusion_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
            == excluded_event_count
        ),
        "first_listing_exclusion_count": (
            0
            <= _nonnegative_metadata_int(
                cash_scale_metadata,
                "first_listing_exclusion_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
            <= excluded_event_count
        ),
        "stored_price_contract": (
            cash_scale_metadata.get("adj_close_decimal_places") == 4
            and cash_scale_metadata.get("cash_in_adj_close") is False
        ),
        "semantic_rows": all(cash_scale_resolution_semantics.values()),
        "cash_action_amount_parity": (
            _cash_scale_resolution_cash_action_parity(
                cash_scale_resolution_rows, published_action_rows,
            )
        ),
        "exact_source_parity": cash_scale_source_parity,
    }
    if not all(cash_scale_resolution_checks.values()):
        raise RuntimeError(
            "Silver 현금배당 스케일 resolution lineage가 깨졌습니다: "
            f"checks={cash_scale_resolution_checks}, "
            f"semantics={cash_scale_resolution_semantics}"
        )

    identity = total_return_asset_identity_evidence(identity_rows)
    identity_metadata = metadata.get("asset_identity")
    identity_checks = {
        key: isinstance(identity_metadata, dict)
        and identity_metadata.get(key) == value
        for key, value in identity.items()
    }
    if not all(identity_checks.values()):
        raise RuntimeError(
            "Silver 총수익 PIT asset identity binding이 현재 RDS와 "
            f"다릅니다: {identity_checks}"
        )

    source_history = metadata.get("source_price_history_metadata_only")
    source_history_start = _date_value(
        source_history.get("coverage_start") if isinstance(source_history, dict) else None,
        label="source price history coverage_start",
    )
    source_history_end = _date_value(
        source_history.get("coverage_end") if isinstance(source_history, dict) else None,
        label="source price history coverage_end",
    )
    observed_source_history_start = _date_value(
        scope.get("source_history_start"),
        label="관측 source price history coverage_start",
    )
    observed_source_history_end = _date_value(
        scope.get("source_history_end"),
        label="관측 source price history coverage_end",
    )
    if (
        not isinstance(source_history, dict)
        or source_history.get("certified_as_total_return") is not False
        or source_history.get("markets") != ["KOSPI", "KOSDAQ"]
        or source_history_start != observed_source_history_start
        or source_history_end != observed_source_history_end
        or observed_source_history_start > date(1995, 12, 31)
        or observed_source_history_end < coverage_end
    ):
        raise RuntimeError(
            "Silver 원시 가격 이력과 2015+ 총수익 인증 범위가 구분되지 않았습니다"
        )
    evidence = {
        "validation_status": "VERIFIED",
        "contract_release": TOTAL_RETURN_CONTRACT_RELEASE,
        "methodology_version": TOTAL_RETURN_METHOD,
        "dividend_treatment": TOTAL_RETURN_DIVIDEND_TREATMENT,
        "quality_run_id": run_id,
        "coverage_start": coverage_start.isoformat(),
        "coverage_end": coverage_end.isoformat(),
        "certified_scope_start": TOTAL_RETURN_SCOPE_START.isoformat(),
        "certified_markets": ["KOSPI", "KOSDAQ"],
        "price_row_count": observed_price_rows,
        "asset_count": observed_assets,
        "action_snapshot_run_id": action_snapshot_run_id,
        "action_snapshot_schema_version": TOTAL_RETURN_ACTION_SNAPSHOT_SCHEMA,
        "action_snapshot_manifest_sha256": action_manifest,
        "action_snapshot_body_digest": action_digest,
        "pit_scope_contract": TOTAL_RETURN_PIT_SCOPE_CONTRACT,
        "pit_input_action_count": pit_input_count,
        "pit_included_action_count": pit_included_count,
        "pit_excluded_action_count": pit_excluded_count,
        "source_receipt_row_count": source_total,
        "source_receipt_row_digest": source_digest,
        "terminal_economic_receipt_count": source_terminal,
        "terminal_economic_receipt_digest": terminal_digest,
        "published_action_count": len(published_action_rows),
        "published_action_row_digest": published_digest,
        "published_action_scope_contract": (
            "issuer_cash_ex_plus_manifest_scale_support_v1"
        ),
        "included_cash_action_parity_count": persisted_cash_count,
        "included_cash_action_parity_digest": action_parity_digest,
        "cash_scale_source_contract": (
            TOTAL_RETURN_CASH_SCALE_SOURCE_CONTRACT
        ),
        "cash_scale_source_evidence_count": cash_scale_source_count,
        "cash_scale_source_evidence_digest": cash_scale_source_digest,
        "cash_scale_source_manifest_sha256": (
            action_cash_scale_source["manifest_sha256"]
        ),
        "cash_scale_source_manifest_digest": (
            cash_scale_source_manifest_digest_value
        ),
        "cash_scale_support_action_count": cash_scale_support_count,
        "cash_scale_support_action_digest": cash_scale_support_digest,
        "cash_scale_support_manifest_digest": (
            cash_scale_support_manifest_digest_value
        ),
        "cash_scale_support_semantic_group_count": (
            cash_scale_support_group_count
        ),
        "disclosure_observation_contract": (
            TOTAL_RETURN_DISCLOSURE_OBSERVATION_CONTRACT
        ),
        "disclosure_mutable_conflict_digest": (
            action_disclosure_audit["mutable_conflict_digest"]
        ),
        "research_role": dict(TOTAL_RETURN_RESEARCH_ROLE),
        "resolution_version": TOTAL_RETURN_RESOLUTION_VERSION,
        "cash_action_count": cash_action_count,
        "canonical_event_count": canonical_event_count,
        "applied_event_count": applied_event_count,
        "excluded_event_count": excluded_event_count,
        "cash_scale_resolution_contract": (
            TOTAL_RETURN_CASH_SCALE_RESOLUTION_CONTRACT
        ),
        "cash_scale_resolution_row_count": cash_scale_row_count,
        "cash_scale_resolution_row_digest": (
            cash_scale_resolution_digest
        ),
        "cash_scale_stable_event_count": cash_scale_stable_count,
        "cash_scale_changed_event_count": cash_scale_changed_count,
        "cash_scale_evidence_match_count": (
            cash_scale_evidence_match_count
        ),
        "cash_scale_adjusted_cash_parity_count": (
            _positive_metadata_int(
                cash_scale_metadata,
                "adjusted_cash_parity_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
        ),
        "cash_scale_first_listing_exclusion_count": (
            _nonnegative_metadata_int(
                cash_scale_metadata,
                "first_listing_exclusion_count",
                label="metadata.cash_adjustment_scale_evidence",
            )
        ),
        "cash_scale_explicit_exclusion_count": excluded_event_count,
        "cash_scale_adj_close_decimal_places": 4,
        "cash_scale_cash_in_adj_close": False,
        "asset_identity_contract": identity["contract"],
        "asset_identity_digest": identity["digest"],
    }
    evidence["evidence_sha256"] = total_return_evidence_sha256(evidence)
    return row.to_dict(), evidence


def _load_validated_total_return_contract(
    conn,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read and independently authenticate every total-return dependency."""
    schema = read_frame(conn, TOTAL_RETURN_SCHEMA_AUDIT_SQL)
    contract = read_frame(conn, TOTAL_RETURN_CONTRACT_SQL)
    row = _one_row(contract, label="KRX total_return_close 계약")
    run_id = str(row.get("quality_run_id") or "")
    metadata = row.get("metadata")
    action_run_id = (
        str(metadata.get("action_snapshot_run_id") or "")
        if isinstance(metadata, dict)
        else ""
    )
    coverage_end = row.get("coverage_end")
    if not run_id or not action_run_id or pd.isna(coverage_end):
        raise RuntimeError(
            "Silver 총수익 계약의 run/coverage/action snapshot binding이 없습니다"
        )
    scope = read_frame(conn, TOTAL_RETURN_SCOPE_AUDIT_SQL, (run_id,))
    action = read_frame(
        conn, TOTAL_RETURN_ACTION_SNAPSHOT_AUDIT_SQL, (action_run_id,),
    )
    source_receipts = read_frame(
        conn, TOTAL_RETURN_SOURCE_RECEIPT_SQL, (action_run_id,),
    )
    cash_scale_source = read_frame(
        conn,
        TOTAL_RETURN_CASH_SCALE_SOURCE_EVIDENCE_SQL,
        (action_run_id,),
    )
    cash_scale_support = read_frame(
        conn,
        TOTAL_RETURN_CASH_SCALE_SUPPORT_ACTION_SQL,
        (action_run_id,),
    )
    published_actions = read_frame(
        conn, TOTAL_RETURN_PUBLISHED_ACTION_SQL, (action_run_id,),
    )
    resolution = read_frame(
        conn, TOTAL_RETURN_RESOLUTION_AUDIT_SQL, (run_id,),
    )
    cash_scale_resolution = read_frame(
        conn, TOTAL_RETURN_CASH_SCALE_RESOLUTION_SQL, (run_id,),
    )
    identity = read_frame(
        conn,
        TOTAL_RETURN_ASSET_IDENTITY_SQL,
        (
            _date_value(coverage_end, label="총수익 coverage_end").isoformat(),
            _date_value(coverage_end, label="총수익 coverage_end").isoformat(),
        ),
    )
    return _validate_total_return_contract(
        contract,
        schema,
        scope,
        action,
        resolution,
        identity,
        source_receipts,
        published_actions,
        cash_scale_source,
        cash_scale_support,
        cash_scale_resolution,
    )


def _contract_attrs(
    row: dict[str, Any], evidence: dict[str, Any],
) -> dict[str, Any]:
    rendered = {
        key: (
            value
            if key == "metadata"
            else None if pd.isna(value) else str(value)
        )
        for key, value in row.items()
    }
    rendered["validation_evidence"] = dict(evidence)
    return rendered


def verify_total_return_validation_evidence(
    evidence: Any,
) -> dict[str, Any]:
    """Verify the content-addressed evidence carried into a panel cache."""
    if not isinstance(evidence, dict):
        raise RuntimeError("Silver 총수익 validation evidence가 없습니다")
    required = {
        "validation_status",
        "contract_release",
        "methodology_version",
        "dividend_treatment",
        "quality_run_id",
        "coverage_start",
        "coverage_end",
        "certified_scope_start",
        "certified_markets",
        "price_row_count",
        "asset_count",
        "action_snapshot_run_id",
        "action_snapshot_schema_version",
        "action_snapshot_manifest_sha256",
        "action_snapshot_body_digest",
        "pit_scope_contract",
        "pit_input_action_count",
        "pit_included_action_count",
        "pit_excluded_action_count",
        "source_receipt_row_count",
        "source_receipt_row_digest",
        "terminal_economic_receipt_count",
        "terminal_economic_receipt_digest",
        "published_action_count",
        "published_action_row_digest",
        "published_action_scope_contract",
        "included_cash_action_parity_count",
        "included_cash_action_parity_digest",
        "cash_scale_source_contract",
        "cash_scale_source_evidence_count",
        "cash_scale_source_evidence_digest",
        "cash_scale_source_manifest_sha256",
        "cash_scale_source_manifest_digest",
        "cash_scale_support_action_count",
        "cash_scale_support_action_digest",
        "cash_scale_support_manifest_digest",
        "cash_scale_support_semantic_group_count",
        "disclosure_observation_contract",
        "disclosure_mutable_conflict_digest",
        "research_role",
        "resolution_version",
        "cash_action_count",
        "canonical_event_count",
        "applied_event_count",
        "excluded_event_count",
        "cash_scale_resolution_contract",
        "cash_scale_resolution_row_count",
        "cash_scale_resolution_row_digest",
        "cash_scale_stable_event_count",
        "cash_scale_changed_event_count",
        "cash_scale_evidence_match_count",
        "cash_scale_adjusted_cash_parity_count",
        "cash_scale_first_listing_exclusion_count",
        "cash_scale_explicit_exclusion_count",
        "cash_scale_adj_close_decimal_places",
        "cash_scale_cash_in_adj_close",
        "asset_identity_contract",
        "asset_identity_digest",
        "evidence_sha256",
    }
    missing = required - set(evidence)
    if missing:
        raise RuntimeError(
            f"Silver 총수익 validation evidence 필드 누락: {sorted(missing)}"
        )
    payload = dict(evidence)
    expected_digest = _sha256_text(
        payload.pop("evidence_sha256"), label="총수익 evidence_sha256",
    )
    actual_digest = total_return_evidence_sha256(payload)
    _sha256_text(
        payload.get("cash_scale_source_evidence_digest"),
        label="총수익 cash-scale source evidence digest",
    )
    for key in (
        "cash_scale_source_manifest_sha256",
        "cash_scale_source_manifest_digest",
        "cash_scale_support_action_digest",
        "cash_scale_support_manifest_digest",
    ):
        _sha256_text(payload.get(key), label=f"총수익 {key}")
    _sha256_text(
        payload.get("cash_scale_resolution_row_digest"),
        label="총수익 cash-scale resolution digest",
    )
    cash_scale_source_count = _nonnegative_metadata_int(
        payload,
        "cash_scale_source_evidence_count",
        label="총수익 validation evidence",
    )
    cash_scale_resolution_count = _positive_metadata_int(
        payload,
        "cash_scale_resolution_row_count",
        label="총수익 validation evidence",
    )
    cash_scale_stable_count = _nonnegative_metadata_int(
        payload,
        "cash_scale_stable_event_count",
        label="총수익 validation evidence",
    )
    cash_scale_changed_count = _nonnegative_metadata_int(
        payload,
        "cash_scale_changed_event_count",
        label="총수익 validation evidence",
    )
    cash_scale_match_count = _nonnegative_metadata_int(
        payload,
        "cash_scale_evidence_match_count",
        label="총수익 validation evidence",
    )
    cash_scale_support_count = _nonnegative_metadata_int(
        payload,
        "cash_scale_support_action_count",
        label="총수익 validation evidence",
    )
    cash_scale_support_group_count = _nonnegative_metadata_int(
        payload,
        "cash_scale_support_semantic_group_count",
        label="총수익 validation evidence",
    )
    cash_scale_adjusted_cash_count = _positive_metadata_int(
        payload,
        "cash_scale_adjusted_cash_parity_count",
        label="총수익 validation evidence",
    )
    cash_scale_first_listing_exclusion_count = _nonnegative_metadata_int(
        payload,
        "cash_scale_first_listing_exclusion_count",
        label="총수익 validation evidence",
    )
    cash_scale_explicit_exclusion_count = _nonnegative_metadata_int(
        payload,
        "cash_scale_explicit_exclusion_count",
        label="총수익 validation evidence",
    )
    fixed_checks = {
        "digest": actual_digest == expected_digest,
        "validation_status": payload.get("validation_status") == "VERIFIED",
        "contract_release": (
            payload.get("contract_release") == TOTAL_RETURN_CONTRACT_RELEASE
        ),
        "methodology_version": (
            payload.get("methodology_version") == TOTAL_RETURN_METHOD
        ),
        "dividend_treatment": (
            payload.get("dividend_treatment")
            == TOTAL_RETURN_DIVIDEND_TREATMENT
        ),
        "certified_scope_start": (
            payload.get("certified_scope_start")
            == TOTAL_RETURN_SCOPE_START.isoformat()
        ),
        "certified_markets": (
            payload.get("certified_markets") == ["KOSPI", "KOSDAQ"]
        ),
        "action_snapshot_schema_version": (
            payload.get("action_snapshot_schema_version")
            == TOTAL_RETURN_ACTION_SNAPSHOT_SCHEMA
        ),
        "cash_scale_source_contract": (
            payload.get("cash_scale_source_contract")
            == TOTAL_RETURN_CASH_SCALE_SOURCE_CONTRACT
        ),
        "cash_scale_resolution_contract": (
            payload.get("cash_scale_resolution_contract")
            == TOTAL_RETURN_CASH_SCALE_RESOLUTION_CONTRACT
        ),
        "cash_scale_count_parity": (
            cash_scale_resolution_count
            == cash_scale_stable_count + cash_scale_changed_count
            and cash_scale_source_count
            == cash_scale_changed_count
            == cash_scale_match_count
            and cash_scale_resolution_count
            == _positive_metadata_int(
                payload,
                "applied_event_count",
                label="총수익 validation evidence",
            )
            and (
                (
                    cash_scale_source_count == 0
                    and cash_scale_support_count == 0
                    and cash_scale_support_group_count == 0
                )
                or (
                    cash_scale_source_count > 0
                    and cash_scale_support_count >= cash_scale_source_count
                    and 0 < cash_scale_support_group_count
                    <= cash_scale_support_count
                )
            )
            and cash_scale_adjusted_cash_count == cash_scale_resolution_count
        ),
        "cash_scale_exclusion_parity": (
            cash_scale_explicit_exclusion_count
            == _nonnegative_metadata_int(
                payload,
                "excluded_event_count",
                label="총수익 validation evidence",
            )
            and cash_scale_first_listing_exclusion_count
            <= cash_scale_explicit_exclusion_count
        ),
        "cash_scale_stored_price_contract": (
            payload.get("cash_scale_adj_close_decimal_places") == 4
            and payload.get("cash_scale_cash_in_adj_close") is False
        ),
        "published_action_scope_contract": (
            payload.get("published_action_scope_contract")
            == "issuer_cash_ex_plus_manifest_scale_support_v1"
        ),
        "pit_scope_contract": (
            payload.get("pit_scope_contract") == TOTAL_RETURN_PIT_SCOPE_CONTRACT
        ),
        "disclosure_observation_contract": (
            payload.get("disclosure_observation_contract")
            == TOTAL_RETURN_DISCLOSURE_OBSERVATION_CONTRACT
        ),
        "research_role": (
            payload.get("research_role") == TOTAL_RETURN_RESEARCH_ROLE
        ),
        "resolution_version": (
            payload.get("resolution_version")
            == TOTAL_RETURN_RESOLUTION_VERSION
        ),
        "asset_identity_contract": (
            payload.get("asset_identity_contract")
            == TOTAL_RETURN_ASSET_IDENTITY_CONTRACT
        ),
    }
    if not all(fixed_checks.values()):
        raise RuntimeError(
            f"Silver 총수익 validation evidence가 변조되었거나 구형입니다: {fixed_checks}"
        )
    return dict(evidence)


def verify_live_total_return_contract(
    conn, expected: dict[str, Any],
) -> dict[str, Any]:
    """Require live RDS to match the total-return lineage bound to cache."""
    bound = verify_total_return_validation_evidence(expected)
    try:
        _row, actual = _load_validated_total_return_contract(conn)
    except (
        psycopg.errors.UndefinedTable,
        psycopg.errors.UndefinedColumn,
        psycopg.errors.InvalidTextRepresentation,
    ) as exc:
        raise RuntimeError(
            "현재 RDS의 Silver 총수익 lineage schema/UUID가 잘못되었습니다"
        ) from exc
    mismatches = {
        key: {"expected": bound.get(key), "actual": actual.get(key)}
        for key in sorted(set(bound) | set(actual))
        if bound.get(key) != actual.get(key)
    }
    if mismatches:
        raise RuntimeError(
            "현재 RDS 총수익 lineage가 캐시 계약과 다릅니다. Silver rebuild "
            f"후 패널을 다시 build하세요: {mismatches}"
        )
    return actual


def research_generation_evidence(
    validation_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Reduce one fully authenticated Silver snapshot to its immutable IDs.

    This artifact is created only after ``verify_live_total_return_contract``
    and the complete asset-identity checks have passed.  Later read-only
    campaign stages may then verify the certified generation with one small
    metadata query instead of rescanning millions of price and lineage rows.
    """
    bound = verify_total_return_validation_evidence(validation_evidence)
    payload = {
        "schema_version": "research-input-generation-v1",
        "quality_run_id": str(bound["quality_run_id"]),
        "action_snapshot_run_id": str(bound["action_snapshot_run_id"]),
        "methodology_version": str(bound["methodology_version"]),
        "dividend_treatment": str(bound["dividend_treatment"]),
        "coverage_start": _date_value(
            bound["coverage_start"], label="generation coverage_start",
        ).isoformat(),
        "coverage_end": _date_value(
            bound["coverage_end"], label="generation coverage_end",
        ).isoformat(),
        "action_snapshot_schema_version": str(
            bound["action_snapshot_schema_version"]
        ),
        "action_snapshot_manifest_sha256": str(
            bound["action_snapshot_manifest_sha256"]
        ),
        "action_snapshot_body_digest": str(
            bound["action_snapshot_body_digest"]
        ),
        "asset_identity_digest": str(bound["asset_identity_digest"]),
        "validation_evidence_sha256": str(bound["evidence_sha256"]),
    }
    payload["generation_digest"] = hashlib.sha256(json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    return payload


def verify_research_generation_evidence(evidence: Any) -> dict[str, Any]:
    """Authenticate the local campaign-level generation certificate."""
    if not isinstance(evidence, dict):
        raise RuntimeError("campaign Silver generation evidence가 없습니다")
    payload = dict(evidence)
    digest = _sha256_text(
        payload.pop("generation_digest", None),
        label="campaign generation_digest",
    )
    required = {
        "schema_version", "quality_run_id", "action_snapshot_run_id",
        "methodology_version", "dividend_treatment", "coverage_start",
        "coverage_end", "action_snapshot_schema_version",
        "action_snapshot_manifest_sha256", "action_snapshot_body_digest",
        "asset_identity_digest", "validation_evidence_sha256",
    }
    if set(payload) != required or payload.get("schema_version") != (
        "research-input-generation-v1"
    ):
        raise RuntimeError("campaign Silver generation evidence schema가 다릅니다")
    for key in (
        "action_snapshot_manifest_sha256", "action_snapshot_body_digest",
        "asset_identity_digest", "validation_evidence_sha256",
    ):
        _sha256_text(payload.get(key), label=f"campaign {key}")
    actual = hashlib.sha256(json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if actual != digest:
        raise RuntimeError("campaign Silver generation evidence digest가 다릅니다")
    return dict(evidence)


def verify_live_research_generation(
    conn, expected: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed if the live certified generation changed mid-campaign.

    The complete lineage/identity scan is deliberately not repeated here; it
    was bound when the campaign was created.  Certified run IDs plus the
    content-addressed action manifest/body digests are the database generation
    key.  Any rebuild or certification change therefore invalidates the
    campaign before candidate SQL or sealed OOS is evaluated.
    """
    bound = verify_research_generation_evidence(expected)
    row = _one_row(
        read_frame(conn, RESEARCH_GENERATION_SQL),
        label="현재 RDS research generation",
    )
    actual = {
        "quality_run_id": str(row.get("quality_run_id") or ""),
        "action_snapshot_run_id": str(
            row.get("action_snapshot_run_id") or ""
        ),
        "methodology_version": str(row.get("methodology_version") or ""),
        "dividend_treatment": str(row.get("dividend_treatment") or ""),
        "coverage_start": _date_value(
            row.get("coverage_start"), label="research generation coverage_start",
        ).isoformat(),
        "coverage_end": _date_value(
            row.get("coverage_end"), label="research generation coverage_end",
        ).isoformat(),
        "action_snapshot_schema_version": str(
            row.get("action_schema_version") or ""
        ),
        "action_snapshot_manifest_sha256": str(
            row.get("persisted_action_manifest_sha256") or ""
        ),
        "action_snapshot_body_digest": str(
            row.get("persisted_action_body_digest") or ""
        ),
    }
    expected_live = {key: bound[key] for key in actual}
    status = {
        "contract": str(row.get("contract_status") or ""),
        "return_quality": str(row.get("return_quality_status") or ""),
        "action_quality": str(row.get("action_quality_status") or ""),
    }
    mirrored = {
        "manifest": str(row.get("action_manifest_sha256") or "")
        == actual["action_snapshot_manifest_sha256"],
        "body": str(row.get("action_body_digest") or "")
        == actual["action_snapshot_body_digest"],
    }
    if actual != expected_live or set(status.values()) != {"CERTIFIED"} or not all(
        mirrored.values()
    ):
        raise RuntimeError(
            "campaign 도중 Silver generation이 변경되었거나 인증이 해제됐습니다: "
            f"expected={expected_live}, actual={actual}, status={status}, "
            f"metadata_parity={mirrored}"
        )
    return bound


def load_price_snapshot(conn) -> pd.DataFrame:
    try:
        contract_row, evidence = _load_validated_total_return_contract(conn)
        prices = read_frame(conn, PRICE_SNAPSHOT_SQL)
    except (
        psycopg.errors.UndefinedTable,
        psycopg.errors.UndefinedColumn,
        psycopg.errors.InvalidTextRepresentation,
    ) as exc:
        conn.rollback()
        raise RuntimeError(
            "Silver 총수익 lineage schema가 없습니다. 배당 총수익 migration과 "
            "인증 rebuild를 먼저 완료하세요."
        ) from exc
    _check_ticker_match_counts(prices)
    prices.attrs["asset_identity"] = asset_identity_evidence(prices)
    prices.attrs["return_contract"] = _contract_attrs(contract_row, evidence)
    prices.attrs["return_roles"] = return_role_contract()
    return prices


def load_fundamentals(conn, metrics: list[str] | tuple[str, ...]) -> pd.DataFrame:
    # ``materialize_pit`` performs its own deterministic local sort.  Asking
    # RDS to sort the complete revision ledger first only prolongs the SSM
    # session and can make an otherwise read-only build fail on tunnel expiry.
    return read_frame(conn, FUNDAMENTAL_SQL, (list(metrics),))


def load_dividend_history(conn) -> pd.DataFrame:
    """Refuse to reinterpret the ex-post return ledger as a PIT feature.

    The current Silver total-return contract certifies latest-corrected dividends for
    realized forward-return labels.  It does not certify historical action
    vintages or a per-signal ``known_at`` view.  A local attrs dictionary must
    never upgrade that label ledger into feature evidence.
    """
    raise RuntimeError(
        "Silver 배당 총수익 ledger는 ex-post label 전용입니다. 별도 "
        "historical-vintage/known_at 계약이 인증되기 전에는 직접 배당 "
        "feature를 만들 수 없습니다."
    )


def load_approved_values(conn) -> pd.DataFrame:
    try:
        return read_frame(conn, APPROVED_VALUES_SQL)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return pd.DataFrame(columns=["factor_key", "asset_id", "as_of_date", "value"])


def load_approved_factor_keys(conn) -> list[str]:
    """Return the APPROVED catalog even when a factor has no value rows.

    T5 must fail closed when approved metadata exists without enough comparable
    history.  Deriving the catalog from ``factor_value`` would silently turn an
    empty or partially loaded approved factor into "no approved factors".
    """
    try:
        frame = read_frame(conn, APPROVED_FACTOR_KEYS_SQL)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return []
    return sorted({str(value) for value in frame["factor_key"].dropna()})


def load_gold_generation(conn) -> dict | None:
    """Load the O(number of approved metadata rows) Gold cache generation.

    Legacy Gold rows do not carry the generation binding.  In that case the
    caller must load values directly and must not reuse a local cache.
    """
    try:
        frame = read_frame(conn, GOLD_GENERATION_SQL)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return None
    if len(frame) != 1:
        raise RuntimeError("Gold generation query는 정확히 한 행이어야 합니다")
    row = frame.iloc[0]
    count = int(row["approved_factor_count"])
    digest_count = int(row["generation_digest_count"])
    raw_keys = row["approved_factor_keys"]
    keys = [] if raw_keys is None else sorted(str(value) for value in raw_keys)
    if len(keys) != count or len(set(keys)) != count:
        raise RuntimeError("Gold generation approved factor exact set이 잘못되었습니다")
    if count == 0:
        return {
            "gold_generation_digest": hashlib.sha256(b"[]").hexdigest(),
            "approved_factor_count": 0,
            "approved_factor_keys": [],
        }
    digest = row["gold_generation_digest"]
    if digest_count == 0 and digest is None:
        return None
    if (
        digest_count != 1
        or not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
    ):
        raise RuntimeError("Gold generation digest가 승인 집합 전체에 일치하지 않습니다")
    return {
        "gold_generation_digest": digest,
        "approved_factor_count": count,
        "approved_factor_keys": keys,
    }


def bind_gold_generation(conn, digest: str) -> dict:
    """Bind every APPROVED metadata row to one generation in the transaction."""
    if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
        raise ValueError("gold_generation_digest는 64자리 소문자 hex여야 합니다")
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE gold.factor
               SET config = jsonb_set(
                   coalesce(config, '{}'::jsonb),
                   '{gold_generation_digest}', to_jsonb(%s::text), true
               )
             WHERE status = 'APPROVED'
            """,
            (digest,),
        )
    observed = load_gold_generation(conn)
    if observed is None or observed["gold_generation_digest"] != digest:
        raise RuntimeError("Gold generation digest 원자 binding 검증에 실패했습니다")
    return observed


def load_gold_trial_history(conn) -> pd.DataFrame:
    try:
        return read_frame(conn, GOLD_TRIAL_HISTORY_SQL)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return pd.DataFrame(columns=["definition_hash", "net_ir", "hac_pvalue"])
