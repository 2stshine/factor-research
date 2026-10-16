"""Auditable source capture for a literature reference expansion, no outcomes."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from engine import reference_gold as gold,reference_library as base,silver
from engine.reference_db import connect
from engine import reference_price_expansion as price
from engine import reference_financial_inputs as financial
from engine.research_generation import canonical,digest,_immutable


def fetch_price(output, *, start='2015-01-01',end='2026-09-30'):
    output=Path(output)
    if output.exists():raise ValueError('Fresh immutable price output directory required')
    output.mkdir(parents=True)
    chunks=[]
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout='300s'")
            cur.execute("SET LOCAL work_mem='64MB'")
            cur.execute("SELECT max(p.trade_date) FROM public.price_daily p JOIN public.dq_run q ON q.run_id=p.quality_run_id AND q.status='CERTIFIED' WHERE p.source='KRX' AND p.market IN ('KOSPI','KOSDAQ')")
            latest=cur.fetchone()[0]
            if latest is None:raise ValueError('No certified price source')
            safe_end=min(pd.Timestamp(end).date(),(pd.Timestamp(latest).to_period('M')-1).end_time.date())
            if pd.Timestamp(start).day!=1 or pd.Timestamp(end).date()!=pd.Timestamp(end).to_period('M').end_time.date():
                raise ValueError('Complete calendar-month boundaries required')
            cur.execute("SELECT asset_id FROM public.asset WHERE exchange='KRX' AND asset_type='stock' AND instrument_type='common_stock' ORDER BY asset_id")
            assets=[r[0] for r in cur.fetchall()]
        for offset in range(0,len(assets),150):
            frame=silver.read_frame(conn,price.EXTENDED_PRICE_SQL,(start,str(safe_end),assets[offset:offset+150]))
            frame.to_parquet(output/f'price-{offset:06d}.parquet',index=False)
            chunks.append(frame)
            print(f'Extended certified price: {min(offset+150,len(assets))}/{len(assets)} assets; {len(frame)} monthly rows',flush=True)
    raw=pd.concat(chunks,ignore_index=True)
    panel,evidence=gold.normalize_price_frame(raw,start=start,safe_end=safe_end,assets=assets,latest=latest)
    columns=[*base._BASE,*base.FEATURE_CONTRACTS,*base._COUNTS,*price.ADDITIONAL_COLUMNS]
    panel=panel.loc[:,list(dict.fromkeys(columns))].copy()
    for column in set(panel)-set(base._BASE):
        panel[column]=pd.to_numeric(panel[column],errors='raise').astype(float)
    evidence={**evidence,'schema_version':'reference-expansion-price-source-v2',
              'query_sha256':hashlib.sha256(price.EXTENDED_PRICE_SQL.encode()).hexdigest(),
              'source_type':'RDS_CERTIFIED_KRX_EXTENDED_PRICE_V2','fetched_at':datetime.now(timezone.utc).isoformat(),
              'chunks_complete':True,'chunks':[{"path":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(output.glob('price-*.parquet'))],
              'feature_contracts':{**base.FEATURE_CONTRACTS,**price.FEATURE_CONTRACTS},
              'units':{**base.FEATURE_UNITS,**price.FEATURE_UNITS}}
    panel.to_parquet(output/'input.parquet',index=False)
    evidence['input_file_sha256']=hashlib.sha256((output/'input.parquet').read_bytes()).hexdigest()
    _immutable(output/'source-evidence.json',canonical(evidence)+b'\n')
    print(json.dumps({'status':'CAPTURED_NOT_PUBLISHED','rows':len(panel),'assets':int(panel.asset_id.nunique()),'evidence_sha256':digest(evidence),'output':str(output)},indent=2),flush=True)
    return panel,evidence


def fetch_financial(output, *, start='2013-01-01',end='2026-09-30'):
    """Capture exact annual accounts and every filing anchor, never outcomes."""
    end_date=pd.Timestamp(end)
    if end_date.date()!=end_date.to_period('M').end_time.date():
        raise ValueError('Complete calendar-month end required')
    cutoff=(end_date.normalize()+pd.Timedelta(days=1)).tz_localize('Asia/Seoul').tz_convert('UTC')
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT asset_id FROM public.asset WHERE exchange='KRX' AND asset_type='stock' AND instrument_type='common_stock' ORDER BY asset_id")
            assets=[row[0] for row in cur.fetchall()]
        manifest=financial.capture_annual_ledger(conn,assets,start,cutoff,output,batch_size=20)
    financial.verify_capture(output)
    print(json.dumps({'status':'CAPTURED_NOT_PUBLISHED','assets_investigated':len(assets),
                      'source_row_counts':manifest['source_row_counts'],
                      'manifest_sha256':manifest['manifest_sha256'],'output':str(output)},indent=2),flush=True)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['fetch-price','fetch-financial'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--start');parser.add_argument('--end',default='2026-09-30')
    args=parser.parse_args()
    if args.command=='fetch-price':fetch_price(args.output,start=args.start or '2015-01-01',end=args.end)
    else:fetch_financial(args.output,start=args.start or '2013-01-01',end=args.end)


if __name__=='__main__':main()
