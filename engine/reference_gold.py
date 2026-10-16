"""New-generation reference measurements; never reads/writes legacy factor values.

Only certified KRX price fields are queried. No forward returns, corrected
dividend labels, legacy factors or empirical lessons enter this adapter.
Publication is explicit, transactional, immutable and checked on read-back.
Reference publication certifies a measurement, NOT predictive profitability.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import pandas as pd

from engine.research_generation import canonical, digest

GENERATION = "phenomenon-research-v1"
ROLE = "MEASUREMENT_AND_CONTROL_NOT_ALPHA_APPROVAL"
SCHEMA_VERSION = "reference-measurements-v1"
DDL_PATH = Path(__file__).resolve().parents[2] / "TeamAlpha-data/sql/reference_library_schema.sql"
READBACK_PROTOCOL = "POSTGRES_BINARY_ALL_ROW_CHUNK_SHA256_V1"
READBACK_CHUNK_SIZE = 10000


def _validate_source_attestation(attestation):
    source=attestation.get('source_type')
    if attestation.get('status')!='CERTIFIED':
        raise ValueError('Real certified source required')
    if source=='RDS_CERTIFIED_KIS_KRX_SHORT_ELIGIBILITY_V2':
        from engine.reference_short_eligibility import SOURCE_CONTRACT,PIT_STATUS
        if (attestation.get('source_contract')!=SOURCE_CONTRACT or attestation.get('pit_status')!=PIT_STATUS
            or attestation.get('first_vintage_independently_verified') is not False
            or attestation.get('identity_contract')!='HISTORICAL_ASSET_ID'
            or attestation.get('scope')!='KRX_COMMON_STOCK'
            or attestation.get('source_version')!=attestation.get('evidence_sha256')
            or attestation.get('availability_policy')!='NEXT_CALENDAR_DAY_0830_KST_EXCLUDE_POST_CUTOFF_TRADES'
            or attestation.get('venue')!='J'
            or attestation.get('daily_official_membership_complete') is not True
            or attestation.get('individual_restrictions_applied') is not True
            or not re.fullmatch('[a-f0-9]{64}',str(attestation.get('policy_manifest_sha256','')))):
            raise ValueError('Short eligibility source contract/PIT/policy mismatch')
        return
    if source=='OFFICIAL_DART_FMP_NEW_INFORMATION_REFERENCE_V1':
        from engine.reference_new_information import SOURCE_CONTRACT,PIT_STATUS
        if (attestation.get('source_contract')!=SOURCE_CONTRACT or attestation.get('pit_status')!=PIT_STATUS
            or attestation.get('first_vintage_independently_verified') is not False
            or attestation.get('identity_contract')!='HISTORICAL_ASSET_ID'
            or attestation.get('scope')!='KRX_COMMON_STOCK'
            or attestation.get('source_version')!=attestation.get('evidence_sha256')
            or attestation.get('availability_policy')!='CERTIFIED_DART_RECEIPT_NEXT_DAY_KST'
            or attestation.get('fmp_filing_timestamp_used') is not False
            or attestation.get('employee_consolidation_scope')!='DISCLOSING_ISSUER_NOT_GROUP'
            or attestation.get('rd_currency')!='KRW'
            or attestation.get('rd_revenue_bridge')!='DART_CFS_EXACT_FY_REL1E6_ABS1KRW'):
            raise ValueError('New information source contract/PIT/receipt/scope mismatch')
        return
    if source=='RDS_CERTIFIED_KIS_MONTHLY_REFERENCE_V1':
        from engine.reference_flow_inputs import SOURCE_CONTRACT,PIT_STATUS
        if (attestation.get('source_contract')!=SOURCE_CONTRACT or attestation.get('pit_status')!=PIT_STATUS
            or attestation.get('first_vintage_independently_verified') is not False
            or attestation.get('identity_contract')!='HISTORICAL_ASSET_ID'
            or attestation.get('scope')!='KRX_COMMON_STOCK'
            or attestation.get('source_version')!=attestation.get('evidence_sha256')
            or attestation.get('availability_policy')!='NEXT_CALENDAR_DAY_0830_KST_EXCLUDE_POST_CUTOFF_TRADES'
            or attestation.get('venue')!='J'):
            raise ValueError('KIS flow source contract/PIT/availability mismatch')
        return
    if source=='RDS_CERTIFIED_REFERENCE_RISK_DIVERSITY_V1':
        from engine.reference_risk_catalog import SOURCE_CONTRACT,PIT_STATUS
        if (attestation.get('source_contract')!=SOURCE_CONTRACT or attestation.get('pit_status')!=PIT_STATUS
            or attestation.get('first_vintage_independently_verified') is not False
            or attestation.get('identity_contract')!='HISTORICAL_ASSET_ID'
            or attestation.get('scope')!='KRX_COMMON_STOCK'
            or attestation.get('source_version')!=attestation.get('evidence_sha256')):
            raise ValueError('Risk diversity source contract/PIT/scope mismatch')
        return
    if source=='RDS_CERTIFIED_REFERENCE_FORMULAIC_V1':
        from engine.reference_daily_diversity import SOURCE_CONTRACT,PIT_STATUS
        if (attestation.get('source_contract')!=SOURCE_CONTRACT or attestation.get('pit_status')!=PIT_STATUS
            or attestation.get('first_vintage_independently_verified') is not False
            or attestation.get('identity_contract')!='HISTORICAL_ASSET_ID'
            or attestation.get('scope')!='KRX_COMMON_STOCK'
            or attestation.get('source_version')!=attestation.get('evidence_sha256')):
            raise ValueError('Daily diversity source contract/PIT/scope mismatch')
        return
    if source=='RDS_CERTIFIED_REFERENCE_DIVERSITY_V1':
        from engine.reference_expansion_100 import SOURCE_CONTRACT,PIT_STATUS
        if (attestation.get('source_contract')!=SOURCE_CONTRACT or attestation.get('pit_status')!=PIT_STATUS
            or attestation.get('first_vintage_independently_verified') is not False
            or attestation.get('identity_contract')!='HISTORICAL_ASSET_ID'
            or attestation.get('scope')!='KRX_COMMON_STOCK'
            or attestation.get('source_version')!=attestation.get('evidence_sha256')):
            raise ValueError('Diversity source contract/PIT/scope mismatch')
        return
    if source=='RDS_CERTIFIED_KRX_PRICE_ONLY':return
    if source=='RDS_CERTIFIED_DART_PROFIT_GROWTH_FY_V1':
        from engine.reference_profit_growth import SOURCE_CONTRACT,PIT_STATUS
        if (attestation.get('source_contract')!=SOURCE_CONTRACT or attestation.get('pit_status')!=PIT_STATUS
            or attestation.get('first_vintage_independently_verified') is not False
            or attestation.get('identity_contract')!='HISTORICAL_ASSET_ID'
            or attestation.get('scope')!='KRX_COMMON_STOCK'
            or attestation.get('source_version')!=attestation.get('evidence_sha256')):
            raise ValueError('Profit-growth source contract/PIT/scope mismatch')
        return
    if source=='RDS_CERTIFIED_KRX_DART_FY_REFERENCE_V2':
        from engine.reference_library_v2 import SOURCE_CONTRACT,PIT_STATUS
        if (attestation.get('source_contract')!=SOURCE_CONTRACT or attestation.get('pit_status')!=PIT_STATUS
            or attestation.get('first_vintage_independently_verified') is not False
            or attestation.get('identity_contract')!='HISTORICAL_ASSET_ID'
            or attestation.get('scope')!='KRX_COMMON_STOCK'
            or attestation.get('source_version')!=attestation.get('evidence_sha256')):
            raise ValueError('Expanded source contract/PIT/scope mismatch')
        return
    raise ValueError('Real certified source required; unsupported source adapter')


def _validate_definition_source(attestation,definitions):
    if attestation.get('source_type')=='RDS_CERTIFIED_KIS_KRX_SHORT_ELIGIBILITY_V2':
        from engine.reference_short_eligibility import definitions as registered
        from engine.reference_library import definition_hash
        allowed={d['id']:definition_hash(d) for d in registered()}
        if any(d['id'] not in allowed or definition_hash(d)!=allowed[d['id']] for d in definitions):
            raise ValueError('Short eligibility definition/source mismatch')
    if attestation.get('source_type')=='OFFICIAL_DART_FMP_NEW_INFORMATION_REFERENCE_V1':
        from engine.reference_new_information import definitions as registered
        from engine.reference_library import definition_hash
        allowed={d['id']:definition_hash(d) for d in registered()}
        if any(d['id'] not in allowed or definition_hash(d)!=allowed[d['id']] for d in definitions):
            raise ValueError('New information definition/source mismatch')
    if attestation.get('source_type')=='RDS_CERTIFIED_KIS_MONTHLY_REFERENCE_V1':
        from engine.reference_flow_inputs import definitions as registered
        from engine.reference_library import definition_hash
        allowed={d['id']:definition_hash(d) for d in registered()}
        if any(d['id'] not in allowed or definition_hash(d)!=allowed[d['id']] for d in definitions):
            raise ValueError('KIS flow definition/source mismatch')
    if attestation.get('source_type')=='RDS_CERTIFIED_REFERENCE_RISK_DIVERSITY_V1':
        from engine.reference_risk_catalog import definitions as registered
        from engine.reference_library import definition_hash
        allowed={d['id']:definition_hash(d) for d in registered()}
        if any(d['id'] not in allowed or definition_hash(d)!=allowed[d['id']] for d in definitions):
            raise ValueError('Risk diversity definition/source mismatch')
    if attestation.get('source_type')=='RDS_CERTIFIED_REFERENCE_FORMULAIC_V1':
        from engine.reference_daily_diversity import definitions as registered
        from engine.reference_library import definition_hash
        allowed={d['id']:definition_hash(d) for d in registered()}
        if any(d['id'] not in allowed or definition_hash(d)!=allowed[d['id']] for d in definitions):
            raise ValueError('Daily diversity definition/source mismatch')
    if attestation.get('source_type')=='RDS_CERTIFIED_REFERENCE_DIVERSITY_V1':
        from engine.reference_expansion_100 import definitions as registered
        from engine.reference_library import definition_hash
        allowed={d['id']:definition_hash(d) for d in registered()}
        if any(d['id'] not in allowed or definition_hash(d)!=allowed[d['id']] for d in definitions):
            raise ValueError('Diversity definition/source mismatch')
    if attestation.get('source_type')=='RDS_CERTIFIED_DART_PROFIT_GROWTH_FY_V1':
        from engine.reference_profit_growth import definitions as profit_definitions
        from engine.reference_library import definition_hash
        allowed={d['id']:definition_hash(d) for d in profit_definitions()}
        if any(d['id'] not in allowed or definition_hash(d)!=allowed[d['id']] for d in definitions):
            raise ValueError('Profit-growth definition/source mismatch')
    if attestation.get('source_type')=='RDS_CERTIFIED_KRX_PRICE_ONLY':
        from engine.reference_library import load_catalog,definition_hash,_EXECUTABLE
        allowed={d['id']:definition_hash(d) for d in load_catalog() if d['id'] in _EXECUTABLE}
        if any(d['id'] not in allowed or definition_hash(d)!=allowed[d['id']] for d in definitions):
            raise ValueError('Definition/source mismatch: Price-only v1 source cannot attest changed or expanded definitions')

# PostgreSQL send functions use big-endian binary encodings, with date/time
# epochs at 2000-01-01. Length-prefix text to avoid concatenation ambiguity.
# Return only hashes through SSM, but cover every persisted field of every row.
READBACK_SQL = """
WITH ordered AS (
 SELECT *, (row_number() OVER (ORDER BY reference_id COLLATE "C",asset_id,as_of_date)-1)/%s::bigint AS chunk_id
 FROM gold.reference_value WHERE dataset_id=%s AND generation_id=%s
), wire AS (
 SELECT chunk_id,reference_id,asset_id,as_of_date,
   int4send(octet_length(convert_to(reference_id,'UTF8'))) || convert_to(reference_id,'UTF8') ||
   int4send(octet_length(convert_to(definition_sha256,'UTF8'))) || convert_to(definition_sha256,'UTF8') ||
   int8send(asset_id) || int4send(octet_length(convert_to(stock_code,'UTF8'))) || convert_to(stock_code,'UTF8') ||
   date_send(as_of_date) || timestamptz_send(known_at) || float8send(value) AS row_bytes
 FROM ordered
)
SELECT chunk_id,count(*),encode(sha256(string_agg(row_bytes,''::bytea
 ORDER BY reference_id COLLATE "C",asset_id,as_of_date)),'hex')
