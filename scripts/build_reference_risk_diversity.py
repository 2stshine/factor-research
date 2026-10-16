"""Compute reference risks and AQR controls with full independent raw-input checks."""
import argparse
import gc
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from engine import reference_daily_diversity as daily, reference_risk_measurements as calc
from engine import reference_risk_catalog as catalog,reference_library as base,reference_gold as gold
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_input,load_json,save_json,sha

def financial_extras(panel,financial_meta,x,dates,assets):
    """Pandas country-rank construction versus scipy independent country ranks."""
    ratio=lambda n,d:n/d.where(d>0)
    a=panel.fy_total_assets;e=panel.fy_total_equity;ni=panel.fy_net_income;cfo=panel.fy_operating_cash_flow
    components=pd.DataFrame(dict(gp=ratio(panel.fy_gross_profit,a),roe=ratio(ni,e),roa=ratio(ni,a),
        cfo=ratio(cfo,a),margin=ratio(panel.fy_gross_profit,panel.fy_revenue),accrual=-ratio(ni-cfo,a)))
    complete=components.notna().all(axis=1)
    components=components.where(complete,axis=0)
    ranks=components.groupby(panel.date).rank(method='average')
    standardized=(ranks-ranks.groupby(panel.date).transform('mean'))/ranks.groupby(panel.date).transform('std')
    total=standardized.sum(axis=1,skipna=False).round(12)
    total_rank=total.groupby(panel.date).rank(method='average')
    quality=(total_rank-total_rank.groupby(panel.date).transform('mean'))/total_rank.groupby(panel.date).transform('std')
    quality_oracle=np.full(len(panel),np.nan)
    for _,idx in panel.groupby('date').groups.items():
        idx=np.array(list(idx));idx=idx[complete.loc[idx].to_numpy()]
        if len(idx)<2:continue
        scores=rankdata(components.loc[idx].to_numpy(),axis=0,method='average')
        z=(scores-scores.mean(axis=0))/scores.std(axis=0,ddof=1)
        aggregate=rankdata(np.round(z.sum(axis=1),12),method='average')
        quality_oracle[idx]=(aggregate-aggregate.mean())/aggregate.std(ddof=1)
    meta=financial_meta[['asset_id','date','fy_period_end']].copy();meta.asset_id=meta.asset_id.astype(str)
    joined=panel[['asset_id','date']].merge(meta,on=['asset_id','date'],validate='one_to_one')
    end=pd.to_datetime(joined.fy_period_end)
    past=end-pd.DateOffset(years=5)
    ai=pd.Index(assets.astype(str)).get_indexer(panel.asset_id)
    def shares_at(d):
        pos=dates.searchsorted(d,side='right')-1
        valid=d.notna().to_numpy()&(pos>=0)&(ai>=0)
        safe=np.clip(pos,0,len(dates)-1)
        valid &= (d-dates[safe]).dt.days.between(0,14).to_numpy()
        factor=x['adj_close'][safe,ai]/x['close'][safe,ai]
        raw=x['shares'][safe,ai]
        adjusted=np.where(valid&(raw>0)&(factor>0),raw/factor,np.nan)
        return adjusted
    s0,s5=shares_at(end),shares_at(past)
    with np.errstate(all='ignore'):
        growth=(panel.fy_gross_profit.to_numpy()/s0-panel.fy5_gross_profit.to_numpy()/s5)/(panel.fy5_revenue.to_numpy()/s5)
        growth_oracle=(panel.fy_gross_profit.to_numpy()*(s5/s0)-panel.fy5_gross_profit.to_numpy())/panel.fy5_revenue.to_numpy()
    good=panel.fy5_revenue.to_numpy()>0
    growth=np.where(good&np.isfinite(growth),growth,np.nan)
    growth_oracle=np.where(good&np.isfinite(growth_oracle),growth_oracle,np.nan)
    return dict(quality_profitability_composite=quality.to_numpy(),gross_profit_growth_per_share_5fy=growth),dict(quality_profitability_composite=quality_oracle,gross_profit_growth_per_share_5fy=growth_oracle)

