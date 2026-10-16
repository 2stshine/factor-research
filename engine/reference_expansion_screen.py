"""Fail-closed screening for the 100-reference expansion (not publication).

The checklist intentionally cannot certify literature, semantic novelty or PIT.
It records those independent reviews and only counts committed Gold receipts.
No return labels or historical research performance are read here.
"""
from __future__ import annotations

import hashlib
from collections import Counter

import numpy as np
import pandas as pd


QUOTAS = {"academic": 20, "aqr": 10, "other_quant_firm": 10}


def fingerprint(formula: str) -> str:
    """Lexical duplicate check only; algebraic/semantic review remains required."""
    return hashlib.sha256("".join(formula.lower().split()).encode()).hexdigest()


def screen(candidate, *, existing_ids=(), existing_formulas=(), existing_concepts=()):
    failures = []
    if candidate["id"] in existing_ids:
        failures.append("EXISTING_ID")
    formula = candidate.get("formula")
    if not formula:
        failures.append("EXACT_FORMULA_NOT_REVIEWED")
    elif fingerprint(formula) in {fingerprint(f) for f in existing_formulas}:
        failures.append("EXACT_FORMULA_DUPLICATE")
    if candidate.get("concept_key") in existing_concepts:
        failures.append("EXISTING_CONCEPT_OR_HORIZON_VARIANT")
    for field, failure in (
        ("primary_formula_reviewed", "PRIMARY_FORMULA_REVIEW_REQUIRED"),
        ("semantic_novelty_reviewed", "SEMANTIC_DUPLICATE_REVIEW_REQUIRED"),
        ("source_contract_verified", "SOURCE_CONTRACT_REQUIRED"),
        ("availability_reviewed", "AVAILABILITY_REVIEW_REQUIRED"),
        ("independent_parity_passed", "INDEPENDENT_CALCULATION_REQUIRED"),
    ):
        if candidate.get(field) is not True:
            failures.append(failure)
    if not candidate.get("source_url") or not candidate.get("source_locator"):
        failures.append("PRIMARY_SOURCE_LOCATOR_REQUIRED")
    if candidate.get("assets", 0) < 100 or candidate.get("observed_months", 0) < 60:
        failures.append("INSUFFICIENT_MEASUREMENT_COVERAGE")
    failures.extend(candidate.get("data_blockers", []))
    return {"id": candidate["id"], "eligible": not failures,
            "failures": sorted(set(failures)), "alpha_approved": False}


def field_coverage(frame):
    """Describe actual feature cells, not firms with certified first-release PIT."""
    if frame.empty or not {"asset_id", "date", "market"} <= set(frame):
        raise ValueError("Nonempty asset-month feature panel required")
    if frame.duplicated(["asset_id", "date"]).any():
        raise ValueError("Duplicate asset-month input")
    records = []
    numeric = [c for c in frame if c.startswith(("fy_", "prev_fy_"))
               and pd.api.types.is_numeric_dtype(frame[c])]
    for market, group in [("TOTAL", frame), *frame.groupby("market", sort=True)]:
        for field in numeric:
            valid = group[field].notna() & np.isfinite(group[field])
            records.append(dict(market=market, field=field, denominator=len(group),
                                nonnull=int(valid.sum()), fraction=float(valid.mean()),
                                assets=int(group.loc[valid, "asset_id"].nunique()),
                                months=int(group.loc[valid, "date"].nunique())))
    return records


def completion(existing_ids, new_references):
    """Count only unique additions backed by a committed all-row verified receipt.

    Each reference has one primary quota bucket: overlapping source affiliations
    never multiply the count. This does not itself replace live DB verification.
    """
    original = set(existing_ids)
    seen = set(original)
    quotas = Counter()
    for ref in new_references:
        if ref["id"] in seen:
            raise ValueError("Duplicate reference ID in completion claims")
        receipt = ref.get("receipt", {})
        if (receipt.get("outer_transaction_committed") is not True
                or receipt.get("status") not in {"PUBLISHED", "ALREADY_PUBLISHED"}
                or receipt.get("readback_rows", 0) <= 0
                or not receipt.get("dataset_id") or not receipt.get("readback_sha256")):
            raise ValueError("A candidate or dry run is not a Gold-loaded reference")
        publication = ref.get("publication", {})
        definitions = publication.get("definitions", {})
        if (ref["id"] not in definitions
                or publication.get("dataset_id") != receipt["dataset_id"]
                or publication.get("row_count") != receipt["readback_rows"]
                or receipt.get("reference_count") != len(definitions)
                or publication.get("profitability_approved") is not False
                or definitions[ref["id"]].get("quota_bucket") != ref.get("quota_bucket")):
            raise ValueError("Reference/source quota must bind the exact committed publication")
        if ref.get("quota_bucket") not in QUOTAS:
            raise ValueError("Exactly one known primary source bucket required")
        seen.add(ref["id"])
        quotas[ref["quota_bucket"]] += 1
    shortages = {k: max(0, n - quotas[k]) for k, n in QUOTAS.items()}
    return dict(existing=len(original), new_loaded=len(seen) - len(original),
                total_loaded=len(seen), minimum_total=100,
                source_counts=dict(quotas), source_shortfalls=shortages,
                total_shortfall=max(0, 100 - len(seen)),
                complete=len(seen) >= 100 and not any(shortages.values()))
