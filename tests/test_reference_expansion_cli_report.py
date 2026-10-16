"""CLI/report contract tests with mocked source transport and Gold aggregates."""
from copy import deepcopy
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from engine import reference_gold as gold,reference_library as base,reference_library_v2 as library
from engine import reference_expansion_formulas as financial
from engine.research_generation import canonical,digest
from scripts import reference_expansion as capture
from scripts import report_reference_expansion as reporting
from scripts import publish_reference_expansion as publisher


def write_json(path,data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_bytes(canonical(data)+b"\n")


class AssetConnection:
    def __init__(self,assets):self.assets=assets;self.commands=[];self.exited=False
    def __enter__(self):return self
    def __exit__(self,*_):self.exited=True;return False
    def cursor(self):return nullcontext(self)
    def execute(self,query):self.commands.append(query)
    def fetchall(self):return [(asset,) for asset in self.assets]


def test_financial_wrapper_exact_readonly_assets_cutoff_batch_and_post_capture_verify(tmp_path,monkeypatch,capsys):
    conn=AssetConnection([2,11,99]);events=[]
    monkeypatch.setattr(capture,"connect",lambda:conn)
    manifest={"source_row_counts":{"core":12,"exact":10,"anchors":5},"manifest_sha256":"a"*64}
    def capture_adapter(connection,assets,start,cutoff,output,*,batch_size):
        assert not connection.exited
        events.append(("capture",connection,assets,start,cutoff,output,batch_size))
        return manifest
    def verify(output):
        assert conn.exited
        events.append(("verify",output))
    monkeypatch.setattr(capture.financial,"capture_annual_ledger",capture_adapter)
    monkeypatch.setattr(capture.financial,"verify_capture",verify)
    output=tmp_path/"financial"
    result=capture.fetch_financial(output,end="2026-09-30")
    assert result is manifest
    assert events[0]==("capture",conn,[2,11,99],"2013-01-01",pd.Timestamp("2026-09-30T15:00:00Z"),output,20)
    assert events[1]==("verify",output)
    assert len(conn.commands)==1 and "instrument_type='common_stock'" in conn.commands[0]
    assert "ORDER BY asset_id" in conn.commands[0] and "gold." not in conn.commands[0]
    report=json.loads(capsys.readouterr().out)
    assert report["status"]=="CAPTURED_NOT_PUBLISHED" and report["assets_investigated"]==3
    assert "password" not in json.dumps(report).lower()


@pytest.mark.parametrize("end",["2026-09-29","2026-09-01","not-a-date"])
def test_bad_financial_end_never_connects(tmp_path,monkeypatch,end):
    calls=[];monkeypatch.setattr(capture,"connect",lambda:calls.append(True))
    with pytest.raises(ValueError):capture.fetch_financial(tmp_path/"financial",end=end)
    assert not calls


def test_capture_or_verification_failure_cannot_print_completed_status(tmp_path,monkeypatch,capsys):
    conn=AssetConnection([1]);monkeypatch.setattr(capture,"connect",lambda:conn)
    monkeypatch.setattr(capture.financial,"capture_annual_ledger",lambda *args,**kwargs:
                        {"source_row_counts":{},"manifest_sha256":"a"*64})
    def reject(_):raise ValueError("incomplete source capture")
    monkeypatch.setattr(capture.financial,"verify_capture",reject)
    with pytest.raises(ValueError,match="incomplete source"):
        capture.fetch_financial(tmp_path/"financial")
    assert "CAPTURED_NOT_PUBLISHED" not in capsys.readouterr().out


@pytest.mark.parametrize("command,default_start",[("fetch-price","2015-01-01"),("fetch-financial","2013-01-01")])
def test_cli_routes_distinct_default_start_dates(tmp_path,monkeypatch,command,default_start):
    calls=[]
    monkeypatch.setattr(capture,"fetch_price",lambda *args,**kwargs:calls.append(("price",args,kwargs)))
    monkeypatch.setattr(capture,"fetch_financial",lambda *args,**kwargs:calls.append(("financial",args,kwargs)))
    output=tmp_path/"output"
    monkeypatch.setattr("sys.argv",["reference_expansion",command,"--output",str(output)])
    capture.main()
    assert calls==[(command.removeprefix("fetch-"),(output,),{"start":default_start,"end":"2026-09-30"})]


def test_financial_cli_forwards_explicit_source_period_without_implicit_publish(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr(capture,"fetch_financial",lambda *args,**kwargs:calls.append((args,kwargs)))
    monkeypatch.setattr("sys.argv",["reference_expansion","fetch-financial","--output",str(tmp_path),
                                    "--start","2010-01-01","--end","2025-12-31"])
    capture.main()
    assert calls==[((tmp_path,),{"start":"2010-01-01","end":"2025-12-31"})]


class InventoryConnection:
    def __init__(self,state):self.state=state
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cursor(self):return self
    def execute(self,query,params=None):self.state.sql.append((query,params));self.query=query
    def fetchall(self):
        return list(self.state.metadata.items()) if 'FROM gold.reference_dataset' in self.query else self.state.inventory


@pytest.fixture
def report_fixture(tmp_path,monkeypatch):
    root=tmp_path/"repo";output=root/"build";output.mkdir(parents=True)
    old_build=root/"old";old_build.mkdir()
    catalog_path=root/"research/phenomena/catalog.json"
    data=library.make_catalog();write_json(catalog_path,data)
    monkeypatch.setattr(library,"CATALOG_PATH",catalog_path)
    monkeypatch.setattr(reporting,"ROOT",root)
    monkeypatch.setattr(reporting,"OLD_BUILD",old_build)
    monkeypatch.setattr(publisher,"MIN_ASSETS",2);monkeypatch.setattr(publisher,"MIN_MONTHS",2)
    monkeypatch.setattr(reporting.gc,"collect",lambda:None)
    catalog={definition["id"]:definition for definition in base.load_catalog(catalog_path)}
    selected=list(financial.FINANCIAL_FORMULAS)[:23]
    groups=[selected[i:i+3] for i in range(0,len(selected),3)]
    entries=[{"dataset_id":reporting.OLD_DATASET,"reference_ids":sorted(base._EXECUTABLE)}]
    entries.extend({"dataset_id":format(i+1,"064x"),"reference_ids":group} for i,group in enumerate(groups))
    program={"schema_version":"phenomenon-program-v2","generation_id":gold.GENERATION,
        "catalog_path":str(catalog_path.relative_to(root)),"catalog_sha256":publisher.sha(catalog_path),
        "reference_datasets":entries,"legacy_gold_policy":"EXCLUDED_NO_FALLBACK"}
    program["program_sha256"]=digest(program)
    old_frames=[];summaries=[];inventory=[];all_frames={}
    for definition in catalog.values():
        ref=definition["id"]
        records=[]
        for asset in (1,2):
            for date in pd.date_range("2020-01-31",periods=2,freq="ME"):
                records.append({"asset_id":str(asset),"stock_code":f"{asset:05d}0","date":date,
                    "known_at":date.tz_localize("Asia/Seoul")+pd.Timedelta(hours=16),
                    "market":"KOSPI" if asset==1 else "KOSDAQ","reference_id":ref,
                    "definition_hash":definition["definition_hash"],"value":float(asset),"oriented_value":float(asset)*definition["orientation"],
                    "source_version":"a"*64,"input_sha256":"b"*64})
        frame=pd.DataFrame(records);all_frames[ref]=frame
        if ref in base._EXECUTABLE:old_frames.append(frame)
        else:
            path=output/"references"/(ref+".parquet");path.parent.mkdir(exist_ok=True)
            frame.to_parquet(path,index=False)
            eligible=ref in selected
            summaries.append({"reference_id":ref,"definition_hash":definition["definition_hash"],
                "assets":2 if eligible else 0,"months":2 if eligible else 0,"value_rows":4 if eligible else 0,
                "eligible_for_publication":eligible,"values_file_sha256":publisher.sha(path),
                "raw_value_diagnostics":{"fixture":"NO_PROFITABILITY_DATA"}})
    old=pd.concat(old_frames,ignore_index=True);old.to_parquet(old_build/"values.parquet",index=False)
    cache=output/"collection-cache";cache.mkdir()
    old.to_parquet(cache/(reporting.OLD_DATASET+".parquet"),index=False)
    # Every new source dataset's local path exists even though live aggregate
    # queries are fake; no report test reaches the user's actual database.
    for entry in entries:
        for ref in entry["reference_ids"]:
            inventory.append((entry["dataset_id"],ref,4,2,2,pd.Timestamp("2020-01-31").date(),pd.Timestamp("2020-02-29").date()))
    panel=next(iter(all_frames.values()))[list(base._BASE)].copy()
    for column in library.FEATURE_COLUMNS:panel[column]=1.
    panel=panel.loc[:,library.ALL_COLUMNS];panel.to_parquet(output/"input.parquet",index=False)
    evidence={"input_rows":4,"assets":2,"first_date":"2020-01-31","last_date":"2020-02-29",
        "input_file_sha256":publisher.sha(output/"input.parquet"),
        "financial_adapter_sha256":publisher.sha(Path(publisher.financial.__file__)),
        "financial_evidence":{"status_counts":{"SOFTWARE_TEST_ONLY":4}}}
    attestation={"status":"CERTIFIED","source_type":library.SOURCE_TYPE,"source_contract":library.SOURCE_CONTRACT,
        "scope":base.INPUT_SCOPE,"identity_contract":base.IDENTITY_CONTRACT,"pit_status":library.PIT_STATUS,
        "first_vintage_independently_verified":False,"source_version":digest(evidence),"evidence_sha256":digest(evidence),
        "input_sha256":library.input_digest(panel),"feature_contracts":library.FEATURE_CONTRACTS,"feature_units":library.FEATURE_UNITS}
    plan={"schema_version":"reference-expansion-publication-plan-v1","generation_id":gold.GENERATION,
        "catalog_sha256":publisher.sha(catalog_path),"input_sha256":attestation["input_sha256"],
        "implementation_sha256":library.implementation_hash(),"minimum_assets":2,"minimum_months":2,
        "existing_dataset_id":reporting.OLD_DATASET,"existing_reference_ids":sorted(base._EXECUTABLE),
        "references":summaries,"eligible_references":selected,"groups":groups,"expected_total_references":30,"alpha_approved":False}
    old_input=panel.loc[:,[*base._BASE,*base.FEATURE_CONTRACTS,*base._COUNTS]].copy()
    old_input.to_parquet(old_build/"input.parquet",index=False)
    old_meta={"generation_id":gold.GENERATION,"role":gold.ROLE,"profitability_approved":False,"legacy_gold_used":False,
        "definitions":{ref:catalog[ref] for ref in sorted(base._EXECUTABLE)},"row_count":len(old),
        "values_sha256":digest(gold.canonical_values(old)),"input_sha256":base.input_panel_digest(old_input),
        "source_version":"ORIGINAL_SOFTWARE_FIXTURE"}
    old_id=digest(old_meta);old_meta["dataset_id"]=old_id
    metadata={old_id:old_meta}
    monkeypatch.setattr(reporting,"OLD_DATASET",old_id);monkeypatch.setattr(publisher,"OLD_DATASET",old_id)
    plan["existing_dataset_id"]=old_id
    entries[0]["dataset_id"]=old_id
    for entry in entries[1:]:
        refs=entry["reference_ids"]
        body={"generation_id":gold.GENERATION,"role":gold.ROLE,"profitability_approved":False,"legacy_gold_used":False,
            "definitions":{ref:catalog[ref] for ref in refs},"row_count":4*len(refs),
            "input_sha256":attestation["input_sha256"],"attestation":attestation,
            "validation":{"implementation_sha256":plan["implementation_sha256"],
                          "references":[summary for summary in summaries if summary["reference_id"] in refs]}}
        dataset_id=digest(body);body["dataset_id"]=dataset_id
        entry["dataset_id"]=dataset_id;metadata[dataset_id]=body
    assignment={ref:entry["dataset_id"] for entry in entries for ref in entry["reference_ids"]}
    inventory=[(assignment[row[1]],*row[1:]) for row in inventory]
    program["program_sha256"]=digest({k:v for k,v in program.items() if k!="program_sha256"})
    plan["plan_sha256"]=digest(plan)
    write_json(output/"publication-plan.json",plan)
    write_json(output/"source-evidence.json",evidence);write_json(output/"input-attestation.json",attestation)
    completion={"status":"COMMITTED_AND_READ_BACK_AWAITING_ACTIVE_POINTER","program_sha256":program["program_sha256"],"value_rows":120,"references":30}
    write_json(output/"completion.json",completion)
    state=SimpleNamespace(root=root,output=output,old_build=old_build,program=program,catalog=catalog,plan=plan,
                          evidence=evidence,attestation=attestation,completion=completion,inventory=inventory,
                          metadata=deepcopy(metadata),sql=[],frames=all_frames)
    monkeypatch.setattr(reporting,"read_collection_program",lambda path:(deepcopy(state.program),deepcopy(catalog),{"generation_id":gold.GENERATION}))
    monkeypatch.setattr(reporting,"connect",lambda:InventoryConnection(state))
    return state


def test_report_uses_live_readonly_counts_and_preserves_nonapproval_scope(report_fixture):
    s=report_fixture
    reporting.report(s.output)
    result=json.loads((s.output/"live-gold-inventory.json").read_bytes())
    assert result["references"]==30 and result["value_rows"]==120 and result["datasets"]==9
    assert not result["alpha_approved"] and not result["legacy_gold_used"]
    assert not result["first_vintage_independently_verified"]
    assert result["report_scope"]=="LIVE_COUNTS_NOT_CURRENT_FULL_VALUE_REAUDIT"
    assert all(item["by_market"]["KOSPI"]["assets"]==1 and item["by_market"]["KOSDAQ"]["assets"]==1 for item in result["inventory"])
    assert all(item["assets_with_60_observed_months"]==0 for item in result["inventory"])
    assert all(query.lstrip().upper().startswith(("SELECT","SET LOCAL")) for query,_ in s.sql)
    assert len(s.sql)==3
    assert set(s.sql[-1][1][0])=={entry["dataset_id"] for entry in s.program["reference_datasets"]}
    assert "gold.factor" not in s.sql[-1][0]


@pytest.mark.parametrize("change",["missing_ref","duplicate_ref","count","assets","months","first_date","completed_rows","program"])
def test_report_rejects_live_or_committed_coverage_mismatch(report_fixture,change):
    s=report_fixture
    if change=="missing_ref":s.inventory.pop()
    elif change=="duplicate_ref":s.inventory.append(s.inventory[0])
    elif change in {"count","assets","months","first_date"}:
        row=list(s.inventory[0]);field={"count":2,"assets":3,"months":4,"first_date":5}[change]
        row[field]=row[field]+1 if field!=5 else pd.Timestamp("2020-01-30").date();s.inventory[0]=tuple(row)
    elif change=="completed_rows":
        s.completion["value_rows"]+=1;write_json(s.output/"completion.json",s.completion)
    else:
        s.completion["program_sha256"]="f"*64;write_json(s.output/"completion.json",s.completion)
    with pytest.raises(ValueError):reporting.report(s.output)
    assert not (s.output/"live-gold-inventory.json").exists()


def test_describe_measures_history_per_security_not_just_global_date_span():
    dates=pd.date_range("2010-01-31",periods=120,freq="ME")
    frame=pd.DataFrame([{"asset_id":asset,"date":date,"market":"KOSPI" if asset<3 else "KOSDAQ"}
                        for asset,length in [(1,120),(2,60),(3,5)] for date in dates[:length]])
    summary=reporting.describe(frame)
    assert summary["assets"]==3 and summary["months"]==120 and summary["value_rows"]==185
    assert summary["median_observed_months_per_asset"]==60
    assert summary["assets_with_60_observed_months"]==2 and summary["assets_with_120_observed_months"]==1
    assert summary["by_market"]["KOSDAQ"]=={"assets":1,"months":5,"value_rows":5}


def test_report_rejects_reference_moved_between_bound_datasets_despite_equal_counts(report_fixture):
    s=report_fixture
    first,last=list(s.inventory[0]),list(s.inventory[-1])
    assert first[0]!=last[0]
    first[0],last[0]=last[0],first[0]
    s.inventory[0],s.inventory[-1]=tuple(first),tuple(last)
    with pytest.raises(ValueError,match="assignment"):
        reporting.report(s.output)
    assert not (s.output/"live-gold-inventory.json").exists()


def test_new_cache_market_mutation_with_unchanged_live_counts_is_rejected(report_fixture):
    s=report_fixture;ref=s.plan["eligible_references"][0]
    path=s.output/"references"/(ref+".parquet")
    frame=pd.read_parquet(path);frame["market"]="KOSPI";frame.to_parquet(path,index=False)
    with pytest.raises(ValueError,match="display cache differs"):
        reporting.report(s.output)
    assert not (s.output/"live-gold-inventory.json").exists()


def test_rehashing_plan_cannot_reauthorize_changed_cache_against_gold_metadata(report_fixture):
    s=report_fixture;ref=s.plan["eligible_references"][0]
    path=s.output/"references"/(ref+".parquet")
    frame=pd.read_parquet(path);frame["market"]="KOSPI";frame.to_parquet(path,index=False)
    summary=next(summary for summary in s.plan["references"] if summary["reference_id"]==ref)
    summary["values_file_sha256"]=publisher.sha(path)
    s.plan["plan_sha256"]=digest({k:v for k,v in s.plan.items() if k!="plan_sha256"})
    write_json(s.output/"publication-plan.json",s.plan)
    with pytest.raises(ValueError,match="Publication checkpoint differs"):
        reporting.report(s.output)
    assert not (s.output/"live-gold-inventory.json").exists()


def test_old_cache_market_is_reconstructed_from_verified_original_input(report_fixture):
    s=report_fixture
    path=s.old_build/"values.parquet"
    values=pd.read_parquet(path);values["market"]="UNTRUSTED_DISPLAY_LABEL";values.to_parquet(path,index=False)
    reporting.report(s.output)
    result=json.loads((s.output/"live-gold-inventory.json").read_bytes())
    originals=[item for item in result["inventory"] if item["reference_id"] in base._EXECUTABLE]
    assert all(set(item["by_market"])=={"KOSPI","KOSDAQ"} for item in originals)


@pytest.mark.parametrize("change",["old_value","old_input","source_evidence","plan_input","metadata_hash","metadata_missing"])
def test_report_rejects_stale_source_or_committed_metadata_binding(report_fixture,change):
    s=report_fixture
    if change=="old_value":
        path=s.old_build/"values.parquet";frame=pd.read_parquet(path);frame.loc[0,"value"]+=1;frame.to_parquet(path,index=False)
    elif change=="old_input":
        path=s.old_build/"input.parquet";frame=pd.read_parquet(path);frame.loc[0,"market"]="KOSDAQ";frame.to_parquet(path,index=False)
    elif change=="source_evidence":
        s.evidence["assets"]+=1;write_json(s.output/"source-evidence.json",s.evidence)
    elif change=="plan_input":
        s.plan["input_sha256"]="f"*64;s.plan["plan_sha256"]=digest({k:v for k,v in s.plan.items() if k!="plan_sha256"})
        write_json(s.output/"publication-plan.json",s.plan)
    elif change=="metadata_hash":next(iter(s.metadata.values()))["row_count"]+=1
    else:s.metadata.pop(next(iter(s.metadata)))
    with pytest.raises(ValueError):reporting.report(s.output)
    assert not (s.output/"live-gold-inventory.json").exists()


def test_offline_db_never_falls_back_to_local_coverage_report(report_fixture,monkeypatch):
    s=report_fixture
    def unavailable():raise ConnectionError("Live database unavailable")
    monkeypatch.setattr(reporting,"connect",unavailable)
    with pytest.raises(ConnectionError):reporting.report(s.output)
    assert not (s.output/"live-gold-inventory.json").exists()
