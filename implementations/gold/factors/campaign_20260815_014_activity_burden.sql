-- Query-only shared implementation for campaign-20260815-014 qualifiers.
-- Monthly price activity and the DART PIT event stream are each materialized once.
WITH query_bounds AS (
    SELECT
        (%(start_month)s::date - INTERVAL '11 months')::date AS history_start,
        (%(end_month)s::date + INTERVAL '1 month')::date
            AS history_end
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
), price_history AS (
    SELECT
        p.asset_id,
        p.trade_date,
        p.market,
        p.market_cap,
        p.adj_close,
        p.trading_value,
        stats.prior_rows + row_number() OVER (
            asset_history
        ) AS age_days,
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
        h.trading_value,
        h.age_days,
        h.first_seen,
        bounds.dataset_start,
        a.name,
        a.instrument_type
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
    SELECT
        monthly.*,
        date_trunc('month', trade_date)::date AS signal_month,
        trading_value / nullif(market_cap, 0) AS scaled_activity
    FROM monthly
    WHERE trade_date >= DATE '2015-01-01'
      AND instrument_type = 'common_stock'
), monthly_features AS (
    SELECT
        research_monthly.*,
        stddev_samp(scaled_activity) OVER asset_months
            AS trading_value_volatility_12m,
        count(scaled_activity) OVER asset_months AS scaled_activity_count,
        lag(signal_month, 11) OVER (
            PARTITION BY asset_id ORDER BY signal_month
        ) AS oldest_signal_month
    FROM research_monthly
    WINDOW asset_months AS (
        PARTITION BY asset_id ORDER BY signal_month
        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    )
), universe AS MATERIALIZED (
    SELECT *
    FROM monthly_features
    WHERE signal_month BETWEEN %(start_month)s::date AND %(end_month)s::date
      AND name !~* '(스팩|SPAC)'
      AND position('리츠' in name) = 0
      AND (age_days >= 250 OR first_seen = dataset_start)
      AND market_cap > 0
      AND adj_close > 0
), fundamental_candidates AS MATERIALIZED (
    SELECT
        f.asset_id, f.period_end, f.fiscal_period, f.metric,
        f.value::double precision AS value,
        f.fs_type, f.available_date, f.revision_key,
        min(f.available_date) FILTER (
            WHERE f.fs_type = 'CFS'
        ) OVER (
            PARTITION BY
                f.asset_id, f.period_end, f.fiscal_period, f.metric
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
    WHERE f.metric IN (
        'revenue', 'operating_income', 'net_income'
    )
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
        u.asset_id, u.trade_date AS as_of_date, u.signal_month,
        f.period_end, f.fiscal_period, f.metric, f.value
    FROM universe u
    JOIN effective_fundamental_events f
      ON f.asset_id = u.asset_id
     AND f.available_date <= u.trade_date
     AND (
         f.next_available_date IS NULL
         OR f.next_available_date > u.trade_date
     )
), fiscal_years AS (
    SELECT
        asset_id, as_of_date, signal_month, metric,
        period_end AS fy_end, value AS fy_value,
        lag(period_end) OVER (
            PARTITION BY asset_id, as_of_date, metric ORDER BY period_end
        ) AS previous_fy_end
    FROM selected
    WHERE metric IN ('revenue', 'operating_income', 'net_income')
      AND fiscal_period = 'FY'
), fy_quarter_candidates AS (
    SELECT
        fy.asset_id, fy.as_of_date, fy.signal_month, fy.metric,
        fy.fy_end, fy.fy_value, q.period_end, q.fiscal_period, q.value,
        row_number() OVER (
            PARTITION BY
                fy.asset_id, fy.as_of_date, fy.metric,
                fy.fy_end, q.fiscal_period
            ORDER BY q.period_end DESC
        ) AS quarter_rank
    FROM fiscal_years fy
    JOIN selected q
      ON q.asset_id = fy.asset_id
     AND q.as_of_date = fy.as_of_date
     AND q.metric = fy.metric
     AND q.fiscal_period IN ('Q1', 'Q2', 'Q3')
     AND q.period_end > coalesce(
            fy.previous_fy_end, fy.fy_end - INTERVAL '370 days'
         )
     AND q.period_end < fy.fy_end
    WHERE NOT EXISTS (
        SELECT 1
        FROM selected explicit_q4
        WHERE explicit_q4.asset_id = fy.asset_id
          AND explicit_q4.as_of_date = fy.as_of_date
          AND explicit_q4.metric = fy.metric
          AND explicit_q4.fiscal_period = 'Q4'
          AND explicit_q4.period_end = fy.fy_end
    )
), derived_q4 AS (
    SELECT
        asset_id, as_of_date, max(signal_month) AS signal_month, metric,
        fy_end AS period_end, 'Q4'::text AS fiscal_period,
        max(fy_value) - sum(value) AS value
    FROM fy_quarter_candidates
    WHERE quarter_rank = 1
    GROUP BY asset_id, as_of_date, metric, fy_end
    HAVING count(DISTINCT fiscal_period) = 3
), standalone_candidates AS (
    SELECT
        asset_id, as_of_date, signal_month, metric,
        period_end, fiscal_period, value
    FROM selected
    WHERE metric IN ('revenue', 'operating_income', 'net_income')
      AND fiscal_period IN ('Q1', 'Q2', 'Q3', 'Q4')
    UNION ALL
    SELECT
        asset_id, as_of_date, signal_month, metric,
        period_end, fiscal_period, value
    FROM derived_q4
), standalone_ranked AS (
    SELECT
        standalone_candidates.*,
        row_number() OVER (
            PARTITION BY asset_id, as_of_date, metric, period_end
            ORDER BY
                CASE fiscal_period
                    WHEN 'Q4' THEN 4
                    WHEN 'Q3' THEN 3
                    WHEN 'Q2' THEN 2
                    WHEN 'Q1' THEN 1
                    ELSE 0
                END DESC
        ) AS period_rank
    FROM standalone_candidates
), flow_sequence AS (
    SELECT
        standalone_ranked.*,
        row_number() OVER (
            PARTITION BY asset_id, as_of_date, metric ORDER BY period_end DESC
        ) AS recent_rank
    FROM standalone_ranked
    WHERE period_rank = 1
), flow_ttm AS (
    SELECT
        asset_id, as_of_date, max(signal_month) AS signal_month, metric,
        sum(value) AS ttm_value
    FROM flow_sequence
    WHERE recent_rank <= 4
    GROUP BY asset_id, as_of_date, metric
    HAVING count(*) = 4
       AND max(period_end) - min(period_end) <= 370
), latest_flows AS (
    SELECT
        asset_id, as_of_date, max(signal_month) AS signal_month,
        max(ttm_value) FILTER (
            WHERE metric = 'revenue'
        ) AS revenue_ttm,
        max(ttm_value) FILTER (
            WHERE metric = 'operating_income'
        ) AS operating_income_ttm,
        max(ttm_value) FILTER (
            WHERE metric = 'net_income'
        ) AS net_income_ttm
    FROM flow_ttm
    GROUP BY asset_id, as_of_date
), raw_values AS (
    SELECT
        'trading_value_volatility_12m'::text AS factor,
        u.asset_id,
        u.trade_date AS as_of_date,
        u.signal_month,
        u.trading_value_volatility_12m AS value,
        -1::integer AS predicted_sign
    FROM universe u
    WHERE u.trading_value_volatility_12m IS NOT NULL
      AND u.scaled_activity_count = 12
      AND u.signal_month = u.oldest_signal_month + INTERVAL '11 months'
    UNION ALL
    SELECT
        'nonoperating_burden_margin',
        f.asset_id,
        f.as_of_date,
        f.signal_month,
        (f.operating_income_ttm - f.net_income_ttm) / f.revenue_ttm,
        -1
    FROM latest_flows f
    WHERE f.revenue_ttm > 0
      AND f.operating_income_ttm IS NOT NULL
      AND f.net_income_ttm IS NOT NULL
), ranked AS (
    SELECT
        factor, asset_id, as_of_date, value,
        rank() OVER (
            PARTITION BY factor, signal_month
            ORDER BY value * predicted_sign DESC
        ) AS rank
    FROM raw_values
    WHERE value IS NOT NULL
)
SELECT factor, asset_id, as_of_date, value, rank
FROM ranked;
