-- adv20_change_12m Gold implementation.
-- value = current 20-day average trading value / exact 12-month lag - 1; sign = -1.
WITH query_bounds AS (
    SELECT
        (%(start_month)s::date - INTERVAL '13 months')::date AS price_start,
        (%(start_month)s::date - INTERVAL '12 months')::date AS history_start,
        (%(end_month)s::date + INTERVAL '1 month')::date AS history_end,
        %(start_month)s::date AS output_start,
        %(end_month)s::date AS output_end
), price_stats AS MATERIALIZED (
    SELECT
        p.asset_id,
        min(p.trade_date) AS first_seen,
        count(*) FILTER (
            WHERE p.trade_date < bounds.price_start
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
      AND p.trade_date >= bounds.price_start
      AND p.trade_date < bounds.history_end
), price_history AS (
    SELECT
        p.asset_id,
        p.trade_date,
        p.market,
        p.market_cap,
        p.adj_close,
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
), monthly AS (
    SELECT
        h.asset_id,
        h.trade_date,
        h.market,
        h.market_cap,
        h.adj_close,
        h.adv20,
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
), research_monthly AS (
    SELECT monthly.*
    FROM monthly
    WHERE trade_date >= DATE '2015-01-01'
      AND instrument_type = 'common_stock'
), monthly_features AS (
    SELECT
        research_monthly.*,
        lag(adv20, 12) OVER (
            PARTITION BY asset_id ORDER BY signal_month
        ) AS prior_adv20,
        lag(signal_month, 12) OVER (
            PARTITION BY asset_id ORDER BY signal_month
        ) AS prior_signal_month
    FROM research_monthly
), raw_values AS (
    SELECT
        f.asset_id,
        f.trade_date AS as_of_date,
        f.signal_month,
        f.adv20 / f.prior_adv20 - 1 AS value
    FROM monthly_features f
    CROSS JOIN query_bounds bounds
    WHERE f.signal_month BETWEEN bounds.output_start AND bounds.output_end
      AND f.name !~* '(스팩|SPAC)'
      AND position('리츠' in f.name) = 0
      AND (f.age_days >= 250 OR f.first_seen = f.dataset_start)
      AND f.market_cap > 0
      AND f.adj_close > 0
      AND f.adv20 IS NOT NULL
      AND f.prior_adv20 > 0
      AND f.signal_month = f.prior_signal_month + INTERVAL '12 months'
), ranked AS (
    SELECT
        asset_id,
        as_of_date,
        value,
        rank() OVER (
            PARTITION BY signal_month ORDER BY value ASC
        ) AS rank
    FROM raw_values
    WHERE value IS NOT NULL
)
SELECT asset_id, as_of_date, value, rank
FROM ranked;
