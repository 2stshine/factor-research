"""Exercise the real active Gold consumer after the exact candidate cutover."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
from engine.reference_db import connect
from engine.phenomenon_reference_collection import read_collection_program
from engine.phenomenon_references import load_active_references,reference_fields
from scripts.publish_reference_expansion import load_json,save_json

REFERENCES=['kr_size_issue_v1','kr_tax_expense_change_assets_fy_v1',
    'kr_nonprice_size_total_assets_v1','kr_wq_041_daily_monthend_v1',
    'kr_bab_beta_reference_v1','kr_edge_spread_reference_v1',
    'kr_gross_profit_growth_per_share_5fy_reference_v1']

def run(directory):
    directory=Path(directory);root=Path(__file__).resolve().parents[1]
    completion=load_json(directory/'completion.json');candidate=load_json(directory/'program.json')
    program,catalog,generation=read_collection_program(root)
    if program!=candidate or not completion['complete'] or not completion['live_database_verified']:
        raise ValueError('Exact completed candidate is not active')
    if set(catalog)!={r for d in program['reference_datasets'] for r in d['reference_ids']}:
        raise ValueError('Catalog contains inactive/extra reference')
    with connect() as conn:
        frame,metadata=load_active_references(conn,root,snapshot_path=directory/'collection-cache',reference_ids=REFERENCES)
    fields=reference_fields(frame,metadata,REFERENCES)
    if fields.attrs['imputed'] or fields.attrs['alpha_approved']:raise ValueError('Consumer changed reference meaning')
    for ref in REFERENCES:
        if not fields[ref].notna().any():raise ValueError('Selected reference has no consumer values')
    result=dict(status='ACTIVE_PUBLISHED_AND_CONSUMER_VERIFIED',verified_at=datetime.now(timezone.utc).isoformat(),
        program_sha256=program['program_sha256'],catalog_sha256=program['catalog_sha256'],
        reference_count=len(catalog),dataset_count=len(program['reference_datasets']),gold_rows=completion['rows'],
        source_counts=completion['source_counts'],selected_references=REFERENCES,
        consumer_rows=len(frame),joined_asset_months=len(fields),
        full_verified_selected_dataset_rows=sum(d['value_rows'] for d in metadata['reference_datasets']),
        selected_nonnull={r:int(fields[r].notna().sum()) for r in REFERENCES},
        verification_scope='ALL_DATASETS_METADATA_COUNTS_AND_PUBLICATION_RECEIPTS; SELECTED_DATASETS_RECHECKED_ALL_ROWS_BY_ACTIVE_CONSUMER',
        alpha_approved=False,pit_status='PIT_ASSUMED',legacy_gold_used=False,imputed=False)
    save_json(directory/'activation-verification.json',result);print(result,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True)
    run(p.parse_args().directory)
