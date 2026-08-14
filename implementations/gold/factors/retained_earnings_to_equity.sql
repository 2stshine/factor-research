-- retained_earnings_to_equity Gold implementation.
-- value = PIT 이익잉여금 / PIT 양의 자기자본; predicted_sign = +1.
WITH price_history AS (
    SELECT
        p.*,
        row_number() OVER (
            PARTITION BY p.asset_id ORDER BY p.trade_date
        ) AS age_days,
        min(p.trade_date) OVER () AS dataset_start,
        min(p.trade_date) OVER (PARTITION BY p.asset_id) AS first_seen,
        row_number() OVER (
            PARTITION BY p.asset_id, date_trunc('month', p.trade_date)
            ORDER BY p.trade_date DESC
        ) AS month_rank
    FROM public.factor_price_feature_daily p
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id
     AND q.status = 'CERTIFIED'
    WHERE p.source = 'KRX'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND p.trade_date < %(end_month)s::date + INTERVAL '1 month'
), monthly AS (
    SELECT
        h.*, a.name, a.instrument_type
    FROM price_history h
    JOIN public.asset a
      ON a.asset_id = h.asset_id
     AND a.exchange = 'KRX'
     AND a.asset_type = 'stock'
    JOIN LATERAL (
        SELECT 1
        FROM public.asset_identifier ai
        WHERE ai.asset_id = h.asset_id
          AND ai.source = 'KRX'
          AND ai.identifier_type = 'ticker'
          AND ai.valid_from <= h.trade_date
          AND (ai.valid_to IS NULL OR ai.valid_to >= h.trade_date)
        ORDER BY ai.valid_from DESC
        LIMIT 1
    ) identifier ON true
    WHERE h.month_rank = 1
), universe AS (
    SELECT
        asset_id,
        trade_date AS as_of_date,
        date_trunc('month', trade_date) AS signal_month
    FROM monthly
    WHERE month_rank = 1
      AND date_trunc('month', trade_date)
          BETWEEN %(start_month)s::date AND %(end_month)s::date
      AND trade_date >= DATE '2015-01-01'
      AND instrument_type = 'common_stock'
      AND name !~* '(스팩|SPAC)'
      AND position('리츠' in name) = 0
      AND (age_days >= 250 OR first_seen = dataset_start)
      AND market_cap > 0
      AND adj_close > 0
), revisions AS (
    SELECT
        u.asset_id, u.as_of_date, u.signal_month,
        f.period_end, f.fiscal_period, f.metric,
        f.value::double precision AS value,
        f.fs_type, f.available_date, f.revision_key,
        row_number() OVER (
            PARTITION BY
                u.asset_id, u.as_of_date, f.period_end,
                f.fiscal_period, f.metric
            ORDER BY
                (f.fs_type = 'CFS') DESC,
                f.available_date DESC,
                f.revision_key DESC
        ) AS revision_rank
    FROM universe u
    JOIN public.fundamental f
      ON f.asset_id = u.asset_id
     AND f.available_date <= u.as_of_date
     AND f.metric IN ('retained_earnings', 'total_equity')
     AND f.source = 'DART'
     AND f.data_basis = 'STANDARDIZED'
     AND f.unit_type = 'currency'
     AND f.value IS NOT NULL
    JOIN public.dq_run q
      ON q.run_id = f.quality_run_id
     AND q.status = 'CERTIFIED'
), latest_metric AS (
    SELECT
        revisions.*,
        row_number() OVER (
            PARTITION BY asset_id, as_of_date, metric
            ORDER BY
                period_end DESC,
                CASE fiscal_period
                    WHEN 'Q4' THEN 5
                    WHEN 'FY' THEN 4
                    WHEN 'Q3' THEN 3
                    WHEN 'Q2' THEN 2
                    WHEN 'Q1' THEN 1
                    ELSE 0
                END DESC
        ) AS metric_rank
    FROM revisions
    WHERE revision_rank = 1
), pivoted AS (
    SELECT
        asset_id, as_of_date, signal_month,
        max(value) FILTER (
            WHERE metric = 'retained_earnings' AND metric_rank = 1
        ) AS retained_earnings,
        max(value) FILTER (
            WHERE metric = 'total_equity' AND metric_rank = 1
        ) AS total_equity
    FROM latest_metric
    GROUP BY asset_id, as_of_date, signal_month
), raw_values AS (
    SELECT
        asset_id, as_of_date, signal_month,
        retained_earnings / total_equity AS value
    FROM pivoted
    WHERE retained_earnings IS NOT NULL
      AND total_equity > 0
), ranked AS (
    SELECT
        asset_id, as_of_date, value,
        rank() OVER (
            PARTITION BY signal_month ORDER BY value DESC
        ) AS rank
    FROM raw_values
)
SELECT asset_id, as_of_date, value, rank
FROM ranked;
