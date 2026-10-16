"""Synthetic source/DB state-machine tests; never contact AWS or real Gold."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from engine import reference_gold as gold,reference_library as base,reference_library_v2 as library
from engine import reference_price_expansion as price
from engine.research_generation import canonical,digest
from scripts import publish_reference_expansion as publish
from scripts import audit_reference_price_expansion as audit


def replace_json(path,value):
    Path(path).write_bytes(canonical(value)+b"\n")


def rehash_plan(plan):
    plan["plan_sha256"]=digest({k:v for k,v in plan.items() if k!="plan_sha256"})
    return plan


class TestConnection:
    __test__=False
    def __init__(self,state,read_only):
        self.state=state;self.read_only=read_only;self.pending={}
        self.db=sqlite3.connect(":memory:")
        self.db.create_function("ln",1,lambda v:math.log(v) if v is not None and v>0 else None)
        self.db.create_function("floor",1,lambda v:math.floor(v) if v is not None else None)
    def __enter__(self):return self
    def __exit__(self,kind,*_):
        self.db.close()
        if kind:return False
        if self.state.fail_commit:
            raise RuntimeError("synthetic outer commit failure")
        # Assert the receipt cannot appear before the outer commit boundary.
        for index in self.state.publishing_indices:
            assert not (self.state.output/"groups"/f"{index:02d}"/"receipt-applied.json").exists()
        self.state.committed.update(self.pending)
        return False
    @contextmanager
    def transaction(self):yield self
    def cursor(self):return TestCursor(self)


class TestCursor:
    __test__=False
    def __init__(self,connection):self.connection=connection;self.result=None
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql):
        self.connection.state.sql.append(sql)
        if sql.startswith("SET LOCAL"):return
        self.result=self.connection.db.execute(sql.replace(" ON COMMIT DROP","").replace("pg_temp.reference_input","reference_input"))
    @property
    def description(self):return [SimpleNamespace(name=d[0]) for d in self.result.description]
    def fetchall(self):return self.result.fetchall()
    @contextmanager
    def copy(self,sql):
        assert sql=="COPY reference_input FROM STDIN"
        yield self
    def write_row(self,row):
        self.connection.db.execute("INSERT INTO reference_input VALUES("+",".join("?" for _ in row)+")",row)


@pytest.fixture
def framework(tmp_path,monkeypatch):
    root=tmp_path/"repo";output=root/"output";output.mkdir(parents=True)
    catalog_path=root/"research/phenomena/catalog.json";catalog_path.parent.mkdir(parents=True)
    replace_json(catalog_path,library.make_catalog())
    monkeypatch.setattr(library,"CATALOG_PATH",catalog_path)
    monkeypatch.setattr(publish,"ROOT",root)
    # Scale only the data-coverage unit-test fixture; the >=30-reference and
    # max3/group policies remain untouched. Production defaults tested below.
    monkeypatch.setattr(publish,"MIN_ASSETS",2)
    monkeypatch.setattr(publish,"MIN_MONTHS",3)
    monkeypatch.setattr(publish.gc,"collect",lambda:None)
    old_build=root/"old-verified-dataset";old_build.mkdir()
    monkeypatch.setattr(publish,"OLD_BUILD",old_build)
    pointer=root/"research/active-generation.json";pointer.write_text("existing-generation-pointer")
    active=root/"research/phenomena/program.json";active.write_text("existing-active-program")
    records=[]
    for asset in (1,2):
        for i,date in enumerate(pd.date_range("2020-01-31",periods=3,freq="ME")):
            row={column:20.+i for column in library.FEATURE_COLUMNS}
            row.update(asset_id=str(asset),stock_code=f"{asset:05d}0",date=date,
                known_at=date.tz_localize("Asia/Seoul")+pd.Timedelta(hours=16),market="KOSPI",
                adj_close=100.+i,market_cap=1e10,nominal_close=1000.+i,
                share_turnover_1m=.01,share_turnover_cv_1m=.2,mean_traded_value_1m=1e8,
                traded_value_cv_1m=.3,zero_volume_fraction_1m=.1,downside_semideviation_252d=.01,
                return_skew_252d=-.2,parkinson_variance_1m=.001,
                overnight_return_1m=.02,intraday_return_1m=-.01,
                daily_return_observations_252d=252.,positive_return_days_1m=12.,negative_return_days_1m=6.)
            records.append(row)
    panel=library.prepare(pd.DataFrame(records).loc[:,library.ALL_COLUMNS])
    panel.to_parquet(output/"input.parquet",index=False)
    evidence={"input_file_sha256":publish.sha(output/"input.parquet"),
              "financial_adapter_sha256":publish.sha(Path(publish.financial.__file__)),
              "fixture":"SOFTWARE_ONLY_NO_REAL_CERTIFICATION"}
    attestation={"status":"CERTIFIED","source_type":library.SOURCE_TYPE,"source_contract":library.SOURCE_CONTRACT,
        "scope":base.INPUT_SCOPE,"identity_contract":base.IDENTITY_CONTRACT,"pit_status":library.PIT_STATUS,
        "first_vintage_independently_verified":False,"source_version":digest(evidence),"evidence_sha256":digest(evidence),
        "input_sha256":library.input_digest(panel),"feature_contracts":library.FEATURE_CONTRACTS,"feature_units":library.FEATURE_UNITS}
    replace_json(output/"source-evidence.json",evidence);replace_json(output/"input-attestation.json",attestation)
    old_definitions={definition["id"]:definition for definition in base.load_catalog()
                     if definition["id"] in base._EXECUTABLE}
    old=pd.DataFrame([{"reference_id":ref,"definition_hash":base.definition_hash(old_definitions[ref]),"asset_id":"1","stock_code":"000010",
                      "date":pd.Timestamp("2020-01-31"),"known_at":pd.Timestamp("2020-01-31T16:00:00+09:00"),"value":1.}
                     for ref in sorted(base._EXECUTABLE)])
    old.to_parquet(old_build/"values.parquet",index=False)
    state=SimpleNamespace(root=root,output=output,panel=panel,attestation=attestation,pointer=pointer,active=active,
        committed={publish.OLD_DATASET:(old,{"dataset_id":publish.OLD_DATASET,"definitions":old_definitions,
                                            "fixture":"previous verified reference dataset"})},
        fail_commit=False,publishing_indices=[],sql=[],connections=[],publish_calls=0,load_calls=[])
    def connect(*,read_only=True):
        state.connections.append(read_only)
        return TestConnection(state,read_only)
    def fake_publish(conn,publication,rows,*,apply=False):
        # Real publication validation and parity payload; only persistence is fake.
        gold.validate_publication(publication,rows)
        state.publish_calls+=1
        if apply:conn.pending[publication["dataset_id"]]=(pd.DataFrame(rows),deepcopy(publication))
        return {"status":"PUBLISHED" if apply else "DRY_RUN","dataset_id":publication["dataset_id"],"rows":len(rows)}
    def loader(conn,*,dataset_id,generation_id=gold.GENERATION,snapshot_path=None):
        state.load_calls.append(dataset_id)
        if dataset_id not in state.committed:raise ValueError("No committed dataset")
        _,metadata=state.committed[dataset_id]
        values=pd.read_parquet(snapshot_path)
        if dataset_id!=publish.OLD_DATASET:gold.validate_publication(metadata,gold.canonical_values(values))
        return values.loc[:,["reference_id","definition_hash","asset_id","stock_code","date","known_at","value"]],deepcopy(metadata)
    monkeypatch.setattr(publish,"connect",connect)
    monkeypatch.setattr(publish,"legacy_metadata_digest",lambda _: {"records":10,"opaque_metadata_md5":"untouched"})
    monkeypatch.setattr(gold,"publish",fake_publish)
    monkeypatch.setattr(gold,"load_library",loader)
    monkeypatch.setattr(gold,"install_schema",lambda conn,apply=False:{"status":"TEST_SCHEMA","apply":apply})
    publish.calculate(output)
    state.plan=publish.load_json(output/"publication-plan.json")
    return state


def test_production_threshold_defaults_are_not_relaxed():
    assert publish.MIN_ASSETS==100 and publish.MIN_MONTHS==60 and publish.GROUP_SIZE==3


def test_calculation_plan_is_bound_bounded_complete_and_not_published(framework):
    s=framework
    publish.validate_plan(s.plan)
    assert len(s.plan["references"])==38
    assert s.plan["expected_total_references"]>=30
    assert all(1<=len(group)<=3 for group in s.plan["groups"])
    assert s.plan["plan_sha256"]==digest({k:v for k,v in s.plan.items() if k!="plan_sha256"})
    assert not s.connections and not s.publish_calls
    assert s.pointer.read_text()=="existing-generation-pointer" and s.active.read_text()=="existing-active-program"


@pytest.mark.parametrize("change",["input_bytes","evidence","attestation_hash","feature_contract"])
def test_frozen_input_mutations_are_blocked(framework,change):
    s=framework
    if change=="input_bytes":
        frame=pd.read_parquet(s.output/"input.parquet");frame.loc[0,"adj_close"]+=1
        frame.to_parquet(s.output/"input.parquet",index=False)
    elif change=="evidence":
        evidence=publish.load_json(s.output/"source-evidence.json");evidence["unexpected"]=True
        replace_json(s.output/"source-evidence.json",evidence)
    else:
        att=publish.load_json(s.output/"input-attestation.json")
        if change=="attestation_hash":att["input_sha256"]="f"*64
        else:att["feature_contracts"]["adj_close"]="UNBOUND_PROXY"
        replace_json(s.output/"input-attestation.json",att)
    with pytest.raises(ValueError):publish.publish_group(s.output,0,apply=True)
    assert not s.connections


@pytest.mark.parametrize("action",["load","resume_prepare","publish"])
def test_financial_adapter_change_requires_fresh_attachment(framework,monkeypatch,action):
    s=framework
    original_sha=publish.sha
    adapter_path=Path(publish.financial.__file__).resolve()
    monkeypatch.setattr(publish,"sha",lambda path:
        "f"*64 if Path(path).resolve()==adapter_path else original_sha(path))
    with pytest.raises(ValueError,match="Financial adapter changed; reattach"):
        if action=="load":publish.load_input(s.output)
        elif action=="resume_prepare":publish.prepare(s.output,s.root/"unused-price",s.root/"unused-financial")
        else:publish.publish_group(s.output,0,apply=True)
    assert not s.connections and not s.publish_calls
    assert not (s.output/"groups/00/receipt-applied.json").exists()
    assert s.active.read_text()=="existing-active-program"


@pytest.mark.parametrize("change",["hash","min_assets","min_months","duplicate","oversized","fewer_than30","input_binding","summary_missing"])
def test_rehashed_invalid_plan_does_not_reach_database(framework,change):
    s=framework;plan=deepcopy(s.plan)
    if change=="hash":plan["plan_sha256"]="f"*64
    else:
        if change=="min_assets":plan["minimum_assets"]=1
        elif change=="min_months":plan["minimum_months"]=1
        elif change=="duplicate":plan["groups"][0][1]=plan["groups"][0][0]
        elif change=="oversized":plan["groups"][0]+=plan["groups"].pop()[0:1]
        elif change=="fewer_than30":plan["expected_total_references"]=29
        elif change=="input_binding":plan["input_sha256"]="f"*64
        else:plan["references"].pop()
        rehash_plan(plan)
    replace_json(s.output/"publication-plan.json",plan)
    with pytest.raises(ValueError):publish.publish_group(s.output,0,apply=True)
    assert not s.connections


def test_plan_and_reference_summary_must_match_even_after_plan_rehash(framework):
    s=framework;plan=deepcopy(s.plan)
    ref=plan["groups"][0][0]
    summary=next(v for v in plan["references"] if v["reference_id"]==ref)
    summary["assets"]+=1  # Still eligible but no longer actual measured coverage.
    replace_json(s.output/"publication-plan.json",rehash_plan(plan))
    with pytest.raises(ValueError):publish.publish_group(s.output,0,apply=True)
    assert not s.connections


def test_reference_file_or_coverage_change_is_not_reused(framework):
    s=framework;ref=s.plan["groups"][0][0]
    path=s.output/"references"/(ref+".json")
    summary=publish.load_json(path);summary["months"]+=1;replace_json(path,summary)
    with pytest.raises(ValueError):publish.publish_group(s.output,0,apply=True)
    assert not s.connections


def test_commit_precedes_applied_receipt_and_checkpoint_is_readback_verified(framework):
    s=framework;s.publishing_indices=[0]
    receipt=publish.publish_group(s.output,0,apply=True)
    assert receipt["outer_transaction_committed"] and receipt["dataset_id"] in s.committed
    assert s.publish_calls==1
    s.publishing_indices=[]
    same=publish.publish_group(s.output,0,apply=True)
    assert same==receipt and s.publish_calls==1 and s.load_calls==[receipt["dataset_id"]]
    assert not (s.output/"verified-program-proposal.json").exists()
    assert s.active.read_text()=="existing-active-program"


def test_commit_failure_leaves_no_applied_checkpoint_and_can_resume(framework):
    s=framework;s.fail_commit=True;s.publishing_indices=[0]
    with pytest.raises(RuntimeError,match="commit failure"):publish.publish_group(s.output,0,apply=True)
    assert not (s.output/"groups/00/receipt-applied.json").exists()
    assert len(s.committed)==1 and s.active.read_text()=="existing-active-program"
    s.fail_commit=False
    receipt=publish.publish_group(s.output,0,apply=True)
    assert receipt["outer_transaction_committed"] and len(s.committed)==2


def test_dry_run_cannot_activate_or_claim_commit(framework):
    s=framework
    receipt=publish.publish_group(s.output,0,apply=False)
    assert receipt["status"]=="DRY_RUN" and receipt["outer_transaction_committed"] is False
    assert not (s.output/"groups/00/receipt-applied.json").exists()
    with pytest.raises((ValueError,FileNotFoundError)):publish.activation_plan(s.output)
    assert not (s.output/"verified-program-proposal.json").exists()


@pytest.mark.parametrize("change",["receipt_id","not_committed","input_binding","implementation","summary"])
def test_corrupt_or_stale_applied_checkpoint_fails(framework,change):
    s=framework
    publish.publish_group(s.output,0,apply=True)
    directory=s.output/"groups/00"
    if change in {"receipt_id","not_committed"}:
        receipt=publish.load_json(directory/"receipt-applied.json")
        receipt["dataset_id" if change=="receipt_id" else "outer_transaction_committed"]="f"*64 if change=="receipt_id" else False
        replace_json(directory/"receipt-applied.json",receipt)
    else:
        publication=publish.load_json(directory/"publication.json")
        if change=="input_binding":publication["input_sha256"]="f"*64
        elif change=="implementation":publication["validation"]["implementation_sha256"]="f"*64
        else:publication["validation"]["references"][0]["months"]+=1
        replace_json(directory/"publication.json",publication)
    before=len(s.connections)
    with pytest.raises(ValueError):publish.publish_group(s.output,0,apply=True)
    assert len(s.connections)==before


def test_legacy_metadata_change_rolls_back_new_publication(framework,monkeypatch):
    s=framework;answers=iter([{"opaque":"before"},{"opaque":"after"}])
    monkeypatch.setattr(publish,"legacy_metadata_digest",lambda _:next(answers))
    with pytest.raises(ValueError,match="Legacy metadata changed"):publish.publish_group(s.output,0,apply=True)
    assert len(s.committed)==1 and not (s.output/"groups/00/receipt-applied.json").exists()


def test_activation_only_writes_proposal_after_all_committed_groups_verified(framework):
    s=framework
    for index in range(len(s.plan["groups"])):publish.publish_group(s.output,index,apply=True)
    publish.activation_plan(s.output)
    proposal=publish.load_json(s.output/"verified-program-proposal.json")
    completion=publish.load_json(s.output/"completion.json")
    assert completion["references"]==s.plan["expected_total_references"]>=30
    assert completion["status"]=="COMMITTED_AND_READ_BACK_AWAITING_ACTIVE_POINTER"
    assert proposal["program_sha256"]==digest({k:v for k,v in proposal.items() if k!="program_sha256"})
    assert all(entry["dataset_id"] in s.committed for entry in proposal["reference_datasets"])
    assert s.pointer.read_text()=="existing-generation-pointer" and s.active.read_text()=="existing-active-program"


@pytest.mark.parametrize("change",["definition_set","definition_formula","row_set"])
def test_activation_rejects_changed_original_seven_before_new_group_reads(framework,change):
    s=framework
    old,metadata=s.committed[publish.OLD_DATASET]
    ref=next(iter(metadata["definitions"]))
    if change=="definition_set":
        metadata["definitions"].pop(ref)
    elif change=="definition_formula":
        definition=metadata["definitions"][ref]
        definition["formula"]="different original measurement"
        definition["definition_hash"]=base.definition_hash(definition)
    else:
        old[~old.reference_id.eq(ref)].to_parquet(publish.OLD_BUILD/"values.parquet",index=False)
    with pytest.raises(ValueError,match="Original seven definitions differ"):
        publish.activation_plan(s.output)
    assert s.load_calls==[publish.OLD_DATASET]
    assert not (s.output/"verified-program-proposal.json").exists()
    assert not (s.output/"collection-cache"/(publish.OLD_DATASET+".parquet")).exists()
    assert s.pointer.read_text()=="existing-generation-pointer" and s.active.read_text()=="existing-active-program"


def price_source(tmp_path):
    source=tmp_path/"source";source.mkdir()
    dates=pd.bdate_range("2020-01-01",periods=70)
    raw=pd.DataFrame({"asset_id":1,"stock_code":"000010","trade_date":dates,
        "known_at":dates.tz_localize("Asia/Seoul")+pd.Timedelta(hours=23,minutes=59,seconds=59),
        "market":"KOSPI","adj_close":100+np.arange(len(dates))*.1,"market_cap":1e10,
        "trading_value":1e12,"open":100.,"close":100.,"high":101.,"low":99.,"volume":1000.,"shares":1e8})
    computed=price.aggregate_daily_for_validation(raw)
    source_columns=list(dict.fromkeys([*base._BASE,*base.FEATURE_CONTRACTS,*base._COUNTS,*price.ADDITIONAL_COLUMNS]))
    computed.loc[:,source_columns].to_parquet(source/"input.parquet",index=False)
    raw.to_parquet(source/"price-000000.parquet",index=False)
    evidence={"chunks_complete":True,"source_type":"RDS_CERTIFIED_KRX_EXTENDED_PRICE_V2",
        "query_sha256":hashlib.sha256(price.EXTENDED_PRICE_SQL.encode()).hexdigest(),
        "input_file_sha256":publish.sha(source/"input.parquet"),
        "chunks":[{"path":"price-000000.parquet","sha256":publish.sha(source/"price-000000.parquet")}]}
    replace_json(source/"source-evidence.json",evidence)
    return source,raw,evidence


class DailyConnection:
    def __init__(self,raw):self.raw=raw;self.position=0
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cursor(self,name=None):self.named=name is not None;return self
    def execute(self,query,params=None):
        if self.named:
            assert query==audit.DAILY_SQL
            assert params[2]==[1]
            self.data=self.raw.drop(columns="known_at").copy();self.data["ticker_count"]=1
    @property
    def description(self):return [SimpleNamespace(name=column) for column in self.data]
    def fetchmany(self,count):
        chunk=self.data.iloc[self.position:self.position+count];self.position+=len(chunk)
        return list(chunk.itertuples(index=False,name=None))


def test_raw_daily_audit_binds_source_and_zero_absolute_amihud_tolerance(tmp_path,monkeypatch):
    source,raw,evidence=price_source(tmp_path)
    monkeypatch.setattr(audit,"connect",lambda:DailyConnection(raw))
    audit.audit(source)
    receipt=publish.load_json(source/"daily-audit.json")
    assert receipt["passed"] and receipt["input_file_sha256"]==evidence["input_file_sha256"]
    assert receipt["price_evidence_sha256"]==digest(evidence)
    assert receipt["raw_file_sha256"]==publish.sha(source/"daily-audit-input.parquet")
    assert receipt["comparison"]["amihud_illiquidity_1m"]["atol"]==0
    assert receipt["comparison"]["turnover_observations_1m"]["rtol"]==0


def test_tiny_but_orders_of_magnitude_amihud_error_must_fail(tmp_path,monkeypatch):
    source,raw,evidence=price_source(tmp_path)
    captured=pd.read_parquet(source/"input.parquet")
    captured["amihud_illiquidity_1m"]*=100
    captured.to_parquet(source/"input.parquet",index=False)
    evidence["input_file_sha256"]=publish.sha(source/"input.parquet")
    replace_json(source/"source-evidence.json",evidence)
    monkeypatch.setattr(audit,"connect",lambda:DailyConnection(raw))
    with pytest.raises(ValueError,match="amihud_illiquidity"):
        audit.audit(source)
    assert publish.load_json(source/"daily-audit.json")["passed"] is False


@pytest.mark.parametrize("key",["input_file_sha256","price_evidence_sha256","query_sha256","oracle_sha256","raw_file_sha256"])
def test_copied_or_stale_daily_audit_is_rejected_before_financial_attachment(tmp_path,monkeypatch,key):
    source,raw,_=price_source(tmp_path)
    monkeypatch.setattr(audit,"connect",lambda:DailyConnection(raw))
    audit.audit(source)
    receipt=publish.load_json(source/"daily-audit.json");receipt[key]="f"*64
    replace_json(source/"daily-audit.json",receipt)
    called=[]
    monkeypatch.setattr(publish.financial,"attach_capture",lambda *args:called.append(args))
    with pytest.raises(ValueError,match="daily audit"):
        publish.prepare(tmp_path/"build",source,tmp_path/"financial")
    assert not called


def test_modified_or_partial_price_capture_never_prepares(tmp_path):
    source,_,evidence=price_source(tmp_path)
    evidence["chunks_complete"]=False;replace_json(source/"source-evidence.json",evidence)
    with pytest.raises(ValueError):publish.verify_price_capture(source)
    evidence["chunks_complete"]=True;replace_json(source/"source-evidence.json",evidence)
    with (source/"price-000000.parquet").open("ab") as stream:stream.write(b"changed")
    with pytest.raises(ValueError,match="chunk mismatch"):publish.verify_price_capture(source)
