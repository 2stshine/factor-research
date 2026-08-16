-- Query-only implementation for net_margin_volatility_12m.
-- value = 최근 12개 신호월 (net_income_ttm / revenue_ttm) 의 표본표준편차
--         (유효 관측 9개 이상, ddof=1)
-- revenue_ttm = 0 인 월은 연구 정의와 동일하게 결측으로 둔다.
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
    WHERE f.metric IN ('revenue', 'net_income')
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
), fiscal_years AS (
    SELECT
        asset_id, as_of_date, signal_month, metric,
        period_end AS fy_end, value AS fy_value,
        lag(period_end) OVER (
            PARTITION BY asset_id, as_of_date, metric ORDER BY period_end
        ) AS previous_fy_end
    FROM selected
    WHERE metric IN ('revenue', 'net_income')
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
    WHERE metric IN ('revenue', 'net_income')
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
        asset_id, as_of_date, metric,
        sum(value) AS ttm_value
    FROM flow_sequence
    WHERE recent_rank <= 4
    GROUP BY asset_id, as_of_date, metric
    HAVING count(*) = 4
       AND max(period_end) - min(period_end) <= 370
), latest_flows AS (
    SELECT
        asset_id, as_of_date,
        max(ttm_value) FILTER (WHERE metric = 'revenue') AS revenue_ttm,
        max(ttm_value) FILTER (WHERE metric = 'net_income') AS net_income_ttm
    FROM flow_ttm
    GROUP BY asset_id, as_of_date
), accounting_months AS (
    SELECT
        m.asset_id,
        m.trade_date AS as_of_date,
        m.signal_month,
        f.net_income_ttm / nullif(f.revenue_ttm, 0) AS net_margin
    FROM factor_monthly m
    LEFT JOIN latest_flows f
      ON f.asset_id = m.asset_id
     AND f.as_of_date = m.trade_date
), rolling_values AS (
    SELECT
        accounting_months.*,
        stddev_samp(net_margin) OVER asset_months AS net_margin_volatility_12m,
        count(net_margin) OVER asset_months AS net_margin_observations_12m
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
        values.net_margin_volatility_12m AS value
    FROM rolling_values values
    JOIN output_universe u
      ON u.asset_id = values.asset_id
     AND u.trade_date = values.as_of_date
    CROSS JOIN query_bounds bounds
    WHERE values.signal_month BETWEEN bounds.output_start AND bounds.output_end
      AND values.net_margin_observations_12m >= 9
      AND values.net_margin_volatility_12m IS NOT NULL
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
