"""Exact active-program reference retrieval, never legacy or latest fallback.

Gold measurements are not a strategy universe, forward-return label, execution
calendar, PIT claim, or alpha approval. Consumers must bind those separately.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

from engine import reference_gold as gold
from engine.reference_library import definition_hash, load_catalog, validate_catalog
from engine.research_generation import digest, load_active_generation


PROGRAM_SCHEMA = "phenomenon-program-v1"
PROGRAM_PATH = Path("research/phenomena/program.json")
CATALOG_PATH = Path("research/phenomena/reference-catalog.json")
PROGRAM_FIELDS = {"schema_version", "generation_id", "catalog_sha256", "reference_dataset_id",
                  "legacy_gold_policy", "program_sha256"}
VALUE_COLUMNS = {"reference_id", "definition_hash", "asset_id", "stock_code", "date", "known_at", "value"}
KEYS = ["asset_id", "date", "stock_code"]


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _regular(path):
    _require(not any(part.is_symlink() for part in (path, *path.parents)) and path.is_file(),
             "Missing or symlinked program/catalog file; fallback forbidden")
    return path


def _definitions(metadata):
    _require(isinstance(metadata, dict) and metadata.get("generation_id") == gold.GENERATION
             and metadata.get("role") == gold.ROLE and metadata.get("profitability_approved") is False
             and metadata.get("legacy_gold_used") is False,
             "Reference metadata must be current-generation measurements, not alpha/legacy data")
    definitions = metadata.get("definitions")
    _require(isinstance(definitions, dict) and bool(definitions), "Explicit nonempty reference definitions required")
    validate_catalog(list(definitions.values()))
    for key, definition in definitions.items():
        _require(key == definition["id"] and definition["readiness"]["status"] == "IMPLEMENTED_REQUIRES_ATTESTATION",
                 "Reference definition identity/readiness mismatch")
        _require(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key) and key not in VALUE_COLUMNS
                 and not key.endswith("__known_at"), "Unsafe reference field name")
    return definitions


def load_active_references(conn, repo_root, *, snapshot_path=None, reference_ids=None):
    """Read only the exact active program's catalog-bound Gold dataset.

    Existing generation pointer validation and Gold read-back digest validation
    are reused. No database query occurs when local program validation fails.
    An optional exact parquet snapshot reduces network transfer only; Gold's
    loader must still validate database metadata and every persisted row.
    """
    root = Path(repo_root).absolute()
    generation = load_active_generation(root)
    _require(generation["generation_id"] == gold.GENERATION,
             "Active generation is not phenomenon-research-v1; legacy fallback forbidden")
    program = json.loads(_regular(root / PROGRAM_PATH).read_bytes())
    if isinstance(program, dict) and program.get("schema_version") == "phenomenon-program-v2":
        from engine.phenomenon_reference_collection import load_reference_collection
        return load_reference_collection(conn, root, snapshot_path=snapshot_path, reference_ids=reference_ids)
    _require(isinstance(program, dict) and set(program) == PROGRAM_FIELDS,
             "Exact phenomenon program schema required")
    _require(program["schema_version"] == PROGRAM_SCHEMA and program["generation_id"] == generation["generation_id"]
             and program["legacy_gold_policy"] == "EXCLUDED_NO_FALLBACK", "Program generation/policy mismatch")
    for key in ("catalog_sha256", "reference_dataset_id", "program_sha256"):
        _require(isinstance(program[key], str) and re.fullmatch(r"[a-f0-9]{64}", program[key]), "Invalid program SHA256")
    _require(program["program_sha256"] == digest({k: v for k, v in program.items() if k != "program_sha256"}),
             "Program content hash mismatch")
    catalog_path = _regular(root / CATALOG_PATH)
    _require(hashlib.sha256(catalog_path.read_bytes()).hexdigest() == program["catalog_sha256"],
             "Active catalog bytes differ from program binding")
    catalog = {item["id"]: item for item in load_catalog(catalog_path)}
    options = {"snapshot_path": snapshot_path} if snapshot_path is not None else {}
    frame, metadata = gold.load_library(conn, dataset_id=program["reference_dataset_id"],
                                       generation_id=generation["generation_id"], **options)
    _require(metadata.get("dataset_id") == program["reference_dataset_id"], "Gold loader returned a different dataset")
    definitions = _definitions(metadata)
    for reference_id, definition in definitions.items():
        _require(reference_id in catalog and definition_hash(definition) == definition_hash(catalog[reference_id]),
                 "Published definition differs from active catalog")
    # Verify the row-to-definition relation independently of adapter delegation.
    _validated_frame(frame, metadata)
    if reference_ids is not None:
        _require(isinstance(reference_ids, (list, tuple)) and reference_ids
                 and all(isinstance(ref, str) for ref in reference_ids)
                 and len(reference_ids) == len(set(reference_ids)) and set(reference_ids) <= set(definitions),
                 "Explicit unique dataset reference selection required")
        frame = frame.loc[frame.reference_id.isin(reference_ids)].copy()
        _require(not frame.empty, "No selected measurements; fallback forbidden")
        metadata = {**metadata, "selected_reference_ids": list(reference_ids)}
    return frame, metadata


def _validated_frame(frame, metadata):
    definitions = _definitions(metadata)
    _require(isinstance(frame, pd.DataFrame) and not frame.empty and frame.columns.is_unique
             and set(frame) == VALUE_COLUMNS, "Exact nonempty Gold reference value schema required")
    result = frame.copy()
    _require(not result[list(VALUE_COLUMNS)].isna().any().any(), "Gold value identity/time/measurement cannot be null")
    _require(result.asset_id.map(lambda x: isinstance(x, (str, int, np.integer)) and not isinstance(x, bool)
                                 and str(x).isdigit() and str(int(x)) == str(x) and int(x) > 0).all(),
             "Positive stable integer asset_id required")
    result["asset_id"] = result.asset_id.astype("int64")
    _require(result.stock_code.map(lambda x: isinstance(x, str) and bool(re.fullmatch(r"[0-9A-Z]{6}", x))).all(),
             "Canonical six-character stock_code strings required")
    result["date"] = pd.to_datetime(result.date, errors="raise")
    _require(result.date.dt.tz is None and result.date.dt.is_month_end.all()
             and result.date.eq(result.date.dt.normalize()).all(), "Formation dates must be calendar month-end")
    _require(result.known_at.map(lambda x: pd.Timestamp(x).tzinfo is not None).all(), "Aware reference known_at required")
    result["known_at"] = pd.to_datetime(result.known_at, utc=True)
    cutoff = (result.date.dt.tz_localize("Asia/Seoul") + pd.Timedelta(days=1)).dt.tz_convert("UTC")
    _require(result.known_at.lt(cutoff).all(), "Reference was unavailable at month-end cutoff")
    _require(pd.api.types.is_numeric_dtype(result.value) and not pd.api.types.is_bool_dtype(result.value)
             and np.isfinite(result.value).all(), "Finite numeric raw reference values required")
    _require(not result.duplicated(["reference_id", "asset_id", "date"]).any(), "Duplicate reference asset-month")
    identity = result[KEYS].drop_duplicates()
    _require(not identity.duplicated(["asset_id", "date"]).any() and not identity.duplicated(["stock_code", "date"]).any(),
             "Conflicting historical asset/ticker mapping")
    _require(set(result.reference_id) <= set(definitions), "Values refer to an undeclared reference")
    expected = result.reference_id.map({key: definition_hash(value) for key, value in definitions.items()})
    _require(result.definition_hash.eq(expected).all(), "Value definition hash mismatch")
    return result


def reference_fields(frame, metadata, reference_ids):
    """Outer-union pivot of raw measurements and their individual known-at clocks.

    Missing combinations remain NaN/NaT. The union is not an eligibility universe;
    no rank, sign, imputation, return, date expansion or market-cap is fabricated.
    A consumer must explicitly join its reviewed population and execution inputs.
    """
    _require(isinstance(reference_ids, (list, tuple)) and reference_ids
             and all(isinstance(ref, str) for ref in reference_ids)
             and len(reference_ids) == len(set(reference_ids)), "Explicit unique reference IDs required")
    source = _validated_frame(frame, metadata)
    definitions = metadata["definitions"]
    _require(set(reference_ids) <= set(definitions), "Requested reference is not in this exact dataset")
    selected = source.loc[source.reference_id.isin(reference_ids)]
    _require(not selected.empty, "No selected measurements; no fallback or synthetic universe")
    result = selected[KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    for reference_id in reference_ids:
        values = selected.loc[selected.reference_id.eq(reference_id), [*KEYS, "value", "known_at"]]
        values = values.rename(columns={"value": reference_id, "known_at": reference_id + "__known_at"})
        result = result.merge(values, on=KEYS, how="left", validate="one_to_one")
    result.attrs = {"dataset_id": metadata["dataset_id"], "generation_id": metadata["generation_id"],
                    "role": "MEASUREMENT_CONTROL", "alpha_approved": False,
                    "reference_ids": list(reference_ids), "row_policy": "OUTER_UNION_OF_SELECTED_MEASUREMENTS_NOT_ELIGIBILITY",
                    "missing_counts": {ref: int(result[ref].isna().sum()) for ref in reference_ids},
                    "definition_hashes": {ref: definition_hash(definitions[ref]) for ref in reference_ids},
                    "source_version": metadata.get("source_version"), "imputed": False}
    for key in ("dataset_kind", "collection_program_sha256", "source_versions", "reference_datasets"):
        if key in metadata:
            result.attrs[key] = metadata[key]
    return result
