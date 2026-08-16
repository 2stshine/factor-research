-- Query-only implementation for max_daily_return_mean_6m.
-- value = 최근 6개 신호월 max_daily_return_1m 의 mean (유효 관측 4개 이상)
-- max_daily_return_1m 은 월내 일별 분할조정 가격수익률의 최대값이며,
-- 연구 패널과 동일하게 관측수 하한을 적용하지 않는다.
-- predicted_sign = -1, 따라서 rank 1은 raw value가 가장 낮은 종목이다.
WITH query_bounds AS (
    SELECT
        (%(start_month)s::date - INTERVAL '12 months')::date AS history_start,
        (%(end_month)s::date + INTERVAL '1 month')::date AS history_end,
        %(start_month)s::date AS output_start,
        %(end_month)s::date AS output_end
), price_stats AS MATERIALIZED (
    SELECT
        p.asset_id,
        min(p.trade_date) AS first_seen,
        count(*) FILTER (WHERE p.trade_date < bounds.history_start) AS prior_rows
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
    SELECT min(first_seen) AS dataset_start FROM price_stats
), price_base AS (
    SELECT p.asset_id, p.trade_date, p.market_cap, p.adj_close
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
        p.asset_id,
        p.trade_date,
        p.market_cap,
        p.adj_close,
        CASE
            WHEN lag(p.adj_close) OVER (asset_history) > 0
             AND p.adj_close > 0
            THEN p.adj_close::double precision
                / lag(p.adj_close::double precision) OVER (asset_history) - 1
        END AS daily_price_return,
        stats.prior_rows + row_number() OVER (asset_history) AS age_days,
        stats.first_seen,
        lead(p.trade_date) OVER (asset_history) AS next_trade_date
    FROM price_base p
    JOIN price_stats stats USING (asset_id)
    WINDOW asset_history AS (PARTITION BY p.asset_id ORDER BY p.trade_date)
), daily_features AS (
    SELECT
        daily_returns.*,
        max(daily_price_return) OVER (
            PARTITION BY asset_id, date_trunc('month', trade_date)
        ) AS max_daily_return_1m
    FROM daily_returns
), monthly AS (
    SELECT
        d.asset_id,
        d.trade_date,
        d.market_cap,
        d.adj_close,
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
), monthly_features AS (
    SELECT
        monthly.*,
        avg(max_daily_return_1m) OVER asset_months
            AS max_daily_return_mean_6m,
        count(max_daily_return_1m) OVER asset_months
            AS max_daily_return_mean_observations_6m
    FROM monthly
    WHERE trade_date >= DATE '2015-01-01'
      AND instrument_type = 'common_stock'
    WINDOW asset_months AS (
        PARTITION BY asset_id ORDER BY signal_month
        ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
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
        asset_id,
        trade_date AS as_of_date,
        signal_month,
        max_daily_return_mean_6m AS value
    FROM universe
    WHERE max_daily_return_mean_observations_6m >= 4
      AND max_daily_return_mean_6m IS NOT NULL
), ranked AS (
    SELECT
        asset_id,
        as_of_date,
        value,
        rank() OVER (PARTITION BY signal_month ORDER BY value ASC) AS rank
    FROM raw_values
    WHERE value IS NOT NULL
)
SELECT asset_id, as_of_date, value, rank
FROM ranked;
