"""RDS Silver read-only access.

Research is downstream of Silver.  This module is the only place that knows the
physical public schema; the rest of the engine works on immutable pandas
snapshots.  Every source row must belong to a CERTIFIED data-quality run.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
from dotenv import load_dotenv


TOTAL_RETURN_METHOD = "krx_gross_dividend_reinvested_v1"
ASSET_IDENTITY_CONTRACT = "krx_month_end_asset_ticker_v1"
ASSET_IDENTITY_META_KEYS = (
    "asset_identity_contract",
    "asset_identity_digest",
    "asset_identity_row_count",
    "asset_identity_asset_count",
    "asset_identity_month_count",
    "asset_identity_cutoff",
)


TOTAL_RETURN_CONTRACT_SQL = """
SELECT source, asset_type, field_name, methodology_version,
       dividend_treatment, status, coverage_start, coverage_end,
       quality_run_id, metadata, certified_at
FROM public.price_return_contract
WHERE source = 'KRX'
  AND asset_type = 'stock'
  AND field_name = 'total_return_close'
"""


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
        i.ticker_match_count,
        lag(p.total_return_close) OVER (
            PARTITION BY p.asset_id ORDER BY p.trade_date
        ) AS prior_total_return_close,
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
        SELECT min(ai.identifier) AS identifier,
               count(*) AS ticker_match_count
        FROM public.asset_identifier ai
        WHERE ai.asset_id = p.asset_id
          AND ai.source = 'KRX'
          AND ai.identifier_type = 'ticker'
          AND ai.valid_from <= p.trade_date
          AND (ai.valid_to IS NULL OR ai.valid_to >= p.trade_date)
    ) i ON true
    WHERE p.source = 'KRX'
      AND a.exchange = 'KRX'
      AND a.asset_type = 'stock'
      AND p.market IN ('KOSPI', 'KOSDAQ')
), daily_returns AS (
    SELECT certified.*,
           CASE
               WHEN prior_total_return_close > 0
                    AND total_return_close > 0
               THEN total_return_close / prior_total_return_close - 1
           END AS daily_total_return
    FROM certified
), daily_features AS (
    SELECT daily_returns.*,
           avg(abs(daily_total_return) / trading_value) FILTER (
               WHERE daily_total_return IS NOT NULL
                 AND trading_value > 0
           ) OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
           ) AS amihud_illiquidity_1m,
           count(daily_total_return) FILTER (
               WHERE trading_value > 0
           ) OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
           ) AS amihud_observations_1m,
           stddev_samp(daily_total_return) OVER (
               PARTITION BY asset_id ORDER BY trade_date
               ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
           ) AS daily_volatility_252d,
           count(daily_total_return) OVER (
               PARTITION BY asset_id ORDER BY trade_date
               ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
           ) AS daily_return_observations_252d,
           max(daily_total_return) OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
           ) AS max_daily_return_1m,
           count(daily_total_return) OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
           ) AS max_daily_return_observations_1m,
           max(adj_close) OVER (
               PARTITION BY asset_id ORDER BY trade_date
               ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
           ) AS price_high_252d,
           count(adj_close) OVER (
               PARTITION BY asset_id ORDER BY trade_date
               ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
           ) AS price_high_observations_252d
    FROM daily_returns
), monthly AS (
    SELECT daily_features.*,
           min(trade_date) OVER () AS dataset_start,
           row_number() OVER (
               PARTITION BY asset_id, date_trunc('month', trade_date)
               ORDER BY trade_date DESC
           ) AS month_rank
    FROM daily_features
)
SELECT asset_id, "Code", "Name", instrument_type, listed_from, listed_to,
       trade_date, close, adj_close, total_return_close, trading_value,
       market_cap, shares, market, adv20, age_days, first_seen, dataset_start,
       quality_run_id, ticker_match_count,
       amihud_illiquidity_1m, amihud_observations_1m,
       daily_volatility_252d, daily_return_observations_252d,
       max_daily_return_1m, max_daily_return_observations_1m,
       price_high_252d, price_high_observations_252d
FROM monthly
WHERE month_rank = 1
ORDER BY asset_id, trade_date
"""


