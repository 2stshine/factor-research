"""Bounded, exact Gold dataset collections for the active reference program.

``load_reference_collection(conn, repo_root, *, reference_ids=None,
snapshot_path=None)`` reads a program-v2 collection. Each entry is an immutable
same-generation Gold dataset with at most seven definitions (new publications
normally use <=3; the seven-definition first dataset remains valid). Selection
loads/verifies every row of each involved dataset before projecting requested
references. No latest, legacy, file-only, partial-verification or missing-group
fallback exists. A cache directory must contain exact ``<dataset_id>.parquet``
regular, non-symlink files; each is still verified against the live database.

Return value is ``(seven_column_frame, collection_metadata)`` compatible with
``phenomenon_references.reference_fields``. ``metadata.dataset_id`` is a
content hash of the collection manifest, NOT a Gold dataset ID. Metadata labels
that distinction, retains every constituent dataset ID/source version, and
does not pretend independently captured sources share one source snapshot.
The same collection identity is returned for different selected subsets;
``selected_reference_ids`` identifies the exact returned projection.

``read_collection_program(repo_root)`` validates all local bindings without a
database call and returns ``(program, catalog_by_id, active_generation)``.
This module does not create programs, modify pointers, publish or approve alpha.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import pandas as pd

from engine import reference_gold as gold
from engine.reference_library import definition_hash, load_catalog
from engine.research_generation import digest, load_active_generation


PROGRAM_SCHEMA = "phenomenon-program-v2"
PROGRAM_PATH = Path("research/phenomena/program.json")
PROGRAM_FIELDS = {"schema_version", "generation_id", "catalog_path", "catalog_sha256",
                  "reference_datasets", "legacy_gold_policy", "program_sha256"}
COLLECTION_SCHEMA = "phenomenon-reference-collection-v1"
MAX_DATASETS = 128
MAX_REFERENCES_PER_DATASET = 7


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(value):
    return isinstance(value,str) and bool(re.fullmatch(r"[a-f0-9]{64}",value))


def _regular(path: Path):
    _require(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),
             "Missing or symlinked collection file; fallback forbidden")
    return path


def read_collection_program(repo_root):
    """Strict active-generation, path, catalog and unique partition validation."""
    root=Path(repo_root).absolute()
    _require(".." not in root.parts, "Unnormalized repository path forbidden")
    generation=load_active_generation(root)
    _require(generation["generation_id"]==gold.GENERATION,
             "Active generation is not phenomenon-research-v1; legacy fallback forbidden")
    program=json.loads(_regular(root/PROGRAM_PATH).read_bytes())
    _require(isinstance(program,dict) and set(program)==PROGRAM_FIELDS,
             "Exact phenomenon collection program schema required")
    _require(program["schema_version"]==PROGRAM_SCHEMA and program["generation_id"]==gold.GENERATION
             and program["legacy_gold_policy"]=="EXCLUDED_NO_FALLBACK", "Collection generation/policy mismatch")
    _require(_sha(program["catalog_sha256"]) and _sha(program["program_sha256"]), "Invalid collection SHA256")
    _require(program["program_sha256"]==digest({k:v for k,v in program.items() if k!="program_sha256"}),
             "Collection program content hash mismatch")
    raw_path=program["catalog_path"]
    _require(isinstance(raw_path,str) and bool(raw_path) and "\\" not in raw_path and "\x00" not in raw_path,
             "Safe relative catalog path required")
    relative=PurePosixPath(raw_path)
    _require(not relative.is_absolute() and ".." not in relative.parts and "." not in relative.parts
             and relative.as_posix()==raw_path and relative.suffix==".json", "Safe relative catalog path required")
    catalog_path=_regular(root/relative)
    _require(hashlib.sha256(catalog_path.read_bytes()).hexdigest()==program["catalog_sha256"],
             "Collection catalog bytes differ from program binding")
    catalog={item["id"]:item for item in load_catalog(catalog_path)}
    datasets=program["reference_datasets"]
    _require(isinstance(datasets,list) and 0<len(datasets)<=MAX_DATASETS, "Bounded nonempty dataset collection required")
    dataset_ids=set(); reference_ids=set()
    for entry in datasets:
        _require(isinstance(entry,dict) and set(entry)=={"dataset_id","reference_ids"}
                 and _sha(entry["dataset_id"]), "Exact dataset/reference binding required")
        _require(entry["dataset_id"] not in dataset_ids, "Duplicate collection dataset")
        dataset_ids.add(entry["dataset_id"])
        refs=entry["reference_ids"]
        _require(isinstance(refs,list) and 0<len(refs)<=MAX_REFERENCES_PER_DATASET
                 and all(isinstance(ref,str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*",ref) for ref in refs),
                 "Bounded nonempty reference ID list required")
        _require(len(refs)==len(set(refs)) and not reference_ids.intersection(refs),
                 "Reference assigned more than once in collection")
        reference_ids.update(refs)
        _require(set(refs)<=set(catalog), "Collection reference absent from exact catalog")
        _require(all(catalog[ref]["readiness"]["status"]=="IMPLEMENTED_REQUIRES_ATTESTATION" for ref in refs),
                 "Collection cannot expose blocked definitions")
    return program,catalog,generation


def _selected(program, reference_ids):
    all_refs={ref for entry in program["reference_datasets"] for ref in entry["reference_ids"]}
    if reference_ids is None:
        return sorted(all_refs)
    _require(isinstance(reference_ids,(list,tuple)) and bool(reference_ids)
             and all(isinstance(ref,str) for ref in reference_ids), "Explicit nonempty reference selection required")
    _require(len(reference_ids)==len(set(reference_ids)) and set(reference_ids)<=all_refs,
             "Unknown or duplicate selected collection reference")
    return sorted(reference_ids)


def _cache_files(snapshot_path, entries):
    if snapshot_path is None:
        return {}
    directory=Path(snapshot_path).absolute()
    _require(".." not in directory.parts and directory.is_dir()
             and not any(part.is_symlink() for part in (directory,*directory.parents)),
             "Collection snapshot_path must be an explicit regular non-symlink directory")
    return {entry["dataset_id"]:_regular(directory/(entry["dataset_id"]+".parquet")) for entry in entries}


def load_reference_collection(conn, repo_root, *, reference_ids=None, snapshot_path=None):
    """Verify bounded datasets individually, then return the selected raw union.

    This is not an authorization shortcut: no file can replace a Gold lookup.
    Prefer explicit reference selection for large collections. Full collection
    reads concatenate typed DataFrames, but never canonicalize all rows at once.
    """
    # Local import prevents a cycle with the public v1/v2 dispatch module.
    from engine.phenomenon_references import _definitions, _validated_frame
    program,catalog,generation=read_collection_program(repo_root)
    selected=_selected(program,reference_ids)
    chosen=set(selected)
    entries=[entry for entry in program["reference_datasets"] if chosen.intersection(entry["reference_ids"])]
    caches=_cache_files(snapshot_path,entries)
    outputs=[]; definitions={}; datasets=[]
    for entry in entries:
        dataset_id=entry["dataset_id"]
        options={"snapshot_path":caches[dataset_id]} if dataset_id in caches else {}
        frame,metadata=gold.load_library(conn,dataset_id=dataset_id,generation_id=gold.GENERATION,**options)
        _require(isinstance(metadata,dict) and metadata.get("dataset_id")==dataset_id,
                 "Gold loader returned a different collection dataset")
        published=_definitions(metadata)
        _require(isinstance(metadata.get("source_version"),str) and bool(metadata["source_version"].strip())
                 and _sha(metadata.get("input_sha256")), "Explicit collection source version/input digest required")
        _require(set(published)==set(entry["reference_ids"]), "Gold dataset definitions differ from exact collection partition")
        for ref,definition in published.items():
            _require(definition_hash(definition)==definition_hash(catalog[ref]),
                     "Published collection definition differs from active catalog")
        # The underlying loader verifies all rows/content against publication;
        # validate row-to-definition identity even when only one ref is wanted.
        checked=_validated_frame(frame,metadata)
        _require(set(checked.reference_id)==set(published), "Collection dataset has no values for a declared reference")
        wanted=chosen.intersection(published)
        projected=checked.loc[checked.reference_id.isin(wanted)].copy()
        outputs.append(projected)
        definitions.update({ref:published[ref] for ref in wanted})
        datasets.append({"dataset_id":dataset_id,"reference_ids":list(entry["reference_ids"]),
                         "selected_reference_ids":sorted(wanted),"source_version":metadata.get("source_version"),
                         "input_sha256":metadata.get("input_sha256"),"value_rows":len(checked),
                         "selected_rows":len(projected)})
        del frame,checked,projected,metadata
    combined=pd.concat(outputs,ignore_index=True)
    # Cross-dataset identity conflicts are not visible to any constituent read.
    identities=combined[["asset_id","date","stock_code"]].drop_duplicates()
    _require(not identities.duplicated(["asset_id","date"]).any()
             and not identities.duplicated(["stock_code","date"]).any(),
             "Conflicting historical identity across collection datasets")
    _require(not combined.duplicated(["reference_id","asset_id","date"]).any(),
             "Duplicate collection reference asset-month")
    manifest={"schema_version":COLLECTION_SCHEMA,"generation_id":gold.GENERATION,
              "program_sha256":program["program_sha256"],"catalog_sha256":program["catalog_sha256"],
              "reference_datasets":program["reference_datasets"]}
    collection_id=digest(manifest)
    metadata={"dataset_id":collection_id,"dataset_kind":"REFERENCE_COLLECTION_NOT_A_GOLD_DATASET",
              "collection_id":collection_id,"collection_manifest":manifest,
              "collection_program_sha256":program["program_sha256"],"generation_id":gold.GENERATION,
              "role":gold.ROLE,"profitability_approved":False,"legacy_gold_used":False,
              "definitions":definitions,"selected_reference_ids":selected,
              "reference_datasets":datasets,"source_version":"MULTI_SNAPSHOT_REFERENCE_COLLECTION",
              "source_versions":{item["dataset_id"]:item["source_version"] for item in datasets},
              "source_snapshot_policy":"EACH_DATASET_IMMUTABLE_INDEPENDENT_SNAPSHOT_NO_COMMON_VINTAGE_ASSUMED",
              "value_rows":len(combined)}
    after,_,after_generation=read_collection_program(repo_root)
    _require(after==program and after_generation==generation,
             "Active collection program/generation changed during read; retry explicit current binding")
    return combined,metadata
