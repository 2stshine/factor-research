"""Independent SQL characteristic parity for the 38 new measurements.

``sql_for(reference_ids, dialect='sqlite'|'postgres')`` reads the feature-only
table ``reference_input``: asset_id text, stock_code text, date text/SQL date,
month_index integer (calendar year*12+month), and required numeric columns.
It returns reference_id, asset_id, stock_code, date, value. Calendar RANGE
windows, not row offsets, implement the two price-history definitions.

``validate_parity(panel, values, conn)`` compares every expected row in SQLite
and every historical month of ten deterministically spaced output asset IDs in
PostgreSQL. It matches reference_gold's existing publication contract. Only a
temporary feature table is created, then dropped; source/Gold tables are never
read or changed. The caller supplies a connection allowing temporary tables.

This verifies formulas over the SAME attested monthly features, not raw source
collection, statement meaning, PIT vintage, statistical significance or alpha.
The price adapter has a separate independent daily aggregation oracle. No LLM
simulates either SQL engine. Tests with a fake PG transport are labeled tests;
actual validate_parity success requires the caller's real PostgreSQL execution.
"""
from __future__ import annotations

import hashlib
import math
import re
import sqlite3

import numpy as np
import pandas as pd

from engine import reference_expansion_formulas as financial
from engine import reference_gold as gold
from engine import reference_price_expansion as price
from engine.research_generation import digest


REFERENCES=frozenset(price.REFERENCE_SPECS)|frozenset(financial.FINANCIAL_FORMULAS)
KEYS=["reference_id","asset_id","stock_code","date"]
RTOL=1e-10
ATOL=0
SELECTION="TEN_EVENLY_SPACED_SORTED_ASSET_IDS_ALL_MONTHS"


def _ids(reference_ids):
    if (not isinstance(reference_ids,(list,tuple)) or not reference_ids
        or not all(isinstance(ref,str) for ref in reference_ids)
        or len(reference_ids)!=len(set(reference_ids)) or not set(reference_ids)<=REFERENCES):
        raise ValueError("Explicit unique registered expansion references required")
    return sorted(reference_ids)


def required_columns(reference_ids):
    columns=set()
    for ref in _ids(reference_ids):
        columns.update(price.REFERENCE_SPECS[ref]["required_columns"] if ref in price.REFERENCE_SPECS
                       else financial.required_columns(ref))
    return sorted(columns)


def _count(column,minimum=15,maximum=31):
    return f"({column} BETWEEN {minimum} AND {maximum} AND {column}=floor({column}))"


