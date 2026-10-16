"""Correct an overstrict policy-name gate without hiding original provenance.

2015-2025 have zero bad_short under the stricter query, proving relaxed-name
equivalence for every source day. Preserve their exact bytes/query receipts.
2026 is fully re-read with the corrected query. All substantive scope/time/
volume/identity checks remain identical. Gold has not consumed the rejected run.
"""
import argparse
from pathlib import Path
import shutil
import pandas as pd
from engine.research_generation import digest
from scripts.capture_reference_short_eligible import SQL,load_policy,policy_connection
from scripts.publish_reference_expansion import load_json,save_json,sha

STRICT_SQL=SQL.replace("OR k.policy_version IS NULL OR k.policy_version NOT IN ('kis-krx-short-scope-v2','kis-provider-trust-v1')",
 "OR k.policy_version IS DISTINCT FROM 'kis-krx-short-scope-v2'")

def run(source,policy,output):
 source=Path(source);policy=Path(policy);out=Path(output);out.mkdir(parents=True,exist_ok=True)
 if any(out.iterdir()):raise ValueError('Fresh revised source directory required')
 old=load_json(source/'manifest.json');_,members,restrictions=load_policy(policy)
 if old['query_sha256']!=digest(STRICT_SQL) or old['manifest_sha256']!=digest({k:v for k,v in old.items() if k!='manifest_sha256'}):raise ValueError('Unexpected original query')
 if old['policy_manifest_sha256']!=sha(policy/'manifest.json'):raise ValueError('Policy changed')
 files=[]
 for item in old['files']:
  path=source/item['path']
  if sha(path)!=item['sha256']:raise ValueError('Original source changed')
  if path.name=='short-2026.parquet':continue
  f=pd.read_parquet(path)
  if not f.bad_short.eq(0).all():raise ValueError('Strict-to-relaxed equivalence not established')
  shutil.copyfile(path,out/path.name)
  revised={**item,'equivalence':'ORIGINAL_STRICT_QUERY_ALL_BAD_SHORT_ZERO; ONLY_POLICY_NAME_GATE_RELAXED',
   'original_manifest_sha256':sha(source/'manifest.json')}
  save_json(out/path.with_suffix('.json').name,revised);files.append(revised)
 with policy_connection(members,restrictions) as conn,conn.cursor() as cur:
  cur.execute("SET LOCAL statement_timeout='10min'");cur.execute('SELECT pg_current_snapshot()::text,transaction_timestamp()');snapshot,at=cur.fetchone()
  cur.execute(SQL,('2026-01-01','2026-09-30')*2);f=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
 if f.empty or f.bad_identity.ne(0).any() or f.duplicated(['asset_id','date']).any():raise ValueError('Source identity mismatch')
 f.to_parquet(out/'short-2026.parquet',index=False)
 item=dict(path='short-2026.parquet',sha256=sha(out/'short-2026.parquet'),rows=len(f),query_sha256=digest(SQL),
  snapshot=snapshot,captured_at=at.isoformat(),policy_manifest_sha256=sha(policy/'manifest.json'))
 save_json(out/'short-2026.json',item);files.append(item)
 for name in ['fixed-raw-sample.parquet','fixed-raw-sample.json']:shutil.copyfile(source/name,out/name)
 evidence={**{k:v for k,v in old.items() if k not in ['manifest_sha256','files','query_sha256']},'files':files,'query_sha256':digest(SQL),
  'source_revision':dict(reason='POLICY_VERSION_NAME_IS_NOT_VENUE_SCOPE',original_manifest_sha256=sha(source/'manifest.json'),
   original_query_sha256=digest(STRICT_SQL),equivalent_unchanged_years=list(range(2015,2026)),recaptured_years=[2026],
   accepted_policy_names=['kis-krx-short-scope-v2','kis-provider-trust-v1'],substantive_scope_and_availability_checks_unchanged=True)}
 evidence['manifest_sha256']=digest(evidence);save_json(out/'manifest.json',evidence)
 print(dict(status='POLICY_NAME_GATE_CORRECTED',recaptured_rows=len(f),remaining_bad_short_days=int(f.bad_short.sum())),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--policy',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.source,a.policy,a.output)
