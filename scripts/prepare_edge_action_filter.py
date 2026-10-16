"""Narrow pre-publication EDGE corporate-action safeguard, preserving raw audit.

The parent arrays were computed by vector and author-based scalar EDGE across
all input rows. This adds separately computed monthly event masks to both;
neither returns, performance thresholds nor ex-post wins enter this filter.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from engine import reference_daily_diversity as daily,reference_risk_catalog as catalog
from engine import reference_gold as gold,reference_library as base
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_json,save_json,sha

def run():
    root=Path('output/phenomena/reference-expansion-100-20261003')
    parent=root/'risk-build';checkpoint=load_json(parent/'raw-checkpoint.json')
    for name,key in [('raw-measurements.parquet','values_file_sha256'),('raw-oracle.parquet','oracle_file_sha256')]:
        if sha(parent/name)!=checkpoint[key]:raise ValueError('Parent calculation bytes changed')
    x,dates,assets,valid,jumps,manifest=daily.load_matrices(root/'daily-source-v2')
    financial_evidence=load_json(root/'financial-diversity/input-evidence.json')
    if sha(root/'financial-diversity/input.parquet')!=financial_evidence['input_file_sha256']:
        raise ValueError('Financial identity input bytes changed')
    if checkpoint['input_sha256']!=digest(dict(daily=manifest['manifest_sha256'],financial=financial_evidence)):
        raise ValueError('Parent oracle arrays belong to a different raw source')
    monthly=pd.DataFrame(jumps,index=dates).resample('ME').max()
    separate=np.array([jumps[dates.to_period('M')==period].any(axis=0) for period in monthly.index.to_period('M')])
    np.testing.assert_array_equal(monthly.to_numpy(),separate)
    identity=pd.read_parquet(root/'financial-diversity/input.parquet')[list(base._BASE)]
    grid=pd.MultiIndex.from_product([monthly.index,assets.astype(str)],names=['date','asset_id'])
    ix=grid.get_indexer(pd.MultiIndex.from_frame(identity[['date','asset_id']]))
    if (ix<0).any():raise ValueError('EDGE month identity absent')
    actual=pd.read_parquet(parent/'raw-measurements.parquet',columns=['edge_spread']).edge_spread.to_numpy()
    expected=pd.read_parquet(parent/'raw-oracle.parquet',columns=['edge_spread']).edge_spread.to_numpy()
    actual=np.where(~monthly.to_numpy().ravel()[ix],actual,np.nan)
    expected=np.where(~separate.ravel()[ix],expected,np.nan)
    np.testing.assert_allclose(actual,expected,rtol=1e-7,atol=1e-8,equal_nan=True)
    d=next(d for d in catalog.definitions() if d['id']=='kr_edge_spread_reference_v1')
    evidence=dict(source_contract=catalog.SOURCE_CONTRACT,parent_checkpoint=checkpoint,
        daily_manifest_sha256=manifest['manifest_sha256'],first_vintage_verified=False,pit_status='PIT_ASSUMED',
        forward_labels_read=False,legacy_gold_used=False,rule='EXCLUDE_MONTH_ANY_ADJ_FACTOR_JUMP_GT_1e-6',
        monthly_identity_sha256=digest(identity.astype(str).to_dict('records')))
    input_hash=digest(evidence);evidence['input_sha256']=input_hash
    att=dict(status='CERTIFIED',source_type=catalog.SOURCE_TYPE,source_contract=catalog.SOURCE_CONTRACT,
        scope=base.INPUT_SCOPE,identity_contract=base.IDENTITY_CONTRACT,pit_status='PIT_ASSUMED',
        first_vintage_independently_verified=False,source_version=digest(evidence),input_sha256=input_hash,evidence_sha256=digest(evidence))
    values=identity.loc[np.isfinite(actual)].copy();values['value']=actual[np.isfinite(actual)]
    values['reference_id']=d['id'];values['oriented_value']=values.value*d['orientation']
    values['definition_hash']=base.definition_hash(d);values['source_version']=att['source_version'];values['input_sha256']=input_hash
    values=values[base._OUTPUT].sort_values(['reference_id','asset_id','date']).reset_index(drop=True)
    na,nm=values.asset_id.nunique(),values.date.nunique()
    if na<100 or nm<60:raise ValueError('EDGE coverage insufficient')
    summary=dict(reference_id=d['id'],definition_hash=base.definition_hash(d),status='MEASUREMENT_VALIDATED',
        input_rows=len(identity),value_rows=len(values),assets=int(na),months=int(nm),first_date=str(values.date.min().date()),last_date=str(values.date.max().date()))
    rows=gold.canonical_values(values)
    parity=dict(kind=catalog.PARITY_KIND,passed=True,rtol=1e-7,atol=1e-8,rows_compared=len(values),values_sha256=digest(rows),
        oracle_sha256=digest(dict(parent=checkpoint['implementation_sha256'],filter=sha(__file__))),raw_input_sha256=input_hash,
        all_input_null_patterns_compared=True,comparison_scope='ALL_PUBLISHED_ASSET_MONTHS_VECTOR_VS_SCALAR_RAW_INPUTS')
    validation=dict(source_version=att['source_version'],input_sha256=input_hash,source_evidence_sha256=digest(evidence),
        implementation_sha256=sha(__file__),role='MEASUREMENT_CONTROL',alpha_approved=False,value_rows=len(values),references=[summary])
    pub,_=gold.build_publication(values,[d],attestation=att,validation=validation,parity=parity)
    output=root/'edge-action-filter'/d['id'];output.mkdir(parents=True,exist_ok=True)
    values.to_parquet(output/'values.parquet',index=False)
    save_json(output/'source-evidence.json',evidence);save_json(output/'publication.json',pub)
    print(summary,flush=True)

if __name__=='__main__':run()