FROM wire GROUP BY chunk_id ORDER BY chunk_id
"""


def binary_readback_chunks(rows, *, chunk_size=READBACK_CHUNK_SIZE):
    """Exact wire hashes of already validated, canonically ordered rows."""
    from datetime import date, datetime, timezone
    import struct
    if type(chunk_size) is not int or not 0 < chunk_size <= 100000:
        raise ValueError('Invalid read-back chunk size')
    if not rows:
        raise ValueError('Nonempty read-back rows required')
    epoch_date=date(2000,1,1)
    epoch_time=datetime(2000,1,1,tzinfo=timezone.utc)
    chunks=[]; hasher=hashlib.sha256(); count=0; previous=None; text_cache={}
    def text_bytes(value):
        if value not in text_cache:
            data=value.encode('utf-8'); text_cache[value]=struct.pack('!i',len(data))+data
        return text_cache[value]
    for row in rows:
        key=(row['reference_id'],row['asset_id'],row['date'])
        if previous is not None and key <= previous:
            raise ValueError('Read-back rows must be unique and in canonical order')
        previous=key
        delta=datetime.fromisoformat(row['known_at'])-epoch_time
        micros=(delta.days*86400+delta.seconds)*1000000+delta.microseconds
        hasher.update(text_bytes(row['reference_id'])+text_bytes(row['definition_hash'])+
                      struct.pack('!q',row['asset_id'])+text_bytes(row['stock_code'])+
                      struct.pack('!iqd',(date.fromisoformat(row['date'])-epoch_date).days,micros,row['value']))
        count+=1
        if count==chunk_size:
            chunks.append({'chunk_id':len(chunks),'row_count':count,'sha256':hasher.hexdigest()})
            hasher=hashlib.sha256(); count=0
    if count:chunks.append({'chunk_id':len(chunks),'row_count':count,'sha256':hasher.hexdigest()})
    return chunks


def verify_database_rows(cur, *, dataset_id, rows):
    """All-row exact binary comparison, NOT a statistical sample or tolerance."""
    expected=binary_readback_chunks(rows)
    cur.execute(READBACK_SQL,(READBACK_CHUNK_SIZE,dataset_id,GENERATION))
    observed=[dict(chunk_id=int(chunk),row_count=int(count),sha256=sha) for chunk,count,sha in cur.fetchall()]
    if observed!=expected:
        raise ValueError('Gold all-row binary read-back differs; transaction must roll back')
    return {'readback_protocol':READBACK_PROTOCOL,'readback_sha256':digest(observed),
            'readback_rows':sum(c['row_count'] for c in observed),'readback_chunks':len(observed),
            'readback_chunk_size':READBACK_CHUNK_SIZE,'readback_sql_sha256':hashlib.sha256(READBACK_SQL.encode()).hexdigest()}

# Windows operate only on historical certified common-stock observations.
# The final monthly row, not intermediate daily rows, receives full-month stats.
PRICE_SQL = """
WITH p AS (
 SELECT p.asset_id, p.trade_date, p.adj_close::float8 AS adj_close,
        p.market_cap::float8 AS market_cap,p.trading_value::float8 AS trading_value,
        p.market,p.quality_run_id::text AS quality_run_id
 FROM public.price_daily p
 JOIN public.asset a ON a.asset_id=p.asset_id
 JOIN public.dq_run q ON q.run_id=p.quality_run_id AND q.status='CERTIFIED'
 WHERE p.source='KRX' AND a.exchange='KRX' AND a.asset_type='stock'
   AND a.instrument_type='common_stock' AND p.market IN ('KOSPI','KOSDAQ')
   AND p.trade_date BETWEEN %s::date AND %s::date
   AND p.asset_id = ANY(%s::bigint[])
), r AS (
 SELECT p.*,CASE WHEN adj_close>0 AND lag(adj_close) OVER w>0
   THEN adj_close/lag(adj_close) OVER w-1 END AS price_return
 FROM p WINDOW w AS (PARTITION BY asset_id ORDER BY trade_date)
), f AS (
 SELECT r.*,
 stddev_samp(price_return) OVER w AS daily_volatility_252d,
 count(price_return) OVER w AS daily_return_observations_252d,
 max(adj_close) OVER w AS price_high_252d,
 count(adj_close) OVER w AS price_high_observations_252d,
 avg(abs(price_return)/trading_value) FILTER(WHERE trading_value>0) OVER m AS amihud_illiquidity_1m,
 count(price_return) FILTER(WHERE trading_value>0) OVER m AS amihud_observations_1m,
 max(price_return) OVER m AS max_daily_return_1m,
 count(price_return) OVER m AS max_daily_return_observations_1m,
 row_number() OVER(PARTITION BY asset_id,date_trunc('month',trade_date) ORDER BY trade_date DESC) AS rn
 FROM r WINDOW w AS (PARTITION BY asset_id ORDER BY trade_date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW),
 m AS (PARTITION BY asset_id,date_trunc('month',trade_date))
)
SELECT f.*,i.stock_code,i.n AS ticker_match_count FROM f
 JOIN LATERAL (
   SELECT min(identifier) AS stock_code,count(*) AS n FROM public.asset_identifier ai
   WHERE ai.asset_id=f.asset_id AND ai.source='KRX' AND ai.identifier_type='ticker'
     AND ai.valid_from<=f.trade_date AND (ai.valid_to IS NULL OR ai.valid_to>=f.trade_date)
 ) i ON true
 WHERE rn=1 ORDER BY asset_id,trade_date
