"""Independent, read-only PostgreSQL diagnostics for v2 FLOW materialization.

Only raw revision rows and asset/date/metric targets are parameters. PostgreSQL
performs revision selection, missing-value barriers, chronological FY residual
derivation and TTM calculation itself. No Python-computed financial values are
passed into the query. This is not a replacement Gold implementation or a
certification of source fiscal calendars. Stock and SUE calculations are outside
this diagnostic's scope.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime
from numbers import Number

from engine.fundamentals import FLOW, FUNDAMENTAL_METHODOLOGY_VERSION


SQL_DIAGNOSTIC_VERSION = "dart-pit-quarter-sql-diagnostic-v2"


def _continuity_select(records_expression: str) -> str:
    """SQL-only counterpart of the declared endpoint/label/finite contract.

    Expressions passed here are internal SQL identifiers, never user input.
    """
    return f"""
WITH points AS (
    SELECT point.ordinality::integer AS position,
           (point.value->>'period_end')::timestamp AS period_end,
           point.value->>'fiscal_period' AS fiscal_period,
           (point.value->>'value')::double precision AS amount
    FROM jsonb_array_elements({records_expression})
         WITH ORDINALITY AS point(value, ordinality)
), ordered AS (
    SELECT *, lag(period_end) OVER (ORDER BY position) AS previous_end,
           lag(fiscal_period) OVER (ORDER BY position) AS previous_label
    FROM points
), basis AS (
    SELECT max(period_end) FILTER (WHERE position = 1) AS first_end,
           bool_and(period_end::date =
             (date_trunc('month', period_end) + interval '1 month - 1 day')::date
           ) AS all_month_end
    FROM points
)
SELECT coalesce(
    count(*) BETWEEN 2 AND 5
    AND count(period_end) = count(*) AND count(amount) = count(*)
    AND bool_and(amount::text NOT IN ('NaN', 'Infinity', '-Infinity'))
    AND bool_and(fiscal_period IN ('Q1', 'Q2', 'Q3', 'Q4'))
    AND bool_and(position = 1 OR (
        period_end > previous_end AND fiscal_period = CASE previous_label
            WHEN 'Q1' THEN 'Q2' WHEN 'Q2' THEN 'Q3'
            WHEN 'Q3' THEN 'Q4' WHEN 'Q4' THEN 'Q1' END
    ))
    AND (
        bool_and(period_end = CASE WHEN basis.all_month_end THEN
            date_trunc('month', basis.first_end)
            + make_interval(months => 3 * (position - 1) + 1)
            - interval '1 day'
            + (basis.first_end - date_trunc('day', basis.first_end))
          ELSE basis.first_end + make_interval(months => 3 * (position - 1)) END
        )
        OR (
            bool_and(extract(isodow FROM period_end) = extract(isodow FROM basis.first_end))
            AND bool_and(position = 1 OR
                floor(extract(epoch FROM period_end - previous_end) / 86400) IN (91, 98))
            AND count(*) FILTER (WHERE position > 1 AND
                floor(extract(epoch FROM period_end - previous_end) / 86400) = 98) <= 1
        )
    ), false) AS passed
