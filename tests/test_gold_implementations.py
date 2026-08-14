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
    "max_daily_return_1m": (-1, "e29c3da27f06a3ba"),
    "net_equity_issuance_price_adjusted_12m": (-1, "01ee73e28cd8f170"),
    "operating_income_to_liabilities": (1, "5ff8c69343b28a3f"),
    "paid_in_capital_ratio": (-1, "8c82db0117290bcd"),
    "realized_volatility_252d": (-1, "e0668fb0e7c0eb69"),
    "trading_turnover_20d": (-1, "c03efb8638407bd6"),
}


def _sql(factor_name: str) -> str:
    return (ROOT / MANIFEST[factor_name]["sql"]).read_text(encoding="utf-8")


def test_manifest_owns_the_reviewed_query_only_implementations_locally():
    assert set(MANIFEST) == set(EXPECTED_DEFINITIONS)
    for factor_name, spec in MANIFEST.items():
        path = (ROOT / spec["sql"]).resolve()
        assert ROOT.resolve() in path.parents
        assert path.is_file()
        assert spec["sql"] == f"implementations/gold/factors/{factor_name}.sql"
        assert spec["feature_price_field"] == "adj_close"
        assert spec["value_contract"] == VALUE_CONTRACT_ID
        expected_sign, expected_hash = EXPECTED_DEFINITIONS[factor_name]
        assert spec["predicted_sign"] == expected_sign
        assert spec["research_definition_hash"] == expected_hash
        assert len(hashlib.sha256(path.read_bytes()).hexdigest()) == 64


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
        assert f"ORDER BY value {rank_order}" in sql


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
    for factor_name in ("paid_in_capital_ratio", "operating_income_to_liabilities"):
        sql = _sql(factor_name)
        body = "\n".join(
            line for line in sql.splitlines()
            if not line.lstrip().startswith("--")
        )
        assert "f.available_date <= u.as_of_date" in sql
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
