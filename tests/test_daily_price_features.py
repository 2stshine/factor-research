"""Contracts for daily-derived features in the Silver month-end snapshot."""
from __future__ import annotations

import re

import pandas as pd
import pytest

from engine import silver
from engine.panel import from_silver_frame


DAILY_FEATURES = {
    "amihud_illiquidity_1m": "1.25e-12",
    "amihud_observations_1m": "20",
    "daily_volatility_252d": "0.018",
    "daily_return_observations_252d": "252",
    "max_daily_return_1m": "0.071",
    "max_daily_return_observations_1m": "20",
    "price_high_252d": "12345.0",
    "price_high_observations_252d": "252",
}


def _normalized_sql() -> str:
    return re.sub(r"\s+", " ", silver.PRICE_SNAPSHOT_SQL.lower()).strip()


def _snapshot_row() -> pd.DataFrame:
    row = {
        "asset_id": 1,
        "Code": "005930",
        "Name": "삼성전자",
        "instrument_type": "common_stock",
        "listed_from": None,
        "listed_to": None,
        "trade_date": "2026-07-31",
        "close": "10000",
        "adj_close": "9900",
        "total_return_close": "10300",
        "trading_value": "5000000000",
        "market_cap": "100000000000",
        "shares": "10000000",
        "market": "KOSPI",
        "adv20": "4000000000",
        "age_days": "300",
        "first_seen": "2025-01-02",
        "dataset_start": "2015-01-02",
        "quality_run_id": "q",
        **DAILY_FEATURES,
    }
    frame = pd.DataFrame([row])
    frame.attrs["return_contract"] = {
        "status": "CERTIFIED",
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "quality_run_id": "q",
    }
    return frame


def test_daily_feature_sql_uses_total_return_for_returns_and_adj_close_for_high():
    sql = _normalized_sql()

    assert "lag(p.total_return_close) over" in sql
    assert "total_return_close / prior_total_return_close - 1" in sql
    assert "avg(abs(daily_total_return) / trading_value) filter" in sql
    assert "trading_value > 0" in sql
    assert "stddev_samp(daily_total_return) over" in sql
    assert "max(daily_total_return) over" in sql
    assert "max(adj_close) over" in sql
    assert "lag(p.adj_close)" not in sql


def test_daily_feature_sql_is_trailing_or_same_calendar_month_only():
    sql = _normalized_sql()

    assert sql.count("rows between 251 preceding and current row") == 4
    assert "following" not in sql
    assert sql.count(
        "partition by asset_id, date_trunc('month', trade_date)"
    ) >= 5
    assert "where month_rank = 1" in sql


def test_panel_requires_and_normalizes_daily_feature_contract():
    panel = from_silver_frame(_snapshot_row(), verbose=False)

    for column, raw_value in DAILY_FEATURES.items():
        assert column in panel.monthly
        assert panel.monthly.loc[0, column] == pytest.approx(float(raw_value))

    missing = _snapshot_row().drop(columns=["price_high_252d"])
    with pytest.raises(ValueError, match="price_high_252d"):
        from_silver_frame(missing, verbose=False)


def test_panel_keeps_total_return_and_split_adjusted_price_semantics_distinct():
    panel = from_silver_frame(_snapshot_row(), verbose=False)
    row = panel.monthly.iloc[0]

    assert row["return_close"] == pytest.approx(10300.0)
    assert row["adj_close"] == pytest.approx(9900.0)
    assert row["price_high_252d"] == pytest.approx(12345.0)
