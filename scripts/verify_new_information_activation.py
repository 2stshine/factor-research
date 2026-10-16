"""Exercise actual active Gold consumer for every newly added measurement."""
import argparse
from pathlib import Path
import shutil
from engine.reference_db import connect
from engine.phenomenon_reference_collection import read_collection_program
from engine.phenomenon_references import load_active_references,reference_fields
from scripts.publish_reference_expansion import load_json,save_json,sha,legacy_metadata_digest

def run(output):
 out=Path(output);root=Path(__file__).resolve().parents[1]
 completion=load_json(out/'completion.json');expected=load_json(out/'program.json')
 program,catalog,_=read_collection_program(root)
 if program!=expected or not completion['live_database_verified']:raise ValueError('Exact audited candidate is not active')
 refs=[r['reference_id'] for r in completion['new_coverage']]
 cache=out/'collection-cache';cache.mkdir(exist_ok=True)
 for did,path in completion['new_dataset_value_paths'].items():
  source=Path(path);target=cache/(did+'.parquet')
  if not target.exists():shutil.copyfile(source,target)
  if sha(target)!=sha(source):raise ValueError('New consumer cache changed')
 with connect() as conn:
  frame,metadata=load_active_references(conn,root,reference_ids=refs,snapshot_path=cache)
  if legacy_metadata_digest(conn)!=completion['legacy_metadata']:raise ValueError('Legacy changed')
 fields=reference_fields(frame,metadata,refs)
 if fields.attrs['imputed'] or fields.attrs['alpha_approved']:raise ValueError('Consumer changed measurement meaning')
 for c in completion['new_coverage']:
  if int(fields[c['reference_id']].notna().sum())!=c['value_rows']:raise ValueError('Consumer lost new values')
 result=dict(status='ACTIVE_GOLD_AND_ALL_NEW_CONSUMER_VALUES_VERIFIED',program_sha256=program['program_sha256'],
  references=len(catalog),datasets=len(program['reference_datasets']),gold_rows=completion['rows'],new_references=len(refs),
  new_rows=completion['new_rows'],consumer_rows=len(frame),union_asset_months=len(fields),
  all_new_nonnull_asset_months=int(fields[refs].notna().all(axis=1).sum()),
  references_verified=refs,new_dataset_all_rows_reverified=True,
  parent_references_preserved=completion['parent_references'],
  parent_preservation='Exact catalog definitions, immutable dataset IDs, live row counts and prior verified cache SHA256',
  imputed=False,alpha_approved=False,pit_status='PIT_ASSUMED',legacy_gold_used=False,
  entire_user_request_complete=completion['entire_user_request_complete'],consensus_history_loaded=False)
 save_json(out/'activation-verification.json',result);print(result,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);run(p.parse_args().output)
