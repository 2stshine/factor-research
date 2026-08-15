from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.implementation import validate_feature_sql
from engine.publish import VALUE_CONTRACT_ID


ROOT = Path(__file__).parents[1]
MANIFEST_PATH = ROOT / "implementations/gold/manifest.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

EXPECTED_DEFINITIONS = {
    "amihud_illiquidity_1m": (1, "72bd57d66a5cb84d"),
    "book_to_market_change_12m": (1, "e73b53f0ffaaf3c5"),
    "capital_stock_growth_12m": (-1, "e09f61de6fa86d70"),
    "capital_stock_to_assets": (-1, "dd1d0d32a2a49a3c"),
    "current_asset_turnover": (1, "05c6633ec72d4e6a"),
    "idiosyncratic_volatility_24m": (-1, "af24645c3a81a842"),
    "max_daily_return_1m": (-1, "e29c3da27f06a3ba"),
    "net_equity_issuance_price_adjusted_12m": (-1, "01ee73e28cd8f170"),
    "net_income_to_liabilities": (1, "0cb38fb5ad3db869"),
    "net_working_capital_yield": (1, "0c14cdb6457bdf0a"),
    "operating_earnings_yield": (1, "692110a461d94df5"),
    "operating_income_to_current_liabilities": (1, "eaf7784cd83b4082"),
    "operating_income_to_liabilities": (1, "5ff8c69343b28a3f"),
    "paid_in_capital_ratio": (-1, "8c82db0117290bcd"),
    "pretax_income_to_liabilities": (1, "47ef014a02b341ff"),
    "realized_volatility_252d": (-1, "e0668fb0e7c0eb69"),
    "revenue_to_noncurrent_assets": (1, "29eedb3de737a6f9"),
    "revenue_to_total_liabilities": (1, "50c3bd228268077e"),
    "retained_earnings_to_equity": (1, "ede7286f5e5ca082"),
    "short_term_reversal_3m": (-1, "bb5c9a621d0bd540"),
    "trading_turnover_20d": (-1, "c03efb8638407bd6"),
}

EXPECTED_BATCH_SQL = {
    "book_to_market_change_12m": "campaign_20260815_007_value_capital.sql",
    "capital_stock_to_assets": "campaign_20260815_007_value_capital.sql",
    "current_asset_turnover": "campaign_20260814_002_batch.sql",
    "net_income_to_liabilities": "campaign_20260815_004_income_coverage.sql",
    "operating_earnings_yield": "campaign_20260814_002_batch.sql",
    "operating_income_to_current_liabilities": "campaign_20260814_002_batch.sql",
    "pretax_income_to_liabilities": "campaign_20260815_004_income_coverage.sql",
    "retained_earnings_to_equity": "campaign_20260814_002_batch.sql",
    "revenue_to_noncurrent_assets": "campaign_20260815_009_revenue_reversal.sql",
    "revenue_to_total_liabilities": "revenue_to_total_liabilities.sql",
    "short_term_reversal_3m": "campaign_20260815_009_revenue_reversal.sql",
}


def _sql(factor_name: str) -> str:
    return (ROOT / MANIFEST[factor_name]["sql"]).read_text(encoding="utf-8")


def test_manifest_owns_the_reviewed_query_only_implementations_locally():
    assert set(MANIFEST) == set(EXPECTED_DEFINITIONS)
    for factor_name, spec in MANIFEST.items():
        path = (ROOT / spec["sql"]).resolve()
        assert ROOT.resolve() in path.parents
        assert path.is_file()
        if "result_factor" in spec:
            assert spec["sql"] == (
                "implementations/gold/factors/"
                f"{EXPECTED_BATCH_SQL[factor_name]}"
            )
            assert spec["result_factor"] == factor_name
            assert "query_chunk_months" not in spec
        else:
            assert spec["sql"] == f"implementations/gold/factors/{factor_name}.sql"
            if factor_name == "idiosyncratic_volatility_24m":
                assert spec["query_chunk_months"] == 24
            else:
                assert "query_chunk_months" not in spec
        assert spec["feature_price_field"] == "adj_close"
        assert spec["value_contract"] == VALUE_CONTRACT_ID
        expected_sign, expected_hash = EXPECTED_DEFINITIONS[factor_name]
        assert spec["predicted_sign"] == expected_sign
        assert spec["research_definition_hash"] == expected_hash
        assert len(hashlib.sha256(path.read_bytes()).hexdigest()) == 64


def test_campaign_batch_implementation_has_exact_factor_discriminators():
    batch = {
        name: spec["result_factor"]
        for name, spec in MANIFEST.items()
        if "result_factor" in spec
    }
    assert batch == {
        "book_to_market_change_12m": "book_to_market_change_12m",
        "capital_stock_to_assets": "capital_stock_to_assets",
        "current_asset_turnover": "current_asset_turnover",
        "net_income_to_liabilities": "net_income_to_liabilities",
        "operating_earnings_yield": "operating_earnings_yield",
        "operating_income_to_current_liabilities": (
            "operating_income_to_current_liabilities"
        ),
        "pretax_income_to_liabilities": "pretax_income_to_liabilities",
        "revenue_to_noncurrent_assets": "revenue_to_noncurrent_assets",
        "revenue_to_total_liabilities": "revenue_to_total_liabilities",
        "retained_earnings_to_equity": "retained_earnings_to_equity",
        "short_term_reversal_3m": "short_term_reversal_3m",
    }