ASSET_IDENTITY_SQL = """
WITH monthly AS (
    SELECT p.asset_id,
           p.trade_date,
           row_number() OVER (
               PARTITION BY p.asset_id, date_trunc('month', p.trade_date)
               ORDER BY p.trade_date DESC
           ) AS month_rank
    FROM public.price_daily p
    JOIN public.asset a ON a.asset_id = p.asset_id
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id AND q.status = 'CERTIFIED'
    WHERE p.source = 'KRX'
      AND a.exchange = 'KRX'
      AND a.asset_type = 'stock'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND (%s::date IS NULL OR p.trade_date <= %s::date)
), month_end AS (
    SELECT asset_id, trade_date
    FROM monthly
    WHERE month_rank = 1
), identified AS (
    SELECT m.asset_id,
           m.trade_date,
           min(ai.identifier) AS "Code",
           count(ai.identifier) AS ticker_match_count
    FROM month_end m
    LEFT JOIN public.asset_identifier ai
      ON ai.asset_id = m.asset_id
     AND ai.source = 'KRX'
     AND ai.identifier_type = 'ticker'
     AND ai.valid_from <= m.trade_date
     AND (ai.valid_to IS NULL OR ai.valid_to >= m.trade_date)
    GROUP BY m.asset_id, m.trade_date
)
SELECT asset_id, "Code", trade_date, ticker_match_count
FROM identified
ORDER BY trade_date, asset_id, "Code"
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
"""


DIVIDEND_HISTORY_SQL = """
WITH current_contract AS (
    SELECT quality_run_id,
           metadata->>'resolution_version' AS resolution_version,
           (metadata->>'action_snapshot_run_id')::uuid AS action_snapshot_run_id
    FROM public.price_return_contract
    WHERE source = 'KRX'
      AND asset_type = 'stock'
      AND field_name = 'total_return_close'
      AND methodology_version = 'krx_gross_dividend_reinvested_v1'
      AND status = 'CERTIFIED'
      AND certified_at IS NOT NULL
      AND metadata->>'resolution_version' IS NOT NULL
      AND metadata->>'action_snapshot_run_id' IS NOT NULL
)
SELECT r.asset_id, r.source, r.action_key, r.resolution_version,
       ca.announcement_date, r.applied_trade_date,
       r.adjusted_cash_amount, r.quality_run_id
FROM current_contract c
JOIN public.dividend_event_resolution r
  ON r.quality_run_id = c.quality_run_id
 AND r.resolution_version = c.resolution_version
JOIN public.corporate_action ca
  ON ca.asset_id = r.asset_id
 AND ca.source = r.source
 AND ca.action_key = r.action_key
 AND ca.quality_run_id = c.action_snapshot_run_id
JOIN public.asset a ON a.asset_id = r.asset_id
JOIN public.dq_run resolution_q
  ON resolution_q.run_id = r.quality_run_id
 AND resolution_q.status = 'CERTIFIED'
JOIN public.dq_run action_q
  ON action_q.run_id = ca.quality_run_id
 AND action_q.status = 'CERTIFIED'
WHERE r.is_canonical IS TRUE
  AND r.excluded_reason IS NULL
  AND r.applied_trade_date IS NOT NULL
  AND r.adjusted_cash_amount > 0
  AND ca.announcement_date IS NOT NULL
  AND ca.source = 'DART_DISCLOSURE'
  AND ca.action_type = 'cash_dividend'
  AND ca.action_scope = 'ISSUER'
  AND a.exchange = 'KRX'
  AND a.asset_type = 'stock'
ORDER BY r.asset_id, r.applied_trade_date, r.action_key
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


APPROVED_FACTOR_KEYS_SQL = """
SELECT DISTINCT factor_key
FROM gold.factor
WHERE status = 'APPROVED'
ORDER BY factor_key
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
    if read_only:
        # Identity validation and every dependent query must observe one RDS
        # snapshot even if Silver is rebuilt concurrently.
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
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


