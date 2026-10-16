"""Independent full SQLite + fixed PostgreSQL checks before reference publishing."""
import argparse
import hashlib
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from engine import reference_flow_inputs as lib,reference_gold as gold,reference_library as base
from engine.reference_db import connect
from engine.reference_expansion_parity import _compare
from engine.research_generation import digest
from scripts.capture_reference_flows import SQL
from scripts.publish_reference_expansion import load_json,save_json,sha

def parity(panel,values,ref,conn,*,specs=None):
 _,expression,cols=(lib.SPECS if specs is None else specs)[ref]
 f=panel[['asset_id','stock_code','date',*cols]].copy();f.asset_id=f.asset_id.astype(str);f.date=f.date.dt.strftime('%Y-%m-%d')
 sql=f"SELECT '{ref}' AS reference_id,asset_id,stock_code,date,{expression} AS value FROM reference_input WHERE ({expression}) IS NOT NULL"
 fields=['asset_id TEXT','stock_code TEXT','date TEXT']+[c+' DOUBLE PRECISION' for c in cols]
 records=list(f.astype(object).where(pd.notna(f),None).itertuples(index=False,name=None))
 with sqlite3.connect(':memory:') as db:
  db.execute('CREATE TABLE reference_input ('+','.join(fields)+')')
  db.executemany('INSERT INTO reference_input VALUES ('+','.join('?' for _ in fields)+')',records)
  cur=db.execute(sql);actual=pd.DataFrame(cur.fetchall(),columns=[c[0] for c in cur.description])
 n=_compare(values,actual,'KIS full SQLite')
 rows=gold.canonical_values(values);assets=sorted({r['asset_id'] for r in rows})
 sample=sorted({assets[(len(assets)-1)*i//9] for i in range(10)})
 with conn.transaction(),conn.cursor() as cur:
  cur.execute('CREATE TEMP TABLE reference_input ('+','.join(fields)+') ON COMMIT DROP')
  with cur.copy('COPY reference_input FROM STDIN') as cp:
   for row in records:
    if int(row[0]) in sample:cp.write_row(row)
  cur.execute(sql);actual=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description]);cur.execute('DROP TABLE pg_temp.reference_input')
 subset=values.loc[values.asset_id.astype(int).isin(sample)];ns=_compare(subset,actual,'KIS fixed PostgreSQL')
 common=dict(passed=True,sql_sha256=hashlib.sha256(sql.encode()).hexdigest(),rtol=1e-10,atol=0)
 return dict(**common,kind='INDEPENDENT_SQLITE_FULL_POSTGRES_FIXED_SAMPLE',rows_compared=n,values_sha256=digest(rows),
  sqlite_full=dict(**common,rows_compared=n),postgres_sample=dict(**common,rows_compared=ns,asset_ids=sample,
   selection='TEN_EVENLY_SPACED_SORTED_ASSET_IDS_ALL_MONTHS',values_sha256=digest(gold.canonical_values(subset))))

def build(source,output):
 source=Path(source);out=Path(output);out.mkdir(parents=True,exist_ok=True)
 implementation={str(Path(f).relative_to(Path(__file__).resolve().parents[1])):dict(sha256=sha(f),source=Path(f).read_text()) for f in
  (__file__,lib.__file__,str(Path(__file__).with_name('capture_reference_flows.py')))}
 save_json(out/'implementation-source.json',implementation)
 m=load_json(source/'manifest.json')
 if m['status']!='COMPLETE' or m['query_sha256']!=digest(SQL) or m['manifest_sha256']!=digest({k:v for k,v in m.items() if k!='manifest_sha256'}):raise ValueError('Unverified capture')
 raw_audit=load_json(source/'raw-audit.json')
 if raw_audit.get('status')!='FIXED_RAW_DAILY_RECONSTRUCTION_PASSED' or raw_audit.get('source_manifest_sha256')!=sha(source/'manifest.json'):
  raise ValueError('Independent daily source reconstruction required')
 frames=[]
 for f in m['files']:
  if sha(source/f['path'])!=f['sha256']:raise ValueError('Source bytes changed')
  frames.append(pd.read_parquet(source/f['path']))
 panel=lib.prepare(pd.concat(frames,ignore_index=True))
 # Full-month source aggregates are frozen, not a promise of first vintages.
 evidence=dict(source_manifest=m,input_sha256=digest(m),forward_labels_read=False,legacy_gold_used=False,
  independent_raw_daily_audit=raw_audit,independent_raw_daily_audit_sha256=sha(source/'raw-audit.json'),
  scope='KRX_COMMON_STOCK_J_ONLY',pit_status='PIT_ASSUMED',source_sql_aggregation='CERTIFIED_DAILY_ROWS_ASOF_POLICY_MONTH_END',
  short_regime='EXCLUDE_2020_03_THROUGH_2025_03_NO_HISTORICAL_INDEX_MEMBERSHIP_PROXY')
 att=dict(status='CERTIFIED',source_type=lib.SOURCE_TYPE,source_contract=lib.SOURCE_CONTRACT,
  pit_status=lib.PIT_STATUS,first_vintage_independently_verified=False,scope=base.INPUT_SCOPE,
  identity_contract=base.IDENTITY_CONTRACT,source_version=digest(evidence),evidence_sha256=digest(evidence),
  input_sha256=digest(m),venue='J',availability_policy=m['availability_policy'])
 impl=digest({str(Path(p).name):sha(p) for p in (__file__,lib.__file__)})
 panel.to_parquet(out/'monthly-input.parquet',index=False);save_json(out/'source-evidence.json',evidence)
 with connect(read_only=False) as conn:
  for definition in lib.definitions():
   ref=definition['id'];series=lib.calculate(panel,ref);mask=series.notna()
   v=panel.loc[mask,['asset_id','stock_code','date','market']].copy();v['known_at']=pd.to_datetime(panel.loc[mask,'short_known_at' if 'short_volume' in ref else 'investor_known_at'],utc=True)
   base._prepare(v)
   v['reference_id']=ref;v['value']=series[mask];v['oriented_value']=v.value
   v['definition_hash']=base.definition_hash(definition);v['source_version']=att['source_version'];v['input_sha256']=att['input_sha256'];v=v[base._OUTPUT].reset_index(drop=True)
   if v.asset_id.nunique()<100 or v.date.nunique()<60:raise ValueError('Insufficient 100-asset/60-month coverage: '+ref)
   check=parity(panel,v,ref,conn)
   summary=dict(reference_id=ref,definition_hash=base.definition_hash(definition),status='MEASUREMENT_VALIDATED',value_rows=len(v),
    assets=int(v.asset_id.nunique()),months=int(v.date.nunique()),first_date=str(v.date.min().date()),last_date=str(v.date.max().date()))
   validation=dict(source_version=att['source_version'],input_sha256=att['input_sha256'],source_evidence_sha256=att['evidence_sha256'],
    implementation_sha256=impl,role='MEASUREMENT_CONTROL',alpha_approved=False,value_rows=len(v),references=[summary])
   pub,_=gold.build_publication(v,[definition],attestation=att,validation=validation,parity=check)
   dest=out/ref;dest.mkdir(exist_ok=True);save_json(dest/'publication.json',pub);v.to_parquet(dest/'values.parquet',index=False)
   print(summary,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args();build(a.source,a.output)
