-- Query-only PIT net-working-capital yield implementation.
WITH query_bounds AS (
    SELECT
        %(start_month)s::date AS history_start,
        (%(end_month)s::date + INTERVAL '1 month')::date AS history_end
), price_stats AS MATERIALIZED (
    SELECT
        p.asset_id,
        min(p.trade_date) AS first_seen,
        count(*) FILTER (
            WHERE p.trade_date < bounds.history_start
        ) AS prior_rows
    FROM public.factor_price_feature_daily p
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id
     AND q.status = 'CERTIFIED'
    CROSS JOIN query_bounds bounds
    WHERE p.source = 'KRX'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND p.trade_date < bounds.history_end
    GROUP BY p.asset_id
), dataset_bounds AS (
    SELECT min(first_seen) AS dataset_start
    FROM price_stats
), price_base AS (
    SELECT
        p.asset_id,
        p.trade_date,
        p.market,
        p.market_cap,
        p.adj_close
    FROM public.factor_price_feature_daily p
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id
     AND q.status = 'CERTIFIED'
    CROSS JOIN query_bounds bounds
    WHERE p.source = 'KRX'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND p.trade_date >= bounds.history_start
      AND p.trade_date < bounds.history_end
), price_history AS (
    SELECT
        p.asset_id,
        p.trade_date,
        p.market,
        p.market_cap,
        p.adj_close,
        stats.prior_rows + row_number() OVER (asset_history) AS age_days,
        stats.first_seen,
        lead(p.trade_date) OVER (asset_history) AS next_trade_date
    FROM price_base p
    JOIN price_stats stats USING (asset_id)
    WINDOW asset_history AS (
        PARTITION BY p.asset_id ORDER BY p.trade_date
    )
), monthly AS (
    SELECT
        h.asset_id,
        h.trade_date,
        h.market_cap,
        h.adj_close,
        h.age_days,
        h.first_seen,
        bounds.dataset_start,
        a.name,
        a.instrument_type,
        date_trunc('month', h.trade_date)::date AS signal_month
    FROM price_history h
    CROSS JOIN dataset_bounds bounds
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
    WHERE h.next_trade_date IS NULL
       OR date_trunc('month', h.next_trade_date)
          <> date_trunc('month', h.trade_date)
), universe AS MATERIALIZED (
    SELECT monthly.*
    FROM monthly
    WHERE trade_date >= DATE '2015-01-01'
      AND instrument_type = 'common_stock'
      AND name !~* '(스팩|SPAC)'
      AND position('리츠' in name) = 0
      AND (age_days >= 250 OR first_seen = dataset_start)
      AND market_cap > 0
      AND adj_close > 0
), fundamental_candidates AS MATERIALIZED (
    SELECT
        f.asset_id,
        f.period_end,
        f.fiscal_period,
        f.metric,
        f.value::double precision AS value,
        f.fs_type,
        f.available_date,
        f.revision_key,
        min(f.available_date) FILTER (
            WHERE f.fs_type = 'CFS'
        ) OVER (
            PARTITION BY f.asset_id, f.period_end, f.fiscal_period, f.metric
        ) AS first_cfs_date,
        row_number() OVER (
            PARTITION BY
                f.asset_id, f.period_end, f.fiscal_period,
                f.metric, f.available_date
            ORDER BY
                (f.fs_type = 'CFS') DESC,
                f.revision_key DESC
        ) AS event_rank
    FROM public.fundamental f
    JOIN public.dq_run q
      ON q.run_id = f.quality_run_id
     AND q.status = 'CERTIFIED'
    WHERE f.metric IN ('current_assets', 'current_liabilities')
      AND f.source = 'DART'
      AND f.data_basis = 'STANDARDIZED'
      AND f.unit_type = 'currency'
      AND f.value IS NOT NULL
      AND f.available_date IS NOT NULL
), effective_fundamental_events AS (
    SELECT
        asset_id,
        period_end,
        fiscal_period,
        metric,
        value,
        available_date,
        lead(available_date) OVER (
            PARTITION BY asset_id, period_end, fiscal_period, metric
            ORDER BY available_date
        ) AS next_available_date
    FROM fundamental_candidates
    WHERE event_rank = 1
      AND (
          fs_type = 'CFS'
          OR first_cfs_date IS NULL
          OR available_date < first_cfs_date
      )
), selected AS (
    SELECT
        u.asset_id,
        u.trade_date AS as_of_date,
        u.signal_month,
        f.period_end,
        f.fiscal_period,
        f.metric,
        f.value
    FROM universe u
    JOIN effective_fundamental_events f
      ON f.asset_id = u.asset_id
     AND f.available_date <= u.trade_date
     AND (
         f.next_available_date IS NULL
         OR f.next_available_date > u.trade_date
     )
), stock_candidates AS (
    SELECT
        selected.*,
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
    FROM selected
), latest_stocks AS (
    SELECT
        asset_id,
        as_of_date,
        max(signal_month) AS signal_month,
        max(value) FILTER (
            WHERE metric = 'current_assets' AND metric_rank = 1
        ) AS current_assets,
        max(value) FILTER (
            WHERE metric = 'current_liabilities' AND metric_rank = 1
        ) AS current_liabilities
    FROM stock_candidates
    GROUP BY asset_id, as_of_date
), raw_values AS (
    SELECT
        stocks.asset_id,
        stocks.as_of_date,
        stocks.signal_month,
        (stocks.current_assets - stocks.current_liabilities) / u.market_cap AS value
    FROM latest_stocks stocks
    JOIN universe u
      ON u.asset_id = stocks.asset_id
     AND u.trade_date = stocks.as_of_date
    WHERE stocks.current_assets IS NOT NULL
      AND stocks.current_liabilities IS NOT NULL
      AND u.market_cap > 0
), ranked AS (
    SELECT
        asset_id,
        as_of_date,
        value,
        rank() OVER (
            PARTITION BY signal_month ORDER BY value DESC
        ) AS rank
    FROM raw_values
    WHERE value IS NOT NULL
)
SELECT asset_id, as_of_date, value, rank
FROM ranked;
