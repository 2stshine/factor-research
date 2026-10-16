"""Freeze monthly aggregates of certified KIS observations in one read snapshot."""
import argparse
from pathlib import Path
import pandas as pd
from engine.reference_db import connect
from engine.reference_financial_inputs import _assert_readonly,_sha
from engine.research_generation import digest
from scripts.publish_reference_expansion import save_json

SQL="""
WITH k AS MATERIALIZED (
 SELECT DISTINCT ON(k.asset_id,k.trade_date,k.kind) k.*
 FROM public.kis_market_observation k JOIN public.dq_run d ON d.run_id=k.quality_run_id AND d.status='CERTIFIED'
 WHERE k.venue='J' AND k.trade_date BETWEEN %s::date AND %s::date
 ORDER BY k.asset_id,k.trade_date,k.kind,k.first_observed_at DESC,k.revision DESC
), p AS (
 SELECT p.asset_id,p.trade_date,p.market,
 (date_trunc('month',p.trade_date::timestamp)+interval '1 month'-interval '1 day')::date AS date,
 ((date_trunc('month',p.trade_date::timestamp)+interval '1 month') AT TIME ZONE 'Asia/Seoul') AS cutoff
 FROM public.price_daily p JOIN public.asset a ON a.asset_id=p.asset_id
 JOIN public.dq_run d ON d.run_id=p.quality_run_id AND d.status='CERTIFIED'
 WHERE p.source='KRX' AND a.exchange='KRX' AND a.instrument_type='common_stock' AND a.asset_type='stock'
 AND p.market IN ('KOSPI','KOSDAQ') AND p.trade_date BETWEEN %s::date AND %s::date
), j AS (
 SELECT p.*,i.payload AS ipay,s.payload AS spay,i.research_available_at AS itime,s.research_available_at AS stime,
 i.availability_basis AS ibasis,s.availability_basis AS sbasis,
 i.first_observed_at AS ifirst,s.first_observed_at AS sfirst,
 i.provider_available_at AS iprovider,s.provider_available_at AS sprovider,
 i.ticker AS iticker,s.ticker AS sticker,
 i.policy_version AS ipolicy,s.policy_version AS spolicy
 FROM p LEFT JOIN k i ON i.asset_id=p.asset_id AND i.trade_date=p.trade_date AND i.kind='investor'
 LEFT JOIN k s ON s.asset_id=p.asset_id AND s.trade_date=p.trade_date AND s.kind='short'
 WHERE ((p.trade_date+1)+time '08:30') AT TIME ZONE 'Asia/Seoul' < p.cutoff
), m AS (
 SELECT asset_id,date,count(*) AS expected_days,max(trade_date) AS last_used_trade_date,
 (array_agg(market ORDER BY trade_date DESC))[1] AS market,
 count(ipay) AS investor_days,count(spay) AS short_days,
 max(itime) AS investor_known_at,max(stime) AS short_known_at,
 min(ifirst) AS first_observed_min,max(ifirst) AS first_observed_max,
 count(iprovider)+count(sprovider) AS provider_timestamp_count,
 count(*) FILTER(WHERE ipay IS NOT NULL AND (ibasis<>'POLICY_ASSUMPTION' OR itime>=cutoff OR itime<((trade_date+1)+time '08:30') AT TIME ZONE 'Asia/Seoul'
 OR ipay->>'frgn_shnu_vol' IS NULL OR ipay->>'frgn_seln_vol' IS NULL OR ipay->>'orgn_shnu_vol' IS NULL OR ipay->>'orgn_seln_vol' IS NULL
 OR (ipay->>'frgn_shnu_vol')::numeric<0 OR (ipay->>'frgn_seln_vol')::numeric<0 OR (ipay->>'orgn_shnu_vol')::numeric<0 OR (ipay->>'orgn_seln_vol')::numeric<0
 OR (ipay->>'frgn_shnu_vol')::numeric-(ipay->>'frgn_seln_vol')::numeric IS DISTINCT FROM (ipay->>'frgn_ntby_qty')::numeric
 OR (ipay->>'orgn_shnu_vol')::numeric-(ipay->>'orgn_seln_vol')::numeric IS DISTINCT FROM (ipay->>'orgn_ntby_qty')::numeric)) AS bad_investor,
 count(*) FILTER(WHERE spay IS NOT NULL AND (sbasis<>'POLICY_ASSUMPTION' OR stime>=cutoff OR stime<((trade_date+1)+time '08:30') AT TIME ZONE 'Asia/Seoul'
 OR spay->>'short_market' IS DISTINCT FROM 'KRX' OR spay->>'volume_market' IS DISTINCT FROM 'KRX' OR spay->>'volume_adjustment' IS DISTINCT FROM 'UNADJUSTED'
 OR spay->>'short_volume' IS NULL OR spay->>'original_daily_volume' IS NULL
 OR (spay->>'short_volume')::numeric<0 OR (spay->>'original_daily_volume')::numeric<0
 OR (spay->>'short_volume')::numeric>(spay->>'original_daily_volume')::numeric)) AS bad_short,
 sum((ipay->>'frgn_shnu_vol')::numeric)::float8 AS fb,sum((ipay->>'frgn_seln_vol')::numeric)::float8 AS fs,
 sum((ipay->>'orgn_shnu_vol')::numeric)::float8 AS ib,sum((ipay->>'orgn_seln_vol')::numeric)::float8 AS isell,
 count(*) FILTER(WHERE (ipay->>'frgn_ntby_qty')::numeric>0)::float8 AS fp,
 count(*) FILTER(WHERE (ipay->>'frgn_ntby_qty')::numeric<0)::float8 AS fn,
 count(*) FILTER(WHERE (ipay->>'orgn_ntby_qty')::numeric>0)::float8 AS ip,
 count(*) FILTER(WHERE (ipay->>'orgn_ntby_qty')::numeric<0)::float8 AS inneg,
 sum((spay->>'short_volume')::numeric)::float8 AS sq,sum((spay->>'original_daily_volume')::numeric)::float8 AS sv,
 array_agg(DISTINCT ipolicy) AS investor_policies,array_agg(DISTINCT spolicy) AS short_policies,
 count(*) FILTER(WHERE ipay IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.asset_identifier a WHERE a.asset_id=j.asset_id AND a.source='KRX' AND a.identifier_type='ticker' AND a.identifier=iticker AND a.valid_from<=trade_date AND (a.valid_to IS NULL OR a.valid_to>=trade_date))) AS bad_investor_identity,
 count(*) FILTER(WHERE spay IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.asset_identifier a WHERE a.asset_id=j.asset_id AND a.source='KRX' AND a.identifier_type='ticker' AND a.identifier=sticker AND a.valid_from<=trade_date AND (a.valid_to IS NULL OR a.valid_to>=trade_date))) AS bad_short_identity
 FROM j GROUP BY asset_id,date
)
SELECT m.*,i.stock_code,i.identity_matches FROM m
JOIN LATERAL (SELECT min(identifier) AS stock_code,count(*) AS identity_matches FROM public.asset_identifier a
 WHERE a.asset_id=m.asset_id AND a.source='KRX' AND a.identifier_type='ticker' AND a.valid_from<=m.last_used_trade_date AND (a.valid_to IS NULL OR a.valid_to>=m.last_used_trade_date)) i ON true
ORDER BY asset_id,date
"""