def sql_for(reference_ids, dialect="sqlite"):
    """Frozen independently written SQL, with no caller-controlled expressions."""
    ids=_ids(reference_ids)
    if dialect not in {"sqlite","postgres"}:
        raise ValueError("SQL dialect must be sqlite or postgres")
    needs_id="kr_information_discreteness_12_2_v1" in ids
    needs_long="kr_reversal_36_13_price_v1" in ids
    extra=[]
    def window(expr,start,end):
        return (f"{expr} OVER (PARTITION BY asset_id ORDER BY month_index "
                f"RANGE BETWEEN {start} PRECEDING AND {end} PRECEDING)")
    if needs_id or needs_long:
        extra.append(window("max(adj_close)",12,12)+" AS historical_p12")
    if needs_long:
        extra.extend([window("max(adj_close)",36,36)+" AS historical_p36",
                      window("count(CASE WHEN adj_close>0 THEN 1 END)",36,12)+" AS historical_long_count"])
    if needs_id:
        counts=(_count("price_return_observations_1m")+
                " AND positive_return_days_1m>=0 AND positive_return_days_1m=floor(positive_return_days_1m)"
                " AND negative_return_days_1m>=0 AND negative_return_days_1m=floor(negative_return_days_1m)"
                " AND positive_return_days_1m+negative_return_days_1m<=price_return_observations_1m")
        extra.extend([
            window("max(adj_close)",1,1)+" AS historical_p1",
            window("count(CASE WHEN adj_close>0 THEN 1 END)",12,1)+" AS historical_id_price_count",
            window(f"count(CASE WHEN {counts} THEN 1 END)",11,1)+" AS historical_id_valid_months",
            window("sum(negative_return_days_1m-positive_return_days_1m)",11,1)+" AS historical_id_signed_days",
            window("sum(price_return_observations_1m)",11,1)+" AS historical_id_days",
        ])
    direct={
        "kr_turnover_1m_v1":("share_turnover_1m",_count("turnover_observations_1m")+" AND share_turnover_1m>=0"),
        "kr_turnover_cv_1m_v1":("share_turnover_cv_1m",_count("turnover_observations_1m")+" AND share_turnover_cv_1m>=0"),
        "kr_traded_value_1m_v1":("ln(mean_traded_value_1m)",_count("traded_value_observations_1m")+" AND mean_traded_value_1m>0"),
        "kr_traded_value_cv_1m_v1":("traded_value_cv_1m",_count("traded_value_observations_1m")+" AND traded_value_cv_1m>=0"),
        "kr_zero_volume_1m_v1":("zero_volume_fraction_1m",_count("volume_observations_1m")+" AND zero_volume_fraction_1m BETWEEN 0 AND 1"),
        "kr_downside_risk_252d_v1":("downside_semideviation_252d",_count("daily_return_observations_252d",200,252)+" AND downside_semideviation_252d>=0"),
        "kr_return_skew_252d_v1":("return_skew_252d",_count("daily_return_observations_252d",200,252)),
        "kr_parkinson_1m_v1":("parkinson_variance_1m",_count("range_observations_1m")+" AND parkinson_variance_1m>=0"),
        "kr_nominal_price_v1":("ln(nominal_close)","nominal_close>0"),
        "kr_reversal_36_13_price_v1":("historical_p12/historical_p36-1",
            "historical_p12>0 AND historical_p36>0 AND historical_long_count=25"),
        "kr_information_discreteness_12_2_v1":(
            "(CASE WHEN historical_p1>historical_p12 THEN 1.0 WHEN historical_p1<historical_p12 THEN -1.0 ELSE 0.0 END)*historical_id_signed_days/historical_id_days",
            "historical_p1>0 AND historical_p12>0 AND historical_id_price_count=12 AND historical_id_valid_months=11 AND historical_id_days>0"),
    }
    for kind in ("overnight","intraday"):
        direct[f"kr_{kind}_momentum_1m_v1"]=(f"{kind}_return_1m",
            _count(f"{kind}_observations_1m")+" AND "+_count("price_observations_1m")+
            f" AND {kind}_observations_1m=price_observations_1m AND {kind}_return_1m>-1")
    selects=[]
    for ref in ids:
        if ref in financial.FINANCIAL_FORMULAS:
            expression=financial.sql_expression(ref)
        else:
            expression,condition=direct[ref]
            expression=f"CASE WHEN {condition} THEN {expression} END"
        selects.append(f"SELECT '{ref}' AS reference_id,asset_id,stock_code,date,{expression} AS value FROM w")
    # The helpers project nonfinite feature cells to NULL exactly as Python does.
    # Finite output guard also rejects arithmetic overflow on SQLite. PostgreSQL
    # arithmetic overflow fails the check rather than silently becoming a value.
    return ("WITH w AS (SELECT reference_input.*"+(" ,"+",\n".join(extra) if extra else "")+
            " FROM reference_input), measured AS (\n"+"\nUNION ALL\n".join(selects)+
            "\n) SELECT reference_id,asset_id,stock_code,date,value FROM measured "
            "WHERE value IS NOT NULL AND abs(value)<=1.7976931348623157e308")


def _prepare(panel,ids):
    required=required_columns(ids)
    needed={"asset_id","stock_code","date",*required}
    if not isinstance(panel,pd.DataFrame) or panel.empty or not panel.columns.is_unique or not needed<=set(panel):
        raise ValueError("Nonempty unique-column feature panel with all required inputs needed")
    frame=panel.loc[:,["asset_id","stock_code","date",*required]].copy()
    if frame[["asset_id","stock_code","date"]].isna().any().any():
        raise ValueError("Null parity identity/time")
    if not frame.asset_id.map(lambda v:isinstance(v,(str,int,np.integer)) and not isinstance(v,bool)
        and str(v).isdigit() and str(int(v))==str(v) and int(v)>0).all():
        raise ValueError("Positive stable integer asset identity required")
    frame.asset_id=frame.asset_id.astype(str)
    if not frame.stock_code.map(lambda v:isinstance(v,str) and bool(re.fullmatch(r"[0-9A-Z]{6}",v))).all():
        raise ValueError("Canonical six-character stock codes required")
    dates=pd.to_datetime(frame.date,errors="raise")
    if dates.dt.tz is not None or not dates.dt.is_month_end.all() or not dates.eq(dates.dt.normalize()).all():
        raise ValueError("Normalized calendar month-end formation dates required")
    frame.date=dates
    month_index=dates.dt.year*12+dates.dt.month
    if "month_index" in panel and not panel.month_index.eq(month_index).all():
        raise ValueError("Supplied month_index disagrees with calendar date")
    frame.insert(3,"month_index",month_index.astype(int))
    if frame.duplicated(["asset_id","date"]).any() or frame.duplicated(["stock_code","date"]).any():
        raise ValueError("Duplicate or ambiguous asset-month parity input")
    for column in required:
        if not pd.api.types.is_numeric_dtype(frame[column]) or pd.api.types.is_bool_dtype(frame[column]):
            raise ValueError("Numeric parity input required: "+column)
        frame[column]=frame[column].astype(float).where(np.isfinite(frame[column]))
    return frame.sort_values(["asset_id","date"]).reset_index(drop=True)


