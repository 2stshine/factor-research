"""RDS Silver read-only access.

Research is downstream of Silver.  This module is the only place that knows the
physical public schema; the rest of the engine works on immutable pandas
snapshots.  Every source row must belong to a CERTIFIED data-quality run.
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from dotenv import load_dotenv


PRICE_SNAPSHOT_SQL = """
WITH certified AS (
    SELECT
        p.asset_id,
        i.identifier AS "Code",
        a.name AS "Name",
        a.instrument_type,
        a.listed_from,
        a.listed_to,
        p.trade_date,
        p.close,
        p.adj_close,
        p.total_return_close,
        p.trading_value,
        p.market_cap,
        p.shares,
        p.market,
        p.quality_run_id,
        avg(p.trading_value) OVER (
            PARTITION BY p.asset_id ORDER BY p.trade_date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS adv20,
        row_number() OVER (
            PARTITION BY p.asset_id ORDER BY p.trade_date
        ) AS age_days,
        min(p.trade_date) OVER (PARTITION BY p.asset_id) AS first_seen
    FROM public.price_daily p
    JOIN public.asset a ON a.asset_id = p.asset_id
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id AND q.status = 'CERTIFIED'
    JOIN LATERAL (
        SELECT ai.identifier
        FROM public.asset_identifier ai
        WHERE ai.asset_id = p.asset_id
          AND ai.source = 'KRX'
          AND ai.identifier_type = 'ticker'
          AND ai.valid_from <= p.trade_date
          AND (ai.valid_to IS NULL OR ai.valid_to >= p.trade_date)
        ORDER BY ai.valid_from DESC
        LIMIT 1
    ) i ON true
    WHERE p.source = 'KRX'
      AND a.exchange = 'KRX'
      AND a.asset_type = 'stock'
      AND p.market IN ('KOSPI', 'KOSDAQ')
), monthly AS (
    SELECT certified.*,
           min(trade_date) OVER () AS dataset_start,
           row_number() OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
               ORDER BY trade_date DESC
           ) AS month_rank
    FROM certified
)
SELECT asset_id, "Code", "Name", instrument_type, listed_from, listed_to,
       trade_date, close, adj_close, total_return_close, trading_value,
       market_cap, shares, market, adv20, age_days, first_seen, dataset_start,
       quality_run_id
FROM monthly
WHERE month_rank = 1
ORDER BY asset_id, trade_date
"""


FUNDAMENTAL_SQL = """
SELECT f.asset_id, f.period_end, f.fiscal_period, f.fs_type,
       f.statement_type, f.available_date, f.available_at,
       f.metric, f.value, f.revision_key, f.quality_run_id
FROM public.fundamental f
JOIN public.asset a ON a.asset_id = f.asset_id
JOIN public.dq_run q
  ON q.run_id = f.quality_run_id AND q.status = 'CERTIFIED'
WHERE f.source = 'DART'
  AND a.exchange = 'KRX'
  AND a.asset_type = 'stock'
  AND f.data_basis = 'STANDARDIZED'
  AND f.unit_type = 'currency'
  AND f.available_date IS NOT NULL
  AND f.metric = ANY(%s)
ORDER BY f.asset_id, f.available_date, f.period_end, f.metric, f.revision_key
"""


APPROVED_VALUES_SQL = """
WITH ranked AS (
    SELECT f.factor_key, v.asset_id, v.as_of_date,
           v.value * coalesce((f.config->>'predicted_sign')::integer, 1) AS value,
           row_number() OVER (
               PARTITION BY f.factor_id, v.asset_id,
                            date_trunc('month', v.as_of_date)
               ORDER BY v.as_of_date DESC
           ) AS month_rank
    FROM gold.factor f
    JOIN gold.factor_value v ON v.factor_id = f.factor_id
    WHERE f.status = 'APPROVED'
)
SELECT factor_key, asset_id, as_of_date, value
FROM ranked
WHERE month_rank = 1
ORDER BY factor_key, asset_id, as_of_date
"""


GOLD_TRIAL_HISTORY_SQL = """
SELECT coalesce(
           nullif(btrim(config->>'research_definition_hash'), ''),
           implementation_hash
       ) AS definition_hash,
       CASE WHEN (evaluation->'metrics'->>'net_ir') ~ '^-?[0-9]+([.][0-9]+)?$'
            THEN (evaluation->'metrics'->>'net_ir')::double precision END AS net_ir,
       CASE WHEN (evaluation->'metrics'->>'hac_pvalue') ~ '^[0-9]+([.][0-9]+)?([eE]-?[0-9]+)?$'
            THEN (evaluation->'metrics'->>'hac_pvalue')::double precision END AS hac_pvalue
