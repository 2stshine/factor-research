"""Freeze certified daily short observations for historical eligibility joining.

Captures raw measurement inputs, not future returns. Latest source revisions are
explicitly PIT_ASSUMED, not first-vintage proof. Each month has its own immutable
read snapshot receipt and can be resumed without recapturing completed months.
"""
import argparse
from pathlib import Path

import pandas as pd

from engine.reference_db import connect
from engine.reference_financial_inputs import _assert_readonly
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_json, save_json, sha

SQL="""
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
)
SELECT p.asset_id,p.trade_date,p.market,p.cutoff,i.stock_code,i.identity_matches,
 k.ticker AS source_ticker,k.payload IS NOT NULL AS source_exists,
 (k.payload->>'short_volume')::float8 AS short_volume,
 (k.payload->>'original_daily_volume')::float8 AS total_volume,
 k.research_available_at AS known_at,k.first_observed_at,k.provider_available_at,
 k.policy_version,k.availability_basis,
 k.payload->>'short_market' AS short_market,k.payload->>'volume_market' AS volume_market,
 k.payload->>'volume_adjustment' AS volume_adjustment
FROM p LEFT JOIN k ON k.asset_id=p.asset_id AND k.trade_date=p.trade_date
JOIN LATERAL (SELECT min(identifier) AS stock_code,count(*) AS identity_matches
 FROM public.asset_identifier a WHERE a.asset_id=p.asset_id AND a.source='KRX' AND a.identifier_type='ticker'
 AND a.valid_from<=p.trade_date AND (a.valid_to IS NULL OR a.valid_to>=p.trade_date)) i ON true
WHERE ((p.trade_date+1)+time '08:30') AT TIME ZONE 'Asia/Seoul' < p.cutoff
ORDER BY p.asset_id,p.trade_date
"""


def capture(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    files=[]
    for month in pd.period_range('2021-05','2023-11',freq='M'):
        start=max(month.start_time.date().isoformat(),'2021-05-03')
        end=min(month.end_time.date().isoformat(),'2023-11-03')
        name=f'short-{month}.parquet'; receipt=output/f'short-{month}.json'
        if receipt.exists():
            item=load_json(receipt)
            if item['query_sha256']!=digest(SQL) or sha(output/name)!=item['sha256']:
                raise ValueError('Checkpoint has changed')
            files.append(item);continue
        with connect() as conn:
            _assert_readonly(conn)
            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout='10min'")
                cur.execute('SELECT pg_current_snapshot()::text,transaction_timestamp()')
                snapshot,at=cur.fetchone()
                cur.execute(SQL,(start,end,start,end))
                frame=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
        if frame.empty or frame.duplicated(['asset_id','trade_date']).any():raise ValueError('Empty/duplicate daily source')
        if frame.identity_matches.ne(1).any():raise ValueError('Historical identity ambiguous')
        has=frame.source_exists
        if frame.loc[has,'source_ticker'].ne(frame.loc[has,'stock_code']).any():raise ValueError('Historical ticker mismatch')
        frame.to_parquet(output/name,index=False)
        item=dict(path=name,sha256=sha(output/name),rows=len(frame),query_sha256=digest(SQL),
                  snapshot=snapshot,captured_at=at.isoformat(),start=start,end=end)
        save_json(receipt,item);files.append(item)
        print(dict(month=str(month),rows=len(frame),source_days=int(has.sum())),flush=True)
    evidence=dict(status='COMPLETE',files=files,query_sha256=digest(SQL),pit_status='PIT_ASSUMED',
                  first_vintage_verified=False,scope='KRX_COMMON_STOCK_J_ONLY',forward_labels_read=False,
                  source_revision_policy='LATEST_CERTIFIED_OBSERVED_AT_MONTH_CAPTURE',
                  availability_policy='NEXT_CALENDAR_DAY_0830_KST_EXCLUDE_POST_CUTOFF_TRADES')
    evidence['manifest_sha256']=digest(evidence);save_json(output/'manifest.json',evidence)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    capture(p.parse_args().output)