def _records(frame):
    for row in frame.itertuples(index=False,name=None):
        yield (row[0],row[1],str(pd.Timestamp(row[2]).date()),int(row[3]),
               *(None if pd.isna(v) else float(v) for v in row[4:]))


def _compare(values,other,label):
    own=values.loc[:,[*KEYS,"value"]].copy()
    other=other.loc[:,[*KEYS,"value"]].copy()
    for frame in (own,other):
        frame["asset_id"]=frame.asset_id.astype(str)
        frame["date"]=pd.to_datetime(frame.date)
    merged=own.merge(other,on=KEYS,how="outer",suffixes=("_py","_sql"),indicator=True,validate="one_to_one")
    if not merged._merge.eq("both").all() or not np.allclose(merged.value_py,merged.value_sql,rtol=RTOL,atol=ATOL,equal_nan=False):
        raise ValueError(f"{label} full-key/value parity failed")
    return len(merged)


def validate_sqlite(panel,values,*,reference_ids=None):
    """Run the complete local SQL comparison; cannot itself satisfy PG parity."""
    ids=_ids(reference_ids if reference_ids is not None else sorted(values.reference_id.unique().tolist()))
    frame=_prepare(panel,ids)
    sql=sql_for(ids,"sqlite")
    with sqlite3.connect(":memory:") as db:
        db.create_function("ln",1,lambda v:math.log(v) if v is not None and v>0 else None)
        db.create_function("floor",1,lambda v:math.floor(v) if v is not None else None)
        fields=["asset_id TEXT","stock_code TEXT","date TEXT","month_index INTEGER"]+[f'"{c}" REAL' for c in frame.columns[4:]]
        db.execute("CREATE TABLE reference_input ("+",".join(fields)+")")
        db.executemany("INSERT INTO reference_input VALUES("+",".join("?" for _ in fields)+")",_records(frame))
        db.execute("CREATE UNIQUE INDEX reference_input_month ON reference_input(asset_id,month_index)")
        cursor=db.execute(sql)
        other=pd.DataFrame(cursor.fetchall(),columns=[d[0] for d in cursor.description])
    compared=_compare(values,other,"SQLite")
    return {"passed":True,"rows_compared":compared,"sqlite_version":sqlite3.sqlite_version,
            "sql_sha256":hashlib.sha256(sql.encode()).hexdigest(),"rtol":RTOL,"atol":ATOL}


def _postgres(conn,panel,values,ids):
    frame=_prepare(panel,ids)
    sql=sql_for(ids,"postgres")
    with conn.transaction(),conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout='180s'")
        fields=["asset_id TEXT","stock_code TEXT","date DATE","month_index INTEGER"]+[f'"{c}" DOUBLE PRECISION' for c in frame.columns[4:]]
        cur.execute("CREATE TEMP TABLE reference_input ("+",".join(fields)+") ON COMMIT DROP")
        with cur.copy("COPY reference_input FROM STDIN") as copy:
            for row in _records(frame):copy.write_row(row)
        cur.execute("CREATE UNIQUE INDEX reference_input_month ON reference_input(asset_id,month_index)")
        cur.execute(sql)
        other=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
        # Drop our own temporary table on successful nested transactions too.
        # On error the transaction/savepoint rolls back its creation instead.
        cur.execute("DROP TABLE pg_temp.reference_input")
    compared=_compare(values,other,"PostgreSQL")
    return {"passed":True,"rows_compared":compared,"sql_sha256":hashlib.sha256(sql.encode()).hexdigest(),
            "values_sha256":digest(gold.canonical_values(values)),"rtol":RTOL,"atol":ATOL}


def validate_parity(panel,values,conn):
    """Full SQLite plus a fixed real-PostgreSQL sample, Gold-contract compatible."""
    rows=gold.canonical_values(values)
    ids=_ids(sorted({row["reference_id"] for row in rows}))
    full=validate_sqlite(panel,values,reference_ids=ids)
    # Gold defines the deterministic sample from valid OUTPUT assets, not all
    # input assets; no-output/new listings therefore cannot shrink PG coverage.
    assets=sorted({row["asset_id"] for row in rows})
    sample=sorted({assets[(len(assets)-1)*i//9] for i in range(10)})
    subset=panel.loc[panel.asset_id.astype(int).isin(sample)]
    expected=values.loc[values.asset_id.astype(int).isin(sample)]
    pg=_postgres(conn,subset,expected,ids)
    return {"passed":True,"kind":"INDEPENDENT_SQLITE_FULL_POSTGRES_FIXED_SAMPLE",
            "rows_compared":full["rows_compared"],"values_sha256":digest(rows),"sql_sha256":full["sql_sha256"],
            "sqlite_full":full,"postgres_sample":{**pg,"asset_ids":sample,"selection":SELECTION},
            "reference_ids":ids,"rtol":RTOL,"atol":ATOL}
