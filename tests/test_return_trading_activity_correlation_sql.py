"""Independent synthetic Silver fixtures in a private, TCP-disabled PostgreSQL.

No connection settings, cached panels, campaign artifacts, or RDS are used.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

import numpy as np
import pandas as pd
import psycopg
import pytest

from engine import implementation, research_policy
from factors.candidates import return_trading_activity_correlation_12m as candidate


ROOT = Path(__file__).parents[1]
FACTOR_NAME = "return_trading_activity_correlation_12m"
SPEC = json.loads((ROOT / "implementations/gold/manifest.json").read_text())[FACTOR_NAME]
SQL_PATH = ROOT / SPEC["sql"]


@pytest.fixture(scope="module")
def synthetic_postgres(tmp_path_factory):
    initdb, pg_ctl = shutil.which("initdb"), shutil.which("pg_ctl")
    if not initdb or not pg_ctl:
        pytest.skip("local PostgreSQL binaries are unavailable")
    work = tmp_path_factory.mktemp("price_activity_sql")
    data = work / "data"
    # macOS has a short Unix socket path limit; pytest's data path may exceed it.
    socket_context = tempfile.TemporaryDirectory(prefix="frpg-", dir="/tmp")
    socket = Path(socket_context.name)
    subprocess.run(
        [initdb, "-D", str(data), "-A", "trust", "--no-locale", "-E", "UTF8"],
        check=True, capture_output=True, text=True,
    )
    options = shlex.join(["-h", "", "-k", str(socket), "-p", "6543", "-F"])
    subprocess.run(
        [pg_ctl, "-D", str(data), "-l", str(work / "postgres.log"),
         "-o", options, "-w", "start"],
        check=True, capture_output=True, text=True,
    )
    try:
        with psycopg.connect(host=str(socket), port=6543, dbname="postgres") as conn:
            yield conn
    finally:
        subprocess.run(
            [pg_ctl, "-D", str(data), "-m", "fast", "-w", "stop"],
            check=True, capture_output=True, text=True,
        )
        socket_context.cleanup()


def _synthetic_daily():
    records = []
    months = pd.period_range("2014-01", "2016-12", freq="M")
    for asset_id in range(1, 14):
        phase = 0.0 if asset_id in (1, 3) else asset_id * 0.3
        price = 100.0
        for step, month in enumerate(months):
            price *= 1.0 + 0.04 * np.sin(step * 0.7 + phase)
            activity = np.exp(18.0 + 0.4 * np.cos(step * 0.9 + phase))
            dates = pd.bdate_range(month.start_time, month.end_time)
            if asset_id == 4:
                # Anchor listing age at dataset start; sparse ADV20 spans years.
                dates = dates[:1] if step == 0 else dates[-1:]
            if asset_id == 5 and month == pd.Period("2015-08", "M"):
                continue
            if asset_id == 13 and month < pd.Period("2015-11", "M"):
                continue
            if asset_id == 8:
                price = 100.0
            if asset_id == 9:
                activity = 1e8
            if asset_id == 7 and month == pd.Period("2015-07", "M"):
                activity = 0.0
            for trade_date in dates:
                close = price
                if (asset_id == 6 and month == pd.Period("2015-07", "M")
                        and trade_date == dates[-1]):
                    close = np.inf
                records.append((asset_id, trade_date, close, activity))
    return pd.DataFrame(records, columns=[
        "asset_id", "trade_date", "adj_close", "trading_value",
    ])


def _populate_and_reference(conn):
    daily = _synthetic_daily()
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE public.dq_run (run_id integer, status text);
            CREATE TABLE public.asset (
                asset_id integer, name text, exchange text, asset_type text,
                instrument_type text
            );
            CREATE TABLE public.asset_identifier (
                asset_id integer, source text, identifier_type text,
                valid_from date, valid_to date
            );
            CREATE TABLE public.factor_price_feature_daily (
                asset_id integer, trade_date date, adj_close numeric,
                trading_value numeric, market_cap numeric,
                source text, market text, quality_run_id integer
            );
            INSERT INTO public.dq_run VALUES (1, 'CERTIFIED');
        """)
        cursor.executemany(
            "INSERT INTO public.asset VALUES (%s, %s, 'KRX', 'stock', %s)",
            [(asset_id, {10: "Example SPAC", 11: "Example 리츠"}.get(asset_id),
              "preferred_stock" if asset_id == 12 else "common_stock")
             for asset_id in range(1, 14)],
        )
        cursor.executemany(
            "INSERT INTO public.asset_identifier VALUES (%s, 'KRX', 'ticker', "
            "'2014-01-01', NULL)",
            [(asset_id,) for asset_id in range(1, 14)],
        )
        cursor.executemany(
            "INSERT INTO public.factor_price_feature_daily VALUES "
            "(%s, %s, %s, %s, 1000000000, 'KRX', 'KOSPI', 1)",
            [(int(row.asset_id), row.trade_date.date(), float(row.adj_close),
              float(row.trading_value)) for row in daily.itertuples()],
        )
    conn.commit()
    daily["first_seen"] = daily.groupby("asset_id")["trade_date"].transform("min")
    daily["age_days"] = daily.groupby("asset_id").cumcount() + 1
    daily["ym"] = daily["trade_date"].dt.to_period("M")
    # The certified ADV20 excludes pre-2015 values before rolling, even when
    # a sparse asset's last nineteen daily rows extend into prior years.
    visible = daily.loc[daily["ym"] >= pd.Period("2015-01", "M")].copy()
    visible["adv20"] = visible.groupby("asset_id")["trading_value"].transform(
        lambda value: value.rolling(20, min_periods=1).mean()
    )
    monthly = visible.groupby(["asset_id", "ym"], sort=False).tail(1).copy()
    monthly = monthly.loc[monthly["asset_id"] != 12].reset_index(drop=True)
    monthly["instrument_type"] = "common_stock"
    monthly["market"] = "KOSPI"
    raw = research_policy.compute_factor(candidate.FACTOR, monthly)
    universe = (
        ~monthly["asset_id"].isin([10, 11])
        & ((monthly["age_days"] >= 250)
           | monthly["first_seen"].eq(daily["trade_date"].min()))
        & monthly["adj_close"].gt(0)
    )
    valid = universe & np.isfinite(raw)
    reference = monthly.loc[valid, ["asset_id", "trade_date"]].rename(
        columns={"trade_date": "as_of_date"},
    )
    reference["value"] = raw.loc[valid].to_numpy()
    return reference