FROM ordered CROSS JOIN basis
"""


CONTIGUITY_SQL = _continuity_select("%s::jsonb")


# Each recursive step replaces only the current FY endpoint in a target's
# standalone-quarter state. This independently reproduces the requirement that
# an unresolved FY is a barrier when processing subsequent fiscal years.
FLOW_TTM_SQL = f"""
WITH RECURSIVE input_rows AS (
    SELECT * FROM jsonb_to_recordset(%s::jsonb) AS row(
        asset_id bigint, period_end timestamp, fiscal_period text, fs_type text,
        available_date timestamp, metric text, value double precision, revision_key text
    )
), targets AS (
    SELECT * FROM jsonb_to_recordset(%s::jsonb) AS target(
        target_id integer, asset_id bigint, as_of_date timestamp, metric text
    )
), ranked AS (
    SELECT target.target_id, row.*,
           row_number() OVER (
               PARTITION BY target.target_id, row.period_end, row.fiscal_period
               ORDER BY (row.fs_type = 'CFS') DESC,
                        row.available_date DESC, row.revision_key COLLATE "C" DESC
           ) AS revision_rank
    FROM targets target JOIN input_rows row
      ON row.asset_id = target.asset_id AND row.metric = target.metric
     AND row.available_date <= target.as_of_date
), selected AS (
    SELECT * FROM ranked WHERE revision_rank = 1
), direct_points AS (
    SELECT target_id, period_end,
           CASE WHEN count(*) = 1
                     AND bool_and(fiscal_period IN ('Q1', 'Q2', 'Q3', 'Q4'))
                THEN min(fiscal_period) ELSE 'INVALID' END AS fiscal_period,
           CASE WHEN count(*) = 1
                     AND bool_and(fiscal_period IN ('Q1', 'Q2', 'Q3', 'Q4'))
                THEN min(value) ELSE NULL END AS value
    FROM selected WHERE fiscal_period <> 'FY'
    GROUP BY target_id, period_end
), initial_state AS (
    SELECT target.target_id, coalesce(jsonb_object_agg(
               point.period_end::text, jsonb_build_object(
                   'period_end', point.period_end, 'fiscal_period', point.fiscal_period,
                   'value', point.value
               )
           ) FILTER (WHERE point.period_end IS NOT NULL), '{{}}'::jsonb) AS state
    FROM targets target LEFT JOIN direct_points point USING (target_id)
    GROUP BY target.target_id
), fiscal_years AS (
    SELECT target_id, period_end, value,
           row_number() OVER (PARTITION BY target_id ORDER BY period_end)::integer AS step
    FROM selected WHERE fiscal_period = 'FY'
), replay(target_id, step, previous_fy, state) AS (
    SELECT target_id, 0, NULL::timestamp, state FROM initial_state
    UNION ALL
    SELECT prior_state.target_id, fiscal_year.step, fiscal_year.period_end,
           CASE WHEN explicit.record->>'fiscal_period' = 'Q4' THEN prior_state.state
                ELSE prior_state.state || jsonb_build_object(
                    fiscal_year.period_end::text,
                    jsonb_build_object(
                        'period_end', fiscal_year.period_end,
                        'fiscal_period', CASE WHEN decision.valid THEN 'Q4' ELSE 'INVALID' END,
                        'value', CASE WHEN decision.valid
                                      THEN fiscal_year.value - preceding.total ELSE NULL END
                    )
                ) END
    FROM replay prior_state
    JOIN fiscal_years fiscal_year
      ON fiscal_year.target_id = prior_state.target_id AND fiscal_year.step = prior_state.step + 1
    CROSS JOIN LATERAL (
        SELECT prior_state.state->fiscal_year.period_end::text AS record
    ) explicit
    CROSS JOIN LATERAL (
        SELECT coalesce(jsonb_agg(point.record ORDER BY point.period_end), '[]'::jsonb) AS records,
               array_agg(point.record->>'fiscal_period' ORDER BY point.period_end) AS labels,
               sum((point.record->>'value')::double precision) AS total
        FROM (
            SELECT item.value AS record, (item.value->>'period_end')::timestamp AS period_end
            FROM jsonb_each(prior_state.state) item
            WHERE (item.value->>'period_end')::timestamp < fiscal_year.period_end
            ORDER BY (item.value->>'period_end')::timestamp DESC LIMIT 3
        ) point
    ) preceding
    CROSS JOIN LATERAL (
        SELECT preceding.records || jsonb_build_array(jsonb_build_object(
            'period_end', fiscal_year.period_end, 'fiscal_period', 'Q4', 'value', fiscal_year.value
        )) AS records
    ) chain
    CROSS JOIN LATERAL (
        SELECT CASE WHEN prior_state.previous_fy IS NULL THEN chain.records ELSE
            jsonb_build_array(jsonb_build_object(
                'period_end', prior_state.previous_fy, 'fiscal_period', 'Q4', 'value', 0.0
            )) || chain.records END AS records
    ) boundary_chain
    CROSS JOIN LATERAL ({_continuity_select('chain.records')}) continuity
    CROSS JOIN LATERAL ({_continuity_select('boundary_chain.records')}) boundary_continuity
    CROSS JOIN LATERAL (
        SELECT coalesce(explicit.record IS NULL
              AND preceding.labels = ARRAY['Q1', 'Q2', 'Q3']::text[]
              AND continuity.passed AND boundary_continuity.passed, false) AS valid
    ) decision
), final_state AS (
    SELECT DISTINCT ON (target_id) target_id, state
    FROM replay ORDER BY target_id, step DESC
)
SELECT target.target_id, target.asset_id, target.as_of_date, target.metric,
       (recent.records->-1->>'period_end')::timestamp AS latest_period_end,
       recent.records->-1->>'fiscal_period' AS latest_fiscal_period,
       (recent.records->-1->>'value')::double precision AS standalone_value,
       jsonb_array_length(recent.records) AS quarter_count,
       (jsonb_array_length(recent.records) = 4 AND continuity.passed) AS contiguous_four_quarters,
       CASE WHEN jsonb_array_length(recent.records) = 4 AND continuity.passed
            THEN recent.total ELSE NULL END AS ttm_value,
       recent.records AS recent_quarters
