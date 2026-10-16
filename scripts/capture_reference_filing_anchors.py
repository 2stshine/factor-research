"""Freeze certified annual issuer/filing anchors, never forward returns."""
import argparse
from pathlib import Path
import pandas as pd
from engine.reference_db import connect
from engine.research_generation import digest
from scripts.publish_reference_expansion import save_json,sha

SQL="""
SELECT DISTINCT f.asset_id,f.period_end,f.filing_id,f.filed,f.available_date,
 f.fs_type,f.currency,f.value::float8 AS revenue,f.quality_run_id::text,
 i.identifier AS corp_code,i.valid_from,i.valid_to
FROM public.fundamental f
JOIN public.asset a ON a.asset_id=f.asset_id
JOIN public.dq_run q ON q.run_id=f.quality_run_id AND q.status='CERTIFIED'
JOIN public.asset_identifier i ON i.asset_id=f.asset_id AND i.source='DART' AND i.identifier_type='corp_code'
JOIN public.dq_run iq ON iq.run_id=i.quality_run_id AND iq.status='CERTIFIED'
WHERE a.exchange='KRX' AND a.instrument_type='common_stock' AND a.asset_type='stock'
AND f.source='DART' AND f.metric='revenue' AND f.fiscal_period='FY'
AND f.data_basis='STANDARDIZED' AND f.unit_type='currency'
AND f.period_end BETWEEN '2015-01-01' AND '2025-12-31'
AND i.valid_from<=f.period_end AND (i.valid_to IS NULL OR i.valid_to>=f.period_end)
ORDER BY f.asset_id,f.period_end,f.filing_id,f.fs_type
"""

def run(output):
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 with connect() as conn,conn.cursor() as cur:
  cur.execute("SET LOCAL statement_timeout='10min'")
  cur.execute('SELECT pg_current_snapshot()::text,transaction_timestamp()');snapshot,at=cur.fetchone()
  cur.execute(SQL);frame=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
 path=out/'filing-anchors.parquet';frame.to_parquet(path,index=False)
 jobs=sorted({(r.corp_code,int(r.period_end.year)) for r in frame.itertuples() if r.period_end.month==12 and r.period_end.day==31})
 save_json(out/'manifest.json',dict(status='COMPLETE',snapshot=snapshot,captured_at=at.isoformat(),query_sha256=digest(SQL),
  path=path.name,sha256=sha(path),rows=len(frame),jobs=[dict(corp_code=c,fiscal_year=y) for c,y in jobs],
  scope='CERTIFIED_DART_DECEMBER_FY_REVENUE_ISSUERS_2015_2025',
  limitation='Source acquisition universe; not entire KRX. Non-December FY and absent certified annual revenue excluded explicitly.',
  forward_labels_read=False))
 print(dict(rows=len(frame),requests=len(jobs),assets=frame.asset_id.nunique()),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();run(a.output)
