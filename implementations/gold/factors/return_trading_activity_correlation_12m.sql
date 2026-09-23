-- Frozen definition e0e91e564995c7a2; raw Pearson correlation, fixed sign -1.
-- Keep the complete 2015+ daily stream for exact ADV20 trading-row windows,
-- including assets with sparse trading or long suspensions.
WITH query_bounds AS (
    SELECT
        (%(end_month)s::date + INTERVAL '1 month')::date AS history_end,
        %(start_month)s::date AS output_start,
        %(end_month)s::date AS output_end
), price_stats AS MATERIALIZED (
    SELECT
        p.asset_id,
        min(p.trade_date) AS first_seen,
        count(*) FILTER (
            WHERE p.trade_date < DATE '2015-01-01'
        ) AS prior_rows
    FROM public.factor_price_feature_daily p
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id
     AND q.status = 'CERTIFIED'
    JOIN public.asset a
      ON a.asset_id = p.asset_id
     AND a.exchange = 'KRX'
     AND a.asset_type = 'stock'
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
        p.market_cap,
        p.adj_close,
        p.trading_value
    FROM public.factor_price_feature_daily p
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id
     AND q.status = 'CERTIFIED'
    JOIN price_stats stats USING (asset_id)
    CROSS JOIN query_bounds bounds
    WHERE p.source = 'KRX'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND p.trade_date >= DATE '2015-01-01'
      AND p.trade_date < bounds.history_end
), price_history AS (
    SELECT
        p.asset_id,
        p.trade_date,
        p.market_cap,
        p.adj_close,
        avg(p.trading_value) OVER (
            PARTITION BY p.asset_id ORDER BY p.trade_date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        )::double precision AS adv20,
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
        h.adv20,
        h.age_days,
        h.first_seen,
        bounds.dataset_start,
        coalesce(a.name, '') AS name,
        date_trunc('month', h.trade_date)::date AS signal_month,
        CASE
            WHEN h.adj_close > 0
             AND h.adj_close < 'Infinity'::double precision
            THEN h.adj_close::double precision
        END AS valid_close,
        CASE
            WHEN h.adv20 > 0
             AND h.adv20 < 'Infinity'::double precision
            THEN ln(h.adv20)
        END AS log_activity
    FROM price_history h
    CROSS JOIN dataset_bounds bounds
    JOIN public.asset a
      ON a.asset_id = h.asset_id
     AND a.exchange = 'KRX'
     AND a.asset_type = 'stock'
     AND a.instrument_type = 'common_stock'
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
), monthly_lags AS (
    SELECT
        monthly.*,
        lag(valid_close) OVER asset_months AS prior_close,
        lag(signal_month) OVER asset_months AS prior_signal_month,
        lag(signal_month, 12) OVER asset_months AS oldest_signal_month
    FROM monthly
    WINDOW asset_months AS (
        PARTITION BY asset_id ORDER BY signal_month
    )
), monthly_returns AS (
    SELECT
        monthly_lags.*,
        CASE
            WHEN signal_month = prior_signal_month + INTERVAL '1 month'
            THEN valid_close / prior_close - 1.0
        END AS monthly_return
    FROM monthly_lags
), paired AS (
    SELECT
        monthly_returns.*,
        CASE WHEN log_activity IS NOT NULL
            THEN monthly_return END AS paired_return,
        CASE WHEN monthly_return IS NOT NULL
            THEN log_activity END AS paired_activity
    FROM monthly_returns
), rolling_moments AS (
    SELECT
        paired.*,
        count(paired_return) OVER asset_months AS observations,
        avg(paired_return) OVER asset_months AS return_mean,
        avg(paired_activity) OVER asset_months AS activity_mean,
        avg(paired_return * paired_activity) OVER asset_months AS product_mean,
        min(paired_return) OVER asset_months
            < max(paired_return) OVER asset_months AS return_varies,
        min(paired_activity) OVER asset_months
            < max(paired_activity) OVER asset_months AS activity_varies,
        var_pop(paired_return) OVER asset_months AS return_variance,
        var_pop(paired_activity) OVER asset_months AS activity_variance
    FROM paired
    WINDOW asset_months AS (
        PARTITION BY asset_id ORDER BY signal_month
        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    )
), raw_values AS (
    SELECT
        f.asset_id,
        f.trade_date AS as_of_date,
        f.signal_month,
        (f.product_mean - f.return_mean * f.activity_mean)
            / sqrt(f.return_variance * f.activity_variance) AS value
    FROM rolling_moments f
    CROSS JOIN query_bounds bounds
    WHERE f.signal_month BETWEEN bounds.output_start AND bounds.output_end
      AND f.signal_month = f.oldest_signal_month + INTERVAL '12 months'
      AND f.observations = 12
      -- Floating aggregate variance can retain roundoff for constant inputs.
      AND f.return_varies
      AND f.activity_varies
      AND f.return_variance > 0
      AND f.activity_variance > 0
      AND f.name !~* '(스팩|SPAC)'
      AND position('리츠' in f.name) = 0
      AND (f.age_days >= 250 OR f.first_seen = f.dataset_start)
      AND f.market_cap > 0
      AND f.adj_close > 0
), ranked AS (
    SELECT
        asset_id,
        as_of_date,
        value,
        rank() OVER (
            PARTITION BY signal_month ORDER BY value ASC
        ) AS rank
    FROM raw_values
    WHERE value > '-Infinity'::double precision
      AND value < 'Infinity'::double precision
)
SELECT asset_id, as_of_date, value, rank
FROM ranked;