"""


def load_certified_price_panel(conn, *, start="2015-01-01", end=None, checkpoint_dir=None):
    """Return feature-only monthly panel plus source evidence, no performance.

    Conservatively omit the latest observed calendar month, even if it may be
    complete. A source-specific closeout contract is needed to include it.
    """
    from engine import silver
    if pd.Timestamp(start).day != 1:
        raise ValueError("Reference start must be first day of a calendar month")
    if end is not None and pd.Timestamp(end).date() != pd.Timestamp(end).to_period('M').end_time.date():
        raise ValueError("Reference end must be a calendar month-end")
    with conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout = '180s'")
        cur.execute("SET LOCAL work_mem = '64MB'")
        cur.execute("""SELECT max(p.trade_date) FROM public.price_daily p
          JOIN public.dq_run q ON q.run_id=p.quality_run_id AND q.status='CERTIFIED'
          WHERE p.source='KRX' AND p.market IN ('KOSPI','KOSDAQ')""")
        latest = cur.fetchone()[0]
    if latest is None:
        raise ValueError("No certified KRX price observations")
    safe_end = (pd.Timestamp(latest).to_period("M") - 1).end_time.date()
    if end is not None:
        safe_end = min(safe_end, pd.Timestamp(end).date())
    if pd.Timestamp(start).date() > safe_end:
        raise ValueError("No closed source months in requested interval")
    with conn.cursor() as cur:
        cur.execute("""SELECT asset_id FROM public.asset WHERE exchange='KRX'
          AND asset_type='stock' AND instrument_type='common_stock' ORDER BY asset_id""")
        assets = [r[0] for r in cur.fetchall()]
    # One repeatable-read transaction fixes the source snapshot across chunks.
    # Checkpoints are forensic outputs, not independently reusable live snapshots.
    chunks=[]
    for offset in range(0,len(assets),150):
        chunk=silver.read_frame(conn, PRICE_SQL, (start,str(safe_end),assets[offset:offset+150]))
        chunks.append(chunk)
        if checkpoint_dir is not None:
            path=Path(checkpoint_dir); path.mkdir(parents=True,exist_ok=True)
            chunk.to_parquet(path/f"price-{offset:06d}.parquet",index=False)
        print(f"Certified price input: {min(offset+150,len(assets))}/{len(assets)} assets, {len(chunk)} monthly rows",flush=True)
    frame=pd.concat(chunks,ignore_index=True)
    return normalize_price_frame(frame,start=start,safe_end=safe_end,assets=assets,latest=latest)


def normalize_price_frame(frame,*,start,safe_end,assets,latest=None):
    """Validate a complete trusted extraction, keeping exclusions auditable."""
    frame=frame.copy()
    if frame.empty or (frame.ticker_match_count != 1).any():
        raise ValueError("Empty source or ambiguous historical identity")
    if not frame.stock_code.map(lambda x: isinstance(x,str) and bool(re.fullmatch(r'[0-9A-Z]{6}',x))).all():
        raise ValueError("Historical ticker must be six-character uppercase ASCII text")
    if frame.duplicated(['asset_id','trade_date']).any():
        raise ValueError('Duplicate monthly price identity')
    # Some upstream rows labeled common_stock are class shares (00104K/37550L).
    # Quarantine non-zero suffixes pending exact historical classification; do
    # not rewrite upstream asset records or presume all alphabetic codes invalid.
    disputed=frame.loc[~frame.stock_code.str.endswith('0')]
    exclusions=[dict(asset_id=int(asset),stock_code=code,rows=len(group),
                     reason='NONZERO_ISSUE_SUFFIX_COMMON_CLASSIFICATION_REQUIRES_REVIEW')
                for (asset,code),group in disputed.groupby(['asset_id','stock_code'],sort=True)]
    frame=frame.loc[frame.stock_code.str.endswith('0')].copy()
    if frame.empty:raise ValueError('No verified-scope common-stock input remains')
    # Retain the actual last observed session separately from formation date.
    frame["observed_trade_date"] = frame.trade_date.astype(str)
    frame["date"] = pd.to_datetime(frame.trade_date).dt.to_period("M").dt.end_time.dt.normalize()
    frame["known_at"] = (pd.to_datetime(frame.trade_date).dt.normalize()
                          + pd.Timedelta(hours=23,minutes=59,seconds=59)).dt.tz_localize("Asia/Seoul")
    runs = sorted(frame.quality_run_id.unique().tolist())
    evidence = {"schema_version":"certified-reference-price-source-v1",
                "source_type":"RDS_CERTIFIED_KRX_PRICE_ONLY", "endpoint_quality_run_ids":runs,
                "contributing_daily_runs":"EVERY_ROW_CERTIFIED_BY_QUERY_NOT_AN_EXHAUSTIVE_RUN_ID_LIST",
                "source_latest_observation":str(latest) if latest is not None else None, "requested_start":start,
                "effective_end":str(safe_end), "query_sha256":hashlib.sha256(PRICE_SQL.encode()).hexdigest(),
                "rows":len(frame), "assets":int(frame.asset_id.nunique()),
                "asset_batches": {"size":150,"asset_ids_sha256":digest(assets),"single_repeatable_read":True},
                "latest_month_omitted_conservatively":True,
                "identity_quarantine":exclusions,"quarantined_monthly_rows":len(disputed),
                "vintage_limitation":"DQ_CERTIFIED_ACCEPTED_PRICE_FEATURE_CONTRACT_NOT_AN_INDEPENDENT_FIRST_VINTAGE_AUDIT",
                "known_at_policy":"OBSERVED_TRADE_DATE_END_KST_CONSERVATIVE_NOT_INTRADAY",
                "legacy_gold_used":False, "forward_labels_read":False}
    frame = frame.drop(columns=["trade_date","ticker_match_count","rn","price_return","quality_run_id","observed_trade_date","trading_value"])
    from engine.reference_library import FEATURE_CONTRACTS
    for column in [*FEATURE_CONTRACTS,'daily_return_observations_252d','amihud_observations_1m',
                   'price_high_observations_252d','max_daily_return_observations_1m']:
        if column in frame:
            # Empty SQL batches can coerce otherwise numeric parquet columns to
            # object on concat. Convert typed numeric/null values, never strings
            # that fail parsing and never ticker identities.
            frame[column]=pd.to_numeric(frame[column],errors='raise').astype('float64')
    return frame, evidence


def canonical_values(values):
    """Stable, lossless-enough JSON rows for digest and PostgreSQL read-back."""
    if not isinstance(values,pd.DataFrame) or values.empty:
        raise ValueError("Nonempty reference values required")
    needed = {"reference_id","definition_hash","asset_id","stock_code","date","known_at","value"}
    if not needed.issubset(values.columns):
        raise ValueError("Reference value columns missing")
    if values.duplicated(["reference_id","asset_id","date"]).any():
        raise ValueError("Duplicate reference value identity")
    import numpy as np
    numeric=pd.to_numeric(values['value'],errors='raise').astype(float)
    if (not np.isfinite(numeric.to_numpy()).all() or not values.stock_code.map(lambda x:type(x) is str).all()
        or not values.stock_code.astype('string').str.fullmatch(r'[0-9A-Z]{6}').all()):
        raise ValueError('Finite value and six-character canonical stock_code required')
    ids=pd.to_numeric(values.asset_id,errors='raise')
    if (ids.isna().any() or (ids<=0).any() or (ids%1!=0).any() or values.asset_id.map(lambda x:isinstance(x,bool)).any()
        or not ids.astype('int64').astype('string').eq(values.asset_id.astype('string')).all()):
        raise ValueError('Positive integer asset_id required')
    if not isinstance(values.known_at.dtype,pd.DatetimeTZDtype):
        if not values.known_at.astype('string').str.contains(r'(?:Z|[+-][0-9]{2}:[0-9]{2})$',regex=True).fillna(False).all():
            raise ValueError('known_at requires a timezone')
    stamps=pd.to_datetime(values.known_at,utc=True,format='mixed')
    days=pd.to_datetime(values.date,format='mixed')
    if stamps.isna().any() or days.isna().any() or days.dt.tz is not None or (stamps.dt.nanosecond!=0).any():
        raise ValueError('Valid dates and database-representable known_at required')
    cutoff=(days.dt.normalize()+pd.Timedelta(days=1)).dt.tz_localize('Asia/Seoul').dt.tz_convert('UTC')
    if (stamps>=cutoff).any():raise ValueError('Reference input became known after formation date')
    frame=pd.DataFrame(dict(reference_id=values.reference_id,definition_hash=values.definition_hash,
                            asset_id=ids.astype('int64'),stock_code=values.stock_code,
                            date=days.dt.strftime('%Y-%m-%d'),
                            known_at=stamps.dt.strftime('%Y-%m-%dT%H:%M:%S.%f').str.rstrip('0').str.rstrip('.')+'+00:00',
                            value=numeric))
    return frame.sort_values(['reference_id','asset_id','date']).to_dict('records')


def build_publication(values, definitions, *, attestation, validation, parity):
    """Freeze publication after input and independent calculation verification."""
    from engine.reference_library import definition_hash
    _validate_source_attestation(attestation)
    _validate_definition_source(attestation,definitions)
    rows=canonical_values(values)
    if parity.get("passed") is not True or parity.get("values_sha256")!=digest(rows):
        raise ValueError("Independent parity must bind exact values")
    defs={d["id"]:d for d in definitions}
    selected={r["reference_id"] for r in rows}
    if not selected.issubset(defs):
        raise ValueError("Published reference missing definition")
    hashes={key:definition_hash(d) for key,d in defs.items()}
    for r in rows:
        if r["definition_hash"]!=hashes[r["reference_id"]]:
            raise ValueError("Definition hash mismatch")
    body={"schema_version":SCHEMA_VERSION,"generation_id":GENERATION,"role":ROLE,
          "source_version":attestation["source_version"],"input_sha256":attestation["input_sha256"],
          "values_sha256":digest(rows),"row_count":len(rows),
          "definitions":{k:defs[k] for k in sorted(selected)},
          "attestation":attestation,"validation":validation,"parity":parity,
          "profitability_approved":False,"legacy_gold_used":False}
    publication={**body,"dataset_id":digest(body)}
    validate_publication(publication,rows)
    return publication,rows


def validate_publication(publication, rows):
    """Consistency gate shared by writer and reader; not external authentication.

    Only the trusted RDS adapter may issue source attestations. A hash alone is
    not evidence that a human-authored certification claim is truthful.
    """
    from engine.reference_library import validate_catalog, definition_hash
    body={k:v for k,v in publication.items() if k!='dataset_id'}
    if digest(body)!=publication.get('dataset_id') or digest(rows)!=publication.get('values_sha256'):
        raise ValueError('Publication or value digest mismatch')
    if (publication.get('schema_version')!=SCHEMA_VERSION or publication.get('generation_id')!=GENERATION
        or publication.get('role')!=ROLE or publication.get('row_count')!=len(rows) or not rows
        or publication.get('profitability_approved') is not False or publication.get('legacy_gold_used') is not False):
        raise ValueError('Invalid publication role/generation/count/approval')
    a,v,p=publication['attestation'],publication['validation'],publication['parity']
    _validate_source_attestation(a)
    _validate_definition_source(a,list(publication['definitions'].values()))
    if (a.get('source_version')!=publication['source_version'] or a.get('input_sha256')!=publication['input_sha256']
        or v.get('source_version')!=a['source_version'] or v.get('input_sha256')!=a['input_sha256']
        or v.get('source_evidence_sha256')!=a.get('evidence_sha256')
        or v.get('role')!='MEASUREMENT_CONTROL' or v.get('alpha_approved') is not False
        or v.get('value_rows')!=len(rows)):
        raise ValueError('Validation provenance/count/role mismatch')
    raw_protocols={
        'INDEPENDENT_PANDAS_NUMPY_FULL_RAW_DAILY':('RDS_CERTIFIED_REFERENCE_FORMULAIC_V1','ALL_PUBLISHED_ASSET_MONTHS_TWO_RAW_DAILY_INTERPRETERS'),
        'INDEPENDENT_VECTOR_SCALAR_FULL_RAW_INPUTS':('RDS_CERTIFIED_REFERENCE_RISK_DIVERSITY_V1','ALL_PUBLISHED_ASSET_MONTHS_VECTOR_VS_SCALAR_RAW_INPUTS'),
    }
    raw_kind=p.get('kind') in raw_protocols
    for sha in (a.get('input_sha256'),a.get('evidence_sha256'),v.get('implementation_sha256'),p.get('oracle_sha256') if raw_kind else p.get('sql_sha256')):
        if not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):
            raise ValueError('Publication provenance requires exact SHA256')
    if raw_kind:
        expected_source,expected_scope=raw_protocols[p['kind']]
        if (a.get('source_type')!=expected_source
            or p.get('passed') is not True or p.get('values_sha256')!=publication['values_sha256']
            or p.get('rows_compared')!=len(rows) or p.get('all_input_null_patterns_compared') is not True
            or p.get('raw_input_sha256')!=a['input_sha256'] or p.get('rtol')!=1e-7 or p.get('atol')!=1e-8
            or p.get('comparison_scope')!=expected_scope):
            raise ValueError('Full raw-daily independent parity incomplete')
    elif (p.get('passed') is not True or p.get('values_sha256')!=publication['values_sha256']
        or p.get('rows_compared')!=len(rows)
        or p.get('atol')!=0 or not isinstance(p.get('rtol'),(int,float)) or not 0<p['rtol']<=1e-10
        or p.get('kind') not in {'INDEPENDENT_POSTGRES_FORMULAS_SAME_ATTESTED_PRICE_FEATURES','INDEPENDENT_SQLITE_FULL_POSTGRES_FIXED_SAMPLE'}):
        raise ValueError('Independent parity binding invalid')
    if p['kind']=='INDEPENDENT_SQLITE_FULL_POSTGRES_FIXED_SAMPLE':
        full,sample=p.get('sqlite_full',{}),p.get('postgres_sample',{})
        if (full.get('passed') is not True or full.get('rows_compared')!=len(rows)
            or full.get('sql_sha256')!=p['sql_sha256'] or sample.get('passed') is not True
            or not sample.get('asset_ids') or sample.get('rows_compared',0)<=0
            or full.get('rtol')!=p['rtol'] or full.get('atol')!=0
            or sample.get('rtol')!=p['rtol'] or sample.get('atol')!=0
            or sample.get('selection')!='TEN_EVENLY_SPACED_SORTED_ASSET_IDS_ALL_MONTHS'):
            raise ValueError('Full/sample independent SQL parity incomplete')
        assets=sorted({row['asset_id'] for row in rows})
        expected=sorted({assets[(len(assets)-1)*i//9] for i in range(10)})
        ids=set(expected);subset=[row for row in rows if row['asset_id'] in ids]
        if (sample['asset_ids']!=expected or sample['rows_compared']!=len(subset)
            or sample.get('values_sha256')!=digest(subset)):
            raise ValueError('PostgreSQL sample does not bind exact declared rows')
    definitions=publication['definitions']; validate_catalog(list(definitions.values()))
    normalized=canonical_values(pd.DataFrame(rows))
    if rows!=normalized or set(definitions)!={r['reference_id'] for r in rows}:
        raise ValueError('Canonical rows/definition set mismatch')
    summaries={s['reference_id']:s for s in v['references']}
    for ref,d in definitions.items():
        expected_definition_hash=definition_hash(d)
        subset=[r for r in rows if r['reference_id']==ref]
        if (d['id']!=ref or d['readiness']['status']!='IMPLEMENTED_REQUIRES_ATTESTATION'
            or any(r['definition_hash']!=expected_definition_hash for r in subset)
            or summaries.get(ref,{}).get('value_rows')!=len(subset)
            or summaries[ref].get('definition_hash')!=expected_definition_hash
            or summaries[ref].get('status')!='MEASUREMENT_VALIDATED'):
            raise ValueError('Definition measurement validation mismatch')
    return publication


def install_schema(conn, *, apply=False):
    if not apply:
        return {"status":"DRY_RUN","ddl_sha256":hashlib.sha256(DDL_PATH.read_bytes()).hexdigest()}
    ddl=DDL_PATH.read_bytes(); sha=hashlib.sha256(ddl).hexdigest()
    with conn.transaction(),conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout='30min'")
        cur.execute("SELECT pg_advisory_xact_lock(7021002001)")
        cur.execute("SELECT to_regclass('gold.reference_schema_version')")
        if cur.fetchone()[0]:
            cur.execute("SELECT ddl_sha256 FROM gold.reference_schema_version WHERE version=%s",(SCHEMA_VERSION,))
            row=cur.fetchone()
            if not row or row[0]!=sha:
                raise ValueError("Existing reference schema version mismatch")
            return {"status":"ALREADY_INSTALLED","ddl_sha256":sha}
        for table in ("reference_definition","reference_dataset","reference_value"):
            cur.execute("SELECT to_regclass(%s)",("gold."+table,))
            if cur.fetchone()[0]:
                raise ValueError("Partial existing reference namespace; refusing replacement")
        cur.execute(ddl.decode())
        cur.execute("INSERT INTO gold.reference_schema_version VALUES (%s,%s)",(SCHEMA_VERSION,sha))
    return {"status":"INSTALLED","ddl_sha256":sha}


def publish(conn, publication, rows, *, apply=False):
    from engine.reference_library import definition_hash
    validate_publication(publication,rows)
    if not apply:
        return {"status":"DRY_RUN","dataset_id":publication["dataset_id"],"row_count":len(rows)}
    with conn.transaction(),conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout='30min'")
        cur.execute("SELECT pg_advisory_xact_lock(7021002001)")
        cur.execute("SELECT metadata FROM gold.reference_dataset WHERE dataset_id=%s",(publication["dataset_id"],))
        existing=cur.fetchone()
        if existing:
            if existing[0]!=publication:
                raise ValueError("Immutable publication collision")
        else:
            for key,d in publication["definitions"].items():
                sha=definition_hash(d)
                cur.execute("SELECT specification FROM gold.reference_definition WHERE generation_id=%s AND reference_id=%s AND definition_sha256=%s",(GENERATION,key,sha))
                found=cur.fetchone()
                if found and found[0]!=d:
                    raise ValueError("Definition collision")
                if not found:
                    cur.execute("INSERT INTO gold.reference_definition VALUES(%s,%s,%s,%s::jsonb,%s)",(GENERATION,key,sha,json.dumps(d),ROLE))
            cur.execute("""INSERT INTO gold.reference_dataset
                (dataset_id,generation_id,source_version,input_sha256,values_sha256,row_count,metadata)
                VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                tuple(publication[k] for k in ("dataset_id","generation_id","source_version","input_sha256","values_sha256","row_count"))+(json.dumps(publication),))
            # Do not transmit constant dataset/definition strings two million
            # times through SSM. Stage compact binary rows and expand constants
            # inside the SAME transaction; immutable Gold triggers still apply.
            from datetime import date,datetime
            mapping={key:i for i,key in enumerate(sorted(publication['definitions']))}
            cur.execute('CREATE TEMP TABLE reference_upload_map (idx smallint PRIMARY KEY,reference_id text,definition_sha256 text) ON COMMIT DROP')
            cur.executemany('INSERT INTO reference_upload_map VALUES (%s,%s,%s)',
                            [(i,key,definition_hash(publication['definitions'][key])) for key,i in mapping.items()])
            cur.execute('''CREATE TEMP TABLE reference_upload (idx smallint,asset_id bigint,stock_code text,
                           as_of_date date,known_at timestamptz,value float8) ON COMMIT DROP''')
            with cur.copy('COPY reference_upload FROM STDIN WITH (FORMAT BINARY)') as copy:
                copy.set_types(['int2','int8','text','date','timestamptz','float8'])
                for n,r in enumerate(rows,1):
                    copy.write_row((mapping[r['reference_id']],r['asset_id'],r['stock_code'],date.fromisoformat(r['date']),
                                    datetime.fromisoformat(r['known_at']),r['value']))
                    if n%250000==0:print(f'Gold staging: {n}/{len(rows)} rows',flush=True)
            print('Gold staging complete; atomic insert and full read-back verification',flush=True)
            cur.execute('''INSERT INTO gold.reference_value
                (dataset_id,generation_id,reference_id,definition_sha256,asset_id,stock_code,as_of_date,known_at,value)
                SELECT %s,%s,m.reference_id,m.definition_sha256,u.asset_id,u.stock_code,u.as_of_date,u.known_at,u.value
                FROM reference_upload u JOIN reference_upload_map m USING(idx)''',(publication['dataset_id'],GENERATION))
        print('Gold rows present; verifying every row with binary chunk hashes',flush=True)
        verification=verify_database_rows(cur,dataset_id=publication['dataset_id'],rows=rows)
    return {"status":"ALREADY_PUBLISHED" if existing else "PUBLISHED","dataset_id":publication["dataset_id"],
            "row_count":len(rows),"reference_count":len(publication["definitions"]),
            **verification,"values_sha256":publication['values_sha256'],"legacy_rows_modified":0,"alpha_approved":False}


