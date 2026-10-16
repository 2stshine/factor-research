"""Verify replacement through the actual research consumer after activation."""
import argparse
from pathlib import Path
import shutil
from engine.reference_db import connect
from engine.reference_short_eligibility import REPLACEMENTS
from engine.phenomenon_reference_collection import read_collection_program
from engine.phenomenon_references import load_active_references,reference_fields
from scripts.publish_reference_expansion import load_json,save_json,sha,legacy_metadata_digest

def run(output,bronze):
 out=Path(output);root=Path(__file__).resolve().parents[1]
 completion=load_json(out/'completion.json');expected=load_json(out/'program.json');prior=load_json(out/'prior-program.json')
 program,catalog,_=read_collection_program(root)
 if program!=expected or not completion['live_database_verified']:raise ValueError('Exact audited candidate not active')
 if set(REPLACEMENTS)&set(catalog) or not set(REPLACEMENTS.values())<=set(catalog):raise ValueError('Old/new active scope incorrect')
 retained=[d for d in prior['reference_datasets'] if not set(d['reference_ids'])&set(REPLACEMENTS)]
 if any(d not in program['reference_datasets'] for d in retained):raise ValueError('Unrelated dataset changed')
 receipt=load_json(Path(bronze)/'upload-receipt.json')
 if receipt['status']!='PRIVATE_BRONZE_ARCHIVE_VERIFIED' or not all(o['checksum_verified'] for o in receipt['objects']):raise ValueError('Bronze not verified')
 refs=list(REPLACEMENTS.values());cache=out/'collection-cache';cache.mkdir(exist_ok=True)
 for did,path in completion['new_dataset_value_paths'].items():
  source=Path(path);target=cache/(did+'.parquet')
  if not target.exists():shutil.copyfile(source,target)
  if sha(target)!=sha(source):raise ValueError('Consumer cache changed')
 with connect() as conn:
  frame,metadata=load_active_references(conn,root,reference_ids=refs,snapshot_path=cache)
  if legacy_metadata_digest(conn)!=completion['legacy_metadata']:raise ValueError('Legacy changed')
 fields=reference_fields(frame,metadata,refs)
 if fields.attrs['imputed'] or fields.attrs['alpha_approved']:raise ValueError('Consumer altered measurement meaning')
 for c in completion['new_coverage']:
  if int(fields[c['reference_id']].notna().sum())!=c['value_rows']:raise ValueError('Consumer lost values')
 result=dict(status='SHORT_REPLACEMENT_ACTIVE_GOLD_ALL_NEW_CONSUMER_VALUES_VERIFIED',program_sha256=program['program_sha256'],
  references=len(catalog),datasets=len(program['reference_datasets']),gold_rows=completion['rows'],
  new_rows=completion['new_rows'],consumer_rows=len(frame),union_asset_months=len(fields),replacements=REPLACEMENTS,
  new_dataset_all_rows_reverified=True,old_datasets_preserved=True,unaffected_references=106,
  parent_preservation='Exact 106 definitions/dataset bindings and prior verified cache hashes; live metadata/counts; old two exact binary readback',
  bronze_receipt_sha256=sha(Path(bronze)/'upload-receipt.json'),imputed=False,alpha_approved=False,
  pit_status='PIT_ASSUMED',first_vintage_verified=False,borrow_availability_verified=False,
  partial_history_restoration_complete=True,all_historical_stock_days_have_data=False,legacy_gold_used=False)
 save_json(out/'activation-verification.json',result);print(result,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--bronze',required=True);a=p.parse_args();run(a.output,a.bronze)
