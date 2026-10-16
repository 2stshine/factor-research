"""Read certified short measurements through frozen official daily eligibility.

Only temporary policy tables are written. Source reads use a read-only snapshot;
no Gold or durable source table is changed. Year checkpoints are hash-bound.
"""
import argparse
from pathlib import Path
import pandas as pd
from engine.reference_db import connect
from engine.reference_financial_inputs import _assert_readonly
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_json,save_json,sha

DAILY_SQL="""
WITH p AS MATERIALIZED (
 SELECT p.asset_id,p.trade_date,p.market,
 ((date_trunc('month',p.trade_date::timestamp)+interval '1 month') AT TIME ZONE 'Asia/Seoul') AS cutoff
 FROM public.price_daily p JOIN public.asset a ON a.asset_id=p.asset_id
 JOIN public.dq_run d ON d.run_id=p.quality_run_id AND d.status='CERTIFIED'
 WHERE p.source='KRX' AND a.exchange='KRX' AND a.instrument_type='common_stock' AND a.asset_type='stock'
 AND p.market IN ('KOSPI','KOSDAQ') AND p.trade_date BETWEEN %s::date AND %s::date
), k AS MATERIALIZED (
 SELECT DISTINCT ON(k.asset_id,k.trade_date) k.*
 FROM public.kis_market_observation k JOIN public.dq_run d ON d.run_id=k.quality_run_id AND d.status='CERTIFIED'
 WHERE k.venue='J' AND k.kind='short' AND k.trade_date BETWEEN %s::date AND %s::date
 ORDER BY k.asset_id,k.trade_date,k.first_observed_at DESC,k.revision DESC
), j AS (
 SELECT p.*,i.stock_code,i.identity_matches,k.ticker AS source_ticker,k.payload IS NOT NULL AS source_exists,
 (k.payload->>'short_volume')::float8 AS short_volume,
 (k.payload->>'original_daily_volume')::float8 AS total_volume,
 k.research_available_at AS known_at,k.first_observed_at,
 (p.trade_date<'2020-03-16'::date OR p.trade_date>='2025-03-31'::date OR
 (p.trade_date BETWEEN '2021-05-03'::date AND '2023-11-05'::date AND EXISTS(
 SELECT 1 FROM pg_temp.short_members m WHERE m.trade_date=p.trade_date AND m.market=p.market AND m.stock_code=i.stock_code))) AS regime_eligible,
 EXISTS(SELECT 1 FROM pg_temp.short_restrictions r WHERE r.trade_date=p.trade_date AND r.stock_code=i.stock_code) AS individually_restricted,
 (k.payload IS NOT NULL AND (k.availability_basis IS DISTINCT FROM 'POLICY_ASSUMPTION'
 OR k.policy_version IS NULL OR k.policy_version NOT IN ('kis-krx-short-scope-v2','kis-provider-trust-v1')
 OR k.research_available_at IS NULL OR k.research_available_at>=p.cutoff
 OR k.research_available_at<((p.trade_date+1)+time '08:30') AT TIME ZONE 'Asia/Seoul'
 OR k.ticker IS DISTINCT FROM i.stock_code
 OR k.payload->>'short_market' IS DISTINCT FROM 'KRX'
 OR k.payload->>'volume_market' IS DISTINCT FROM 'KRX'
 OR k.payload->>'volume_adjustment' IS DISTINCT FROM 'UNADJUSTED'
 OR k.payload->>'short_volume' IS NULL OR k.payload->>'original_daily_volume' IS NULL
 OR (k.payload->>'short_volume')::numeric<0 OR (k.payload->>'original_daily_volume')::numeric<0
 OR (k.payload->>'short_volume')::numeric>(k.payload->>'original_daily_volume')::numeric)) AS bad_source
 FROM p LEFT JOIN k ON k.asset_id=p.asset_id AND k.trade_date=p.trade_date
 JOIN LATERAL(SELECT min(identifier) AS stock_code,count(*) AS identity_matches FROM public.asset_identifier a
 WHERE a.asset_id=p.asset_id AND a.source='KRX' AND a.identifier_type='ticker'
 AND a.valid_from<=p.trade_date AND (a.valid_to IS NULL OR a.valid_to>=p.trade_date)) i ON true
 WHERE ((p.trade_date+1)+time '08:30') AT TIME ZONE 'Asia/Seoul'<p.cutoff
)
SELECT *,regime_eligible AND NOT individually_restricted AS eligible FROM j
"""
SQL="""WITH daily AS ("""+DAILY_SQL+"""), m AS (
 SELECT asset_id,(date_trunc('month',trade_date::timestamp)+interval '1 month'-interval '1 day')::date AS date,
 (array_agg(stock_code ORDER BY trade_date DESC))[1] AS stock_code,
 (array_agg(market ORDER BY trade_date DESC))[1] AS market,
 count(*) AS expected_days,count(*) FILTER(WHERE eligible) AS eligible_days,
 count(*) FILTER(WHERE NOT regime_eligible) AS excluded_regime_days,
 count(*) FILTER(WHERE regime_eligible AND individually_restricted) AS excluded_individual_days,
 count(*) FILTER(WHERE eligible AND source_exists) AS short_days,
 count(*) FILTER(WHERE eligible AND bad_source) AS bad_short,
 count(*) FILTER(WHERE identity_matches<>1) AS bad_identity,
 sum(short_volume) FILTER(WHERE eligible) AS sq,sum(total_volume) FILTER(WHERE eligible) AS sv,
 max(known_at) FILTER(WHERE eligible) AS short_known_at,
 min(first_observed_at) FILTER(WHERE eligible) AS first_observed_min,
 max(first_observed_at) FILTER(WHERE eligible) AS first_observed_max
 FROM daily GROUP BY asset_id,date
) SELECT * FROM m ORDER BY asset_id,date"""

