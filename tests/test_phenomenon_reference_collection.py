"""Collection composition integrity; fixtures do not certify production Gold."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from engine import phenomenon_reference_collection as collection
from engine import phenomenon_references as references
from engine import reference_gold as gold
from engine.reference_library import CATALOG_PATH, definition_hash, load_catalog
from engine.research_generation import canonical, digest, make_generation


def write_program(root,program):
    program={k:v for k,v in program.items() if k!="program_sha256"}
    program["program_sha256"]=digest(program)
    (root/collection.PROGRAM_PATH).write_bytes(canonical(program)+b"\n")
    return program


@pytest.fixture
def setup(tmp_path,monkeypatch):
    root=tmp_path/"repo"
    generation=make_generation(generation_id=gold.GENERATION)
    path=Path("research/generations")/gold.GENERATION/(generation["generation_sha256"]+".json")
    (root/path).parent.mkdir(parents=True)
    (root/path).write_bytes(canonical(generation)+b"\n")
    pointer={"schema_version":"active-research-generation-v1","generation_id":gold.GENERATION,
             "generation_sha256":generation["generation_sha256"],"manifest_path":path.as_posix(),
             "legacy_gold_policy":"EXCLUDED_NO_FALLBACK"}
    pointer["pointer_sha256"]=digest(pointer)
    (root/"research/active-generation.json").write_bytes(canonical(pointer)+b"\n")
    catalog_path="research/phenomena/reference-catalog-expansion-test.json"
    (root/catalog_path).parent.mkdir(parents=True)
    (root/catalog_path).write_bytes(CATALOG_PATH.read_bytes())
    ready=[d for d in load_catalog() if d["readiness"]["status"]=="IMPLEMENTED_REQUIRES_ATTESTATION"]
    groups=[ready[:2],ready[2:4],ready[4:7]]
    assert len(ready)>=7
    entries=[{"dataset_id":digit*64,"reference_ids":[d["id"] for d in group]}
             for digit,group in zip("abc",groups)]
    program=write_program(root,{"schema_version":collection.PROGRAM_SCHEMA,"generation_id":gold.GENERATION,
        "catalog_path":catalog_path,"catalog_sha256":hashlib.sha256((root/catalog_path).read_bytes()).hexdigest(),
        "reference_datasets":entries,"legacy_gold_policy":"EXCLUDED_NO_FALLBACK"})
    store={}
    for entry,group in zip(entries,groups):
        definitions={d["id"]:d for d in group}
        rows=[{"reference_id":ref,"definition_hash":definition_hash(definitions[ref]),
               "asset_id":asset,"stock_code":{1:"005930",2:"0037T0"}[asset],"date":"2025-01-31",
               "known_at":"2025-01-31T16:00:00+09:00","value":float(asset)}
              for ref in entry["reference_ids"] for asset in [1,2]]
        metadata={"dataset_id":entry["dataset_id"],"generation_id":gold.GENERATION,"role":gold.ROLE,
                  "profitability_approved":False,"legacy_gold_used":False,"definitions":definitions,
                  "source_version":"independent-source-"+entry["dataset_id"][0],"input_sha256":entry["dataset_id"]}
        store[entry["dataset_id"]]=(pd.DataFrame(rows),metadata)
    calls=[]
    def loader(conn,**kwargs):
        calls.append(kwargs)
        frame,metadata=store[kwargs["dataset_id"]]
        return frame.copy(),deepcopy(metadata)
    monkeypatch.setattr(gold,"load_library",loader)
    return root,program,store,calls


def test_full_collection_exact_bound_datasets_and_provenance(setup):
    root,program,store,calls=setup
    frame,metadata=references.load_active_references(None,root)
    assert len(frame)==14 and len(calls)==3
    assert metadata["dataset_id"]==digest(metadata["collection_manifest"])
    assert metadata["dataset_kind"]=="REFERENCE_COLLECTION_NOT_A_GOLD_DATASET"
    assert metadata["dataset_id"] not in store
    assert metadata["collection_program_sha256"]==program["program_sha256"]
    assert len(metadata["definitions"])==7
    assert len(metadata["source_versions"])==3
    assert not metadata["profitability_approved"] and not metadata["legacy_gold_used"]
    assert all(call["generation_id"]==gold.GENERATION for call in calls)
    field=references.reference_fields(frame,metadata,[program["reference_datasets"][0]["reference_ids"][0]])
    assert field.attrs["dataset_kind"]==metadata["dataset_kind"]
    assert field.attrs["source_versions"]==metadata["source_versions"]


def test_selected_reference_loads_whole_containing_dataset_only(setup):
    root,program,store,calls=setup
    entry=program["reference_datasets"][1]
    requested=[entry["reference_ids"][0]]
    frame,metadata=references.load_active_references(None,root,reference_ids=requested)
    assert calls==[{"dataset_id":entry["dataset_id"],"generation_id":gold.GENERATION}]
    assert set(frame.reference_id)==set(metadata["definitions"])==set(requested)
    assert metadata["reference_datasets"][0]["value_rows"]==len(store[entry["dataset_id"]][0])
    assert metadata["reference_datasets"][0]["selected_rows"]==2


def test_collection_identity_independent_of_selected_projection(setup):
    root,program,_,_=setup
    ids=[entry["reference_ids"][0] for entry in program["reference_datasets"]]
    left=references.load_active_references(None,root,reference_ids=ids[:1])[1]
    right=references.load_active_references(None,root,reference_ids=ids[1:])[1]
    assert left["collection_id"]==right["collection_id"]
    assert left["selected_reference_ids"]!=right["selected_reference_ids"]


@pytest.mark.parametrize("change",["extra","hash","policy","generation","duplicate_dataset","duplicate_reference",
                                     "abs_catalog","escape_catalog","normalized_catalog","missing_catalog","unknown_ref","empty_groups"])
def test_invalid_program_fails_before_any_gold_access(setup,change):
    root,program,_,calls=setup
    if change=="extra":program["latest_fallback"]=True
    elif change=="hash":program["catalog_sha256"]="0"*64
    elif change=="policy":program["legacy_gold_policy"]="ALLOW"
    elif change=="generation":program["generation_id"]="reference-factor-v3"
    elif change=="duplicate_dataset":program["reference_datasets"][1]["dataset_id"]=program["reference_datasets"][0]["dataset_id"]
    elif change=="duplicate_reference":program["reference_datasets"][1]["reference_ids"][0]=program["reference_datasets"][0]["reference_ids"][0]
    elif change=="abs_catalog":program["catalog_path"]="/tmp/catalog.json"
    elif change=="escape_catalog":program["catalog_path"]="../catalog.json"
    elif change=="normalized_catalog":program["catalog_path"]="research/./phenomena/reference-catalog-expansion-test.json"
    elif change=="missing_catalog":program["catalog_path"]="missing.json"
    elif change=="unknown_ref":program["reference_datasets"][0]["reference_ids"][0]="legacy_alpha"
    else:program["reference_datasets"]=[]
    write_program(root,program)
    with pytest.raises(ValueError):references.load_active_references(None,root)
    assert not calls


@pytest.mark.parametrize("requested",[[],["unknown"],[1],["kr_size_issue_v1","kr_size_issue_v1"],"kr_size_issue_v1"])
def test_bad_selected_projection_does_not_query(setup,requested):
    root,_,_,calls=setup
    with pytest.raises(ValueError):references.load_active_references(None,root,reference_ids=requested)
    assert not calls


@pytest.mark.parametrize("change",["dataset","generation","alpha","legacy","definition","missing_definition","extra_definition",
                                     "row_hash","future","missing_ref_values","row_label","source_version","input_digest"])
def test_corrupt_gold_group_cannot_enter_collection(setup,change):
    root,program,store,_=setup
    dataset_id=program["reference_datasets"][0]["dataset_id"]
    frame,metadata=store[dataset_id]
    ref=next(iter(metadata["definitions"]))
    if change=="dataset":metadata["dataset_id"]="f"*64
    elif change=="generation":metadata["generation_id"]="reference-factor-v3"
    elif change=="alpha":metadata["profitability_approved"]=True
    elif change=="legacy":metadata["legacy_gold_used"]=True
    elif change=="source_version":metadata["source_version"]=""
    elif change=="input_digest":metadata["input_sha256"]="not_bound"
    elif change=="definition":
        definition=metadata["definitions"][ref]
        definition["formula"]="different"
        definition["definition_hash"]=definition_hash(definition)
    elif change=="missing_definition":metadata["definitions"].pop(ref)
    elif change=="extra_definition":
        extra=next(d for d in load_catalog() if d["id"] not in metadata["definitions"] and d["readiness"]["status"]=="IMPLEMENTED_REQUIRES_ATTESTATION")
        metadata["definitions"][extra["id"]]=extra
    elif change=="row_hash":frame.loc[0,"definition_hash"]="f"*64
    elif change=="future":frame.loc[0,"known_at"]="2025-02-01T00:00:00+09:00"
    elif change=="missing_ref_values":frame=frame[~frame.reference_id.eq(ref)]
    elif change=="row_label":frame["fwd_return"]=1.
    store[dataset_id]=(frame,metadata)
    with pytest.raises(ValueError):references.load_active_references(None,root)


def test_unselected_row_in_loaded_group_is_still_checked(setup):
    root,program,store,_=setup
    entry=program["reference_datasets"][0]
    requested,unwanted=entry["reference_ids"]
    frame,_=store[entry["dataset_id"]]
    frame.loc[frame.reference_id.eq(unwanted),"known_at"]="2025-02-01T00:00:00+09:00"
    with pytest.raises(ValueError,match="unavailable"):
        references.load_active_references(None,root,reference_ids=[requested])


def test_cross_dataset_historic_identity_conflicts_fail(setup):
    root,program,store,_=setup
    frame,_=store[program["reference_datasets"][1]["dataset_id"]]
    frame.loc[frame.asset_id.eq(1),"stock_code"]="999990"
    with pytest.raises(ValueError,match="across collection"):
        references.load_active_references(None,root)


def test_snapshot_directory_routes_exact_cache_files_and_keeps_db_required(setup,tmp_path):
    root,program,_,calls=setup
    directory=tmp_path/"cache"
    directory.mkdir()
    for entry in program["reference_datasets"]:
        # Loader mocked here: underlying Gold loader has independent parquet +
        # all-row binary verification tests. A cache never bypasses that call.
        (directory/(entry["dataset_id"]+".parquet")).write_bytes(b"test transport placeholder")
    references.load_active_references(None,root,snapshot_path=directory)
    assert len(calls)==3
    assert all(call["snapshot_path"]==directory/(call["dataset_id"]+".parquet") for call in calls)


@pytest.mark.parametrize("kind",["file_not_dir","missing_cache","symlink_dir","symlink_file"])
def test_unsafe_or_incomplete_cache_is_rejected_before_db(setup,tmp_path,kind):
    root,program,_,calls=setup
    directory=tmp_path/"cache"
    if kind=="file_not_dir":directory.write_bytes(b"not directory")
    else:
        directory.mkdir()
        if kind=="symlink_dir":
            alternate=tmp_path/"linked"
            alternate.symlink_to(directory,target_is_directory=True)
            directory=alternate
        elif kind=="symlink_file":
            target=tmp_path/"target.parquet";target.write_bytes(b"untrusted")
            (directory/(program["reference_datasets"][0]["dataset_id"]+".parquet")).symlink_to(target)
    with pytest.raises(ValueError):references.load_active_references(None,root,snapshot_path=directory)
    assert not calls


def test_gold_error_cannot_fallback_to_cache_or_skip_group(setup,monkeypatch):
    root,_,_,_=setup
    def unavailable(*_,**__):raise ConnectionError("database unavailable")
    monkeypatch.setattr(gold,"load_library",unavailable)
    with pytest.raises(ConnectionError):references.load_active_references(None,root)


def test_active_program_change_during_read_is_detected(setup,monkeypatch):
    root,program,store,_=setup
    called=[]
    def change_program(conn,*,dataset_id,generation_id):
        called.append(dataset_id)
        if len(called)==1:
            changed=deepcopy(program)
            changed["reference_datasets"]=list(reversed(changed["reference_datasets"]))
            write_program(root,changed)
        return store[dataset_id]
    monkeypatch.setattr(gold,"load_library",change_program)
    with pytest.raises(ValueError,match="changed during read"):
        references.load_active_references(None,root)


def test_same_generation_original_seven_can_remain_one_exact_dataset(setup):
    root,program,store,calls=setup
    first=program["reference_datasets"][0]["dataset_id"]
    frames=[];definitions={};all_refs=[]
    for entry in program["reference_datasets"]:
        frame,metadata=store[entry["dataset_id"]]
        frames.append(frame);definitions.update(metadata["definitions"]);all_refs.extend(entry["reference_ids"])
    metadata=deepcopy(store[first][1]);metadata["definitions"]=definitions
    store[first]=(pd.concat(frames,ignore_index=True),metadata)
    program["reference_datasets"]=[{"dataset_id":first,"reference_ids":all_refs}]
    write_program(root,program)
    frame,metadata=references.load_active_references(None,root)
    assert len(frame)==14 and len(calls)==1 and len(metadata["definitions"])==7