FROM gold.factor
WHERE coalesce(
          nullif(btrim(config->>'research_definition_hash'), ''),
          implementation_hash
      ) IS NOT NULL
ORDER BY factor_id
"""


def _load_environment() -> None:
    """Load local configuration without overriding injected production secrets."""
    load_dotenv(override=False)
    configured = os.environ.get("TEAMALPHA_DATA_DIR")
    if configured:
        data_repo = Path(configured).expanduser()
    else:
        data_repo = Path(__file__).resolve().parents[2] / "TeamAlpha-data"
    load_dotenv(data_repo / ".env", override=False)


def database_url() -> str:
    _load_environment()
    secret_id = os.environ.get("SILVER_DB_SECRET_ID")
    if secret_id:
        import boto3

        profile = os.environ.get("AWS_PROFILE")
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        secret = session.client("secretsmanager").get_secret_value(SecretId=secret_id)
        payload = json.loads(secret["SecretString"])
        url = payload.get("SILVER_DB_URL")
        if not url:
            raise SystemExit(f"Secrets Manager {secret_id!r}에 SILVER_DB_URL이 없습니다")
        return url
    url = os.environ.get("SILVER_DB_URL")
    if not url:
        raise SystemExit(
            "SILVER_DB_URL이 필요합니다. RDS가 터널 뒤에 있으면 먼저 터널을 여세요."
        )
    return url


def connect(*, read_only: bool = True):
    """Connect with bounded network waits; research never mutates public Silver."""
    conninfo = database_url()
    host_override = os.environ.get("SILVER_DB_HOST_OVERRIDE")
    port_override = os.environ.get("SILVER_DB_PORT_OVERRIDE")
    if host_override or port_override:
        overrides = {}
        if host_override:
            overrides["host"] = host_override
        if port_override:
            overrides["port"] = int(port_override)
        conninfo = psycopg.conninfo.make_conninfo(conninfo, **overrides)
    conn = psycopg.connect(
        conninfo,
        connect_timeout=15,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
        tcp_user_timeout=60_000,
    )
    conn.read_only = read_only
    return conn


def read_frame(conn, sql: str, params: Any = None, *, chunk_size: int = 50_000) -> pd.DataFrame:
    """Read a query in bounded chunks without relying on pandas' DBAPI adapter."""
    frames: list[pd.DataFrame] = []
    with conn.cursor() as cur:
        cur.execute(sql, params)
        columns = [d.name for d in cur.description]
        while rows := cur.fetchmany(chunk_size):
            frames.append(pd.DataFrame.from_records(rows, columns=columns))
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


def load_price_snapshot(conn) -> pd.DataFrame:
    return read_frame(conn, PRICE_SNAPSHOT_SQL)


def load_fundamentals(conn, metrics: list[str] | tuple[str, ...]) -> pd.DataFrame:
    return read_frame(conn, FUNDAMENTAL_SQL, (list(metrics),))


def load_approved_values(conn) -> pd.DataFrame:
    try:
        return read_frame(conn, APPROVED_VALUES_SQL)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return pd.DataFrame(columns=["factor_key", "asset_id", "as_of_date", "value"])


def load_gold_trial_history(conn) -> pd.DataFrame:
    try:
        return read_frame(conn, GOLD_TRIAL_HISTORY_SQL)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return pd.DataFrame(columns=["definition_hash", "net_ir", "hac_pvalue"])
