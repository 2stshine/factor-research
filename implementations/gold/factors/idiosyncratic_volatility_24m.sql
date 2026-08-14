-- campaign-20260814-002 idiosyncratic_volatility_24m Gold implementation.
-- value = 최근 24개월 PIT 시장수익으로 설명되지 않는 월수익 잔차 표준편차.
-- This price-only query is intentionally separate from the campaign accounting
-- query so its resumable chunks never rebuild the DART fundamental event stream.
WITH query_bounds AS (
    SELECT
        (%(start_month)s::date - INTERVAL '24 months')::date AS history_start,
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
        stats.prior_rows + row_number() OVER asset_history AS age_days,
        stats.first_seen,
        lead(p.trade_date) OVER asset_history AS next_trade_date
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
        date_trunc('month', trade_date)::date AS signal_month
    FROM monthly
    WHERE trade_date >= DATE '2015-01-01'
      AND instrument_type = 'common_stock'
), lagged AS (
    SELECT
        research_monthly.*,
        lag(signal_month) OVER asset_months AS prior_signal_month,
        lag(adj_close) OVER asset_months AS prior_adj_close,
        lag(market) OVER asset_months AS prior_market,
        lag(market_cap) OVER asset_months AS prior_market_cap
    FROM research_monthly
    WINDOW asset_months AS (
        PARTITION BY asset_id ORDER BY signal_month
    )
), asset_returns AS (
    SELECT
        lagged.*,
        CASE
            WHEN signal_month = prior_signal_month + INTERVAL '1 month'
             AND prior_adj_close > 0
            THEN adj_close / prior_adj_close - 1
        END AS asset_return
    FROM lagged
), market_returns AS (
    SELECT
        signal_month,
        prior_market,
        sum(asset_return * prior_market_cap)
            / nullif(sum(prior_market_cap), 0) AS market_return
    FROM asset_returns
    WHERE asset_return IS NOT NULL
      AND prior_market IS NOT NULL
      AND prior_market_cap > 0
    GROUP BY signal_month, prior_market
), paired AS (
    SELECT
        r.*,
        CASE WHEN r.asset_return IS NOT NULL AND m.market_return IS NOT NULL
             THEN r.asset_return END AS paired_asset_return,
        CASE WHEN r.asset_return IS NOT NULL AND m.market_return IS NOT NULL
             THEN m.market_return END AS paired_market_return
    FROM asset_returns r
    LEFT JOIN market_returns m
      ON m.signal_month = r.signal_month
     AND m.prior_market = r.prior_market
), idio_rolling AS (
    SELECT
        paired.*,
        count(paired_asset_return) OVER window_24m AS observations,
        var_samp(paired_asset_return) OVER window_24m AS asset_variance,
        var_samp(paired_market_return) OVER window_24m AS market_variance,
        covar_samp(paired_asset_return, paired_market_return)
            OVER window_24m AS asset_market_covariance
    FROM paired
    WINDOW window_24m AS (
        PARTITION BY asset_id
        ORDER BY signal_month
        RANGE BETWEEN INTERVAL '23 months' PRECEDING AND CURRENT ROW
    )
), raw_values AS (
    SELECT
        asset_id,
        trade_date AS as_of_date,
        signal_month,
        sqrt(greatest(
            asset_variance
              - asset_market_covariance * asset_market_covariance
                / market_variance,
            0
        )) AS value
    FROM idio_rolling
    WHERE signal_month BETWEEN %(start_month)s::date AND %(end_month)s::date
      AND name !~* '(스팩|SPAC)'
      AND position('리츠' in name) = 0
      AND (age_days >= 250 OR first_seen = dataset_start)
      AND market_cap > 0
      AND adj_close > 0
      AND observations >= 18
      AND market_variance > 0
      AND asset_variance IS NOT NULL
      AND asset_market_covariance IS NOT NULL
), ranked AS (
    SELECT
        asset_id,
        as_of_date,
        value,
        rank() OVER (
            PARTITION BY signal_month
            ORDER BY value ASC
        ) AS rank
    FROM raw_values
    WHERE value IS NOT NULL
)
SELECT asset_id, as_of_date, value, rank
FROM ranked;
