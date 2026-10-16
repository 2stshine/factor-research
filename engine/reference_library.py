"""Frozen literature measurements, not alpha approvals or legacy Gold factors.

This module neither reads a database nor evaluates returns. An authenticated
adapter must attest the exact feature-only input snapshot. Attestation is a
provenance contract, not a claim that arbitrary caller-supplied JSON is trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


CATALOG_PATH = Path(__file__).resolve().parents[1] / "research/phenomena/reference-catalog.json"
LIBRARY_VERSION = "phenomena-reference-library-v1"
IDENTITY_CONTRACT = "HISTORICAL_ASSET_ID"
INPUT_SCOPE = "KRX_COMMON_STOCK"
FEATURE_CONTRACTS = {
    "adj_close": "PIT_ADJUSTED_PRICE_NOT_EX_POST_TOTAL_RETURN",
    "market_cap": "ISSUE_MARKET_CAP_KRW",
    "daily_volatility_252d": "SAMPLE_STD_PRICE_RETURN_LAST_252_OBSERVED_ROWS",
    "amihud_illiquidity_1m": "MONTH_MEAN_ABS_PRICE_RETURN_PER_KRW_POSITIVE_VALUE",
    "price_high_252d": "MAX_ADJUSTED_PRICE_LAST_252_OBSERVED_ROWS",
    "max_daily_return_1m": "MONTH_MAX_DAILY_PRICE_RETURN",
}
FEATURE_UNITS = {
    "adj_close": "KRW", "market_cap": "KRW",
    "daily_volatility_252d": "DECIMAL_RETURN",
    "amihud_illiquidity_1m": "PER_KRW", "price_high_252d": "KRW",
    "max_daily_return_1m": "DECIMAL_RETURN",
}
_BASE = ("asset_id", "stock_code", "date", "known_at", "market")
_COUNTS = ("daily_return_observations_252d", "amihud_observations_1m",
           "price_high_observations_252d", "max_daily_return_observations_1m")
_ALLOWED = frozenset(_BASE + tuple(FEATURE_CONTRACTS) + _COUNTS)
_OUTPUT = list(_BASE) + ["reference_id", "value", "oriented_value",
                         "definition_hash", "source_version", "input_sha256"]
_EXECUTABLE = frozenset({"kr_size_issue_v1", "kr_momentum_12_2_price_v1",
                         "kr_reversal_1m_price_v1", "kr_low_volatility_252d_v1",
                         "kr_amihud_1m_v1", "kr_high_252d_v1", "kr_max_1m_v1"})


@dataclass(frozen=True)
class ReferenceLibraryResult:
    values: pd.DataFrame
    validation: dict[str, Any]
    blocked: list[dict[str, Any]]


def definition_hash(definition: Mapping[str, Any]) -> str:
    """Hash all definition metadata except its optional self-referential hash."""
    payload = {k: v for k, v in definition.items() if k != "definition_hash"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def implementation_hash() -> str:
    """Bind calculation implementation separately from literature definition."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def load_catalog(path: str | Path | None = None) -> list[dict[str, Any]]:
    raw = json.loads(Path(path or CATALOG_PATH).read_text())
    if raw.get("schema_version") != LIBRARY_VERSION:
        raise ValueError("Unsupported reference catalog schema")
    definitions = raw["definitions"]
    validate_catalog(definitions)
    return [{**item, "definition_hash": definition_hash(item)} for item in definitions]