def load_policy(path):
 path=Path(path);m=load_json(path/'manifest.json')
 if m['status']!='COMPLETE' or m['manifest_sha256']!=digest({k:v for k,v in m.items() if k!='manifest_sha256'}):raise ValueError('Invalid policy manifest')
 for name,key in [('members.parquet','members_sha256'),('restriction-days.parquet','restriction_days_sha256')]:
  if sha(path/name)!=m[key]:raise ValueError('Policy bytes changed')
 for item in m['raw_exports']:
  if sha(path/item['path'])!=item['sha256']:raise ValueError('Official restriction export changed')
 for item in m['membership_receipts']:
  if sha(item['path'])!=item['sha256']:raise ValueError('Official membership receipt changed')
 return m,pd.read_parquet(path/'members.parquet'),pd.read_parquet(path/'restriction-days.parquet')

def policy_connection(members,restrictions):
 conn=connect(read_only=False)
 try:
  with conn.cursor() as cur:
   cur.execute('CREATE TEMP TABLE short_members (market text,trade_date date,stock_code text,PRIMARY KEY(market,trade_date,stock_code)) ON COMMIT PRESERVE ROWS')
   cur.execute('CREATE TEMP TABLE short_restrictions (stock_code text,trade_date date,PRIMARY KEY(stock_code,trade_date)) ON COMMIT PRESERVE ROWS')
   for table,frame,cols in [('short_members',members,['market','trade_date','stock_code']),('short_restrictions',restrictions,['stock_code','trade_date'])]:
    with cur.copy('COPY pg_temp.'+table+' FROM STDIN') as cp:
     for row in frame[cols].itertuples(index=False,name=None):cp.write_row(row)
   cur.execute('ANALYZE pg_temp.short_members');cur.execute('ANALYZE pg_temp.short_restrictions')
  conn.commit()
  with conn.cursor() as cur:cur.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
  _assert_readonly(conn)
  return conn
 except Exception:
  conn.close();raise

def capture(policy,output):
 m,members,restrictions=load_policy(policy);out=Path(output);out.mkdir(parents=True,exist_ok=True);files=[]
 with policy_connection(members,restrictions) as conn:
  with conn.cursor() as cur:
   cur.execute("SET LOCAL statement_timeout='10min'");cur.execute('SELECT pg_current_snapshot()::text,transaction_timestamp()');snapshot,at=cur.fetchone()
  for year in range(2015,2027):
   path=out/f'short-{year}.parquet';receipt=path.with_suffix('.json')
   if receipt.exists():
    item=load_json(receipt)
    if sha(path)!=item['sha256'] or item['query_sha256']!=digest(SQL) or item['policy_manifest_sha256']!=sha(Path(policy)/'manifest.json'):raise ValueError('Checkpoint mismatch')
   else:
    start=f'{year}-01-01';end=f'{year}-12-31' if year<2026 else '2026-09-30'
    with conn.cursor() as cur:
     cur.execute(SQL,(start,end,start,end));frame=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
    if frame.empty or frame.bad_identity.ne(0).any() or frame.duplicated(['asset_id','date']).any():raise ValueError('Invalid source identity/keys')
    frame.to_parquet(path,index=False)
    item=dict(path=path.name,sha256=sha(path),rows=len(frame),query_sha256=digest(SQL),snapshot=snapshot,captured_at=at.isoformat(),policy_manifest_sha256=sha(Path(policy)/'manifest.json'))
    save_json(receipt,item)
   files.append(item);print(dict(year=year,rows=item['rows']),flush=True)
 evidence=dict(status='COMPLETE',files=files,query_sha256=digest(SQL),policy_manifest_sha256=sha(Path(policy)/'manifest.json'),
  pit_status='PIT_ASSUMED',first_vintage_verified=False,forward_labels_read=False,
  availability_policy='NEXT_CALENDAR_DAY_0830_KST_EXCLUDE_POST_CUTOFF_TRADES',
  source_revision_policy='LATEST_CERTIFIED_OBSERVED_AT_CAPTURE_NOT_STRICT_HISTORICAL_ASOF')
 evidence['manifest_sha256']=digest(evidence);save_json(out/'manifest.json',evidence)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--policy',required=True);p.add_argument('--output',required=True);a=p.parse_args();capture(a.policy,a.output)