def _query(conn, start, end):
    with conn.cursor() as cursor:
        cursor.execute(SQL_PATH.read_text(), {
            "start_month": start + "-01", "end_month": end + "-01",
        })
        return pd.DataFrame(cursor.fetchall(), columns=[
            column.name for column in cursor.description
        ])


def test_synthetic_silver_raw_keys_and_negative_direction_rank_parity(synthetic_postgres):
    conn = synthetic_postgres
    reference = _populate_and_reference(conn)
    actual = _query(conn, "2016-01", "2016-12")
    evidence = implementation.compare_parity(
        candidate.FACTOR, reference, actual,
        implementation_uri=f"repo://factor-research/{SPEC['sql']}",
        implementation_sha256=hashlib.sha256(SQL_PATH.read_bytes()).hexdigest(),
        manifest_spec=SPEC,
        discovery_signal_start="2016-01", discovery_signal_end="2016-12",
        discovery_snapshot_digest="a" * 64,
        strategy_sha256=hashlib.sha256(Path(candidate.__file__).read_bytes()).hexdigest(),
    )
    assert evidence["passed"], json.dumps(evidence, indent=2)
    assert {1, 2, 3, 4, 5, 6, 7, 13}.issubset(set(actual["asset_id"]))
    assert not set(actual["asset_id"]).intersection({8, 9, 10, 11, 12})
    for asset_id, first_month in ((5, "2016-09"), (6, "2016-08"), (7, "2016-07")):
        assert str(pd.to_datetime(actual.loc[
            actual["asset_id"].eq(asset_id), "as_of_date"
        ]).min().to_period("M")) == first_month
    # A later output request must still use all required trading-day history.
    narrowed = _query(conn, "2016-09", "2016-12")
    expected = actual.loc[pd.to_datetime(actual["as_of_date"]) >= "2016-09-01"]
    columns = ["as_of_date", "asset_id"]
    pd.testing.assert_frame_equal(
        narrowed.sort_values(columns).reset_index(drop=True),
        expected.sort_values(columns).reset_index(drop=True),
    )