def validate_catalog(definitions: Sequence[Mapping[str, Any]]) -> None:
    ids: set[str] = set()
    for item in definitions:
        required = {"id", "name_ko", "family", "object_type", "role", "formula",
                    "orientation", "required_columns", "sources", "adaptation",
                    "readiness", "lookback", "alpha_approved"}
        if required - set(item):
            raise ValueError(f"Incomplete reference definition: {required - set(item)}")
        if item["id"] in ids:
            raise ValueError("Duplicate reference ID")
        ids.add(item["id"])
        if item["role"] != "MEASUREMENT_CONTROL" or item["alpha_approved"] is not False:
            raise ValueError("Reference catalog must not confer alpha approval")
        if item["orientation"] not in (-1, 1):
            raise ValueError("Orientation must be frozen at +1 or -1")
        if not item["sources"] or not all(str(s.get("url", "")).startswith("https://")
                                           for s in item["sources"]):
            raise ValueError("Primary literature sources required")
        if item["readiness"]["status"] not in {"IMPLEMENTED_REQUIRES_ATTESTATION", "BLOCKED"}:
            raise ValueError("Invalid reference readiness")
        if "definition_hash" in item and item["definition_hash"] != definition_hash(item):
            raise ValueError("Reference definition hash mismatch")


def _prepare(panel: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(panel, pd.DataFrame) or panel.empty:
        raise ValueError("A nonempty feature-only DataFrame is required")
    if set(_BASE) - set(panel):
        raise ValueError(f"Missing identity/time columns: {set(_BASE) - set(panel)}")
    if set(panel) - _ALLOWED:
        raise ValueError(f"Unrecognized or label columns forbidden: {sorted(set(panel) - _ALLOWED)}")
    frame = panel.copy()
    if frame[list(_BASE)].isna().any().any():
        raise ValueError("Null identity or time values are forbidden")
    if not frame["stock_code"].map(lambda x: isinstance(x, str) and bool(re.fullmatch(r"[0-9A-Z]{6}", x))).all():
        raise ValueError("stock_code must preserve six-character uppercase ASCII alphanumeric strings including leading zeros")
    if not frame["asset_id"].map(lambda x: isinstance(x, (str, int, np.integer))
                                 and not isinstance(x, bool) and str(x).strip() == str(x)
                                 and str(x) != "").all():
        raise ValueError("Stable asset_id values are required")
    frame["asset_id"] = frame["asset_id"].astype(str)
    if not frame["market"].isin(["KOSPI", "KOSDAQ"]).all():
        raise ValueError("Only attested KOSPI/KOSDAQ common stock inputs are supported")
    dates = pd.to_datetime(frame["date"], errors="raise")
    if dates.dt.tz is not None or not dates.dt.is_month_end.all() or not (dates == dates.dt.normalize()).all():
        raise ValueError("date must be timezone-naive calendar month-end at midnight")
    frame["date"] = dates
    # Reject naive known_at values instead of interpreting ambiguous local times as UTC.
    if not frame["known_at"].map(lambda value: pd.Timestamp(value).tzinfo is not None).all():
        raise ValueError("known_at must carry a timezone")
    frame["known_at"] = pd.to_datetime(frame["known_at"], utc=True)
    cutoff = (dates.dt.tz_localize("Asia/Seoul") + pd.Timedelta(days=1)
              - pd.Timedelta(nanoseconds=1)).dt.tz_convert("UTC")
    if (frame["known_at"] > cutoff).any():
        raise ValueError("Input was not known by formation month-end")
    if frame.duplicated(["asset_id", "date"]).any():
        raise ValueError("Duplicate asset-month inputs")
    if frame.duplicated(["stock_code", "date"]).any():
        raise ValueError("Ambiguous ticker identity within a month")
    for column in set(frame) - set(_BASE):
        if not pd.api.types.is_numeric_dtype(frame[column]) or pd.api.types.is_bool_dtype(frame[column]):
            raise ValueError(f"Numeric feature column required: {column}")
        frame[column] = frame[column].astype(float)
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def input_panel_digest(panel: pd.DataFrame) -> str:
    """Order-insensitive exact-input digest; validates the strict feature schema."""
    frame = _prepare(panel).reindex(sorted(panel.columns), axis=1)
    digest = hashlib.sha256()
    digest.update(json.dumps(list(frame.columns), separators=(",", ":")).encode())
    digest.update(pd.util.hash_pandas_object(frame, index=False).to_numpy(dtype="uint64").tobytes())
    return digest.hexdigest()


def _validate_attestation(panel: pd.DataFrame, attestation: Mapping[str, Any]) -> str:
    for key in ("source_version", "source_contract", "evidence_sha256", "input_sha256"):
        if not isinstance(attestation.get(key), str) or not attestation[key].strip():
            raise ValueError(f"Missing attestation {key}")
    for key in ("evidence_sha256", "input_sha256"):
        if not re.fullmatch(r"[a-f0-9]{64}", attestation[key]):
            raise ValueError(f"Invalid attestation {key}")
    if attestation.get("status") != "CERTIFIED":
        raise ValueError("Input attestation must be CERTIFIED")
    if attestation.get("identity_contract") != IDENTITY_CONTRACT or attestation.get("scope") != INPUT_SCOPE:
        raise ValueError("Historical common-stock identity/scope attestation required")
    actual = input_panel_digest(panel)
    if attestation["input_sha256"] != actual:
        raise ValueError("Attested input digest mismatch")
    return actual


def _finite(frame: pd.DataFrame, column: str, *, positive: bool = False) -> pd.Series:
    values = frame[column].where(np.isfinite(frame[column]))
    return values.where(values > 0) if positive else values


def _count_valid(frame: pd.DataFrame, column: str, minimum: int, maximum: int) -> pd.Series:
    values = _finite(frame, column)
    return values.between(minimum, maximum) & values.eq(np.floor(values))


def _price_path(frame: pd.DataFrame, start_lag: int, end_lag: int) -> pd.Series:
    # Reindex each asset onto its full monthly calendar. A missing interior month
    # invalidates the window; observation-row shift must never bridge a gap.
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, group in frame.groupby("asset_id", sort=False):
        periods = group["date"].dt.to_period("M")
        calendar = pd.period_range(periods.min(), periods.max(), freq="M")
        prices = pd.Series(_finite(group, "adj_close", positive=True).to_numpy(), index=periods).reindex(calendar)
        required_count = start_lag - end_lag + 1
        valid = prices.shift(end_lag).rolling(required_count, min_periods=required_count).count().eq(required_count)
        raw = (prices.shift(end_lag) / prices.shift(start_lag) - 1).where(valid)
        result.loc[group.index] = raw.reindex(periods).to_numpy()
    return result


def _calculate(frame: pd.DataFrame, reference_id: str) -> pd.Series:
    if reference_id == "kr_size_issue_v1":
        return np.log(_finite(frame, "market_cap", positive=True))
    if reference_id == "kr_momentum_12_2_price_v1":
        return _price_path(frame, 12, 1)
    if reference_id == "kr_reversal_1m_price_v1":
        return _price_path(frame, 1, 0)
    if reference_id == "kr_low_volatility_252d_v1":
        value = _finite(frame, "daily_volatility_252d")
        return value.where(value.ge(0) & _count_valid(frame, "daily_return_observations_252d", 200, 252))
    if reference_id == "kr_amihud_1m_v1":
        value = _finite(frame, "amihud_illiquidity_1m")
        return value.where(value.ge(0) & _count_valid(frame, "amihud_observations_1m", 15, 31))
    if reference_id == "kr_high_252d_v1":
        value = _finite(frame, "adj_close", positive=True) / _finite(frame, "price_high_252d", positive=True)
        return value.where(value.le(1 + 1e-12) & _count_valid(frame, "price_high_observations_252d", 252, 252))
    if reference_id == "kr_max_1m_v1":
        value = _finite(frame, "max_daily_return_1m")
        return value.where(value.gt(-1) & _count_valid(frame, "max_daily_return_observations_1m", 15, 31))
    raise ValueError(f"No implementation for {reference_id}")


def calculate_reference_panel(
    panel: pd.DataFrame, *, input_attestation: Mapping[str, Any],
    definitions: Sequence[str] | None = None, as_of: str | pd.Timestamp | None = None,
) -> ReferenceLibraryResult:
    """Calculate frozen raw/oriented characteristics from attested price features.

    ``definitions`` is a sequence of registered IDs, never arbitrary formulas.
    Missing/unattested inputs produce explicit blocked records, not proxy values.
    Invalid row measurements produce no value and are counted in validation.
    No financial formula executes until an account/period/vintage adapter exists.
    """
    digest = _validate_attestation(panel, input_attestation)
    frame = _prepare(panel)
    if as_of is not None:
        cutoff = pd.Timestamp(as_of)
        if cutoff.tzinfo is not None:
            cutoff = cutoff.tz_convert("Asia/Seoul").tz_localize(None)
        frame = frame.loc[frame["date"] <= cutoff.normalize()].copy()
    catalog = {item["id"]: item for item in load_catalog()}
    ids = list(definitions) if definitions is not None else list(catalog)
    if len(ids) != len(set(ids)) or set(ids) - set(catalog):
        raise ValueError("Unknown or duplicate reference IDs")
    outputs: list[pd.DataFrame] = []
    blocked: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for reference_id in ids:
        definition = catalog[reference_id]
        reasons = list(definition["readiness"].get("blockers", []))
        if reference_id not in _EXECUTABLE:
            reasons.append("No authenticated account/benchmark/composite adapter implemented")
        missing = set(definition["required_columns"]) - set(frame)
        if missing:
            reasons.append("Missing columns: " + ", ".join(sorted(missing)))
        for column in set(definition["required_columns"]) & set(FEATURE_CONTRACTS):
            if input_attestation.get("feature_contracts", {}).get(column) != FEATURE_CONTRACTS[column]:
                reasons.append(f"Unattested feature estimator: {column}")
            if input_attestation.get("units", {}).get(column) != FEATURE_UNITS[column]:
                reasons.append(f"Unattested input unit: {column}")
        if reasons:
            blocked.append({"reference_id": reference_id, "definition_hash": definition["definition_hash"],
                            "status": "BLOCKED", "reasons": reasons})
            continue
        raw = _calculate(frame, reference_id).replace([np.inf, -np.inf], np.nan)
        valid = raw.notna()
        output = frame.loc[valid, list(_BASE)].copy()
        output["reference_id"] = reference_id
        output["value"] = raw.loc[valid]
        output["oriented_value"] = raw.loc[valid] * definition["orientation"]
        output["definition_hash"] = definition["definition_hash"]
        output["source_version"] = input_attestation["source_version"]
        output["input_sha256"] = digest
        outputs.append(output)
        summaries.append({"reference_id": reference_id, "definition_hash": definition["definition_hash"],
                          "status": "MEASUREMENT_VALIDATED" if valid.any() else "NO_VALID_ROWS",
                          "input_rows": len(frame), "value_rows": int(valid.sum()),
                          "missing_or_invalid_rows": int((~valid).sum()),
                          "first_date": str(output["date"].min().date()) if valid.any() else None,
                          "last_date": str(output["date"].max().date()) if valid.any() else None})
    values = pd.concat(outputs, ignore_index=True) if outputs else pd.DataFrame(columns=_OUTPUT)
    if not values.empty:
        values = values[_OUTPUT].sort_values(["reference_id", "asset_id", "date"]).reset_index(drop=True)
    validation = {"schema_version": LIBRARY_VERSION, "role": "MEASUREMENT_CONTROL",
                  "alpha_approved": False, "source_version": input_attestation["source_version"],
                  "implementation_sha256": implementation_hash(),
                  "input_sha256": digest, "source_evidence_sha256": input_attestation["evidence_sha256"],
                  "input_rows": len(frame), "value_rows": len(values), "references": summaries,
                  "blocked_count": len(blocked), "publication_readiness": "REQUIRES_TRUSTED_ADAPTER_AND_PUBLISHER"}
    return ReferenceLibraryResult(values=values, validation=validation, blocked=blocked)
