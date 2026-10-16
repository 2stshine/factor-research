"""Explicit two-for-two collection replacement; preserve every old Gold dataset.

Preflight checks new values against the 106 retained measurements. Preparation
verifies committed Gold and builds an inert candidate program. It never activates
the candidate or deletes the old program/catalog/values.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from engine import reference_gold as gold,reference_library as base
from engine.reference_db import connect
from engine.reference_short_eligibility import REPLACEMENTS
from engine.phenomenon_reference_collection import read_collection_program
from engine.research_generation import digest
from scripts.audit_reference_new_information import baseline,indexed,pair
from scripts.publish_reference_expansion import load_json,save_json,sha,legacy_metadata_digest
from scripts.report_reference_expansion import describe

ROOT=Path(__file__).resolve().parents[1]
PARENT='e6c81cbc31b00a95ea74f7532fba59beaea61bbf02a657d7b34629bf1ca007a8'
BASELINE=ROOT/'output/phenomena/reference-new-information-20261003/activation-108-audit'

def inputs(build):
 program,catalog,_=read_collection_program(ROOT);prior,paths=baseline(program,PARENT,BASELINE)
 pubs={};frames={};value_paths={}
 for ref in REPLACEMENTS.values():
  path=Path(build)/ref;pub=load_json(path/'publication.json');f=pd.read_parquet(path/'values.parquet')
  gold.validate_publication(pub,gold.canonical_values(f))
  if set(pub['definitions'])!={ref}:raise ValueError('Exact replacement definition required')
  pubs[ref]=pub;frames[ref]=f;value_paths[pub['dataset_id']]=str((path/'values.parquet').resolve())
 return program,catalog,prior,paths,pubs,frames,value_paths

def preflight(build,output):
 program,catalog,prior,paths,pubs,frames,_=inputs(build);new={r:indexed(f) for r,f in frames.items()};comparisons=[];changes=[]
 for entry in program['reference_datasets']:
  did=entry['dataset_id'];path=paths[did]
  if sha(path)!=prior['cache_file_sha256'][did]:raise ValueError('Parent cache changed')
  for ref,g in pd.read_parquet(path).groupby('reference_id'):
   old=indexed(g)
   if ref in REPLACEMENTS:
    nr=REPLACEMENTS[ref];joined=pd.concat([old.rename('old'),new[nr].rename('new')],axis=1)
    if new[nr].index.get_level_values('date').max()<old.index.get_level_values('date').max():raise ValueError('Unreviewed loss of latest measurement month')
    both=joined.dropna();changed=~np.isclose(both.old,both.new,rtol=1e-12,atol=0)
    clocks=g[['asset_id','date','known_at']].copy();clocks['date']=pd.to_datetime(clocks.date)
    fresh=frames[nr][['asset_id','date','known_at']].copy();fresh['date']=pd.to_datetime(fresh.date)
    clocks=clocks.merge(fresh,on=['asset_id','date'],validate='one_to_one',suffixes=('_old','_new'))
    changed_clocks=int(pd.to_datetime(clocks.known_at_old,utc=True).ne(pd.to_datetime(clocks.known_at_new,utc=True)).sum())
    changes.append(dict(old_reference=ref,new_reference=nr,old_rows=len(old),new_rows=len(new[nr]),
     overlap=len(both),unchanged=int((~changed).sum()),changed=int(changed.sum()),
     changed_known_at_on_overlap=changed_clocks,
     added=int((joined.old.isna()&joined.new.notna()).sum()),removed=int((joined.old.notna()&joined.new.isna()).sum())))
   else:
    for nr,v in new.items():comparisons.append(dict(a=nr,b=ref,**pair(v,old)))
 a,b=list(new);comparisons.append(dict(a=a,b=b,**pair(new[a],new[b])))
 if any(x.get('identical') or x.get('affine_equivalent') for x in comparisons):raise ValueError('Duplicate retained measurement')
 result=dict(status='EXPLICIT_TWO_FOR_TWO_REPLACEMENT_PREFLIGHT_PASSED',parent_program_sha256=PARENT,
  replacements=REPLACEMENTS,changes=changes,comparisons=comparisons,
  publications={r:dict(dataset_id=p['dataset_id'],values_sha256=p['values_sha256']) for r,p in pubs.items()},
  old_datasets_preserved=True,unaffected_references=106,forward_returns_read=False,independent_alphas_claimed=False)
 save_json(output,result);print(dict(status=result['status'],changes=changes),flush=True)

def prepare(build,preflight_path,output):
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 program,catalog,prior,paths,pubs,frames,new_paths=inputs(build);pre=load_json(preflight_path)
 expected={r:dict(dataset_id=p['dataset_id'],values_sha256=p['values_sha256']) for r,p in pubs.items()}
 if pre['status']!='EXPLICIT_TWO_FOR_TWO_REPLACEMENT_PREFLIGHT_PASSED' or pre['publications']!=expected or pre['parent_program_sha256']!=PARENT:raise ValueError('Preflight mismatch')
 old_entries=[d for d in program['reference_datasets'] if set(d['reference_ids'])&set(REPLACEMENTS)]
 if len(old_entries)!=2 or any(len(d['reference_ids'])!=1 for d in old_entries):raise ValueError('Old refs not isolated datasets')
 datasets=[d for d in program['reference_datasets'] if d not in old_entries]
 definitions={r:d for r,d in catalog.items() if r not in REPLACEMENTS};coverage=[]
 for ref,pub in pubs.items():
  receipt=load_json(Path(build)/ref/'receipt-applied.json');check=load_json(Path(build)/ref/'committed-verification.json')
  if not receipt['outer_transaction_committed'] or not check['passed'] or check['dataset_id']!=pub['dataset_id']:raise ValueError('Uncommitted replacement')
  definitions[ref]=pub['definitions'][ref];datasets.append(dict(dataset_id=pub['dataset_id'],reference_ids=[ref]))
  coverage.append(dict(reference_id=ref,name_ko=definitions[ref]['name_ko'],dataset_id=pub['dataset_id'],**describe(frames[ref])))
 if len(definitions)!=len(catalog) or len(definitions)!=108:raise ValueError('Replacement changed reference count')
 all_paths={did:str(path.resolve()) for did,path in paths.items()};all_paths.update(new_paths)
 for did,path in paths.items():
  if sha(path)!=prior['cache_file_sha256'][did]:raise ValueError('Parent cache changed')
 with connect() as conn,conn.cursor() as cur:
  cur.execute("SET LOCAL statement_timeout='10min'")
  legacy=legacy_metadata_digest(conn)
  if legacy!=prior['legacy_metadata']:raise ValueError('Legacy changed')
  # Exact binary readback of both old datasets and both new datasets.
  for did in [d['dataset_id'] for d in old_entries]+list(new_paths):
   f,meta=gold.load_library(conn,dataset_id=did,snapshot_path=Path(all_paths[did]))
   if did in new_paths and meta!=next(p for p in pubs.values() if p['dataset_id']==did):raise ValueError('New publication differs')
  ids=list(all_paths)
  cur.execute('SELECT dataset_id,metadata FROM gold.reference_dataset WHERE dataset_id=ANY(%s::text[]) AND generation_id=%s',(ids,gold.GENERATION));live=dict(cur.fetchall())
  if set(live)!=set(ids):raise ValueError('Existing or new dataset absent')
  for entry in datasets+old_entries:
   pub=live[entry['dataset_id']]
   if digest({k:v for k,v in pub.items() if k!='dataset_id'})!=entry['dataset_id'] or set(pub['definitions'])!=set(entry['reference_ids']):raise ValueError('Live immutable binding changed')
   for ref,d in pub['definitions'].items():
    if base.definition_hash(d)!=base.definition_hash(definitions.get(ref,catalog.get(ref))):raise ValueError('Definition changed')
  cur.execute('SELECT dataset_id,reference_id,count(*) FROM gold.reference_value WHERE dataset_id=ANY(%s::text[]) AND generation_id=%s GROUP BY dataset_id,reference_id',(ids,gold.GENERATION))
  counts=cur.fetchall();rows={did:sum(n for d,r,n in counts if d==did) for did in ids}
  for did in paths:
   if rows[did]!=prior['dataset_rows'][did]:raise ValueError('Old rows changed')
  for did,pub in live.items():
   if rows[did]!=pub['row_count']:raise ValueError('Live row count differs')
 original=load_json(ROOT/program['catalog_path']);cat={**original,'definitions':[definitions[r] for r in sorted(definitions)]}
 save_json(out/'catalog.json',cat)
 candidate={**program,'catalog_path':'research/phenomena/reference-catalog-short-eligible-108-20261004.json',
  'catalog_sha256':sha(out/'catalog.json'),'reference_datasets':datasets}
 candidate['program_sha256']=digest({k:v for k,v in candidate.items() if k!='program_sha256'})
 save_json(out/'program.json',candidate);save_json(out/'prior-program.json',program)
 active_ids={d['dataset_id'] for d in datasets}
 result=dict(status='SHORT_REPLACEMENT_PREPARED_NOT_ACTIVATED',parent_program_sha256=PARENT,
  candidate_program_sha256=candidate['program_sha256'],references=108,datasets=len(datasets),
  rows=sum(rows[d] for d in active_ids),new_rows=sum(len(f) for f in frames.values()),new_coverage=coverage,
  replacements=REPLACEMENTS,archived_datasets=old_entries,old_datasets_exact_all_row_readback_verified=True,
  parent_references=106,unaffected_definitions_and_dataset_bindings_preserved=True,legacy_metadata=legacy,
  preflight_sha256=sha(preflight_path),live_database_verified=True,new_dataset_value_paths=new_paths,
  dataset_rows={d:rows[d] for d in active_ids},cache_paths={d:all_paths[d] for d in active_ids},
  cache_file_sha256={d:sha(all_paths[d]) for d in active_ids},pit_status='PIT_ASSUMED',alpha_approved=False,
  entire_user_request_complete=False)
 save_json(out/'completion.json',result);print({k:v for k,v in result.items() if isinstance(v,(str,int,bool))},flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',required=True);p.add_argument('--output',required=True)
 p.add_argument('--preflight');a=p.parse_args()
 if a.preflight:prepare(a.build,a.preflight,a.output)
 else:preflight(a.build,a.output)
