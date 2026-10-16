"""Explicit, pure rewrite of one pinned price snapshot query.

No execution, I/O, monkeypatch, or persisted SQL change. Callers must separately
validate real-DB parity and performance; structural checks do not establish them.
"""
from hashlib import sha256


SOURCE_SQL_SHA256 = "e5f7d557794b313fe8ac4d5d009391374027be3e394d05a90afa94d0d0fe8576"
_LATERAL = """    JOIN LATERAL (
        SELECT min(ai.identifier) AS identifier,
               count(*) AS ticker_match_count
        FROM public.asset_identifier ai
        WHERE ai.asset_id = p.asset_id
          AND ai.source = 'KRX'
          AND ai.identifier_type = 'ticker'
          AND ai.valid_from <= p.trade_date
          AND (ai.valid_to IS NULL OR ai.valid_to >= p.trade_date)
    ) i ON true
"""
_TAIL = "FROM monthly\nWHERE month_rank = 1\nORDER BY asset_id, trade_date\n"


def _replace_once(sql, old, new):
    if sql.count(old) != 1:
        raise ValueError("Pinned price query structure must contain each target exactly once")
    return sql.replace(old, new, 1)


def deferred_identity_sql(original_sql: str) -> str:
    """Move only the pinned aggregate lookup after monthly row selection.

    The original aggregate has no GROUP BY/HAVING: even zero matching identifiers
    produces (NULL, 0), preserving downstream missing/overlap failures. All daily
    rows, windows and dataset_start remain upstream. Mapping uses the selected
    trade_date, never the calendar month-end. This is not an arbitrary SQL rewriter.
    """
    if not isinstance(original_sql, str) or sha256(original_sql.encode()).hexdigest() != SOURCE_SQL_SHA256:
        raise ValueError("Unexpected PRICE_SNAPSHOT_SQL SHA256; explicit source review required")
    if original_sql.count("JOIN LATERAL (") != 1:
        raise ValueError("Pinned price query must contain exactly one LATERAL block")
    sql = _replace_once(original_sql, '        i.identifier AS "Code",\n', "")
    sql = _replace_once(sql, "        i.ticker_match_count,\n", "")
    sql = _replace_once(sql, _LATERAL, "")
    sql = _replace_once(sql,
        'SELECT asset_id, "Code", "Name", instrument_type, listed_from, listed_to,\n',
        'SELECT m.asset_id, i.identifier AS "Code", "Name", instrument_type, listed_from, listed_to,\n')
    sql = _replace_once(sql,
        "       quality_run_id, total_return_quality_run_id, ticker_match_count,\n",
        "       quality_run_id, total_return_quality_run_id, i.ticker_match_count,\n")
    moved = _LATERAL.replace("p.asset_id", "m.asset_id").replace("p.trade_date", "m.trade_date")
    return _replace_once(sql, _TAIL,
        "FROM (\n    SELECT * FROM monthly WHERE month_rank = 1\n) m\n"
        + moved + "ORDER BY m.asset_id, m.trade_date\n")
