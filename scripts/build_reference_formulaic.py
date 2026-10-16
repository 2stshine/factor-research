"""Dual-interpreter raw daily calculation; writes no DB until all checks pass."""
import argparse
import gc
from pathlib import Path
import numpy as np
import pandas as pd
from engine import reference_daily_diversity as lib, reference_formulaic as calc
from engine import reference_library as base, reference_gold as gold
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_input,save_json,load_json,sha

def run(source,output,references=None):
    source,output=Path(source),Path(output);output.mkdir(parents=True,exist_ok=True)
    x,dates,assets,valid,jumps,manifest=lib.load_matrices(source)
    with np.errstate(all='ignore'):
        vwap=x['trading_value']/x['volume']
    x['vwap']=np.where((x['volume']>0)&(vwap>=x['low'])&(vwap<=x['high']),vwap,np.nan)
    identity,_=load_input(Path('output/phenomena/reference-expansion-20261003/build-v2'))
    identity=identity[list(base._BASE)].copy()
    periods=dates.to_period('M')
    endpoints=np.flatnonzero(np.r_[periods[:-1]!=periods[1:],True])
    calendar=dates[endpoints].to_period('M').to_timestamp('M')
    lookup=pd.MultiIndex.from_product([calendar,assets.astype(str)],names=['date','asset_id'])
    keys=pd.MultiIndex.from_frame(identity[['date','asset_id']])
    indexer=lookup.get_indexer(keys)
    if (indexer<0).any():raise ValueError('Identity outside daily source grid')
    evidence=dict(source_contract=lib.SOURCE_CONTRACT,daily_manifest_sha256=manifest['manifest_sha256'],
        daily_capture_path=str(source.resolve()),monthly_identity_sha256=digest(identity.astype(str).to_dict('records')),
        input_sha256=digest(dict(manifest=manifest['manifest_sha256'],identity=identity.astype(str).to_dict('records'))),
        first_vintage_verified=False,pit_status=lib.PIT_STATUS,legacy_gold_used=False,forward_labels_read=False,
        price_basis='RAW_OHLCV_WITH_CORPORATE_ACTION_CROSSING_WINDOWS_EXCLUDED_PRICE_ONLY_RETURNS',
        comparison='INDEPENDENT_PANDAS_ROLLING_VS_NUMPY_CENTERED_WINDOWS_AND_SCIPY_RANKS')
    att=dict(status='CERTIFIED',source_type=lib.SOURCE_TYPE,source_contract=lib.SOURCE_CONTRACT,
        scope=base.INPUT_SCOPE,identity_contract=base.IDENTITY_CONTRACT,pit_status=lib.PIT_STATUS,
        first_vintage_independently_verified=False,evidence_sha256=digest(evidence),source_version=digest(evidence),input_sha256=evidence['input_sha256'])
    for definition in lib.definitions():
        if references is not None and int(definition['id'].split('_')[2]) not in references:continue
        ref=definition['id'];out=output/ref;out.mkdir(parents=True,exist_ok=True)
        if (out/'publication.json').exists():
            pub=load_json(out/'publication.json')
            if pub['input_sha256']!=att['input_sha256'] or pub['definitions'][ref]!=definition:raise ValueError('Frozen checkpoint differs')
            print(dict(resume='BUILT',reference=ref),flush=True);continue
        h=definition['lookback']['daily_observations']
        good=(pd.DataFrame(valid.astype(float)).rolling(h,min_periods=h).sum().to_numpy()==h)
        good &= (pd.DataFrame(jumps.astype(float)).rolling(h,min_periods=h).sum().to_numpy()==0)
        print(dict(calculating=ref,backend='pandas'),flush=True)
        full=calc.evaluate(definition['formula'],x,'pandas')
        actual=np.where(good[endpoints],full[endpoints],np.nan).ravel()[indexer];del full
        print(dict(calculating=ref,backend='independent_numpy'),flush=True)
        full=calc.evaluate(definition['formula'],x,'numpy')
        expected=np.where(good[endpoints],full[endpoints],np.nan).ravel()[indexer];del full,good
        try:
            np.testing.assert_allclose(actual,expected,rtol=1e-7,atol=1e-8,equal_nan=True,err_msg=ref)
        except AssertionError as exc:
            # Numerical disagreement is quarantined, never counted as Gold.
            bad=~np.isclose(actual,expected,rtol=1e-7,atol=1e-8,equal_nan=True)
            save_json(out/'quarantine.json',dict(reference_id=ref,status='NOT_PUBLISHED_PARITY_FAILED',
                mismatches=int(bad.sum()),input_sha256=att['input_sha256'],
                implementation_sha256=lib.implementation_hash(),detail=str(exc)))
            print(dict(quarantined=ref,mismatches=int(bad.sum())),flush=True)
            gc.collect()
            continue
        values=identity.loc[np.isfinite(actual)].copy()
        values['reference_id']=ref;values['value']=actual[np.isfinite(actual)]
        values['oriented_value']=values.value;values['definition_hash']=base.definition_hash(definition)
        values['source_version']=att['source_version'];values['input_sha256']=att['input_sha256']
        values=values[base._OUTPUT].sort_values(['reference_id','asset_id','date']).reset_index(drop=True)
        n_assets,n_months=values.asset_id.nunique(),values.date.nunique()
        if n_assets<100 or n_months<60:raise ValueError('Coverage insufficient')
        if values.value.nunique()<3:raise ValueError('Degenerate measurement')
        rows=gold.canonical_values(values)
        parity=dict(kind=lib.PARITY_KIND,passed=True,rtol=1e-7,atol=1e-8,rows_compared=len(values),
            values_sha256=digest(rows),oracle_sha256=sha(calc.__file__),raw_input_sha256=att['input_sha256'],
            all_input_null_patterns_compared=True,comparison_scope='ALL_PUBLISHED_ASSET_MONTHS_TWO_RAW_DAILY_INTERPRETERS')
        summary=dict(reference_id=ref,definition_hash=base.definition_hash(definition),status='MEASUREMENT_VALIDATED',
            input_rows=len(identity),value_rows=len(values),assets=int(n_assets),months=int(n_months),
            first_date=str(values.date.min().date()),last_date=str(values.date.max().date()))
        validation=dict(source_version=att['source_version'],input_sha256=att['input_sha256'],source_evidence_sha256=digest(evidence),
            implementation_sha256=lib.implementation_hash(),role='MEASUREMENT_CONTROL',alpha_approved=False,value_rows=len(values),references=[summary])
        pub,_=gold.build_publication(values,[definition],attestation=att,validation=validation,parity=parity)
        values.to_parquet(out/'values.parquet',index=False)
        save_json(out/'source-evidence.json',evidence);save_json(out/'publication.json',pub)
        print(dict(summary,build_status='BUILD_VERIFIED_NOT_YET_GOLD'),flush=True)
        del values,rows
        gc.collect()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--references',type=int,nargs='+')
    a=p.parse_args();run(a.source,a.output,a.references)
