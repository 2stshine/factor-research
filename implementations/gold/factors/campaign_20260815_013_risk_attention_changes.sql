-- Query-only shared implementation for campaign-20260815-013 qualifiers.
-- One narrow certified daily price ordering feeds all three change signals.
WITH query_bounds AS (
    SELECT
        (%(start_month)s::date - INTERVAL '25 months')::date AS history_start,
        (%(end_month)s::date + INTERVAL '1 month')::date AS history_end,
        %(start_month)s::date AS output_start,
        %(end_month)s::date AS output_end
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
        p.adj_close,
        p.trading_value
    FROM public.factor_price_feature_daily p
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id
     AND q.status = 'CERTIFIED'
    CROSS JOIN query_bounds bounds
    WHERE p.source = 'KRX'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND p.trade_date >= bounds.history_start
      AND p.trade_date < bounds.history_end
), daily_returns AS (
    SELECT
        p.*,
        CASE
            WHEN lag(p.adj_close) OVER (asset_history) > 0
             AND p.adj_close > 0
            THEN p.adj_close / lag(p.adj_close) OVER (asset_history) - 1
        END AS daily_price_return,
        avg(p.trading_value) OVER (
            PARTITION BY p.asset_id ORDER BY p.trade_date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS adv20,
        stats.prior_rows + row_number() OVER (asset_history) AS age_days,
        stats.first_seen,
        lead(p.trade_date) OVER (asset_history) AS next_trade_date
    FROM price_base p
    JOIN price_stats stats USING (asset_id)
    WINDOW asset_history AS (
        PARTITION BY p.asset_id ORDER BY p.trade_date
    )
), daily_features AS (
    SELECT
        daily_returns.*,
        stddev_samp(daily_price_return) OVER (
            PARTITION BY asset_id ORDER BY trade_date
            ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
        ) AS daily_volatility_252d,
        max(daily_price_return) OVER (
            PARTITION BY asset_id, date_trunc('month', trade_date)
        ) AS max_daily_return_1m
    FROM daily_returns
), monthly AS (
    SELECT
        d.asset_id,
        d.trade_date,
        d.market,
        d.market_cap,
        d.adj_close,
        d.adv20,
        d.daily_volatility_252d,
        d.max_daily_return_1m,
        d.age_days,
        d.first_seen,
        bounds.dataset_start,
        a.name,
        a.instrument_type,
        date_trunc('month', d.trade_date)::date AS signal_month
    FROM daily_features d
    CROSS JOIN dataset_bounds bounds
    JOIN public.asset a
      ON a.asset_id = d.asset_id
     AND a.exchange = 'KRX'
     AND a.asset_type = 'stock'
    JOIN LATERAL (
        SELECT 1
        FROM public.asset_identifier ai
        WHERE ai.asset_id = d.asset_id
          AND ai.source = 'KRX'
          AND ai.identifier_type = 'ticker'
          AND ai.valid_from <= d.trade_date
          AND (ai.valid_to IS NULL OR ai.valid_to >= d.trade_date)
        ORDER BY ai.valid_from DESC
        LIMIT 1
    ) identifier ON true
    WHERE d.next_trade_date IS NULL
       OR date_trunc('month', d.next_trade_date)
          <> date_trunc('month', d.trade_date)
), research_monthly AS (
    SELECT monthly.*
    FROM monthly
    WHERE trade_date >= DATE '2015-01-01'
      AND instrument_type = 'common_stock'
), monthly_features AS (
    SELECT
        research_monthly.*,
        adv20 / nullif(market_cap, 0) AS scaled_turnover,
        lag(daily_volatility_252d, 12) OVER (asset_months)
            AS prior_daily_volatility,
        lag(max_daily_return_1m, 12) OVER (asset_months)
            AS prior_max_daily_return,
        lag(adv20 / nullif(market_cap, 0), 6) OVER (asset_months)
            AS prior_scaled_turnover,
        lag(signal_month, 12) OVER (asset_months) AS prior_month_12,
        lag(signal_month, 6) OVER (asset_months) AS prior_month_6
    FROM research_monthly
    WINDOW asset_months AS (
        PARTITION BY asset_id ORDER BY signal_month
    )
), universe AS MATERIALIZED (
    SELECT f.*
    FROM monthly_features f
    CROSS JOIN query_bounds bounds
    WHERE f.signal_month BETWEEN bounds.output_start AND bounds.output_end
      AND f.name !~* '(스팩|SPAC)'
      AND position('리츠' in f.name) = 0
      AND (f.age_days >= 250 OR f.first_seen = f.dataset_start)
      AND f.market_cap > 0
      AND f.adj_close > 0
), raw_values AS (
    SELECT
        'daily_volatility_change_12m'::text AS factor,
        asset_id,
        trade_date AS as_of_date,
        signal_month,
        daily_volatility_252d / prior_daily_volatility - 1 AS value,
        -1::integer AS predicted_sign
    FROM universe
    WHERE prior_daily_volatility > 0
      AND signal_month = prior_month_12 + INTERVAL '12 months'
    UNION ALL
    SELECT
        'max_daily_return_change_12m',
        asset_id,
        trade_date AS as_of_date,
        signal_month,
        max_daily_return_1m - prior_max_daily_return AS value,
        -1
    FROM universe
    WHERE prior_max_daily_return IS NOT NULL
      AND max_daily_return_1m IS NOT NULL
      AND signal_month = prior_month_12 + INTERVAL '12 months'
    UNION ALL
    SELECT
        'turnover_change_6m',
        asset_id,
        trade_date AS as_of_date,
        signal_month,
        scaled_turnover / prior_scaled_turnover - 1 AS value,
        -1
    FROM universe
    WHERE prior_scaled_turnover > 0
      AND signal_month = prior_month_6 + INTERVAL '6 months'
), ranked AS (
    SELECT
        factor,
        asset_id,
        as_of_date,
        value,
        rank() OVER (
            PARTITION BY factor, signal_month
            ORDER BY value * predicted_sign DESC
        ) AS rank
    FROM raw_values
    WHERE value IS NOT NULL
)
SELECT factor, asset_id, as_of_date, value, rank
FROM ranked;
