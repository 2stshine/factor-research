"""Pure publication contracts; production DB is never contacted by unit tests."""
from copy import deepcopy

import pandas as pd
import pytest

from engine import reference_gold as g
from engine.reference_library import load_catalog, definition_hash
from engine.research_generation import digest


def fixture():
    d=load_catalog()[0]
    values=pd.DataFrame([dict(reference_id=d["id"],definition_hash=definition_hash(d),asset_id="1",
        stock_code="005930",date="2020-01-31",known_at="2020-01-31T23:59:59+09:00",value=1.0)])
    att=dict(status="CERTIFIED",source_type="RDS_CERTIFIED_KRX_PRICE_ONLY",source_version="v1",input_sha256="a"*64,evidence_sha256='b'*64)
    parity=dict(passed=True,values_sha256=digest(g.canonical_values(values)),rows_compared=1,sql_sha256='c'*64,rtol=1e-10,atol=0,
                kind='INDEPENDENT_POSTGRES_FORMULAS_SAME_ATTESTED_PRICE_FEATURES')
    validation=dict(value_rows=1,source_version='v1',input_sha256='a'*64,source_evidence_sha256='b'*64,
                    role='MEASUREMENT_CONTROL',alpha_approved=False,implementation_sha256='d'*64,
                    references=[dict(reference_id=d['id'],definition_hash=definition_hash(d),value_rows=1,status='MEASUREMENT_VALIDATED')])
    pub,rows=g.build_publication(values,[d],attestation=att,validation=validation,parity=parity)
    return values,pub,rows,att,parity,d


def test_publication_separates_measurement_from_alpha():
    _,pub,rows,*_=fixture()
    assert not pub["profitability_approved"] and not pub["legacy_gold_used"]
    assert g.publish(None,pub,rows)==dict(status="DRY_RUN",dataset_id=pub["dataset_id"],row_count=1)
    assert rows[0]["stock_code"]=="005930"


@pytest.mark.parametrize("field,value",[("value",float("nan")),("value",float("inf")),("stock_code",5930),
    ("known_at","2020-02-01T00:00:00+09:00"),("known_at","2020-02-01T12:00:00+09:00"),("known_at","2020-01-31"),("asset_id",0)])
def test_invalid_rows_rejected(field,value):
    frame,*_=fixture(); frame[field]=frame[field].astype(object); frame.loc[0,field]=value
    with pytest.raises((ValueError,TypeError)):g.canonical_values(frame)


def test_duplicate_values_rejected():
    frame,*_=fixture()
    with pytest.raises(ValueError,match="Duplicate"):g.canonical_values(pd.concat([frame,frame]))


def test_synthetic_and_assumed_never_published():
    v,_,_,a,p,d=fixture()
    for key,val in [("status","PIT_ASSUMED"),("source_type","SYNTHETIC")]:
        b={**a,key:val}
        with pytest.raises(ValueError,match="Real certified"):
            g.build_publication(v,[d],attestation=b,validation={},parity=p)


def test_parity_and_definition_bind_exact_values():
    v,_,_,a,p,d=fixture(); v.loc[0,"value"]=2
    with pytest.raises(ValueError,match="parity"):
        g.build_publication(v,[d],attestation=a,validation={},parity=p)
    p["values_sha256"]=digest(g.canonical_values(v)); d={**d,"formula":"changed"}
    with pytest.raises(ValueError,match="Definition"):
        g.build_publication(v,[d],attestation=a,validation={},parity=p)


def test_publish_detects_mutations_before_any_db_call():
    _,pub,rows,*_=fixture(); rows[0]["value"]=2
    with pytest.raises(ValueError,match="digest"):g.publish(None,pub,rows,apply=True)
    _,pub,rows,*_=fixture(); pub["role"]="ALPHA_APPROVED"
    with pytest.raises(ValueError):g.publish(None,pub,rows,apply=True)


def test_price_query_excludes_labels_and_legacy_gold():
    assert "total_return" not in g.PRICE_SQL
    assert "gold.factor" not in g.PRICE_SQL
    assert "q.status='CERTIFIED'" in g.PRICE_SQL
    ddl=g.DDL_PATH.read_text()
    assert "gold.factor_value" not in ddl and "DROP TABLE" not in ddl
    assert "reference_value_creation_transaction" in ddl


@pytest.mark.parametrize('field,value',[('profitability_approved',True),('legacy_gold_used',True),
    ('attestation',{}),('validation',{}),('parity',{})])
def test_rehash_does_not_bypass_semantic_publication_gate(field,value):
    _,pub,rows,*_=fixture();pub[field]=value
    pub['dataset_id']=digest({k:v for k,v in pub.items() if k!='dataset_id'})
    with pytest.raises((ValueError,KeyError)):g.publish(None,pub,rows,apply=True)


def test_partial_month_date_rejected_before_query():
    with pytest.raises(ValueError,match='month-end'):g.load_certified_price_panel(None,end='2025-01-15')
    with pytest.raises(ValueError,match='first day'):g.load_certified_price_panel(None,start='2020-01-03')


def test_alphanumeric_ticker_is_not_coerced_or_dropped():
    frame,*_=fixture();frame.loc[0,'stock_code']='0037T0'
    assert g.canonical_values(frame)[0]['stock_code']=='0037T0'