FROM targets target JOIN final_state USING (target_id)
CROSS JOIN LATERAL (
    SELECT coalesce(jsonb_agg(point.record ORDER BY point.period_end), '[]'::jsonb) AS records,
           sum((point.record->>'value')::double precision) AS total
    FROM (
        SELECT item.value AS record, (item.value->>'period_end')::timestamp AS period_end
        FROM jsonb_each(final_state.state) item
        ORDER BY (item.value->>'period_end')::timestamp DESC LIMIT 4
    ) point
) recent
CROSS JOIN LATERAL ({_continuity_select('recent.records')}) continuity
ORDER BY target.target_id
"""


def sql_sha256() -> str:
    """Digest the actual complete SQL text sent for the full FLOW diagnostic."""
    return hashlib.sha256(FLOW_TTM_SQL.encode("utf-8")).hexdigest()


def _timestamp(value, label: str) -> str:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Invalid {label}") from exc
    elif isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time())
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise ValueError(f"{label} must be a naive source date/timestamp")
    return value.isoformat()


def _asset_id(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= 2**63 - 1:
        raise ValueError("asset_id must be a positive signed-bigint integer")
    return value


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be nonempty text")
    return value


def _amount(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Number):
        raise ValueError("value must be a finite number or explicit null")
    try:
        amount = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("value must be a finite number or explicit null") from exc
    if not math.isfinite(amount):
        raise ValueError("Nonfinite JSON values are unsupported; use explicit null for missing input")
    return amount


def _point(row: dict) -> dict:
    required = {"period_end", "fiscal_period", "value"}
    if not isinstance(row, dict) or not required.issubset(row):
        raise ValueError("Quarter point requires period_end, fiscal_period and value")
    return {"period_end": _timestamp(row["period_end"], "period_end"),
            "fiscal_period": _text(row["fiscal_period"], "fiscal_period"),
            "value": _amount(row["value"])}


def continuity_parameters(points: list[dict]) -> tuple[str]:
    """Serialize observations only; do not compute a contiguity answer."""
    return (json.dumps([_point(point) for point in points], allow_nan=False),)


def flow_ttm_parameters(rows: list[dict], targets: list[dict]) -> tuple[str, str]:
    """Validate/serialize raw fixture inputs without selecting or deriving rows.

    Ambiguous identical-priority revision duplicates are rejected rather than
    assigning PostgreSQL's unspecified tie order a parity meaning. The query
    currently supports FLOW metrics, naive timestamps and finite/null inputs.
    """
    normalized_rows = []
    revision_keys = set()
    for row in rows:
        required = {"asset_id", "period_end", "fiscal_period", "fs_type",
                    "available_date", "metric", "value", "revision_key"}
        if not isinstance(row, dict) or not required.issubset(row):
            raise ValueError("Raw revision row is missing required fields")
        point = _point(row)
        item = {**point, "asset_id": _asset_id(row["asset_id"]),
                "fs_type": _text(row["fs_type"], "fs_type"),
                "available_date": _timestamp(row["available_date"], "available_date"),
                "metric": _text(row["metric"], "metric"),
                "revision_key": _text(row["revision_key"], "revision_key")}
        if item["metric"] not in FLOW:
            raise ValueError("The independent SQL diagnostic supports FLOW metrics only")
        identity = tuple(item[key] for key in ("asset_id", "period_end", "fiscal_period", "metric"))
        priority = (item["fs_type"] == "CFS", item["available_date"], item["revision_key"])
        if (identity, priority) in revision_keys:
            raise ValueError("Ambiguous identical-priority raw revision duplicates")
        revision_keys.add((identity, priority))
        normalized_rows.append(item)
    normalized_targets = []
    target_keys = set()
    for index, target in enumerate(targets):
        if not isinstance(target, dict) or not {"asset_id", "as_of_date", "metric"}.issubset(target):
            raise ValueError("Target requires asset_id, as_of_date and metric")
        item = {"target_id": index, "asset_id": _asset_id(target["asset_id"]),
                "as_of_date": _timestamp(target["as_of_date"], "as_of_date"),
                "metric": _text(target["metric"], "metric")}
        if item["metric"] not in FLOW:
            raise ValueError("The independent SQL diagnostic supports FLOW targets only")
        identity = (item["asset_id"], item["as_of_date"], item["metric"])
        if identity in target_keys:
            raise ValueError("Duplicate target identity")
        target_keys.add(identity)
        normalized_targets.append(item)
    return (json.dumps(normalized_rows, allow_nan=False),
            json.dumps(normalized_targets, allow_nan=False))


def query_flow_ttm(conn, rows: list[dict], targets: list[dict]) -> list[dict]:
    """Execute one SELECT on an already read-only connection; never commit."""
    if getattr(conn, "read_only", None) is not True:
        raise ValueError("Independent fundamental diagnostic requires a read-only connection")
    params = flow_ttm_parameters(rows, targets)
    with conn.cursor() as cursor:
        cursor.execute(FLOW_TTM_SQL, params)
        columns = [column.name for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
