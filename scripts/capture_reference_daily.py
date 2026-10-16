"""Freeze certified daily inputs in a single read-only snapshot; never outcomes."""
from pathlib import Path
import argparse
import hashlib
import json
import pandas as pd

from engine.reference_db import connect
from engine.reference_financial_inputs import _query, _assert_readonly, _sha
from engine.research_generation import digest

SQL = """
SELECT p.asset_id,p.trade_date,p.market,p.open::float8,p.high::float8,
 p.low::float8,p.close::float8,p.adj_close::float8,p.volume::float8,
 p.trading_value::float8,p.market_cap::float8,p.shares::float8,
 p.quality_run_id::text
FROM public.price_daily p
JOIN public.asset a ON a.asset_id=p.asset_id
JOIN public.dq_run q ON q.run_id=p.quality_run_id AND q.status='CERTIFIED'
WHERE p.source='KRX' AND a.exchange='KRX' AND a.asset_type='stock'
 AND a.instrument_type='common_stock' AND p.market IN ('KOSPI','KOSDAQ')
 AND p.trade_date BETWEEN %s::date AND %s::date AND p.asset_id=ANY(%s::bigint[])
ORDER BY p.asset_id,p.trade_date
"""

def capture(output, start='2013-01-01', end='2026-09-30'):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('Use a fresh directory; incomplete snapshots cannot be mixed')
    with connect() as conn:
        _assert_readonly(conn)
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout='120s'")
            cur.execute('SELECT pg_current_snapshot()::text, transaction_timestamp()')
            snapshot, captured = cur.fetchone()
            cur.execute("SELECT asset_id FROM public.asset WHERE exchange='KRX' AND asset_type='stock' AND instrument_type='common_stock' ORDER BY asset_id")
            assets = [r[0] for r in cur.fetchall()]
        files = []
        for offset in range(0, len(assets), 75):
            batch = assets[offset:offset+75]
            with conn.cursor(name='daily_source_capture') as cur:
                cur.execute(SQL, (start, end, batch))
                columns = [d.name for d in cur.description]
                chunks = []
                while rows := cur.fetchmany(25000):
                    chunks.append(pd.DataFrame(rows, columns=columns))
                frame = pd.concat(chunks,ignore_index=True) if chunks else pd.DataFrame(columns=columns)
            if frame.duplicated(['asset_id','trade_date']).any():
                raise ValueError('Ambiguous daily source identity')
            name = f'daily-{offset//75:04d}.parquet'
            frame.to_parquet(out/name, index=False)
            files.append(dict(path=name, sha256=_sha(out/name), rows=len(frame), asset_ids=batch))
            print(dict(batch=offset//75, assets=len(assets), rows=len(frame)), flush=True)
        manifest = dict(version='certified-reference-daily-v1', status='COMPLETE',
            snapshot=snapshot, captured_at=captured.isoformat(), start=start, end=end,
            files=files, rows=sum(x['rows'] for x in files), query_sha256=hashlib.sha256(SQL.encode()).hexdigest(),
            scope='KRX_COMMON_STOCK', pit_status='PIT_ASSUMED', first_vintage_verified=False,
            price_basis='KRX_PRICE_NOT_TOTAL_RETURN', forward_labels_read=False)
        manifest['manifest_sha256'] = digest(manifest)
        (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        print(dict(status='COMPLETE', rows=manifest['rows'], manifest_sha256=manifest['manifest_sha256']),flush=True)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    capture(args.output)
