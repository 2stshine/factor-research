-- Query-only implementation for retained_earnings_to_assets_volatility_12m.
-- value = 최근 12개 신호월 (retained_earnings / total_assets) 의 표본표준편차
--         (유효 관측 9개 이상, ddof=1)
-- 두 지표 모두 stock 계정이므로 4분기 합산이나 Q4 역산을 적용하지 않고
-- PIT 시점의 최신 보고값을 그대로 사용한다.
-- total_assets = 0 인 월은 연구 정의와 동일하게 결측으로 둔다.
-- predicted_sign = -1, 따라서 rank 1은 raw value가 가장 낮은 종목이다.
WITH query_bounds AS (
    SELECT
        (%(start_month)s::date - INTERVAL '11 months')::date AS history_start,
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
), price_history AS (
    SELECT
        p.*,
        stats.prior_rows + row_number() OVER (asset_history) AS age_days,
        stats.first_seen,
        lead(p.trade_date) OVER (asset_history) AS next_trade_date
    FROM price_base p
    JOIN price_stats stats USING (asset_id)
    WINDOW asset_history AS (PARTITION BY p.asset_id ORDER BY p.trade_date)
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
), factor_monthly AS MATERIALIZED (
    SELECT monthly.*
    FROM monthly
    CROSS JOIN query_bounds bounds
    WHERE signal_month >= bounds.history_start
      AND signal_month <= bounds.output_end
      AND trade_date >= DATE '2015-01-01'
      AND instrument_type = 'common_stock'
), output_universe AS MATERIALIZED (
    SELECT factor_monthly.*
    FROM factor_monthly
    CROSS JOIN query_bounds bounds
    WHERE signal_month BETWEEN bounds.output_start AND bounds.output_end
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
        min(f.available_date) FILTER (WHERE f.fs_type = 'CFS') OVER (
            PARTITION BY f.asset_id, f.period_end, f.fiscal_period, f.metric
        ) AS first_cfs_date,
        row_number() OVER (
            PARTITION BY
                f.asset_id, f.period_end, f.fiscal_period,
                f.metric, f.available_date
            ORDER BY (f.fs_type = 'CFS') DESC, f.revision_key DESC
        ) AS event_rank
    FROM public.fundamental f
    JOIN public.dq_run q
      ON q.run_id = f.quality_run_id
     AND q.status = 'CERTIFIED'
    WHERE f.metric IN ('retained_earnings', 'total_assets')
      AND f.source = 'DART'
      AND f.data_basis = 'STANDARDIZED'
      AND f.unit_type = 'currency'
      AND f.value IS NOT NULL
      AND f.available_date IS NOT NULL
), effective_fundamental_events AS (
    SELECT
        asset_id, period_end, fiscal_period, metric, value,
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
        m.asset_id,
        m.trade_date AS as_of_date,
        m.signal_month,
        f.period_end,
        f.fiscal_period,
        f.metric,
        f.value
    FROM factor_monthly m
    JOIN effective_fundamental_events f
      ON f.asset_id = m.asset_id
     AND f.available_date <= m.trade_date
     AND (f.next_available_date IS NULL OR f.next_available_date > m.trade_date)
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
    WHERE metric IN ('retained_earnings', 'total_assets')
), latest_stocks AS (
    SELECT
        asset_id,
        as_of_date,
        max(value) FILTER (
            WHERE metric_rank = 1 AND metric = 'retained_earnings'
        ) AS retained_earnings,
        max(value) FILTER (
            WHERE metric_rank = 1 AND metric = 'total_assets'
        ) AS total_assets
    FROM stock_candidates
    GROUP BY asset_id, as_of_date
), accounting_months AS (
    SELECT
        m.asset_id,
        m.trade_date AS as_of_date,
        m.signal_month,
        s.retained_earnings / nullif(s.total_assets, 0) AS retained_earnings_to_assets
    FROM factor_monthly m
    LEFT JOIN latest_stocks s
      ON s.asset_id = m.asset_id
     AND s.as_of_date = m.trade_date
), rolling_values AS (
    SELECT
        accounting_months.*,
        stddev_samp(retained_earnings_to_assets) OVER asset_months
            AS retained_earnings_to_assets_volatility_12m,
        count(retained_earnings_to_assets) OVER asset_months
            AS retained_earnings_to_assets_observations_12m
    FROM accounting_months
    WINDOW asset_months AS (
        PARTITION BY asset_id ORDER BY signal_month
        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    )
), raw_values AS (
    SELECT
        values.asset_id,
        values.as_of_date,
        values.signal_month,
        values.retained_earnings_to_assets_volatility_12m AS value
    FROM rolling_values values
    JOIN output_universe u
      ON u.asset_id = values.asset_id
     AND u.trade_date = values.as_of_date
    CROSS JOIN query_bounds bounds
    WHERE values.signal_month BETWEEN bounds.output_start AND bounds.output_end
      AND values.retained_earnings_to_assets_observations_12m >= 9
      AND values.retained_earnings_to_assets_volatility_12m IS NOT NULL
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
