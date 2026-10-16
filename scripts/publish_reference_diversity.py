"""Publish small immutable batches, resume only exact completed checkpoints."""
import argparse
import gc
from pathlib import Path
import pandas as pd
from engine import reference_expansion_100 as lib, reference_library as base, reference_gold as gold
from engine.reference_diversity_parity import validate
from engine.reference_db import connect
from engine.research_generation import digest
from scripts.publish_reference_expansion import sha,save_json,load_json,legacy_metadata_digest

def run(source,output,apply=False):
    source,output=Path(source),Path(output)
    evidence=load_json(source/'input-evidence.json')
    if sha(source/'input.parquet')!=evidence['input_file_sha256']:
        raise ValueError('Input bytes differ')
    p=pd.read_parquet(source/'input.parquet')
    if lib.input_digest(p)!=evidence['input_sha256']:
        raise ValueError('Input digest differs')
    # Identity/time validation is shared with the original trusted adapter.
    base._prepare(p[list(base._BASE)])
    raw=lib.financial_values(p)
    definitions={d['id']:d for d in lib.definitions() if d['id'] in raw}
    old=base.load_catalog('research/phenomena/reference-catalog-47-20261003.json')
    if set(definitions)&{d['id'] for d in old}:raise ValueError('Existing ID collision')
    input_sha=lib.input_digest(p)
    att=dict(status='CERTIFIED',source_type=lib.SOURCE_TYPE,source_contract=lib.SOURCE_CONTRACT,
        scope=base.INPUT_SCOPE,identity_contract=base.IDENTITY_CONTRACT,pit_status=lib.PIT_STATUS,
        first_vintage_independently_verified=False,evidence_sha256=digest(evidence),
        source_version=digest(evidence),input_sha256=input_sha)
    refs=sorted(raw)
    output.mkdir(parents=True,exist_ok=True)
    for offset in range(0,len(refs),3):
        group=refs[offset:offset+3]
        out=output/f'group-{offset//3:02d}'
        out.mkdir(parents=True,exist_ok=True)
        if (out/'committed-verification.json').exists():
            pub=load_json(out/'publication.json')
            if set(pub['definitions'])!=set(group) or pub['input_sha256']!=input_sha or any(base.definition_hash(pub['definitions'][r])!=base.definition_hash(definitions[r]) for r in group):
                raise ValueError('Checkpoint differs from requested inputs/definitions')
            print(dict(resume='ALREADY_COMMITTED',references=group),flush=True)
            continue
        frames=[]; summaries=[]
        for ref in group:
            v=raw[ref]; definition=definitions[ref]
            frame=p.loc[v.notna(),list(base._BASE)].copy()
            frame['reference_id']=ref; frame['value']=v[v.notna()]
            frame['oriented_value']=frame.value*definition['orientation']
            frame['definition_hash']=base.definition_hash(definition)
            frame['source_version']=att['source_version']; frame['input_sha256']=input_sha
            frame=frame[base._OUTPUT].sort_values(['reference_id','asset_id','date']).reset_index(drop=True)
            assets,months=frame.asset_id.nunique(),frame.date.nunique()
            if assets<100 or months<60:raise ValueError(f'{ref}: insufficient coverage {assets}/{months}')
            summary=dict(reference_id=ref,definition_hash=base.definition_hash(definition),status='MEASUREMENT_VALIDATED',
                input_rows=len(p),value_rows=len(frame),assets=int(assets),months=int(months),
                first_date=str(frame.date.min().date()),last_date=str(frame.date.max().date()))
            print(summary,flush=True); summaries.append(summary);frames.append(frame)
        values=pd.concat(frames,ignore_index=True)
        validation=dict(source_version=att['source_version'],input_sha256=input_sha,source_evidence_sha256=digest(evidence),
            implementation_sha256=lib.implementation_hash(),role='MEASUREMENT_CONTROL',alpha_approved=False,
            value_rows=len(values),references=summaries)
        with connect(read_only=False) as conn:
            before=legacy_metadata_digest(conn)
            parity=validate(p,values,conn)
            publication,rows=gold.build_publication(values,[definitions[r] for r in group],attestation=att,validation=validation,parity=parity)
            save_json(out/'publication.json',publication)
            path=out/'values.parquet'
            if path.exists():pd.testing.assert_frame_equal(pd.read_parquet(path),values,check_exact=True)
            else:values.to_parquet(path,index=False)
            receipt=gold.publish(conn,publication,rows,apply=apply)
            if legacy_metadata_digest(conn)!=before:raise ValueError('Legacy metadata changed')
        receipt.update(outer_transaction_committed=apply,legacy_metadata_before=before,legacy_metadata_after=before)
        save_json(out/('receipt-applied.json' if apply else 'receipt-dry-run.json'),receipt)
        if apply:
            with connect() as conn:
                actual,meta=gold.load_library(conn,dataset_id=publication['dataset_id'],snapshot_path=path)
                if meta!=publication or len(actual)!=len(values):raise ValueError('Committed readback differs')
            save_json(out/'committed-verification.json',dict(passed=True,dataset_id=publication['dataset_id'],rows=len(values),reference_ids=group,profitability_approved=False))
        print(receipt,flush=True)
        del values,frames,rows
        gc.collect()

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',required=True,type=Path);ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    run(a.source,a.output,a.apply)