def test_classification_conflicts_are_quarantined_not_upstream_rewritten():
    frame=pd.DataFrame([dict(asset_id=asset,stock_code=code,trade_date='2020-01-31',ticker_match_count=1,
             quality_run_id='certified-run',rn=1,price_return=.01,trading_value=100,market='KOSPI',adj_close=100.,market_cap=1000.)
             for asset,code in [(1,'005930'),(2,'0037T0'),(3,'00104K'),(4,'37550L')]])
    panel,e=g.normalize_price_frame(frame,start='2020-01-01',safe_end='2020-01-31',assets=[1,2,3,4])
    assert panel.stock_code.tolist()==['005930','0037T0']
    assert e['quarantined_monthly_rows']==2 and len(e['identity_quarantine'])==2
    assert len(frame)==4


def test_existing_publication_is_readback_verified_without_insert():
    from contextlib import nullcontext
    _,pub,rows,*_=fixture()
    class Cursor:
        commands=[]
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,sql,args=None):self.commands.append(sql)
        def fetchone(self):return (pub,)
        def fetchall(self):return [tuple(row.values()) for row in g.binary_readback_chunks(rows)]
    cursor=Cursor()
    class Connection:
        def transaction(self):return nullcontext()
        def cursor(self):return cursor
    receipt=g.publish(Connection(),pub,rows,apply=True)
    assert receipt['status']=='ALREADY_PUBLISHED' and receipt['values_sha256']==pub['values_sha256']
    assert receipt['readback_protocol']==g.READBACK_PROTOCOL and receipt['readback_rows']==1
    assert all('INSERT' not in command and 'COPY' not in command for command in cursor.commands)


def test_sample_parity_binds_exact_subset_even_after_rehash():
    _,pub,rows,*_=fixture()
    original=deepcopy(pub['parity'])
    pub['parity']={**original,'kind':'INDEPENDENT_SQLITE_FULL_POSTGRES_FIXED_SAMPLE',
                   'sqlite_full':deepcopy(original),'postgres_sample':{**original,'asset_ids':[1],
                       'selection':'TEN_EVENLY_SPACED_SORTED_ASSET_IDS_ALL_MONTHS'}}
    pub['dataset_id']=digest({k:v for k,v in pub.items() if k!='dataset_id'})
    g.validate_publication(pub,rows)
    pub['parity']['postgres_sample']['values_sha256']='d'*64
    pub['dataset_id']=digest({k:v for k,v in pub.items() if k!='dataset_id'})
    with pytest.raises(ValueError,match='exact declared rows'):g.validate_publication(pub,rows)


def test_binary_readback_closed_form_postgres_encoding():
    import hashlib
    import struct
    row=dict(reference_id='r',definition_hash='d',asset_id=1,stock_code='005930',date='2000-01-01',
             known_at='2000-01-01T09:00:00+09:00',value=1.25)
    wire=(b'\x00\x00\x00\x01r'+b'\x00\x00\x00\x01d'+struct.pack('!q',1)+
          b'\x00\x00\x00\x06005930'+bytes(12)+bytes.fromhex('3ff4000000000000'))
    assert g.binary_readback_chunks([row])==[dict(chunk_id=0,row_count=1,sha256=hashlib.sha256(wire).hexdigest())]


@pytest.mark.parametrize('field,value',[('reference_id','x'),('definition_hash','x'),('asset_id',2),
    ('stock_code','0037T0'),('date','2020-02-29'),('known_at','2020-01-31T14:59:58+00:00'),('value',1.00000000001)])
def test_binary_readback_covers_every_value_field(field,value):
    _,_,rows,*_=fixture(); changed=deepcopy(rows);changed[0][field]=value
    assert g.binary_readback_chunks(rows)!=g.binary_readback_chunks(changed)


def test_binary_readback_boundaries_dates_signed_zero_and_order():
    _,_,rows,*_=fixture()
    rows=[{**rows[0],'asset_id':i} for i in range(1,6)]
    chunks=g.binary_readback_chunks(rows,chunk_size=2)
    assert [c['row_count'] for c in chunks]==[2,2,1]
    assert [c['chunk_id'] for c in chunks]==[0,1,2]
    for invalid in [[],list(reversed(rows)),rows+[rows[-1]]]:
        with pytest.raises(ValueError):g.binary_readback_chunks(invalid)
    for invalid_size in [0,-1,True,1.1,100001]:
        with pytest.raises(ValueError):g.binary_readback_chunks(rows,chunk_size=invalid_size)
    a={**rows[0],'date':'1999-12-31','known_at':'1999-12-31T00:00:00+00:00','value':0.0}
    b={**a,'value':-0.0}
    assert g.binary_readback_chunks([a])!=g.binary_readback_chunks([b])


@pytest.mark.parametrize('mutation',['hash','count','missing','extra','order'])
def test_binary_readback_rejects_any_database_difference(mutation):
    _,pub,rows,*_=fixture()
    observed=[tuple(row.values()) for row in g.binary_readback_chunks(rows)]
    if mutation=='hash':observed[0]=(0,1,'f'*64)
    elif mutation=='count':observed[0]=(0,2,observed[0][2])
    elif mutation=='missing':observed=[]
    elif mutation=='extra':observed=observed+observed
    else:observed[0]=(1,1,observed[0][2])
    class Cursor:
        def execute(self,sql,params):
            assert sql==g.READBACK_SQL and params==(g.READBACK_CHUNK_SIZE,pub['dataset_id'],g.GENERATION)
        def fetchall(self):return observed
    with pytest.raises(ValueError,match='binary read-back differs'):
        g.verify_database_rows(Cursor(),dataset_id=pub['dataset_id'],rows=rows)
