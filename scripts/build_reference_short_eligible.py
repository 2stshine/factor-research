"""Build two replacement measurements, gated by official policy/raw parity."""
import argparse
from pathlib import Path
import pandas as pd
from engine import reference_short_eligibility as lib,reference_gold as gold,reference_library as base
from engine.reference_db import connect
from engine.research_generation import digest
from scripts.capture_reference_short_eligible import SQL,load_policy
from scripts.build_reference_flows import parity
from scripts.publish_reference_expansion import load_json,save_json,sha

def build(source,policy,output):
 source=Path(source);policy=Path(policy);out=Path(output);out.mkdir(parents=True,exist_ok=True)
 m=load_json(source/'manifest.json');pm,_,_=load_policy(policy);audit=load_json(source/'raw-audit.json')
 csv_check=load_json(policy.parent/'krx-daily-membership/csv-crosscheck.json')
 if csv_check['status']!='ALL_STAGED_FULL_CSV_DOM_MEMBERSHIP_MATCHED' or csv_check['checked_dates']<2:raise ValueError('Full CSV cross-check required')
 for c in csv_check['checks']:
  if sha(c['raw_path'])!=c['raw_sha256']:raise ValueError('Cross-check CSV changed')
 if m['status']!='COMPLETE' or m['query_sha256']!=digest(SQL) or m['manifest_sha256']!=digest({k:v for k,v in m.items() if k!='manifest_sha256'}):raise ValueError('Unverified source capture')
 if m['policy_manifest_sha256']!=sha(policy/'manifest.json'):raise ValueError('Policy binding changed')
 if (audit.get('status')!='DAILY_POLICY_RECONSTRUCTION_PASSED' or audit['source_manifest_sha256']!=sha(source/'manifest.json')
  or audit['policy_manifest_sha256']!=sha(policy/'manifest.json') or audit['fixed_raw_sha256']!=sha(source/'fixed-raw-sample.parquet')):raise ValueError('Raw reconstruction required')
 frames=[]
 for f in m['files']:
  if sha(source/f['path'])!=f['sha256']:raise ValueError('Source changed')
  frame=pd.read_parquet(source/f['path'])
  if f['query_sha256']!=digest(SQL):
   from scripts.revise_short_policy_source import STRICT_SQL
   revision=m.get('source_revision',{})
   if (f['query_sha256']!=digest(STRICT_SQL) or not frame.bad_short.eq(0).all()
    or f.get('original_manifest_sha256')!=revision.get('original_manifest_sha256')
    or revision.get('substantive_scope_and_availability_checks_unchanged') is not True):raise ValueError('Unproven query equivalence')
  frames.append(frame)
 panel=lib.prepare(pd.concat(frames,ignore_index=True))
 evidence=dict(source_manifest=m,policy_manifest=pm,raw_audit=audit,membership_csv_crosscheck=csv_check,scope='KRX_COMMON_STOCK_J_ONLY',pit_status='PIT_ASSUMED',
  input_sha256=digest(m),forward_labels_read=False,legacy_gold_used=False,borrow_availability_verified=False,
  independent_raw_daily_audit_sha256=sha(source/'raw-audit.json'))
 att=dict(status='CERTIFIED',source_type=lib.SOURCE_TYPE,source_contract=lib.SOURCE_CONTRACT,pit_status=lib.PIT_STATUS,
  first_vintage_independently_verified=False,scope=base.INPUT_SCOPE,identity_contract=base.IDENTITY_CONTRACT,
  source_version=digest(evidence),evidence_sha256=digest(evidence),input_sha256=digest(m),venue='J',
  availability_policy=m['availability_policy'],policy_manifest_sha256=sha(policy/'manifest.json'),
  daily_official_membership_complete=True,individual_restrictions_applied=True)
 files=[Path(__file__),Path(lib.__file__),Path(__file__).with_name('capture_reference_short_eligible.py'),
  Path(__file__).with_name('audit_reference_short_eligible.py'),Path(__file__).with_name('stage_krx_short_policy.py'),Path(__file__).with_name('stage_krx_membership_dom.py'),
  Path(__file__).with_name('audit_krx_membership_csv.py'),Path(__file__).with_name('capture_reference_short_daily.py'),
  Path(__file__).with_name('revise_short_policy_source.py')]
 implementation={str(p.relative_to(Path(__file__).resolve().parents[1])):dict(sha256=sha(p),source=p.read_text()) for p in files}
 save_json(out/'implementation-source.json',implementation);impl=digest(implementation)
 panel.to_parquet(out/'monthly-input.parquet',index=False);save_json(out/'source-evidence.json',evidence)
 with connect(read_only=False) as conn:
  for definition in lib.definitions():
   ref=definition['id'];series=lib.calculate(panel,ref);mask=series.notna()
   v=panel.loc[mask,['asset_id','stock_code','date','market']].copy();v['known_at']=pd.to_datetime(panel.loc[mask,'short_known_at'],utc=True)
   base._prepare(v);v['reference_id']=ref;v['value']=series[mask];v['oriented_value']=v.value
   v['definition_hash']=base.definition_hash(definition);v['source_version']=att['source_version'];v['input_sha256']=att['input_sha256'];v=v[base._OUTPUT].reset_index(drop=True)
   if v.asset_id.nunique()<100 or v.date.nunique()<60:raise ValueError('Insufficient coverage')
   check=parity(panel,v,ref,conn,specs=lib.SPECS)
   summary=dict(reference_id=ref,definition_hash=base.definition_hash(definition),status='MEASUREMENT_VALIDATED',value_rows=len(v),
    assets=int(v.asset_id.nunique()),months=int(v.date.nunique()),first_date=str(v.date.min().date()),last_date=str(v.date.max().date()))
   validation=dict(source_version=att['source_version'],input_sha256=att['input_sha256'],source_evidence_sha256=att['evidence_sha256'],
    implementation_sha256=impl,role='MEASUREMENT_CONTROL',alpha_approved=False,value_rows=len(v),references=[summary])
   pub,_=gold.build_publication(v,[definition],attestation=att,validation=validation,parity=check)
   dest=out/ref;dest.mkdir(exist_ok=True);save_json(dest/'publication.json',pub);v.to_parquet(dest/'values.parquet',index=False)
   print(summary,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--policy',required=True);p.add_argument('--output',required=True);a=p.parse_args();build(a.source,a.policy,a.output)
