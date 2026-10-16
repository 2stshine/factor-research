"""Prepare (not activate) an additive, live-verified reference collection."""
import argparse
from itertools import combinations
from pathlib import Path
import numpy as np
import pandas as pd
from engine import reference_gold as gold,reference_library as base
from engine.reference_db import connect
from engine.phenomenon_reference_collection import read_collection_program
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_json,save_json,sha,legacy_metadata_digest
from scripts.report_reference_expansion import describe

ROOT=Path(__file__).resolve().parents[1]
PARENT_SHA='797c849cea0af2c076a790da68696348f925414a935250b35c3745a3c1c02289'
BASE_AUDIT=ROOT/'output/phenomena/reference-expansion-100-20261003/final-audit'

def indexed(frame):
 p=frame[['asset_id','date','value']].copy();p.asset_id=p.asset_id.astype(int);p.date=pd.to_datetime(p.date)
 return p.set_index(['asset_id','date']).value.sort_index()

def pair(a,b):
 j=pd.concat([a.rename('a'),b.rename('b')],axis=1,join='inner').dropna();n=len(j)
 if n<1000:return dict(overlap=n,checked=False)
 x,y=j.a.to_numpy(),j.b.to_numpy();sx=float(np.std(x));sy=float(np.std(y))
 identical=bool(np.allclose(x,y,rtol=1e-10,atol=1e-12))
 affine=False;corr=None
 if sx>1e-15 and sy>1e-15:
  u=(x-x.mean())/sx;v=(y-y.mean())/sy;corr=float(np.mean(u*v))
  affine=bool(np.max(np.abs(u-np.sign(corr)*v))<1e-8)
 return dict(overlap=n,checked=True,identical=identical,affine_equivalent=affine,correlation=corr)

def baseline(program,expected_parent,baseline_audit):
 if program['program_sha256']!=expected_parent:raise ValueError('Active parent changed; do not overwrite')
 audit=Path(baseline_audit);prior=load_json(audit/'completion.json')
 if prior.get('candidate_program_sha256')!=expected_parent or prior.get('live_database_verified') is not True:raise ValueError('Baseline audit does not certify parent program')
 ids={d['dataset_id'] for d in program['reference_datasets']}
 if set(prior['dataset_rows'])!=ids or set(prior['cache_file_sha256'])!=ids:raise ValueError('Baseline dataset/cache scope differs')
 paths={did:Path(prior.get('cache_paths',{}).get(did,audit/'collection-cache'/f'{did}.parquet')) for did in ids}
 return prior,paths

def preflight(builds,output,*,expected_parent=PARENT_SHA,baseline_audit=BASE_AUDIT):
 """No database writes: reject duplicates BEFORE publication."""
 program,catalog,_=read_collection_program(ROOT)
 prior,baseline_paths=baseline(program,expected_parent,baseline_audit);new={};publications={}
 for directory in builds:
  for path in sorted(Path(directory).glob('*/publication.json')):
   pub=load_json(path);frame=pd.read_parquet(path.with_name('values.parquet'))
   gold.validate_publication(pub,gold.canonical_values(frame))
   publications[pub['dataset_id']]=dict(values_sha256=pub['values_sha256'],publication_sha256=sha(path))
   for ref,group in frame.groupby('reference_id'):
    if ref in catalog or ref in new:raise ValueError('Reference ID reused')
    new[ref]=indexed(group)
 if not new:raise ValueError('No validated new measurements')
 results=[dict(a=a,b=b,**pair(new[a],new[b])) for a,b in combinations(sorted(new),2)]
 for entry in program['reference_datasets']:
  did=entry['dataset_id'];path=baseline_paths[did]
  if sha(path)!=prior['cache_file_sha256'][did]:raise ValueError('Baseline source cache changed')
  for ref,group in pd.read_parquet(path).groupby('reference_id'):
   old=indexed(group)
   for nr,values in new.items():results.append(dict(a=nr,b=ref,**pair(values,old)))
 if any(r.get('identical') or r.get('affine_equivalent') for r in results):raise ValueError('Duplicate/equivalent measurement; do not publish')
 result=dict(status='PREPUBLICATION_DUPLICATE_PREFLIGHT_PASSED',parent_program_sha256=expected_parent,
  new_references=sorted(new),publications=publications,pairs=results,forward_returns_read=False,
  semantics='No exact or affine duplicate on observed overlap; not proof of independent economic alpha')
 save_json(output,result);print(dict(status=result['status'],new_references=len(new),pairs=len(results)),flush=True)