def capture(output):
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 if any(out.iterdir()):raise ValueError('Fresh capture directory required')
 with connect() as conn:
  _assert_readonly(conn)
  with conn.cursor() as cur:
   cur.execute("SET LOCAL statement_timeout='10min'");cur.execute('SELECT pg_current_snapshot()::text,transaction_timestamp()')
   snapshot,at=cur.fetchone()
  files=[]
  for year in range(2015,2027):
   start=f'{year}-01-01';end=f'{year}-12-31' if year<2026 else '2026-09-30'
   with conn.cursor() as cur:
    cur.execute(SQL,(start,end,start,end));frame=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
   if len(frame) and (frame.identity_matches.ne(1).any() or frame.bad_investor_identity.gt(0).any() or frame.bad_short_identity.gt(0).any()):raise ValueError('Source historical identity mismatch')
   if len(frame):
    cutoffs=(pd.to_datetime(frame.date)+pd.Timedelta(days=1)).dt.tz_localize('Asia/Seoul').dt.tz_convert('UTC')
    for field in ('investor_known_at','short_known_at'):
     times=pd.to_datetime(frame[field],utc=True)
     if (times.notna()&(times>=cutoffs)).any():raise ValueError('Post-cutoff source time; capture must not publish')
   name=f'flow-{year}.parquet';frame.to_parquet(out/name,index=False)
   files.append(dict(path=name,sha256=_sha(out/name),rows=len(frame)))
   print(dict(year=year,asset_months=len(frame)),flush=True)
  evidence=dict(status='COMPLETE',snapshot=snapshot,captured_at=at.isoformat(),files=files,query_sha256=digest(SQL),
   pit_status='PIT_ASSUMED',first_vintage_verified=False,scope='KRX_COMMON_STOCK_J_ONLY',
   availability_policy='NEXT_CALENDAR_DAY_0830_KST_EXCLUDE_POST_CUTOFF_TRADES',
   source_revision_policy='LATEST_CERTIFIED_OBSERVED_AT_CAPTURE_NOT_STRICT_HISTORICAL_ASOF',forward_labels_read=False)
  evidence['manifest_sha256']=digest(evidence);save_json(out/'manifest.json',evidence)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();capture(a.output)
