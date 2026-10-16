"""Return-blind measurement admission. Never an alpha or trading approval.

Full-history coverage is a present-day inventory diagnostic, not a historical
feature-selection signal. Historical strategy runs must additionally screen
availability within each training fold and disclose historical reuse.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re

import numpy as np
import pandas as pd

from engine.reference_library import definition_hash
from engine.research_generation import digest

SCHEMA = "reference-admission-v1"


@dataclass(frozen=True)
class AdmissionPolicy:
    minimum_assets: int = 100
    minimum_observed_months: int = 60
    pit_policy: str = "PIT_ASSUMED_ACCEPTED_NOT_FIRST_VINTAGE_VERIFIED"

    def validate(self):
        if (type(self.minimum_assets) is not int or self.minimum_assets < 1
                or type(self.minimum_observed_months) is not int or self.minimum_observed_months < 1
                or self.pit_policy != "PIT_ASSUMED_ACCEPTED_NOT_FIRST_VINTAGE_VERIFIED"):
            raise ValueError("Invalid explicit admission policy")


def assess_measurement(frame, definition, *, policy: AdmissionPolicy):
    """Pure assessment of one exact definition; no return labels accepted."""
    policy.validate()
    from engine.phenomenon_references import VALUE_COLUMNS
    if set(frame.columns) != VALUE_COLUMNS:
        raise ValueError("Admission requires only seven measurement columns; no returns")
    f = frame.copy()
    errors, gaps, warnings = [], [], []
    if f.empty:
        gaps.append("NO_MEASUREMENTS")
    if not f.reference_id.eq(definition["id"]).all():
        errors.append("REFERENCE_ID_MISMATCH")
    if not f.definition_hash.eq(definition_hash(definition)).all():
        errors.append("DEFINITION_HASH_MISMATCH")
    if f.duplicated(["asset_id", "date"]).any():
        errors.append("DUPLICATE_ASSET_MONTH")
    if not f.stock_code.map(lambda x: isinstance(x, str) and bool(re.fullmatch(r"[0-9A-Z]{6}", x))).all():
        errors.append("INVALID_SECURITY_CODE")
    if not f.asset_id.map(lambda x: not isinstance(x, bool) and str(x).isdigit() and int(x) > 0).all():
        errors.append("INVALID_ASSET_ID")
    identities = f[["asset_id", "date", "stock_code"]].drop_duplicates()
    if identities.duplicated(["asset_id", "date"]).any() or identities.duplicated(["stock_code", "date"]).any():
        errors.append("CONFLICTING_HISTORICAL_IDENTITY")
    try:
        dates = pd.to_datetime(f.date, errors="raise")
        if dates.dt.tz is not None or not (dates.dt.is_month_end & dates.eq(dates.dt.normalize())).all():
            raise ValueError("Not month end")
        if not f.known_at.map(lambda x: pd.notna(x) and pd.Timestamp(x).tzinfo is not None).all():
            raise ValueError("Naive known_at")
        known = pd.to_datetime(f.known_at, utc=True)
        cutoff = (dates.dt.tz_localize("Asia/Seoul") + pd.Timedelta(days=1)).dt.tz_convert("UTC")
        if not known.lt(cutoff).all():
            errors.append("FUTURE_KNOWN_AT")
    except (ValueError, TypeError, AttributeError):
        errors.append("INVALID_MEASUREMENT_CLOCK")
        dates = pd.Series(pd.NaT, index=f.index, dtype="datetime64[ns]")
    numeric = pd.to_numeric(f.value, errors="coerce")
    if not pd.api.types.is_numeric_dtype(f.value) or pd.api.types.is_bool_dtype(f.value) or not np.isfinite(numeric).all():
        errors.append("NONFINITE_OR_NONNUMERIC_VALUE")
    if not definition.get("formula") or not definition.get("sources"):
        errors.append("MISSING_DEFINITION_OR_SOURCE")
    assets, months = int(f.asset_id.nunique()), int(dates.nunique())
    if assets < policy.minimum_assets:
        gaps.append("INSUFFICIENT_ASSETS")
    if months < policy.minimum_observed_months:
        gaps.append("INSUFFICIENT_MONTHS")
    valid = numeric[np.isfinite(numeric)]
    if len(valid) and valid.nunique() == 1:
        warnings.append("CONSTANT_MEASUREMENT_NOT_AUTOMATICALLY_BAD_DATA")
    monthly = f.assign(month=dates).groupby("month").asset_id.nunique()
    by_asset = f.assign(month=dates).groupby("asset_id").month.nunique()
    return {"reference_id": definition["id"], "definition_sha256": definition_hash(definition),
            "name_ko": definition.get("name_ko", definition["id"]), "family": definition.get("family"),
            "assessment": "REJECTED" if errors else "NEEDS_DATA" if gaps else "PASS",
            "errors": errors, "data_gaps": gaps, "warnings": warnings,
            "rows": len(f), "assets": assets, "observed_months": months,
            "first_date": None if dates.isna().all() else str(dates.min().date()),
            "latest_date": None if dates.isna().all() else str(dates.max().date()),
            "median_assets_per_month": float(monthly.median()) if len(monthly) else None,
            "median_months_per_asset": float(by_asset.median()) if len(by_asset) else None,
            "zero_fraction": float(valid.eq(0).mean()) if len(valid) else None,
            "quantiles": {str(q): float(valid.quantile(q)) for q in (.01, .5, .99)} if len(valid) else {},
            "pit_status": policy.pit_policy, "profitability_tested": False,
            "first_vintage_independently_verified": False}


def definition_signature(definition):
    # Exact semantics only. High correlation alone is not a definition duplicate.
    return digest({"formula": " ".join(definition["formula"].split()),
                   "required_columns": sorted(definition.get("required_columns", [])),
                   "lookback": definition.get("lookback"),
                   "object_type": definition.get("object_type")})


def finalize(rows, definitions, *, program_sha256, policy, live_database_verified, source_receipts, origin="OBSERVED"):
    """Create a separate, content-addressed overlay; never change Gold/program."""
    policy.validate()
    if len(rows) != len(definitions) or {r["reference_id"] for r in rows} != set(definitions):
        raise ValueError("Admission must cover the exact candidate set once")
    if origin not in {"OBSERVED", "SYNTHETIC"} or type(live_database_verified) is not bool:
        raise ValueError("Explicit origin/verification required")
    seen, decisions = {}, []
    for r in sorted(rows, key=lambda x: x["reference_id"]):
        row = {**r, "errors": list(r["errors"]), "warnings": list(r["warnings"])}
        signature = definition_signature(definitions[row["reference_id"]])
        if signature in seen:
            row["assessment"] = "REJECTED"
            row["errors"].append("DUPLICATE_DEFINITION:" + seen[signature])
        else:
            seen[signature] = row["reference_id"]
        row["status"] = ("ADMITTED" if row["assessment"] == "PASS" else row["assessment"]) if live_database_verified or origin == "SYNTHETIC" else "UNVERIFIED_SNAPSHOT_ONLY"
        decisions.append(row)
    result = {"schema": SCHEMA, "origin": origin, "program_sha256": program_sha256,
              "policy": asdict(policy), "policy_sha256": digest(asdict(policy)),
              "status": "ADMISSION_EVALUATED" if live_database_verified else "SOFTWARE_TEST_ONLY" if origin == "SYNTHETIC" else "SNAPSHOT_DIAGNOSTIC_NOT_ADMISSION",
              "live_database_verified": live_database_verified, "source_receipts": source_receipts,
              "decisions": decisions, "return_labels_read": False, "alpha_approved": False,
              "gold_modified": False, "strategy_selected": False,
              "coverage_denominator": "OBSERVED_ASSET_MONTHS_NOT_KRX_UNIVERSE_COVERAGE",
              "limitations": ["PIT_ASSUMED is not independently verified first-release history.",
                              "Admission does not establish statistical/economic independence or profitable alpha.",
                              "Full-history support is inventory metadata; strategy selection must be train-only."]}
    result["admission_sha256"] = digest(result)
    return result


def admitted_features(report, *, program_sha256, origin):
    if report.get("admission_sha256") != digest({k: v for k, v in report.items() if k != "admission_sha256"}):
        raise ValueError("Admission report hash mismatch")
    if report.get("schema") != SCHEMA or report["program_sha256"] != program_sha256 or report["origin"] != origin:
        raise ValueError("Admission origin/program mismatch")
    if origin == "OBSERVED" and (not report["live_database_verified"] or report["status"] != "ADMISSION_EVALUATED"):
        raise ValueError("Snapshot-only diagnostics cannot authorize strategy inputs")
    return {r["reference_id"]: r["definition_sha256"] for r in report["decisions"] if r["status"] == "ADMITTED"}