def run(builds,output,*,expected_parent=PARENT_SHA,baseline_audit=BASE_AUDIT):
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 program,catalog,_=read_collection_program(ROOT)
 prior,baseline_paths=baseline(program,expected_parent,baseline_audit)
 original=load_json(ROOT/program['catalog_path'])
 definitions={d['id']:d for d in original['definitions']};datasets=list(program['reference_datasets']);new={};pubs={};coverage=[];caches={}
 for directory in builds:
  for path in sorted(Path(directory).glob('*/publication.json')):
   pub=load_json(path);receipt=load_json(path.with_name('receipt-applied.json'));verified=load_json(path.with_name('committed-verification.json'))
   if not receipt.get('outer_transaction_committed') or not verified.get('passed') or verified['dataset_id']!=pub['dataset_id']:raise ValueError('Uncommitted reference build')
   frame=pd.read_parquet(path.with_name('values.parquet'));gold.validate_publication(pub,gold.canonical_values(frame))
   if any(r in definitions for r in pub['definitions']):raise ValueError('Existing reference cannot be replaced')
   datasets.append(dict(dataset_id=pub['dataset_id'],reference_ids=sorted(pub['definitions'])))
   pubs[pub['dataset_id']]=pub;caches[pub['dataset_id']]=str(path.with_name('values.parquet').resolve())
   for ref,d in pub['definitions'].items():
    definitions[ref]=d;part=frame.loc[frame.reference_id.eq(ref)];new[ref]=indexed(part)
    coverage.append(dict(reference_id=ref,name_ko=d['name_ko'],dataset_id=pub['dataset_id'],**describe(part)))
 if not new:raise ValueError('No new committed measurements')
 print(dict(stage='publication_bindings_verified',new_references=len(new)),flush=True)
 duplicate=[]
 for a,b in combinations(sorted(new),2):duplicate.append(dict(a=a,b=b,**pair(new[a],new[b])))
 for entry in program['reference_datasets']:
  did=entry['dataset_id'];path=baseline_paths[did]
  if sha(path)!=prior['cache_file_sha256'][did]:raise ValueError('Baseline duplicate audit cache changed')
  frame=pd.read_parquet(path)
  for ref,group in frame.groupby('reference_id'):
   old=indexed(group)
   for nr,values in new.items():duplicate.append(dict(a=nr,b=ref,**pair(values,old)))
 if any(r.get('identical') or r.get('affine_equivalent') for r in duplicate):raise ValueError('Duplicate/equivalent reference found')
 save_json(out/'duplicate-audit.json',dict(status='NO_EXACT_OR_AFFINE_DUPLICATES_ON_OBSERVED_OVERLAP',pairs=duplicate,
  limitations='Not a proof of independent economic alpha. No returns read; pairs with fewer than 1000 overlaps are explicitly unchecked. Missing history not imputed.'))
 with connect() as conn,conn.cursor() as cur:
  cur.execute("SET LOCAL statement_timeout='10min'")
  legacy=legacy_metadata_digest(conn)
  if legacy!=prior['legacy_metadata']:raise ValueError('Legacy metadata changed')
  ids=[d['dataset_id'] for d in datasets]
  cur.execute('SELECT dataset_id,metadata FROM gold.reference_dataset WHERE dataset_id=ANY(%s::text[]) AND generation_id=%s',(ids,gold.GENERATION))
  live=dict(cur.fetchall())
  if set(live)!=set(ids):raise ValueError('Missing Gold datasets')
  for entry in datasets:
   pub=live[entry['dataset_id']]
   if digest({k:v for k,v in pub.items() if k!='dataset_id'})!=entry['dataset_id']:raise ValueError('Live metadata identity mismatch')
   if set(pub['definitions'])!=set(entry['reference_ids']) or pub['profitability_approved'] is not False:raise ValueError('Live definition scope changed')
   for ref,d in pub['definitions'].items():
    if base.definition_hash(d)!=base.definition_hash(definitions[ref]):raise ValueError('Live catalog hash differs')
   if entry['dataset_id'] in pubs and pubs[entry['dataset_id']]!=pub:raise ValueError('New live publication differs')
  cur.execute('''SELECT dataset_id,reference_id,count(*),count(DISTINCT asset_id),count(DISTINCT as_of_date),min(as_of_date),max(as_of_date)
   FROM gold.reference_value WHERE dataset_id=ANY(%s::text[]) AND generation_id=%s GROUP BY dataset_id,reference_id''',(ids,gold.GENERATION))
  counts=[dict(dataset_id=r[0],reference_id=r[1],rows=r[2],assets=r[3],months=r[4],first_date=str(r[5]),last_date=str(r[6])) for r in cur.fetchall()]
 expected={(d['dataset_id'],r) for d in datasets for r in d['reference_ids']}
 if {(r['dataset_id'],r['reference_id']) for r in counts}!=expected:raise ValueError('Live value partition mismatch')
 for did,pub in live.items():
  rows=sum(r['rows'] for r in counts if r['dataset_id']==did)
  if rows!=pub['row_count']:raise ValueError('Live row count changed')
  if did in prior['dataset_rows'] and rows!=prior['dataset_rows'][did]:raise ValueError('Existing parent value counts changed')
 for c in coverage:
  actual=next(r for r in counts if r['reference_id']==c['reference_id'])
  if actual['rows']!=c['value_rows'] or actual['assets']!=c['assets'] or actual['months']!=c['months']:raise ValueError('New coverage differs from committed values')
 cat={**original,'definitions':[definitions[r] for r in sorted(definitions)]};save_json(out/'catalog.json',cat)
 catpath=f'research/phenomena/reference-catalog-new-information-{len(definitions)}-20261003.json'
 candidate={**program,'catalog_path':catpath,'catalog_sha256':sha(out/'catalog.json'),'reference_datasets':datasets}
 candidate['program_sha256']=digest({k:v for k,v in candidate.items() if k!='program_sha256'});save_json(out/'program.json',candidate)
 all_paths={**{did:str(path.resolve()) for did,path in baseline_paths.items()},**caches}
 result=dict(status='ADDITIVE_COLLECTION_PREPARED_NOT_ACTIVATED',parent_program_sha256=expected_parent,
  parent_references=len(catalog),parent_audit_path=str(Path(baseline_audit).resolve()),
  candidate_program_sha256=candidate['program_sha256'],references=len(definitions),new_references=len(new),datasets=len(datasets),
  rows=sum(r['rows'] for r in counts),new_rows=sum(r['value_rows'] for r in coverage),new_coverage=coverage,
  live_counts=counts,legacy_metadata=legacy,duplicate_audit_sha256=sha(out/'duplicate-audit.json'),
  live_database_verified=True,new_dataset_value_paths=caches,alpha_approved=False,pit_status='PIT_ASSUMED',
  dataset_rows={did:sum(r['rows'] for r in counts if r['dataset_id']==did) for did in live},
  cache_paths=all_paths,cache_file_sha256={did:sha(path) for did,path in all_paths.items()},
  missing_consensus_history=True,entire_user_request_complete=False)
 save_json(out/'completion.json',result);print({k:v for k,v in result.items() if isinstance(v,(str,int,float,bool))},flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='append',required=True);p.add_argument('--output',required=True)
 p.add_argument('--preflight-only',action='store_true');p.add_argument('--expected-parent',default=PARENT_SHA)
 p.add_argument('--baseline-audit',default=str(BASE_AUDIT));a=p.parse_args()
 kwargs=dict(expected_parent=a.expected_parent,baseline_audit=a.baseline_audit)
 if a.preflight_only:preflight(a.build,a.output,**kwargs)
 else:run(a.build,a.output,**kwargs)
