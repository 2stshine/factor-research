"""Read-only live Gold inventory and source coverage for the active collection."""
from __future__ import annotations

import argparse
from collections import Counter
import gc
from pathlib import Path

import pandas as pd

from engine import reference_library as base, reference_library_v2 as library, reference_gold as gold
from engine.reference_db import connect
from engine.phenomenon_reference_collection import read_collection_program
from engine.research_generation import digest
from scripts.publish_reference_expansion import (ROOT,OLD_BUILD,OLD_DATASET,load_json,save_json,validate_plan,
                                                validate_publication_binding,load_input,sha)


def report(output):
    output=Path(output);plan=load_json(output/'publication-plan.json');validate_plan(plan)
    panel,attestation=load_input(output)
    if attestation['input_sha256']!=plan['input_sha256']:
        raise ValueError('Inventory input differs from frozen publication plan')
    del panel;gc.collect()
    completed=load_json(output/'completion.json')
    program,catalog,_=read_collection_program(ROOT)
    if program['program_sha256']!=completed['program_sha256']:
        raise ValueError('Active program differs from fully committed/read-back collection')
    ids=[entry['dataset_id'] for entry in program['reference_datasets']]
    expected_pairs={(entry['dataset_id'],ref) for entry in program['reference_datasets'] for ref in entry['reference_ids']}
    metadata_by_id={}
    with connect() as conn,conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout='10min'")
        cur.execute('''SELECT dataset_id,metadata FROM gold.reference_dataset
            WHERE dataset_id=ANY(%s::text[]) AND generation_id=%s''',(ids,gold.GENERATION))
        records=cur.fetchall()
        if len(records)!=len(ids) or {row[0] for row in records}!=set(ids):
            raise ValueError('Live Gold metadata differs from exact active dataset collection')
        for dataset_id,metadata in records:
            if (not isinstance(metadata,dict) or metadata.get('dataset_id')!=dataset_id
                or digest({k:v for k,v in metadata.items() if k!='dataset_id'})!=dataset_id
                or metadata.get('generation_id')!=gold.GENERATION or metadata.get('role')!=gold.ROLE
                or metadata.get('profitability_approved') is not False or metadata.get('legacy_gold_used') is not False):
                raise ValueError('Live Gold publication metadata binding invalid')
            metadata_by_id[dataset_id]=metadata
        for entry in program['reference_datasets']:
            metadata=metadata_by_id[entry['dataset_id']];refs=entry['reference_ids']
            definitions=metadata.get('definitions',{})
            if (set(definitions)!=set(refs) or any(base.definition_hash(definitions[ref])!=catalog[ref]['definition_hash'] for ref in refs)):
                raise ValueError('Live Gold definitions differ from exact active catalog partition')
            if entry['dataset_id']!=OLD_DATASET:
                validate_publication_binding(metadata,plan,refs,attestation)
        cur.execute('''SELECT dataset_id,reference_id,count(*),count(DISTINCT asset_id),
            count(DISTINCT as_of_date),min(as_of_date),max(as_of_date)
            FROM gold.reference_value WHERE dataset_id=ANY(%s::text[]) AND generation_id=%s
            GROUP BY dataset_id,reference_id ORDER BY reference_id''',(ids,gold.GENERATION))
        inventory=[dict(dataset_id=r[0],reference_id=r[1],value_rows=r[2],assets=r[3],months=r[4],
                        first_date=str(r[5]),last_date=str(r[6])) for r in cur.fetchall()]
    expected={ref for entry in program['reference_datasets'] for ref in entry['reference_ids']}
    if len(inventory)!=len(expected) or {(r['dataset_id'],r['reference_id']) for r in inventory}!=expected_pairs:
        raise ValueError('Live Gold dataset/reference assignment differs from active collection')
    for dataset_id,metadata in metadata_by_id.items():
        if sum(item['value_rows'] for item in inventory if item['dataset_id']==dataset_id)!=metadata.get('row_count'):
            raise ValueError('Live Gold dataset row count differs from committed metadata')
    snapshots={}
    old=pd.read_parquet(OLD_BUILD/'values.parquet')
    if digest(gold.canonical_values(old))!=metadata_by_id[OLD_DATASET]['values_sha256']:
        raise ValueError('Original reference values differ from committed Gold metadata')
    old_input=pd.read_parquet(OLD_BUILD/'input.parquet')
    if base.input_panel_digest(old_input)!=metadata_by_id[OLD_DATASET]['input_sha256']:
        raise ValueError('Original reference input differs from committed Gold metadata')
    identity=base._prepare(old_input)[['asset_id','date','stock_code','market']]
    old['asset_id']=old.asset_id.astype(str);old['date']=pd.to_datetime(old.date)
    # market is absent from Gold's seven-column value hash. Derive it from the
    # verified source input instead of trusting the extra cache display column.
    old=old.drop(columns='market',errors='ignore').merge(identity,on=['asset_id','date','stock_code'],
                                                       how='left',validate='many_to_one',indicator=True)
    if not old._merge.eq('both').all():raise ValueError('Original reference identity absent from verified input')
    old=old.drop(columns='_merge')
    del old_input,identity;gc.collect()
    for ref,group in old.groupby('reference_id'):
        snapshots[ref]=describe(group)
    del old;gc.collect()
    for ref in plan['eligible_references']:
        path=output/'references'/f'{ref}.parquet'
        summary=next(item for item in plan['references'] if item['reference_id']==ref)
        if sha(path)!=summary['values_file_sha256']:
            raise ValueError('Reference display cache differs from frozen publication summary: '+ref)
        frame=pd.read_parquet(path)
        snapshots[ref]=describe(frame)
        del frame
    summaries={s['reference_id']:s for s in plan['references']}
    for item in inventory:
        ref=item['reference_id'];definition=catalog[ref];source=snapshots[ref]
        for key in ('value_rows','assets','months','first_date','last_date'):
            if item[key]!=source[key]:raise ValueError('Live Gold coverage differs from verified source cache: '+ref)
        item.update(name_ko=definition['name_ko'],family=definition['family'],
                    evidence_tier=definition.get('evidence_tier','ORIGINAL_V1_LITERATURE_MEASUREMENT'),
                    by_market=source['by_market'],median_observed_months_per_asset=source['median_observed_months_per_asset'],
                    assets_with_60_observed_months=source['assets_with_60_observed_months'],
                    assets_with_120_observed_months=source['assets_with_120_observed_months'])
        if ref in summaries:item['raw_value_diagnostics']=summaries[ref]['raw_value_diagnostics']
    evidence=load_json(output/'source-evidence.json')
    result={'status':'ACTIVE_LIVE_GOLD_INVENTORY_VERIFIED',
            'report_scope':'LIVE_COUNTS_NOT_CURRENT_FULL_VALUE_REAUDIT',
            'references':len(inventory),'datasets':len(ids),
            'value_rows':sum(r['value_rows'] for r in inventory),'program_sha256':program['program_sha256'],
            'family_counts':dict(Counter(r['family'] for r in inventory)),
            'evidence_tier_counts':dict(Counter(r['evidence_tier'] for r in inventory)),
            'price_input_rows':evidence['input_rows'],'price_input_assets':evidence['assets'],
            'price_first_date':evidence['first_date'],'price_last_date':evidence['last_date'],
            'first_vintage_independently_verified':False,'alpha_approved':False,'legacy_gold_used':False,
            'financial_source_coverage':evidence['financial_evidence'],
            'inventory':inventory}
    if result['value_rows']!=completed['value_rows'] or result['references']<30:
        raise ValueError('Live inventory does not meet committed completion count')
    save_json(output/'live-gold-inventory.json',result)
    print({key:result[key] for key in ('status','references','datasets','value_rows','family_counts')},flush=True)


def describe(frame):
    depth=frame.groupby('asset_id').date.nunique()
    return {'value_rows':len(frame),'assets':int(frame.asset_id.nunique()),'months':int(frame.date.nunique()),
            'first_date':str(pd.Timestamp(frame.date.min()).date()),'last_date':str(pd.Timestamp(frame.date.max()).date()),
            'median_observed_months_per_asset':float(depth.median()),
            'assets_with_60_observed_months':int(depth.ge(60).sum()),
            'assets_with_120_observed_months':int(depth.ge(120).sum()),
            'by_market':{str(market):{'value_rows':len(group),'assets':int(group.asset_id.nunique()),
                                    'months':int(group.date.nunique())} for market,group in frame.groupby('market')}}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    report(parser.parse_args().output)
