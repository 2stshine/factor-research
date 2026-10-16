"""Bind financial panels to a replayed, versioned Silver ledger; no DB access.

This is a local integrity/provenance contract, not independent first-vintage
certification. Price-only synthetic panels can skip it; execution cache loading
must explicitly require financial features. Existing archive files are untouched.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

import pandas as pd

from engine import fundamentals, silver


VERSION = "fundamental-panel-replay-contract-v1"
META_KEY = "fundamental_replay_contract"
OVERLAY_META_KEY = "historical_fundamental_overlay_contract"
META_KEYS = (META_KEY, OVERLAY_META_KEY)
_RECEIPT = "fundamental_materialization_receipt"
_LEDGER_REQUIRED = {
    "asset_id", "period_end", "fiscal_period", "fs_type", "available_date",
    "available_at", "statement_type", "metric", "value", "revision_key", "quality_run_id",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _frame_digest(frame, columns, order):
    scoped = frame[list(columns)].copy()
    scoped = scoped.sort_values(list(order), kind="mergesort").reset_index(drop=True)
    schema = [(str(column), str(scoped[column].dtype)) for column in scoped]
    hasher = hashlib.sha256(_digest(schema).encode())
    hasher.update(pd.util.hash_pandas_object(scoped, index=False, categorize=True).values.tobytes())
    return hasher.hexdigest()


def _method():
    return {"methodology_version": fundamentals.FUNDAMENTAL_METHODOLOGY_VERSION,
            "materializer_source_sha256": fundamentals.source_sha256(),
            "source_query_sha256": hashlib.sha256(silver.FUNDAMENTAL_SQL.encode()).hexdigest()}


def _ledger(rows):
    if not isinstance(rows, pd.DataFrame) or not _LEDGER_REQUIRED.issubset(rows.columns):
        raise ValueError("Financial provenance requires the certified raw Silver ledger columns")
    if rows.empty:
        raise ValueError("An empty financial ledger cannot certify a financial execution panel")
    runs = rows["quality_run_id"]
    if runs.isna().any() or runs.astype(str).str.strip().eq("").any():
        raise ValueError("Financial ledger rows need explicit quality_run_id provenance")
    counts = {str(key): int(value) for key, value in runs.astype(str).value_counts().sort_index().items()}
    return {"row_count": len(rows), "quality_run_ids": sorted(counts),
            "quality_run_count": len(counts), "rows_by_quality_run": counts,
            "ledger_sha256": _frame_digest(rows, sorted(rows.columns), sorted(rows.columns)),
            "source": "RDS public.fundamental / CERTIFIED DART STANDARDIZED currency query",
            "independent_first_vintage_verification": False}


def _materialized_digest(frame):
    return _frame_digest(frame, sorted(frame.columns), ("asset_id", "available_date"))


def materialize(rows, *, verbose=True):
    """Replay once and return a frame carrying an integrity-checked local receipt."""
    provenance = _ledger(rows)
    frame = fundamentals.materialize_pit(rows, verbose=verbose)
    receipt = {"schema_version": VERSION, **_method(), "ledger": provenance,
               "materialized_frame_sha256": _materialized_digest(frame)}
    receipt["sha256"] = _digest(receipt)
    frame.attrs[_RECEIPT] = receipt
    return frame


def _financial_digest(frame, features):
    required = {"asset_id", "ym", "trade_date", "available_date", *features}
    if not required.issubset(frame.columns):
        raise ValueError("Bound financial panel columns are missing")
    if frame.duplicated(["asset_id", "ym"]).any():
        raise ValueError("Financial panel asset/month keys are duplicated")
    return _frame_digest(frame, sorted(required), ("asset_id", "ym", "trade_date"))


def bind(panel, raw_certified_rows, *, materialized=None):
    """Verify an actual replay/attachment before adding new-panel metadata.

    Use ``materialize(rows)`` then pass that frame to avoid a second replay.
    A precomputed frame without this verified receipt cannot bless old values.
    """
    fund = materialize(raw_certified_rows, verbose=False) if materialized is None else materialized
    receipt = deepcopy(fund.attrs.get(_RECEIPT))
    if not isinstance(receipt, dict):
        raise ValueError("Use fundamental_contract.materialize for a bound financial replay")
    receipt_sha = receipt.pop("sha256", None)
    if (receipt_sha != _digest(receipt) or receipt.get("schema_version") != VERSION
            or any(receipt.get(key) != value for key, value in _method().items())
            or receipt.get("ledger") != _ledger(raw_certified_rows)
            or receipt.get("materialized_frame_sha256") != _materialized_digest(fund)):
        raise ValueError("Financial materialization receipt changed or belongs to another ledger/version")
    features = sorted(fundamentals.PIT_FEATURES)
    if not set(features).issubset(panel.monthly.columns):
        raise ValueError("New financial panels must contain the complete materialized feature contract")
    base = panel.monthly.drop(columns=[*features, "available_date"], errors="ignore")
    expected = fundamentals.attach(base, fund, features)
    observed_sha = _financial_digest(panel.monthly, features)
    if observed_sha != _financial_digest(expected, features):
        raise ValueError("Panel financial values are not the attached current-methodology replay")
    contract = {**receipt, "materialization_receipt_sha256": receipt_sha,
                "financial_features": features, "panel_row_count": len(panel.monthly),
                "financial_frame_sha256": observed_sha}
    contract["sha256"] = _digest(contract)
    panel.meta[META_KEY] = contract
    return deepcopy(contract)


def verify(panel, *, require_financial=False):
    """Reject unbound/stale/tampered execution inputs without reading the ledger."""
    if OVERLAY_META_KEY in panel.meta:
        if META_KEY in panel.meta:
            raise RuntimeError("Ambiguous legacy and historical-overlay provenance")
        # Explicitly separate source contract; never claim a document overlay
        # came from the legacy public.fundamental query.
        from engine import historical_fundamental_overlay

        return historical_fundamental_overlay.verify(panel)
    features = set(panel.monthly.columns) & set(fundamentals.PIT_FEATURES)
    if not features and META_KEY not in panel.meta and not require_financial:
        return {"status": "SKIPPED_PRICE_ONLY_PANEL", "financial_features": []}
    contract = deepcopy(panel.meta.get(META_KEY))
    if not isinstance(contract, dict):
        raise RuntimeError("Financial cache lacks a versioned replay contract; rebuild from certified ledger")
    expected_sha = contract.pop("sha256", None)
    if expected_sha != _digest(contract) or contract.get("schema_version") != VERSION:
        raise RuntimeError("Financial replay contract is missing, old, or altered")
    if any(contract.get(key) != value for key, value in _method().items()):
        raise RuntimeError("Financial methodology/source changed; old cache cannot execute")
    required_features = sorted(fundamentals.PIT_FEATURES)
    if contract.get("financial_features") != required_features or features != set(required_features):
        raise RuntimeError("Financial replay feature set differs from the current contract")
    ledger = contract.get("ledger", {})
    if not isinstance(ledger, dict):
        raise RuntimeError("Financial source quality-run provenance is malformed")
    counts = ledger.get("rows_by_quality_run", {})
    if (not isinstance(counts, dict) or not counts
            or any(not isinstance(k, str) or not k.strip() for k in counts)
            or any(type(v) is not int or v <= 0 for v in counts.values())
            or ledger.get("quality_run_ids") != sorted(counts)
            or ledger.get("quality_run_count") != len(counts)
            or ledger.get("row_count") != sum(counts.values())
            or not _SHA256.fullmatch(str(ledger.get("ledger_sha256")))
            or ledger.get("independent_first_vintage_verification") is not False):
        raise RuntimeError("Financial source quality-run provenance is malformed")
    receipt = {key: contract.get(key) for key in (
        "schema_version", "methodology_version", "materializer_source_sha256",
        "source_query_sha256", "ledger", "materialized_frame_sha256",
    )}
    if (not _SHA256.fullmatch(str(receipt["materialized_frame_sha256"]))
            or _digest(receipt) != contract.get("materialization_receipt_sha256")):
        raise RuntimeError("Financial replay materialization receipt is malformed")
    try:
        digest = _financial_digest(panel.monthly, required_features)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    if (contract.get("panel_row_count") != len(panel.monthly)
            or contract.get("financial_frame_sha256") != digest):
        raise RuntimeError("Financial frame content changed after methodology binding")
    return {"status": "VERIFIED_LOCAL_REPLAY_BINDING", "contract_sha256": expected_sha,
            **_method(), "ledger_sha256": ledger["ledger_sha256"]}


def scoped_metadata(panel):
    """Preserve immutable origin evidence in derived snapshots, without rebinding.

    The full financial-frame hash remains a parent binding, not a claim that a
    sliced frame itself passed ``verify``. Full execution caches are verified
    before derivation; derived snapshots receive their own overall panel hash.
    """
    return {key: deepcopy(panel.meta[key]) for key in META_KEYS if key in panel.meta}