def load_library(conn, *, dataset_id, generation_id=GENERATION, snapshot_path=None):
    """Exact immutable dataset, optionally avoiding transfer of all raw DB rows.

    A local parquet is only a transport cache: the database remains mandatory.
    Its exact publication metadata validates every cached row, then every
    persisted DB row is compared through PostgreSQL binary chunk hashes. The
    immutable dataset/value creation contract keeps both reads consistent in
    this transaction; no local metadata or latest/legacy fallback is allowed.
    """
    if generation_id!=GENERATION:
        raise ValueError("Wrong reference generation")
    columns=['reference_id','definition_hash','asset_id','stock_code','date','known_at','value']
    with conn.transaction(),conn.cursor() as cur:
        cur.execute("SELECT metadata FROM gold.reference_dataset WHERE dataset_id=%s AND generation_id=%s",(dataset_id,generation_id))
        found=cur.fetchone()
        if not found:
            raise ValueError("Exact reference dataset not found")
        metadata=found[0]
        if not isinstance(metadata,dict) or metadata.get('dataset_id')!=dataset_id or metadata.get('generation_id')!=generation_id:
            raise ValueError('Reference dataset identity mismatch')
        if snapshot_path is None:
            cur.execute("""SELECT reference_id,definition_sha256 AS definition_hash,asset_id,stock_code,
                as_of_date AS date,known_at,value FROM gold.reference_value WHERE dataset_id=%s AND generation_id=%s
                ORDER BY reference_id,asset_id,as_of_date""",(dataset_id,generation_id))
            result=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
        else:
            import os
            import stat
            path=Path(snapshot_path).absolute()
            if ('..' in path.parts or path.suffix!='.parquet' or not path.is_file()
                    or any(part.is_symlink() for part in (path,*path.parents))):
                raise ValueError('Reference snapshot must be an explicit regular non-symlink parquet file')
            # Open the validated file itself, never follow a replacement symlink.
            fd=os.open(path,os.O_RDONLY | getattr(os,'O_NOFOLLOW',0))
            with os.fdopen(fd,'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError('Reference snapshot is not a regular file')
                cached=pd.read_parquet(stream)
            full_schema=set(columns)|{'market','oriented_value','source_version','input_sha256'}
            if not cached.columns.is_unique or set(cached) not in (set(columns),full_schema):
                raise ValueError('Unknown reference snapshot schema; only Gold rows or library values allowed')
            if set(cached)==full_schema:
                for key in ('source_version','input_sha256'):
                    if cached[key].isna().any() or not cached[key].eq(metadata[key]).all():
                        raise ValueError('Reference snapshot provenance differs from database metadata')
            result=cached.loc[:,columns].copy()
        rows=canonical_values(result)
        validate_publication(metadata,rows)
        if snapshot_path is not None:
            cur.execute("SET LOCAL statement_timeout='30min'")
            verify_database_rows(cur,dataset_id=dataset_id,rows=rows)
    return result,metadata
