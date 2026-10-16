"""Full independent SQLite and fixed-ten-asset PostgreSQL formula checks."""
import hashlib
import sqlite3
import pandas as pd
from engine import reference_gold as gold, reference_expansion_100 as lib
from engine.reference_expansion_parity import _compare
from engine.research_generation import digest

def validate(panel,values,conn):
    refs=sorted(values.reference_id.unique())
    cols=sorted({c for ref in refs for c in lib.SPECS[ref]['columns']})
    frame=panel[['asset_id','stock_code','date',*cols]].copy()
    frame.asset_id=frame.asset_id.astype(str)
    frame.date=pd.to_datetime(frame.date).dt.strftime('%Y-%m-%d')
    inner=' UNION ALL '.join(f"SELECT '{ref}' AS reference_id,asset_id,stock_code,date,{lib.SPECS[ref]['sql']} AS value FROM reference_input" for ref in refs)
    sql=f'SELECT * FROM ({inner}) calculated WHERE value IS NOT NULL AND abs(value)<=1.7976931348623157e308'
    fields=['asset_id TEXT','stock_code TEXT','date TEXT']+[c+' DOUBLE PRECISION' for c in cols]
    records=list(frame.astype(object).where(pd.notna(frame),None).itertuples(index=False,name=None))
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE reference_input ('+','.join(fields)+')')
        db.executemany('INSERT INTO reference_input VALUES ('+','.join('?' for c in fields)+')',records)
        cur=db.execute(sql)
        observed=pd.DataFrame(cur.fetchall(),columns=[c[0] for c in cur.description])
    count=_compare(values,observed,'SQLite full')
    rows=gold.canonical_values(values)
    assets=sorted({r['asset_id'] for r in rows})
    sample=sorted({assets[(len(assets)-1)*i//9] for i in range(10)})
    with conn.transaction(),conn.cursor() as cur:
        cur.execute('CREATE TEMP TABLE reference_input ('+','.join(fields)+') ON COMMIT DROP')
        with cur.copy('COPY reference_input FROM STDIN') as cp:
            for row in records:
                if int(row[0]) in sample:cp.write_row(row)
        cur.execute(sql)
        observed=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
        cur.execute('DROP TABLE pg_temp.reference_input')
    subset=values.loc[values.asset_id.astype(int).isin(sample)]
    sample_count=_compare(subset,observed,'PostgreSQL fixed sample')
    common=dict(passed=True,sql_sha256=hashlib.sha256(sql.encode()).hexdigest(),rtol=1e-10,atol=0)
    return dict(**common,kind='INDEPENDENT_SQLITE_FULL_POSTGRES_FIXED_SAMPLE',rows_compared=count,
        values_sha256=digest(rows),sqlite_full=dict(**common,rows_compared=count),
        postgres_sample=dict(**common,rows_compared=sample_count,asset_ids=sample,
            selection='TEN_EVENLY_SPACED_SORTED_ASSET_IDS_ALL_MONTHS',values_sha256=digest(gold.canonical_values(subset))))