def test_campaign_batch_reuses_one_narrow_causal_price_ordering():
    sql = _sql("current_asset_turnover")
    assert "p.*" not in sql
    assert "month_rank" not in sql
    assert "trade_date DESC" not in sql
    assert "lead(p.trade_date) OVER (asset_history)" in sql
    assert "PARTITION BY p.asset_id ORDER BY p.trade_date" in sql
    assert "stats.prior_rows + row_number()" in sql
    assert "price_stats AS MATERIALIZED" in sql
    assert "universe AS MATERIALIZED" in sql


def test_campaign_batch_replays_fundamentals_once_as_effective_intervals():
    sql = _sql("current_asset_turnover")
    assert "fundamental_candidates AS MATERIALIZED" in sql
    assert "effective_fundamental_events AS" in sql
    assert "first_cfs_date" in sql
    assert "lead(available_date) OVER" in sql
    assert "f.next_available_date > u.trade_date" in sql
    assert "f.available_date <= u.trade_date" in sql
    assert "PARTITION BY\n                u.asset_id, u.trade_date" not in sql
    assert MANIFEST["current_asset_turnover"].get("query_chunk_months") is None
    assert MANIFEST["current_asset_turnover"]["planner_enable_nestloop"] is False
    assert "public.fundamental" not in _sql("idiosyncratic_volatility_24m")


def test_price_only_idio_chunks_preserve_the_exact_legacy_value_contract():
    sql = _sql("idiosyncratic_volatility_24m")
    assert "(%(start_month)s::date - INTERVAL '24 months')" in sql
    assert "RANGE BETWEEN INTERVAL '23 months' PRECEDING AND CURRENT ROW" in sql
    assert "asset_variance" in sql
    assert "asset_market_covariance * asset_market_covariance" in sql
    assert "observations >= 18" in sql
    assert "ORDER BY value ASC" in sql
    assert MANIFEST["idiosyncratic_volatility_24m"]["query_chunk_months"] == 24


def test_every_implementation_is_read_only_and_uses_the_certified_feature_view():
    for factor_name, spec in MANIFEST.items():
        sql = _sql(factor_name)
        validate_feature_sql(sql)
        assert "public.factor_price_feature_daily" in sql
        assert "public.price_daily" not in sql
        assert "total_return_close" not in sql
        assert "%(start_month)s" in sql
        assert "%(end_month)s" in sql
        assert "INSERT INTO" not in sql.upper()
        assert "adj_close > 0" in sql
        rank_order = "DESC" if spec["predicted_sign"] == 1 else "ASC"
        assert (
            "ORDER BY value * predicted_sign DESC" in sql
            or f"ORDER BY value {rank_order}" in sql
        )


def test_daily_price_implementations_match_research_windows():
    snippets = {
        "amihud_illiquidity_1m": (
            "avg(abs(daily_price_return) / trading_value) FILTER",
            "amihud_observations_1m >= 10",
        ),
        "max_daily_return_1m": (
            "max(daily_price_return) OVER",
            "max_daily_return_observations_1m >= 10",
        ),
        "realized_volatility_252d": (
            "stddev_samp(daily_price_return) OVER",
            "ROWS BETWEEN 251 PRECEDING AND CURRENT ROW",
            "daily_return_observations_252d >= 126",
        ),
    }
    for factor_name, required in snippets.items():
        sql = _sql(factor_name)
        assert "trade_date >= DATE '2015-01-01'" in sql
        assert "certified_feature_price" in sql
        for snippet in required:
            assert snippet in sql


def test_accounting_implementations_are_point_in_time():
    for factor_name in (
        "current_asset_turnover",
        "operating_earnings_yield",
        "operating_income_to_current_liabilities",
        "operating_income_to_liabilities",
        "paid_in_capital_ratio",
        "retained_earnings_to_equity",
    ):
        sql = _sql(factor_name)
        body = "\n".join(
            line for line in sql.splitlines()
            if not line.lstrip().startswith("--")
        )
        assert (
            "f.available_date <= u.trade_date" in sql
            if "result_factor" in MANIFEST[factor_name]
            else "f.available_date <= u.as_of_date" in sql
        )
        assert "q.status = 'CERTIFIED'" in sql
        assert "fundamental_current" not in body


def test_net_equity_issuance_uses_price_adjusted_exact_calendar_lag():
    sql = _sql("net_equity_issuance_price_adjusted_12m")
    assert "market_cap::double precision / adj_close::double precision" in sql
    assert "lag(adjusted_share_base, 12)" in sql
    assert "lag(signal_month, 12)" in sql
    assert "prior_adjusted_share_base > 0" in sql
    assert "signal_month = prior_signal_month + INTERVAL '12 months'" in sql


def test_turnover_uses_current_plus_previous_nineteen_rows():
    sql = _sql("trading_turnover_20d")
    assert "ROWS BETWEEN 19 PRECEDING AND CURRENT ROW" in sql
    assert "adv20 > 0" not in sql
