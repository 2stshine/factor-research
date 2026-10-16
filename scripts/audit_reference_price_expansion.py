"""Independent raw daily-to-monthly audit, sampled by identity not performance."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from engine import reference_library as base, reference_price_expansion as price
from engine.reference_db import connect
from scripts.publish_reference_expansion import verify_price_capture,save_json,sha
from engine.research_generation import digest

DAILY_SQL="""
SELECT p.asset_id,p.trade_date,p.market,p.adj_close::float8,p.market_cap::float8,
 p.trading_value::float8,p.open::float8,p.high::float8,p.low::float8,
 p.close::float8,p.volume::float8,p.shares::float8,
 i.stock_code,i.n AS ticker_count
FROM public.price_daily p
JOIN public.asset a ON a.asset_id=p.asset_id
JOIN public.dq_run q ON q.run_id=p.quality_run_id AND q.status='CERTIFIED'
JOIN LATERAL (
 SELECT min(identifier) AS stock_code,count(*) AS n FROM public.asset_identifier ai
 WHERE ai.asset_id=p.asset_id AND ai.source='KRX' AND ai.identifier_type='ticker'
 AND ai.valid_from<=p.trade_date AND (ai.valid_to IS NULL OR ai.valid_to>=p.trade_date)
) i ON true
WHERE p.source='KRX' AND a.exchange='KRX' AND a.asset_type='stock'
 AND a.instrument_type='common_stock' AND p.market IN ('KOSPI','KOSDAQ')
 AND p.trade_date BETWEEN %s::date AND %s::date AND p.asset_id=ANY(%s::bigint[])
ORDER BY p.asset_id,p.trade_date
"""


def audit(source):
    source=Path(source);evidence=verify_price_capture(source)
    panel=pd.read_parquet(source/'input.parquet')
    ids=sorted(panel.asset_id.astype(int).unique().tolist())
    selected=sorted({ids[(len(ids)-1)*i//9] for i in range(10)})
    expected=panel[panel.asset_id.astype(int).isin(selected)].copy()
    start=str(panel.date.min().to_period('M').start_time.date());end=str(panel.date.max().date())
    chunks=[]
    with connect() as conn:
        with conn.cursor() as cur:cur.execute("SET LOCAL statement_timeout='180s'")
        with conn.cursor(name='reference_daily_audit') as cur:
            cur.execute(DAILY_SQL,(start,end,selected));columns=[c.name for c in cur.description]
            while rows:=cur.fetchmany(2000):chunks.append(pd.DataFrame(rows,columns=columns))
    raw=pd.concat(chunks,ignore_index=True)
    if not raw.ticker_count.eq(1).all():raise ValueError('Raw sampled historical identity ambiguous')
    raw=raw.drop(columns='ticker_count')
    raw['trade_date']=pd.to_datetime(raw.trade_date)
    raw['known_at']=(raw.trade_date+pd.Timedelta(hours=23,minutes=59,seconds=59)).dt.tz_localize('Asia/Seoul').dt.tz_convert('UTC')
    raw.to_parquet(source/'daily-audit-input.parquet',index=False)
    computed=price.aggregate_daily_for_validation(raw)
    fields=list(dict.fromkeys([*base.FEATURE_CONTRACTS,*base._COUNTS,*price.ADDITIONAL_COLUMNS]))
    keys=['asset_id','date','stock_code','market']
    for frame in (expected,computed):frame['asset_id']=frame.asset_id.astype(str)
    merged=expected.merge(computed,on=keys,how='outer',validate='one_to_one',indicator=True,suffixes=('_sql','_oracle'))
    if not merged._merge.eq('both').all():raise ValueError('Raw audit differs from captured monthly identity grid')
    failures=[];metrics={}
    for field in fields:
        left=merged[field+'_sql'].to_numpy(dtype=float);right=merged[field+'_oracle'].to_numpy(dtype=float)
        is_count=field in (*base._COUNTS,*price.COUNT_COLUMNS)
        atol=0 if is_count or field=='amihud_illiquidity_1m' else 1e-12
        rtol=0 if is_count else 1e-9
        matches=np.isclose(left,right,rtol=rtol,atol=atol,equal_nan=True)
        metrics[field]={'rows':len(left),'mismatches':int((~matches).sum()),
                        'rtol':rtol,'atol':atol,
                        'max_absolute_error':float(np.nanmax(np.abs(left-right))) if np.isfinite(left-right).any() else None}
        if not matches.all():failures.append(field)
    receipt={'passed':not failures,'selection':'TEN_EVENLY_SPACED_SORTED_CAPTURED_ASSET_IDS_ALL_DAYS',
        'asset_ids':selected,'daily_rows':len(raw),'monthly_rows':len(merged),
        'input_file_sha256':evidence['input_file_sha256'],'price_evidence_sha256':digest(evidence),
        'raw_file_sha256':sha(source/'daily-audit-input.parquet'),
        'query_sha256':hashlib.sha256(DAILY_SQL.encode()).hexdigest(),
        'oracle_sha256':hashlib.sha256(Path(price.__file__).read_bytes()).hexdigest(),
        'comparison':metrics,'failures':failures,
        'limitation':'INDEPENDENT_CALCULATION_ON_SAME_PROVIDER; FRESH_RAW_SNAPSHOT_MATCHES_CAPTURED_SAMPLE_NOT_FIRST_VINTAGE_PROOF'}
    save_json(source/'daily-audit.json',receipt)
    if failures:raise ValueError('Raw daily audit failed for: '+', '.join(failures))
    print(f'Independent daily audit PASS: {len(raw):,} daily rows → {len(merged):,} monthly rows; {len(fields)} fields',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True)
    audit(parser.parse_args().source)