def run(source,output):
    source,output=Path(source),Path(output);output.mkdir(parents=True,exist_ok=True)
    x,dates,assets,valid,jumps,manifest=daily.load_matrices(source)
    financial=Path('output/phenomena/reference-expansion-100-20261003/financial-diversity')
    fe=load_json(financial/'input-evidence.json')
    if sha(financial/'input.parquet')!=fe['input_file_sha256']:raise ValueError('Financial bytes differ')
    panel=pd.read_parquet(financial/'input.parquet').reset_index(drop=True)
    identity=panel[list(base._BASE)].copy();base._prepare(identity)
    old=Path('output/phenomena/reference-expansion-20261003/build-v2')
    olde=load_json(old/'source-evidence.json')
    if sha(old/'financial-features.parquet')!=olde['financial_features_file_sha256']:raise ValueError('FY identity bytes differ')
    financial_meta=pd.read_parquet(old/'financial-features.parquet',columns=['asset_id','date','fy_period_end'])
    periods=dates.to_period('M');ends=np.flatnonzero(np.r_[periods[:-1]!=periods[1:],True])
    calendar=dates[ends].to_period('M').to_timestamp('M')
    grid=pd.MultiIndex.from_product([calendar,assets.astype(str)],names=['date','asset_id'])
    indexer=grid.get_indexer(pd.MultiIndex.from_frame(identity[['date','asset_id']]))
    if (indexer<0).any():raise ValueError('Monthly identity missing')
    output_values={};oracle_values={}
    evidence=dict(source_contract=catalog.SOURCE_CONTRACT,daily_manifest_sha256=manifest['manifest_sha256'],
        daily_capture_path=str(source.resolve()),financial_input_evidence_sha256=digest(fe),
        financial_meta_sha256=sha(old/'financial-features.parquet'),input_sha256=digest(dict(daily=manifest['manifest_sha256'],financial=fe)),
        first_vintage_verified=False,pit_status='PIT_ASSUMED',forward_labels_read=False,legacy_gold_used=False,
        market_proxy='LAGGED_CAP_WEIGHT_KRX_CERTIFIED_COMMON_STOCK_PRICE_RETURNS_NOT_OFFICIAL_TR')
    cache=output/'raw-measurements.parquet';oracle_cache=output/'raw-oracle.parquet'
    implementation=digest({str(Path(p).name):sha(p) for p in [__file__,calc.__file__,catalog.__file__,daily.__file__]})
    if (output/'raw-checkpoint.json').exists():
        checkpoint=load_json(output/'raw-checkpoint.json')
        if checkpoint['implementation_sha256']!=implementation or checkpoint['input_sha256']!=evidence['input_sha256'] or sha(cache)!=checkpoint['values_file_sha256'] or sha(oracle_cache)!=checkpoint['oracle_file_sha256']:
            raise ValueError('Raw checkpoint changed')
        output_values={k:v.to_numpy() for k,v in pd.read_parquet(cache).items()}
        oracle_values={k:v.to_numpy() for k,v in pd.read_parquet(oracle_cache).items()}
    else:
        market=calc.market_series(x)
        with np.errstate(all='ignore'):
            x['log_returns']=np.log1p(x['returns'])
        logs=x['log_returns'];width=len(assets)
        x['log_returns_3']=logs+np.vstack([np.full((1,width),np.nan),logs[:-1]])+np.vstack([np.full((2,width),np.nan),logs[:-2]])
        monthly_close=x['adj_close'][ends]
        monthly_shares=(x['shares']*x['close']/x['adj_close'])[ends]
        adjusted_volume=pd.DataFrame(x['volume']*x['adj_close']/x['close'],index=dates).resample('ME').sum(min_count=15).reindex(calendar).to_numpy()
        monthly_return=np.vstack([np.full((1,width),np.nan),monthly_close[1:]/monthly_close[:-1]-1])
        weekprices=pd.DataFrame(x['adj_close'],index=dates).resample('W-FRI').last()
        weekly=weekprices.pct_change(fill_method=None)
        # Missing market sessions are unknown, never silently zero returns.
        weekly_market=(1+pd.Series(market,index=dates)).resample('W-FRI').agg(lambda s:np.prod(s.to_numpy()))-1
        vector_arrays={};scalar_arrays={}
        start=identity.date.min()
        for j,end in enumerate(ends):
            if calendar[j]<start:continue
            print(dict(month=str(calendar[j].date()),phase='vector_and_independent_stockwise_oracle'),flush=True)
            va=calc.monthly_risk(x,dates,int(end),market)
            vb=calc.monthly_risk(x,dates,int(end),market,oracle=True)
            # Raw OHLC EDGE must not mistake a split/rights jump for a spread.
            in_month=(dates.to_period('M')==calendar[j].to_period('M'))&(dates<=dates[end])
            action_month=jumps[in_month].any(axis=0)
            va['edge_spread']=np.where(action_month,np.nan,va['edge_spread'])
            vb['edge_spread']=np.where(action_month,np.nan,vb['edge_spread'])
            va['price_delay']=calc.price_delay(weekly,weekly_market,calendar[j])
            vb['price_delay']=calc.price_delay(weekly,weekly_market,calendar[j],True)
            va['volume_trend']=calc.volume_trend(adjusted_volume,j)
            vb['volume_trend']=calc.volume_trend(adjusted_volume,j,True)
            va['calendar_seasonality']=np.full(width,np.nan);vb['calendar_seasonality']=np.full(width,np.nan)
            if j>=59:
                historical=monthly_return[[j-23,j-35,j-47,j-59]]
                va['calendar_seasonality']=historical.mean(axis=0)
                vb['calendar_seasonality']=np.array([sum(v)/4 if np.isfinite(v).all() else np.nan for v in historical.T])
            va['net_share_issuance']=np.full(width,np.nan);vb['net_share_issuance']=np.full(width,np.nan)
            if j>=12:
                a,b=monthly_shares[j],monthly_shares[j-12]
                with np.errstate(all='ignore'):
                    va['net_share_issuance']=np.where((a>0)&(b>0),-np.log(a/b),np.nan)
                    vb['net_share_issuance']=np.where((a>0)&(b>0),np.log(b)-np.log(a),np.nan)
            for k in va:
                if k not in vector_arrays:
                    vector_arrays[k]=np.full((len(ends),width),np.nan);scalar_arrays[k]=np.full((len(ends),width),np.nan)
                a=np.where(valid[end]&np.isfinite(va[k]),va[k],np.nan);b=np.where(valid[end]&np.isfinite(vb[k]),vb[k],np.nan)
                np.testing.assert_allclose(a,b,rtol=1e-7,atol=1e-8,equal_nan=True,err_msg=f'{k}/{calendar[j]}')
                vector_arrays[k][j]=a;scalar_arrays[k][j]=b
        output_values={k:v.ravel()[indexer] for k,v in vector_arrays.items()}
        oracle_values={k:v.ravel()[indexer] for k,v in scalar_arrays.items()}
        extra,extra_oracle=financial_extras(panel,financial_meta,x,dates,assets)
        output_values.update(extra);oracle_values.update(extra_oracle)
        pd.DataFrame(output_values).to_parquet(cache,index=False);pd.DataFrame(oracle_values).to_parquet(oracle_cache,index=False)
        save_json(output/'raw-checkpoint.json',dict(input_sha256=evidence['input_sha256'],implementation_sha256=implementation,
            values_file_sha256=sha(cache),oracle_file_sha256=sha(oracle_cache)))
    att=dict(status='CERTIFIED',source_type=catalog.SOURCE_TYPE,source_contract=catalog.SOURCE_CONTRACT,
        scope=base.INPUT_SCOPE,identity_contract=base.IDENTITY_CONTRACT,pit_status='PIT_ASSUMED',first_vintage_independently_verified=False,
        evidence_sha256=digest(evidence),source_version=digest(evidence),input_sha256=evidence['input_sha256'])
    for definition in catalog.definitions():
        ref=definition['id'];key=ref.removeprefix('kr_').removesuffix('_reference_v1')
        actual,expected=output_values[key],oracle_values[key]
        np.testing.assert_allclose(actual,expected,rtol=1e-7,atol=1e-8,equal_nan=True,err_msg=ref)
        out=output/ref;out.mkdir(parents=True,exist_ok=True)
        values=identity.loc[np.isfinite(actual)].copy();values['reference_id']=ref;values['value']=actual[np.isfinite(actual)]
        values['oriented_value']=values.value*definition['orientation'];values['definition_hash']=base.definition_hash(definition)
        values['source_version']=att['source_version'];values['input_sha256']=att['input_sha256']
        values=values[base._OUTPUT].sort_values(['reference_id','asset_id','date']).reset_index(drop=True)
        na,nm=values.asset_id.nunique(),values.date.nunique()
        if na<100 or nm<60:raise ValueError(f'Coverage insufficient {ref}: {na}/{nm}')
        rows=gold.canonical_values(values)
        parity=dict(kind=catalog.PARITY_KIND,passed=True,rtol=1e-7,atol=1e-8,rows_compared=len(values),values_sha256=digest(rows),
            oracle_sha256=implementation,raw_input_sha256=att['input_sha256'],all_input_null_patterns_compared=True,
            comparison_scope='ALL_PUBLISHED_ASSET_MONTHS_VECTOR_VS_SCALAR_RAW_INPUTS')
        summary=dict(reference_id=ref,definition_hash=base.definition_hash(definition),status='MEASUREMENT_VALIDATED',input_rows=len(panel),
            value_rows=len(values),assets=int(na),months=int(nm),first_date=str(values.date.min().date()),last_date=str(values.date.max().date()))
        validation=dict(source_version=att['source_version'],input_sha256=att['input_sha256'],source_evidence_sha256=digest(evidence),implementation_sha256=implementation,
            role='MEASUREMENT_CONTROL',alpha_approved=False,value_rows=len(values),references=[summary])
        pub,_=gold.build_publication(values,[definition],attestation=att,validation=validation,parity=parity)
        save_json(out/'source-evidence.json',evidence);save_json(out/'publication.json',pub)
        if (out/'values.parquet').exists():pd.testing.assert_frame_equal(pd.read_parquet(out/'values.parquet'),values,check_exact=True)
        else:values.to_parquet(out/'values.parquet',index=False)
        print(dict(summary,build_status='BUILD_VERIFIED_NOT_YET_GOLD'),flush=True)
        del values,rows;gc.collect()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run(a.source,a.output)