def _identity_cutoff(value: Any) -> pd.Timestamp:
    try:
        cutoff = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"asset identity cutoff 날짜가 잘못되었습니다: {value!r}") from exc
    if pd.isna(cutoff):
        raise ValueError("asset identity cutoff은 비어 있을 수 없습니다")
    if cutoff.tzinfo is not None:
        cutoff = cutoff.tz_convert("UTC").tz_localize(None)
    return cutoff.normalize()


def asset_identity_evidence(
    frame: pd.DataFrame, *, cutoff: Any | None = None,
) -> dict[str, Any]:
    """Return the canonical PIT month-end ``asset_id``/ticker identity digest.

    The digest hashes only JSON rows of ``[date ISO, asset_id integer, Code
    exact text]`` in deterministic order.  No numeric conversion, padding, or
    trimming is permitted for ``Code`` because those transformations can hide
    an asset remap.
    """
    required = {"asset_id", "Code", "trade_date"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            f"asset identity 필수 컬럼 누락: {sorted(missing)}"
        )

    scoped = frame.loc[:, ["asset_id", "Code", "trade_date"]].copy()
    if scoped.empty:
        raise RuntimeError("asset identity 월말 스냅샷 행이 없습니다")
    dates = pd.to_datetime(scoped["trade_date"], errors="coerce")
    if dates.isna().any():
        raise RuntimeError(
            "asset identity trade_date가 비었거나 날짜가 아닙니다: "
            f"{int(dates.isna().sum()):,}행"
        )
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_convert("UTC").dt.tz_localize(None)
    scoped["trade_date"] = dates.dt.normalize()

    requested_cutoff = (
        _identity_cutoff(cutoff)
        if cutoff is not None
        else scoped["trade_date"].max()
    )
    scoped = scoped.loc[scoped["trade_date"] <= requested_cutoff].copy()
    if scoped.empty:
        raise RuntimeError(
            "asset identity cutoff 이내의 월말 스냅샷 행이 없습니다: "
            f"cutoff={requested_cutoff.date().isoformat()}"
        )

    raw_codes = scoped["Code"]
    bad_code = raw_codes.map(
        lambda value: (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or "\x00" in value
        )
    )
    if bad_code.any():
        sample = raw_codes.loc[bad_code].head(3).tolist()
        raise RuntimeError(
            "asset identity Code는 공백 없는 정확한 문자열이어야 합니다; "
            f"숫자 변환·zero-padding은 허용하지 않습니다: sample={sample!r}"
        )

    numeric_ids = pd.to_numeric(scoped["asset_id"], errors="coerce")
    finite_ids = numeric_ids.map(
        lambda value: False if pd.isna(value) else math.isfinite(float(value))
    )
    bad_id = (
        numeric_ids.isna()
        | ~finite_ids
        | numeric_ids.mod(1).ne(0)
        | numeric_ids.lt(0)
    )
    if bad_id.any():
        sample = scoped.loc[bad_id, "asset_id"].head(3).tolist()
        raise RuntimeError(
            "asset identity asset_id는 0 이상의 정수여야 합니다: "
            f"sample={sample!r}"
        )
    scoped["asset_id"] = numeric_ids.astype("int64")
    scoped["ym"] = scoped["trade_date"].dt.to_period("M")

    duplicated_asset = scoped.duplicated(["asset_id", "ym"], keep=False)
    if duplicated_asset.any():
        sample = scoped.loc[
            duplicated_asset, ["asset_id", "trade_date", "Code"]
        ].head(4).to_dict("records")
        raise RuntimeError(
            "asset identity (asset_id, month)가 중복되었습니다: "
            f"sample={sample}"
        )
    duplicated_code = scoped.duplicated(["Code", "ym"], keep=False)
    if duplicated_code.any():
        sample = scoped.loc[
            duplicated_code, ["asset_id", "trade_date", "Code"]
        ].head(4).to_dict("records")
        raise RuntimeError(
            "asset identity (Code, month)가 중복되었습니다: "
            f"sample={sample}"
        )

    scoped = scoped.sort_values(
        ["trade_date", "asset_id", "Code"], kind="mergesort"
    )
    digest = hashlib.sha256()
    for row in scoped.itertuples(index=False):
        digest.update(json.dumps(
            [row.trade_date.date().isoformat(), int(row.asset_id), row.Code],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"))
        digest.update(b"\n")

    return {
        "asset_identity_contract": ASSET_IDENTITY_CONTRACT,
        "asset_identity_digest": digest.hexdigest(),
        "asset_identity_row_count": int(len(scoped)),
        "asset_identity_asset_count": int(scoped["asset_id"].nunique()),
        "asset_identity_month_count": int(scoped["ym"].nunique()),
        "asset_identity_cutoff": requested_cutoff.date().isoformat(),
    }


def _check_ticker_match_counts(frame: pd.DataFrame) -> None:
    if "ticker_match_count" not in frame.columns:
        return
    counts = pd.to_numeric(frame["ticker_match_count"], errors="coerce")
    invalid = counts.ne(1) | counts.isna()
    if invalid.any():
        columns = [
            column for column in
            ("asset_id", "trade_date", "Code", "ticker_match_count")
            if column in frame.columns
        ]
        sample = frame.loc[invalid, columns].head(5).to_dict("records")
        raise RuntimeError(
            "Silver PIT ticker는 각 (asset_id, trade_date)에 정확히 하나여야 "
            f"합니다. 누락 또는 유효기간 중첩: sample={sample}"
        )


def load_asset_identity_snapshot(
    conn, *, cutoff: Any | None = None,
) -> pd.DataFrame:
    """Load and validate the live RDS month-end PIT identity at ``cutoff``."""
    normalized = _identity_cutoff(cutoff) if cutoff is not None else None
    parameter = None if normalized is None else normalized.date().isoformat()
    frame = read_frame(conn, ASSET_IDENTITY_SQL, (parameter, parameter))
    _check_ticker_match_counts(frame)
    evidence = asset_identity_evidence(frame, cutoff=normalized)
    frame.attrs["asset_identity"] = evidence
    return frame


def verify_live_asset_identity(
    conn, expected: dict[str, Any], *, cutoff: Any | None = None,
) -> dict[str, Any]:
    """Fail closed when live RDS identity differs from bound panel evidence."""
    missing = [key for key in ASSET_IDENTITY_META_KEYS if key not in expected]
    if missing:
        raise RuntimeError(
            f"예상 asset identity 계약 메타데이터가 없습니다: {missing}"
        )
    expected_cutoff = _identity_cutoff(expected["asset_identity_cutoff"])
    if cutoff is not None and _identity_cutoff(cutoff) != expected_cutoff:
        raise RuntimeError(
            "asset identity 검증 cutoff와 패널 계약 cutoff가 다릅니다: "
            f"requested={_identity_cutoff(cutoff).date().isoformat()}, "
            f"bound={expected_cutoff.date().isoformat()}"
        )
    live = load_asset_identity_snapshot(conn, cutoff=expected_cutoff)
    actual = live.attrs["asset_identity"]
    mismatches = {
        key: {"expected": expected[key], "actual": actual[key]}
        for key in ASSET_IDENTITY_META_KEYS
        if str(expected[key]) != str(actual[key])
    }
    if mismatches:
        raise RuntimeError(
            "현재 RDS의 asset_id↔ticker PIT identity가 패널 계약과 "
            f"다릅니다: {mismatches}"
        )
    return actual


def load_price_snapshot(conn) -> pd.DataFrame:
    try:
        contract = read_frame(conn, TOTAL_RETURN_CONTRACT_SQL)
    except psycopg.errors.UndefinedTable as exc:
        conn.rollback()
        raise RuntimeError(
            "Silver 총수익 계약 테이블이 없습니다. 배당 총수익 migration과 "
            "인증 rebuild를 먼저 완료하세요."
        ) from exc
    if len(contract) != 1:
        raise RuntimeError(
            "KRX stock total_return_close 계약은 정확히 한 행이어야 합니다: "
            f"rows={len(contract)}"
        )
    row = contract.iloc[0]
    if (
        row["status"] != "CERTIFIED"
        or row["methodology_version"] != TOTAL_RETURN_METHOD
        or pd.isna(row["certified_at"])
    ):
        raise RuntimeError(
            "Silver total_return_close가 배당 포함 총수익으로 인증되지 않았습니다: "
            f"status={row['status']}, method={row['methodology_version']}"
        )
    prices = read_frame(conn, PRICE_SNAPSHOT_SQL)
    _check_ticker_match_counts(prices)
    prices.attrs["asset_identity"] = asset_identity_evidence(prices)
    prices.attrs["return_contract"] = {
        key: (None if pd.isna(value) else str(value))
        for key, value in row.to_dict().items()
    }
    return prices


def load_fundamentals(conn, metrics: list[str] | tuple[str, ...]) -> pd.DataFrame:
    # ``materialize_pit`` performs its own deterministic local sort.  Asking
    # RDS to sort the complete revision ledger first only prolongs the SSM
    # session and can make an otherwise read-only build fail on tunnel expiry.
    return read_frame(conn, FUNDAMENTAL_SQL, (list(metrics),))


def load_dividend_history(conn) -> pd.DataFrame:
    """Load only dividends used by the current certified KRX return build.

    The resolution run and version are taken from the same contract that
    certifies ``total_return_close``.  A stale action audit can therefore
    never be mixed with a newer price-return snapshot.
    """
    try:
        contract = read_frame(conn, TOTAL_RETURN_CONTRACT_SQL)
    except psycopg.errors.UndefinedTable as exc:
        conn.rollback()
        raise RuntimeError(
            "Silver 배당 총수익 계약 테이블이 없습니다. 인증 rebuild를 먼저 "
            "완료하세요."
        ) from exc
    if len(contract) != 1:
        raise RuntimeError(
            "KRX stock total_return_close 계약은 정확히 한 행이어야 합니다: "
            f"rows={len(contract)}"
        )
    row = contract.iloc[0]
    metadata = row.get("metadata")
    if (
        row["status"] != "CERTIFIED"
        or row["methodology_version"] != TOTAL_RETURN_METHOD
        or pd.isna(row["certified_at"])
        or pd.isna(row["coverage_start"])
        or pd.isna(row["coverage_end"])
        or not isinstance(metadata, dict)
        or not metadata.get("resolution_version")
        or not metadata.get("action_snapshot_run_id")
    ):
        raise RuntimeError(
            "Silver 배당 이력이 인증된 총수익 계약에 묶여 있지 않습니다: "
            f"status={row['status']}, method={row['methodology_version']}"
        )
    try:
        dividends = read_frame(conn, DIVIDEND_HISTORY_SQL)
    except psycopg.errors.UndefinedTable as exc:
        conn.rollback()
        raise RuntimeError(
            "Silver 배당 resolution 테이블이 없습니다. 인증 rebuild를 먼저 "
            "완료하세요."
        ) from exc
    dividends.attrs["return_contract"] = {
        key: (None if pd.isna(value) else str(value))
        for key, value in row.to_dict().items()
    }
    return dividends


def load_approved_values(conn) -> pd.DataFrame:
    try:
        return read_frame(conn, APPROVED_VALUES_SQL)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return pd.DataFrame(columns=["factor_key", "asset_id", "as_of_date", "value"])


def load_approved_factor_keys(conn) -> list[str]:
    """Return the APPROVED catalog even when a factor has no value rows.

    T5 must fail closed when approved metadata exists without enough comparable
    history.  Deriving the catalog from ``factor_value`` would silently turn an
    empty or partially loaded approved factor into "no approved factors".
    """
    try:
        frame = read_frame(conn, APPROVED_FACTOR_KEYS_SQL)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return []
    return sorted({str(value) for value in frame["factor_key"].dropna()})


def load_gold_trial_history(conn) -> pd.DataFrame:
    try:
        return read_frame(conn, GOLD_TRIAL_HISTORY_SQL)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return pd.DataFrame(columns=["definition_hash", "net_ir", "hac_pvalue"])
