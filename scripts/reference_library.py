"""Build/verify/publish explicit new-generation reference measurements.

No return performance, legacy Gold fallback, alpha promotion or old-campaign
execution. Default build writes local artifacts only; Gold requires --apply.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from engine import reference_gold as gold, reference_library as library, silver
from engine.research_generation import canonical, digest, _immutable


# Independent SQL implementation of the seven registered characteristic formulas.
# A temporary feature-only table is dropped at commit; no source rows are edited.
PARITY_SQL = """
WITH w AS (
 SELECT *,lag(adj_close,1) OVER a AS p1,lag(adj_close,12) OVER a AS p12,
 lag(date,1) OVER a AS d1,lag(date,12) OVER a AS d12,
 count(*) FILTER(WHERE adj_close>0) OVER(
   PARTITION BY asset_id ORDER BY date ROWS BETWEEN 12 PRECEDING AND 1 PRECEDING) AS n12
 FROM reference_parity_input WINDOW a AS(PARTITION BY asset_id ORDER BY date)
)
SELECT asset_id,date,'kr_size_issue_v1' AS reference_id,ln(market_cap) AS value FROM w WHERE market_cap>0
UNION ALL SELECT asset_id,date,'kr_momentum_12_2_price_v1',p1/p12-1 FROM w
 WHERE p1>0 AND p12>0 AND n12=12
 AND date_trunc('month',d1)=date_trunc('month',date)-interval '1 month'
 AND date_trunc('month',d12)=date_trunc('month',date)-interval '12 month'
UNION ALL SELECT asset_id,date,'kr_reversal_1m_price_v1',adj_close/p1-1 FROM w
 WHERE adj_close>0 AND p1>0 AND date_trunc('month',d1)=date_trunc('month',date)-interval '1 month'
UNION ALL SELECT asset_id,date,'kr_low_volatility_252d_v1',daily_volatility_252d FROM w
 WHERE daily_volatility_252d>=0 AND daily_return_observations_252d BETWEEN 200 AND 252
UNION ALL SELECT asset_id,date,'kr_amihud_1m_v1',amihud_illiquidity_1m FROM w
 WHERE amihud_illiquidity_1m>=0 AND amihud_observations_1m BETWEEN 15 AND 31
UNION ALL SELECT asset_id,date,'kr_high_252d_v1',adj_close/price_high_252d FROM w
 WHERE adj_close>0 AND price_high_252d>0 AND price_high_observations_252d=252 AND adj_close/price_high_252d<=1+1e-12
UNION ALL SELECT asset_id,date,'kr_max_1m_v1',max_daily_return_1m FROM w
 WHERE max_daily_return_1m>-1 AND max_daily_return_observations_1m BETWEEN 15 AND 31
