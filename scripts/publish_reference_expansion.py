"""Bounded, checkpointed publication of explicitly attested reference features.

No future-return or legacy factor values are selected. The catalog is frozen
before measurement. Each new reference needs >=100 securities and >=60 observed
months, regardless of return performance. The old seven keep their exact Gold
dataset, while each new immutable publication contains at most three references.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from engine import reference_gold as gold, reference_library as base
from engine import reference_library_v2 as library, reference_financial_inputs as financial
from engine import reference_price_expansion as price
from engine.reference_db import connect
from engine.research_generation import canonical, digest, _immutable

MIN_ASSETS=100
MIN_MONTHS=60
GROUP_SIZE=3
ROOT=Path(__file__).resolve().parents[1]
OLD_DATASET='7f26985eab9cb2a7bf59aac109b142139072a5a8d0cd4fd8ea6e59dbcbe9859a'
OLD_BUILD=ROOT/'output/phenomena/reference-build-20261002-v4'


def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def save_json(path,value):
    _immutable(Path(path),canonical(value)+b'\n')


def load_json(path):return json.loads(Path(path).read_bytes())


def verify_price_capture(directory):
    directory=Path(directory)
    evidence=load_json(directory/'source-evidence.json')
    if (evidence.get('chunks_complete') is not True
        or evidence.get('source_type')!='RDS_CERTIFIED_KRX_EXTENDED_PRICE_V2'
        or evidence.get('query_sha256')!=hashlib.sha256(price.EXTENDED_PRICE_SQL.encode()).hexdigest()
        or evidence.get('input_file_sha256')!=sha(directory/'input.parquet')
        or not evidence.get('chunks')):
        raise ValueError('Only the complete, matching corrected price capture may be used')
    for item in evidence['chunks']:
        if Path(item['path']).name!=item['path'] or sha(directory/item['path'])!=item['sha256']:
            raise ValueError('Price source chunk mismatch')
    return evidence


def prepare(output,price_source,financial_source):
    output=Path(output)
    if (output/'input-attestation.json').exists():
        panel,attestation=load_input(output)
        print(f'Existing exact completed input: {len(panel)} rows',flush=True)
        return
    output.mkdir(parents=True,exist_ok=True)
    price_evidence=verify_price_capture(price_source)
    daily_audit=load_json(Path(price_source)/'daily-audit.json')
    from scripts.audit_reference_price_expansion import DAILY_SQL
    if (daily_audit.get('passed') is not True or daily_audit.get('failures')
        or daily_audit.get('input_file_sha256')!=price_evidence['input_file_sha256']
        or daily_audit.get('price_evidence_sha256')!=digest(price_evidence)
        or daily_audit.get('query_sha256')!=hashlib.sha256(DAILY_SQL.encode()).hexdigest()
        or daily_audit.get('oracle_sha256')!=sha(Path(price.__file__))
        or daily_audit.get('raw_file_sha256')!=sha(Path(price_source)/'daily-audit-input.parquet')):
        raise ValueError('Independent raw daily audit must pass before source preparation')
    source=pd.read_parquet(Path(price_source)/'input.parquet')
    print(f'Attaching exact annual filings to {len(source)} asset-months',flush=True)
    features,financial_evidence=financial.attach_capture(source,financial_source)
    features.to_parquet(output/'financial-features.parquet',index=False)
    keep=['asset_id','date','stock_code','market','financial_known_at',*library.FINANCIAL_COLUMNS]
    joined=source.merge(features[keep],on=['asset_id','date','stock_code','market'],
                        how='left',validate='one_to_one',indicator=True)
    if not joined._merge.eq('both').all():raise ValueError('Financial attachment changed base identity')
    joined['known_at']=pd.concat([pd.to_datetime(joined.known_at,utc=True),
                                  pd.to_datetime(joined.financial_known_at,utc=True)],axis=1).max(axis=1)
    panel=library.prepare(joined.loc[:,library.ALL_COLUMNS])
    panel.to_parquet(output/'input.parquet',index=False)
    evidence={
        'schema_version':'reference-expansion-input-evidence-v2',
        'source_contract':library.SOURCE_CONTRACT,
        'price_source':str(Path(price_source).resolve()),'price_evidence':price_evidence,
        'price_daily_audit':daily_audit,
        'financial_source':str(Path(financial_source).resolve()),'financial_evidence':financial_evidence,
        'financial_adapter_sha256':sha(Path(financial.__file__)),
        'financial_features_file_sha256':sha(output/'financial-features.parquet'),
        'input_file_sha256':sha(output/'input.parquet'),
        'input_rows':len(panel),'assets':int(panel.asset_id.nunique()),
        'first_date':str(panel.date.min().date()),'last_date':str(panel.date.max().date()),
        'pit_status':library.PIT_STATUS,'first_vintage_independently_verified':False,
        'snapshots':'PRICE_AND_FINANCIAL_CAPTURES_HAVE_INDEPENDENT_IMMUTABLE_SNAPSHOTS',
        'availability':'MAX_PRICE_AND_SELECTED_FY_CLOCK_LE_CALENDAR_MONTH_END_KST',
        'financial_currency':'KRW_ONLY_NO_IMPLICIT_FX',
        'eligibility':{'minimum_assets':MIN_ASSETS,'minimum_observed_months':MIN_MONTHS,
                       'selection_uses_returns':False},
        'legacy_gold_used':False,'forward_labels_read':False,
    }
    evidence_sha=digest(evidence)
    attestation={
        'status':'CERTIFIED','source_type':library.SOURCE_TYPE,'source_contract':library.SOURCE_CONTRACT,
        'scope':base.INPUT_SCOPE,'identity_contract':base.IDENTITY_CONTRACT,
        'pit_status':library.PIT_STATUS,'first_vintage_independently_verified':False,
        'source_version':evidence_sha,'evidence_sha256':evidence_sha,
        'input_sha256':library.input_digest(panel),
        'feature_contracts':library.FEATURE_CONTRACTS,'feature_units':library.FEATURE_UNITS,
    }
    library.validate_attestation(panel,attestation)
    save_json(output/'source-evidence.json',evidence)
    save_json(output/'input-attestation.json',attestation)
    print(json.dumps({'status':'INPUT_READY_NOT_PUBLISHED','input_rows':len(panel),'assets':evidence['assets'],
                      'financial_status':financial_evidence['status_counts']},ensure_ascii=False),flush=True)


def load_input(output):
    output=Path(output)
    evidence=load_json(output/'source-evidence.json');attestation=load_json(output/'input-attestation.json')
    if digest(evidence)!=attestation.get('evidence_sha256') or sha(output/'input.parquet')!=evidence['input_file_sha256']:
        raise ValueError('Frozen source bytes or provenance changed')
    if evidence.get('financial_adapter_sha256')!=sha(Path(financial.__file__)):
        raise ValueError('Financial adapter changed; reattach the immutable capture into a fresh build')
    panel=pd.read_parquet(output/'input.parquet')
    library.validate_attestation(panel,attestation)
    return library.prepare(panel),attestation


def calculate(output):
    output=Path(output);panel,attestation=load_input(output)
    catalog=base.load_catalog(library.CATALOG_PATH)
    selected=[d for d in catalog if d['id'] not in base._EXECUTABLE]
    (output/'references').mkdir(exist_ok=True)
    summaries=[];eligible=[]
    for definition in selected:
        ref=definition['id']
        values,summary=library.calculate_one(panel,ref,attestation=attestation,validated=True)
        summary['eligible_for_publication']=summary['assets']>=MIN_ASSETS and summary['months']>=MIN_MONTHS
        path=output/'references'/f'{ref}.parquet'
        if path.exists():
            pd.testing.assert_frame_equal(values,pd.read_parquet(path),check_exact=True)
        else:values.to_parquet(path,index=False)
        summary['values_file_sha256']=sha(path)
        save_json(output/'references'/f'{ref}.json',summary)
        summaries.append(summary)
        if summary['eligible_for_publication']:eligible.append(ref)
        print(f'{ref}: {len(values):,} values / {summary["assets"]:,} assets / {summary["months"]} months; eligible={summary["eligible_for_publication"]}',flush=True)
        del values;gc.collect()
    plan={
        'schema_version':'reference-expansion-publication-plan-v1','generation_id':gold.GENERATION,
        'catalog_sha256':sha(library.CATALOG_PATH),'input_sha256':attestation['input_sha256'],
        'implementation_sha256':library.implementation_hash(),'minimum_assets':MIN_ASSETS,'minimum_months':MIN_MONTHS,
        'existing_dataset_id':OLD_DATASET,'existing_reference_ids':sorted(base._EXECUTABLE),
        'references':summaries,'eligible_references':eligible,
        'groups':[eligible[i:i+GROUP_SIZE] for i in range(0,len(eligible),GROUP_SIZE)],
        'expected_total_references':7+len(eligible),'alpha_approved':False,
    }
    if plan['expected_total_references']<30:raise ValueError('Fewer than 30 references meet the data threshold; acquisition required')
    plan['plan_sha256']=digest(plan)
    save_json(output/'publication-plan.json',plan)
    print(json.dumps({'status':'CALCULATED_NOT_PUBLISHED','eligible_new':len(eligible),'groups':len(plan['groups'])}),flush=True)


def legacy_metadata_digest(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*),md5(coalesce(string_agg(md5(to_jsonb(f)::text),'' ORDER BY factor_id),'')) FROM gold.factor f")
        count,value=cur.fetchone()
    return {'records':count,'opaque_metadata_md5':value}


def validate_plan(plan):
    if (plan.get('schema_version')!='reference-expansion-publication-plan-v1'
        or plan.get('generation_id')!=gold.GENERATION
        or plan.get('plan_sha256')!=digest({k:v for k,v in plan.items() if k!='plan_sha256'})
        or plan.get('catalog_sha256')!=sha(library.CATALOG_PATH)
        or plan.get('implementation_sha256')!=library.implementation_hash()
        or plan.get('minimum_assets')!=MIN_ASSETS or plan.get('minimum_months')!=MIN_MONTHS
        or plan.get('existing_dataset_id')!=OLD_DATASET
        or plan.get('existing_reference_ids')!=sorted(base._EXECUTABLE)):
        raise ValueError('Frozen publication plan contract mismatch')
    definitions={d['id']:d for d in base.load_catalog(library.CATALOG_PATH) if d['id'] not in base._EXECUTABLE}
    summaries=plan['references'];names=[s['reference_id'] for s in summaries]
    if len(names)!=len(set(names)) or set(names)!=set(definitions):raise ValueError('Exact complete candidate summaries required')
    eligible=[]
    for summary in summaries:
        if summary['definition_hash']!=definitions[summary['reference_id']]['definition_hash']:
            raise ValueError('Plan definition hash mismatch')
        expected=summary['assets']>=MIN_ASSETS and summary['months']>=MIN_MONTHS and summary['value_rows']>0
        if summary['eligible_for_publication'] is not expected:raise ValueError('Plan eligibility mismatch')
        if expected:eligible.append(summary['reference_id'])
    groups=plan['groups']
    if (not groups or any(not isinstance(group,list) or not 0<len(group)<=GROUP_SIZE for group in groups)
        or [ref for group in groups for ref in group]!=eligible or plan['eligible_references']!=eligible
        or plan['expected_total_references']!=len(eligible)+len(base._EXECUTABLE)
        or plan['expected_total_references']<30):
        raise ValueError('Unique bounded eligible partition with at least 30 references required')


def validate_publication_binding(publication,plan,refs,attestation):
    if (set(publication['definitions'])!=set(refs) or publication.get('input_sha256')!=plan['input_sha256']
        or publication.get('attestation')!=attestation
        or publication['validation'].get('implementation_sha256')!=plan['implementation_sha256']
        or publication['validation'].get('references')!=[s for s in plan['references'] if s['reference_id'] in refs]):
        raise ValueError('Publication checkpoint differs from exact current plan/input')


def publish_group(output,index,*,apply=False):
    from engine.reference_expansion_parity import validate_parity
    output=Path(output);plan=load_json(output/'publication-plan.json')
    validate_plan(plan)
    if index<0 or index>=len(plan['groups']):raise ValueError('Invalid group index')
    refs=plan['groups'][index]
    panel,attestation=load_input(output)
    if attestation['input_sha256']!=plan['input_sha256']:
        raise ValueError('Publication plan differs from exact input snapshot')
    frames=[]
    for ref in refs:
        summary=load_json(output/'references'/f'{ref}.json')
        planned=next(s for s in plan['references'] if s['reference_id']==ref)
        if summary!=planned:raise ValueError('Per-reference checkpoint differs from publication plan')
        path=output/'references'/f'{ref}.parquet'
        if sha(path)!=summary['values_file_sha256']:raise ValueError('Reference snapshot byte mismatch')
        values,check=library.calculate_one(panel,ref,attestation=attestation,validated=True)
        if any(summary.get(key)!=value for key,value in check.items()):
            raise ValueError('Recalculated reference coverage differs from frozen summary')
        if check['assets']<MIN_ASSETS or check['months']<MIN_MONTHS or check['value_rows']<=0:
            raise ValueError('Recalculated reference fails publication data threshold')
        pd.testing.assert_frame_equal(values,pd.read_parquet(path),check_exact=True)
        frames.append(values)
    values=pd.concat(frames,ignore_index=True);del frames;gc.collect()
    definitions=[d for d in base.load_catalog(library.CATALOG_PATH) if d['id'] in refs]
    validation={'source_version':attestation['source_version'],'input_sha256':attestation['input_sha256'],
                'source_evidence_sha256':attestation['evidence_sha256'],'implementation_sha256':plan['implementation_sha256'],
                'role':'MEASUREMENT_CONTROL','alpha_approved':False,'value_rows':len(values),
                'references':[s for s in plan['references'] if s['reference_id'] in refs]}
    group_dir=output/'groups'/f'{index:02d}';group_dir.mkdir(parents=True,exist_ok=True)
    existing_receipt=group_dir/'receipt-applied.json'
    if existing_receipt.exists():
        receipt=load_json(existing_receipt);publication=load_json(group_dir/'publication.json')
        validate_publication_binding(publication,plan,refs,attestation)
        if (not receipt.get('outer_transaction_committed') or receipt.get('status') not in ('PUBLISHED','ALREADY_PUBLISHED')
            or receipt.get('dataset_id')!=publication['dataset_id']
            or set(publication['definitions'])!=set(refs)):
            raise ValueError('Invalid committed checkpoint')
        with connect() as conn:
            cached,metadata=gold.load_library(conn,dataset_id=publication['dataset_id'],
                snapshot_path=output/'collection-cache'/(publication['dataset_id']+'.parquet'))
            if metadata!=publication:raise ValueError('Checkpoint differs from committed metadata')
            pd.testing.assert_frame_equal(values[list(cached)].reset_index(drop=True),cached.reset_index(drop=True),check_exact=True,check_dtype=False)
        print(f'Group {index}: existing committed checkpoint reverified ({len(cached):,} rows)',flush=True)
        return receipt
    with connect(read_only=False) as conn:
        before=legacy_metadata_digest(conn)
        print(f'Group {index}: full independent parity for {len(values):,} rows',flush=True)
        parity=validate_parity(panel,values,conn)
        publication,rows=gold.build_publication(values,definitions,attestation=attestation,validation=validation,parity=parity)
        save_json(group_dir/'publication.json',publication)
        cache=output/'collection-cache';cache.mkdir(exist_ok=True)
        cache_path=cache/(publication['dataset_id']+'.parquet')
        if cache_path.exists():pd.testing.assert_frame_equal(values,pd.read_parquet(cache_path),check_exact=True)
        else:values.to_parquet(cache_path,index=False)
        schema=gold.install_schema(conn,apply=apply)
        receipt=gold.publish(conn,publication,rows,apply=apply)
        after=legacy_metadata_digest(conn)
        if before!=after:raise ValueError('Legacy metadata changed during publication; transaction rolled back')
        receipt.update(schema=schema,legacy_metadata_before=before,legacy_metadata_after=after)
    # Only the exited outer connection context has committed the transaction.
    receipt['outer_transaction_committed']=bool(apply)
    save_json(group_dir/('receipt-applied.json' if apply else 'receipt-dry-run.json'),receipt)
    print(json.dumps(receipt,ensure_ascii=False),flush=True)
    return receipt


def activation_plan(output):
    """Prepare exact binding only after committed reads; caller applies via patch."""
    output=Path(output);plan=load_json(output/'publication-plan.json')
    validate_plan(plan)
    panel,attestation=load_input(output)
    if attestation['input_sha256']!=plan['input_sha256']:raise ValueError('Activation input differs from plan')
    del panel;gc.collect()
    all_new=[ref for group in plan['groups'] for ref in group]
    if (len(all_new)!=len(set(all_new)) or all_new!=plan['eligible_references']
        or set(all_new).intersection(base._EXECUTABLE) or len(all_new)+len(base._EXECUTABLE)<30):
        raise ValueError('At least 30 unique exact planned references required')
    entries=[{'dataset_id':OLD_DATASET,'reference_ids':sorted(base._EXECUTABLE)}]
    total_rows=0
    with connect() as conn:
        old_values,old_metadata=gold.load_library(conn,dataset_id=OLD_DATASET,snapshot_path=OLD_BUILD/'values.parquet')
        current_catalog={d['id']:d for d in base.load_catalog(library.CATALOG_PATH)}
        if (set(old_metadata.get('definitions',{}))!=set(base._EXECUTABLE)
            or any(base.definition_hash(definition)!=current_catalog[ref]['definition_hash']
                   for ref,definition in old_metadata['definitions'].items())
            or set(old_values.reference_id)!=set(base._EXECUTABLE)):
            raise ValueError('Original seven definitions differ from exact reusable dataset')
        total_rows+=len(old_values)
        cache=output/'collection-cache';cache.mkdir(exist_ok=True)
        old_path=cache/(OLD_DATASET+'.parquet')
        if old_path.exists():
            if sha(old_path)!=sha(OLD_BUILD/'values.parquet'):raise ValueError('Old cache differs')
        else:shutil.copyfile(OLD_BUILD/'values.parquet',old_path)
        del old_values;gc.collect()
        for index,refs in enumerate(plan['groups']):
            group=output/'groups'/f'{index:02d}'
            receipt=load_json(group/'receipt-applied.json');publication=load_json(group/'publication.json')
            validate_publication_binding(publication,plan,refs,attestation)
            if (not receipt.get('outer_transaction_committed') or receipt['status'] not in ('PUBLISHED','ALREADY_PUBLISHED')
                or receipt.get('dataset_id')!=publication['dataset_id']):
                raise ValueError('Not all groups have committed')
            dataset=publication['dataset_id']
            verified,metadata=gold.load_library(conn,dataset_id=dataset,snapshot_path=cache/(dataset+'.parquet'))
            if set(verified.reference_id)!=set(refs) or metadata!=publication:raise ValueError('Readback reference partition differs')
            total_rows+=len(verified)
            entries.append({'dataset_id':dataset,'reference_ids':refs})
            print(f'Committed readback group {index}: {len(verified):,} rows',flush=True)
            del verified,metadata;gc.collect()
    body={'schema_version':'phenomenon-program-v2','generation_id':gold.GENERATION,
          'catalog_path':str(library.CATALOG_PATH.relative_to(ROOT)),'catalog_sha256':plan['catalog_sha256'],
          'reference_datasets':entries,'legacy_gold_policy':'EXCLUDED_NO_FALLBACK'}
    program={**body,'program_sha256':digest(body)}
    save_json(output/'verified-program-proposal.json',program)
    save_json(output/'completion.json',{'status':'COMMITTED_AND_READ_BACK_AWAITING_ACTIVE_POINTER',
        'references':sum(len(e['reference_ids']) for e in entries),'datasets':len(entries),'value_rows':total_rows,
        'verified_at':datetime.now(timezone.utc).isoformat(),'program_sha256':program['program_sha256'],
        'alpha_approved':False,'first_vintage_verified':False})
    print(json.dumps(load_json(output/'completion.json')),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','calculate','publish-group','activation-plan'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--price-source',type=Path);parser.add_argument('--financial-source',type=Path)
    parser.add_argument('--group',type=int);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if args.command=='prepare':
        if not args.price_source or not args.financial_source:parser.error('Both completed source directories required')
        prepare(args.output,args.price_source,args.financial_source)
    elif args.command=='calculate':calculate(args.output)
    elif args.command=='publish-group':
        if args.group is None:parser.error('--group required')
        publish_group(args.output,args.group,apply=args.apply)
    else:activation_plan(args.output)


if __name__=='__main__':main()