"""


def check_sql_parity(conn, panel, values):
    import numpy as np
    columns=["asset_id","date",*library.FEATURE_CONTRACTS,
             "daily_return_observations_252d","amihud_observations_1m",
             "price_high_observations_252d","max_daily_return_observations_1m"]
    columns=list(dict.fromkeys(columns))
    with conn.transaction(),conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout='120s'")
        fields=["asset_id bigint","date date"]+[f'"{c}" double precision' for c in columns[2:]]
        cur.execute("CREATE TEMP TABLE reference_parity_input ("+",".join(fields)+") ON COMMIT DROP")
        with cur.copy("COPY reference_parity_input FROM STDIN") as copy:
            for row in panel[columns].itertuples(index=False,name=None):
                copy.write_row(tuple(None if pd.isna(v) else v for v in row))
        cur.execute(PARITY_SQL)
        other=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
    own=values[["asset_id","date","reference_id","value"]].copy()
    for f in (own,other):
        f["asset_id"]=f.asset_id.astype(str)
        f["date"]=pd.to_datetime(f.date)
    merged=own.merge(other,on=["asset_id","date","reference_id"],how="outer",suffixes=("_py","_sql"),indicator=True,validate="one_to_one")
    if not merged._merge.eq("both").all() or not np.allclose(merged.value_py,merged.value_sql,rtol=1e-10,atol=0,equal_nan=False):
        raise ValueError("Python/SQL reference calculation parity failed")
    return {"passed":True,"kind":"INDEPENDENT_POSTGRES_FORMULAS_SAME_ATTESTED_PRICE_FEATURES",
            "rows_compared":len(merged),"sql_sha256":__import__('hashlib').sha256(PARITY_SQL.encode()).hexdigest(),
            "values_sha256":digest(gold.canonical_values(values)),"rtol":1e-10,"atol":0}


SQLITE_PARITY_SQL=(PARITY_SQL
    .replace("date_trunc('month',d1)=date_trunc('month',date)-interval '1 month'",
             "date(d1,'start of month')=date(date,'start of month','-1 month')")
    .replace("date_trunc('month',d12)=date_trunc('month',date)-interval '12 month'",
             "date(d12,'start of month')=date(date,'start of month','-12 month')"))


def check_full_sqlite_parity(panel,values):
    """Full independent SQL engine evaluation without transmitting 2M result rows.

    Inputs are the identical attested monthly features, just as for PostgreSQL.
    This certifies characteristic formulas, not independent raw daily ingestion.
    """
    import sqlite3
    import numpy as np
    columns=['asset_id','date',*library.FEATURE_CONTRACTS,
             'daily_return_observations_252d','amihud_observations_1m',
             'price_high_observations_252d','max_daily_return_observations_1m']
    with sqlite3.connect(':memory:') as db:
        fields=['asset_id INTEGER','date TEXT']+[f'"{c}" REAL' for c in columns[2:]]
        db.execute('CREATE TABLE reference_parity_input ('+','.join(fields)+')')
        def rows():
            for row in panel[columns].itertuples(index=False,name=None):
                yield (int(row[0]),str(pd.Timestamp(row[1]).date()),*(None if pd.isna(v) else float(v) for v in row[2:]))
        db.executemany('INSERT INTO reference_parity_input VALUES('+','.join('?' for _ in columns)+')',rows())
        cur=db.execute(SQLITE_PARITY_SQL)
        other=pd.DataFrame(cur.fetchall(),columns=[d[0] for d in cur.description])
    own=values[['asset_id','date','reference_id','value']].copy()
    for frame in (own,other):
        frame['asset_id']=frame.asset_id.astype(str);frame['date']=pd.to_datetime(frame.date)
    merged=own.merge(other,on=['asset_id','date','reference_id'],how='outer',suffixes=('_py','_sql'),indicator=True,validate='one_to_one')
    if not merged._merge.eq('both').all() or not np.allclose(merged.value_py,merged.value_sql,rtol=1e-10,atol=0,equal_nan=False):
        raise ValueError('Full Python/SQLite reference calculation parity failed')
    return dict(passed=True,rows_compared=len(merged),sqlite_version=sqlite3.sqlite_version,
                sql_sha256=__import__('hashlib').sha256(SQLITE_PARITY_SQL.encode()).hexdigest(),rtol=1e-10,atol=0)


def check_bounded_sql_parity(conn,panel,values):
    print('Independent SQLite: comparing every reference value',flush=True)
    full=check_full_sqlite_parity(panel,values)
    assets=sorted(panel.asset_id.astype(int).unique().tolist())
    # Fixed evenly spaced identity sample, selected without seeing any errors or
    # economic results. Every historical month of each sampled asset is retained.
    sample=sorted({assets[(len(assets)-1)*i//9] for i in range(10)})
    subset=panel.loc[panel.asset_id.astype(int).isin(sample)]
    expected=values.loc[values.asset_id.astype(int).isin(sample)]
    print(f'PostgreSQL: independent second-engine check of {len(sample)} fixed assets',flush=True)
    pg=check_sql_parity(conn,subset,expected)
    return dict(passed=True,kind='INDEPENDENT_SQLITE_FULL_POSTGRES_FIXED_SAMPLE',rows_compared=full['rows_compared'],
                values_sha256=digest(gold.canonical_values(values)),sql_sha256=full['sql_sha256'],
                sqlite_full=full,postgres_sample={**pg,'asset_ids':sample,'selection':'TEN_EVENLY_SPACED_SORTED_ASSET_IDS_ALL_MONTHS'},
                rtol=1e-10,atol=0)


def publish_snapshot(output, *, apply=False):
    """Revalidate immutable source snapshot without fetching all prices again.

    A failed live fetch is not resumable from partial chunks: only a completed
    attested input snapshot may be re-calculated and published with this command.
    """
    output=Path(output)
    evidence=json.loads((output/'source-evidence.json').read_bytes())
    attestation=json.loads((output/'input-attestation.json').read_bytes())
    panel=pd.read_parquet(output/'input.parquet')
    if digest(evidence)!=attestation.get('evidence_sha256') or digest(evidence)!=attestation.get('source_version'):
        raise ValueError('Source evidence digest differs from input attestation')
    if attestation.get('input_sha256')!=library.input_panel_digest(panel):
        raise ValueError('Frozen reference input was modified')
    result=library.calculate_reference_panel(panel,input_attestation=attestation)
    original=pd.read_parquet(output/'values.parquet')
    try:pd.testing.assert_frame_equal(result.values,original,check_dtype=False,check_exact=True)
    except AssertionError as error:raise ValueError('Recalculated reference values differ from frozen artifact') from error
    with silver.connect(read_only=False) as conn:
        before=silver.read_frame(conn,'SELECT factor_id,factor_key,version,status,config,evaluation FROM gold.factor ORDER BY factor_id')
        parity=check_bounded_sql_parity(conn,panel,result.values)
        publication,rows=gold.build_publication(result.values,library.load_catalog(),attestation=attestation,validation=result.validation,parity=parity)
        _immutable(output/('publication-'+publication['dataset_id']+'.json'),canonical(publication)+b'\n')
        print('Formula parity passed; validating/publishing immutable Gold dataset',flush=True)
        schema=gold.install_schema(conn,apply=apply)
        receipt=gold.publish(conn,publication,rows,apply=apply)
        after=silver.read_frame(conn,'SELECT factor_id,factor_key,version,status,config,evaluation FROM gold.factor ORDER BY factor_id')
        pd.testing.assert_frame_equal(before,after)
    receipt={**receipt,'schema':schema,'legacy_metadata_unchanged':True,'blocked_count':len(result.blocked),
             'source_snapshot':str(output),'completed_at':datetime.now(timezone.utc).isoformat()}
    target=output/('publish-receipt-'+publication['dataset_id']+('-applied' if apply else '-dry')+'.json')
    if not target.exists():_immutable(target,canonical(receipt)+b'\n')
    return receipt


def run(output, *, start="2015-01-01", end=None, apply=False):
    output=Path(output)
    if output.exists():
        raise ValueError("Use a fresh immutable output directory")
    output.mkdir(parents=True)
    with silver.connect() as conn:
        panel,evidence=gold.load_certified_price_panel(conn,start=start,end=end,checkpoint_dir=output/"source-chunks")
        legacy_before=silver.read_frame(conn,"SELECT factor_id,factor_key,version,status,config,evaluation FROM gold.factor ORDER BY factor_id")
    evidence["fetched_at"]=datetime.now(timezone.utc).isoformat()
    _immutable(output/"source-evidence.json",canonical(evidence)+b"\n")
    panel.to_parquet(output/"input.parquet",index=False)
    attestation={"status":"CERTIFIED","source_type":evidence["source_type"],
        "source_version":digest(evidence),"source_contract":"CERTIFIED_KRX_FEATURE_ONLY_MONTHLY_V1",
        "evidence_sha256":digest(evidence),"input_sha256":library.input_panel_digest(panel),
        "identity_contract":library.IDENTITY_CONTRACT,"scope":library.INPUT_SCOPE,
        "units":library.FEATURE_UNITS,"feature_contracts":library.FEATURE_CONTRACTS}
    _immutable(output/"input-attestation.json",canonical(attestation)+b"\n")
    result=library.calculate_reference_panel(panel,input_attestation=attestation)
    result.values.to_parquet(output/"values.parquet",index=False)
    _immutable(output/"validation.json",canonical(result.validation)+b"\n")
    _immutable(output/"blocked.json",canonical(result.blocked)+b"\n")
    with silver.connect(read_only=False) as conn:
        parity=check_bounded_sql_parity(conn,panel,result.values)
        publication,rows=gold.build_publication(result.values,library.load_catalog(),attestation=attestation,validation=result.validation,parity=parity)
        _immutable(output/"publication.json",canonical(publication)+b"\n")
        schema=gold.install_schema(conn,apply=apply)
        receipt=gold.publish(conn,publication,rows,apply=apply)
        legacy_after=silver.read_frame(conn,"SELECT factor_id,factor_key,version,status,config,evaluation FROM gold.factor ORDER BY factor_id")
        pd.testing.assert_frame_equal(legacy_before,legacy_after)
    report={"schema_version":"reference-library-run-v1",**receipt,"schema":schema,
        "completed_at":datetime.now(timezone.utc).isoformat(),"source":evidence,
        "definitions":result.validation["references"],"blocked":result.blocked,
        "legacy_metadata_unchanged":True,"legacy_value_write_paths_used":False,
        "profitability_evaluated":False,"input_snapshot":str(output/"input.parquet")}
    _immutable(output/"receipt.json",canonical(report)+b"\n")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["catalog","build","publish","readback"])
    p.add_argument("--output",type=Path)
    p.add_argument("--start",default="2015-01-01")
    p.add_argument("--end")
    p.add_argument("--apply",action="store_true")
    p.add_argument("--dataset-id")
    p.add_argument("--snapshot-path",type=Path,
                   help="readback only: exact parquet transport cache, still verified against every DB row")
    args=p.parse_args()
    if args.snapshot_path is not None and args.command!="readback":
        p.error("--snapshot-path is only valid for readback")
    if args.command=="catalog":
        report={"definitions":library.load_catalog(),"alpha_approved":False}
    elif args.command=="readback":
        if not args.dataset_id:p.error("--dataset-id required")
        with silver.connect() as conn:
            values,metadata=gold.load_library(conn,dataset_id=args.dataset_id,snapshot_path=args.snapshot_path)
        report={"dataset_id":args.dataset_id,"rows":len(values),"definitions":len(metadata["definitions"]),"digest_verified":True,"alpha_approved":False}
    elif args.command=='publish':
        if not args.output:p.error('--output completed build directory required')
        report=publish_snapshot(args.output,apply=args.apply)
    else:
        if not args.output:p.error("--output required")
        report=run(args.output,start=args.start,end=args.end,apply=args.apply)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
