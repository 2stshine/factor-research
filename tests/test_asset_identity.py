"""Contracts that bind cached research rows to live KRX asset identities."""
from __future__ import annotations

import pickle
import re

import pandas as pd
import pytest

from engine import silver
from engine.panel import (
    Panel,
    asset_identity_evidence,
    bind_asset_identity,
    from_silver_frame,
    verify_asset_identity,
)
from scripts import run as run_script


def _return_evidence(run_id: str = "q") -> dict:
    evidence = {
        "validation_status": "VERIFIED",
        "contract_release": silver.TOTAL_RETURN_CONTRACT_RELEASE,
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "dividend_treatment": silver.TOTAL_RETURN_DIVIDEND_TREATMENT,
        "quality_run_id": run_id,
        "coverage_start": "2024-01-31",
        "coverage_end": "2024-02-29",
        "certified_scope_start": "2015-01-01",
        "certified_markets": ["KOSPI", "KOSDAQ"],
        "price_row_count": 2,
        "asset_count": 1,
        "action_snapshot_run_id": "action-run",
        "action_snapshot_schema_version": (
            silver.TOTAL_RETURN_ACTION_SNAPSHOT_SCHEMA
        ),
        "action_snapshot_manifest_sha256": "a" * 64,
        "action_snapshot_body_digest": "b" * 64,
        "pit_scope_contract": silver.TOTAL_RETURN_PIT_SCOPE_CONTRACT,
        "pit_input_action_count": 1,
        "pit_included_action_count": 1,
        "pit_excluded_action_count": 0,
        "source_receipt_row_count": 1,
        "source_receipt_row_digest": "d" * 64,
        "terminal_economic_receipt_count": 1,
        "terminal_economic_receipt_digest": "e" * 64,
        "published_action_count": 1,
        "published_action_row_digest": "f" * 64,
        "published_action_scope_contract": (
            "issuer_cash_ex_plus_manifest_scale_support_v1"
        ),
        "included_cash_action_parity_count": 1,
        "included_cash_action_parity_digest": "1" * 64,
        "cash_scale_source_contract": (
            silver.TOTAL_RETURN_CASH_SCALE_SOURCE_CONTRACT
        ),
        "cash_scale_source_evidence_count": 0,
        "cash_scale_source_evidence_digest": "3" * 64,
        "cash_scale_source_manifest_sha256": "5" * 64,
        "cash_scale_source_manifest_digest": "6" * 64,
        "cash_scale_support_action_count": 0,
        "cash_scale_support_action_digest": "7" * 64,
        "cash_scale_support_manifest_digest": "8" * 64,
        "cash_scale_support_semantic_group_count": 0,
        "disclosure_observation_contract": (
            silver.TOTAL_RETURN_DISCLOSURE_OBSERVATION_CONTRACT
        ),
        "disclosure_mutable_conflict_digest": "2" * 64,
        "research_role": dict(silver.TOTAL_RETURN_RESEARCH_ROLE),
        "resolution_version": silver.TOTAL_RETURN_RESOLUTION_VERSION,
        "cash_action_count": 1,
        "canonical_event_count": 1,
        "applied_event_count": 1,
        "excluded_event_count": 0,
        "cash_scale_resolution_contract": (
            silver.TOTAL_RETURN_CASH_SCALE_RESOLUTION_CONTRACT
        ),
        "cash_scale_resolution_row_count": 1,
        "cash_scale_resolution_row_digest": "4" * 64,
        "cash_scale_stable_event_count": 1,
        "cash_scale_changed_event_count": 0,
        "cash_scale_evidence_match_count": 0,
        "cash_scale_adjusted_cash_parity_count": 1,
        "cash_scale_first_listing_exclusion_count": 0,
        "cash_scale_explicit_exclusion_count": 0,
        "cash_scale_adj_close_decimal_places": 4,
        "cash_scale_cash_in_adj_close": False,
        "asset_identity_contract": silver.TOTAL_RETURN_ASSET_IDENTITY_CONTRACT,
        "asset_identity_digest": "c" * 64,
    }
    evidence["evidence_sha256"] = silver.total_return_evidence_sha256(evidence)
    return evidence


def _identity_rows() -> pd.DataFrame:
    return pd.DataFrame({
        "asset_id": [1, 2, 1, 2],
        "Code": ["000001", "000002", "000001", "000002"],
        "trade_date": [
            "2024-01-31", "2024-01-31", "2024-02-29", "2024-02-29",
        ],
    })


def _cache_panel(rows: pd.DataFrame, *, bind: bool = True) -> Panel:
    frame = rows.copy()
    frame["adj_close"] = 100.0
    frame["total_return_close"] = 100.0
    panel = Panel(
        frame, pd.Series(dtype="datetime64[ns]"),
        meta=silver.return_role_contract(),
    )
    if bind:
        bind_asset_identity(panel)
    return panel


def _silver_rows() -> pd.DataFrame:
    frame = pd.DataFrame({
        "asset_id": [1, 1],
        "Code": ["000001", "000001"],
        "Name": ["테스트", "테스트"],
        "instrument_type": ["common_stock", "common_stock"],
        "listed_from": [None, None],
        "listed_to": [None, None],
        "trade_date": ["2024-01-31", "2024-02-29"],
        "close": [100.0, 101.0],
        "adj_close": [100.0, 101.0],
        "total_return_close": [100.0, 102.0],
        "trading_value": [1_000_000.0, 1_100_000.0],
        "market_cap": [10_000_000.0, 10_100_000.0],
        "shares": [100_000.0, 100_000.0],
        "market": ["KOSPI", "KOSPI"],
        "adv20": [900_000.0, 950_000.0],
        "age_days": [300, 320],
        "first_seen": ["2023-01-02", "2023-01-02"],
        "dataset_start": ["2020-01-02", "2020-01-02"],
        "quality_run_id": ["q", "q"],
        "total_return_quality_run_id": ["q", "q"],
        "amihud_illiquidity_1m": [1e-9, 1e-9],
        "amihud_observations_1m": [20, 20],
        "daily_volatility_252d": [.01, .01],
        "daily_return_observations_252d": [252, 252],
        "max_daily_return_1m": [.02, .02],
        "max_daily_return_observations_1m": [20, 20],
        "price_high_252d": [110.0, 111.0],
        "price_high_observations_252d": [252, 252],
    })
    frame.attrs["return_contract"] = {
        "status": "CERTIFIED",
        "methodology_version": silver.TOTAL_RETURN_METHOD,
        "quality_run_id": "q",
        "validation_evidence": _return_evidence(),
    }
    frame.attrs["return_roles"] = silver.return_role_contract()
    return frame


def test_identity_digest_is_order_and_non_identity_column_invariant():
    frame = _identity_rows()
    original = asset_identity_evidence(frame)

    changed = frame.sample(frac=1, random_state=7).reset_index(drop=True)
    changed["f_arbitrary_factor"] = [9.0, 8.0, 7.0, 6.0]
    changed["Name"] = ["d", "c", "b", "a"]
    assert asset_identity_evidence(changed) == original
    assert original["asset_identity_contract"] == (
        "krx_month_end_asset_ticker_v1"
    )


@pytest.mark.parametrize("column,replacement", [
    ("asset_id", 99),
    ("Code", "999999"),
    ("trade_date", "2024-02-28"),
])
def test_identity_digest_is_sensitive_to_each_canonical_field(
    column: str, replacement,
):
    frame = _identity_rows()
    original = asset_identity_evidence(frame)["asset_identity_digest"]
    frame.loc[2, column] = replacement
    changed = asset_identity_evidence(frame)["asset_identity_digest"]
    assert changed != original


def test_identity_cutoff_ignores_later_appends():
    cutoff = "2024-01-31"
    base = _identity_rows().iloc[:2].copy()
    appended = _identity_rows()

    assert asset_identity_evidence(base, cutoff=cutoff) == (
        asset_identity_evidence(appended, cutoff=cutoff)
    )


def test_identity_rejects_duplicate_asset_and_duplicate_code_per_month():
    duplicated_asset = _identity_rows().iloc[:2].copy()
    duplicated_asset.loc[1, "asset_id"] = 1
    with pytest.raises(RuntimeError, match=r"\(asset_id, month\).+중복"):
        asset_identity_evidence(duplicated_asset)

    duplicated_code = _identity_rows().iloc[:2].copy()
    duplicated_code.loc[1, "Code"] = "000001"
    with pytest.raises(RuntimeError, match=r"\(Code, month\).+중복"):
        asset_identity_evidence(duplicated_code)


@pytest.mark.parametrize("bad_code", [None, "", "  ", " 000001", 1])
def test_identity_rejects_blank_or_non_exact_text_code(bad_code):
    frame = _identity_rows().iloc[:2].copy()
    frame["Code"] = frame["Code"].astype(object)
    frame.loc[0, "Code"] = bad_code
    with pytest.raises(RuntimeError, match="정확한 문자열"):
        asset_identity_evidence(frame)


def test_from_silver_frame_binds_identity_metadata():
    prices = _silver_rows()
    expected = asset_identity_evidence(prices)

    built = from_silver_frame(prices, verbose=False)

    for key in silver.ASSET_IDENTITY_META_KEYS:
        assert built.meta[key] == expected[key]
    assert verify_asset_identity(built) == expected


def test_panel_identity_metadata_missing_or_tampered_fails_closed():
    panel = Panel(_identity_rows(), pd.Series(dtype="datetime64[ns]"))
    bind_asset_identity(panel)

    missing = Panel(panel.monthly.copy(), panel.dead.copy(), {})
    with pytest.raises(RuntimeError, match="메타데이터가 없습니다"):
        verify_asset_identity(missing)

    panel.meta["asset_identity_digest"] = "0" * 64
    with pytest.raises(RuntimeError, match="캐시 내용과 다릅니다"):
        verify_asset_identity(panel)


def test_live_identity_remap_fails_before_research(monkeypatch):
    cached = _identity_rows()
    expected = asset_identity_evidence(cached)
    live = cached.copy()
    live.loc[live["Code"].eq("000001"), "asset_id"] = 2
    live.loc[live["Code"].eq("000002"), "asset_id"] = 1
    live["ticker_match_count"] = 1

    monkeypatch.setattr(
        silver, "read_frame", lambda conn, sql, params=None: live.copy(),
    )
    with pytest.raises(RuntimeError, match="현재 RDS.+다릅니다"):
        silver.verify_live_asset_identity(object(), expected)


def test_confirmation_detects_remap_confined_to_closure_month(monkeypatch):
    cached = _identity_rows()
    required = cached[cached["trade_date"].eq("2024-01-31")].copy()
    panel = Panel(required, pd.Series(dtype="datetime64[ns]"))
    bind_asset_identity(panel)
    run_script._bind_closure_asset_identity(
        panel.meta, asset_identity_evidence(cached),
    )

    live_required = required.copy()
    live_closure = cached.copy()
    closure_rows = live_closure["trade_date"].eq("2024-02-29")
    live_closure.loc[closure_rows, "asset_id"] = [2, 1]
    live_required["ticker_match_count"] = 1
    live_closure["ticker_match_count"] = 1

    def live_rows(_conn, _sql, params=None):
        cutoff = params[0]
        return (
            live_required.copy()
            if cutoff == "2024-01-31"
            else live_closure.copy()
        )

    monkeypatch.setattr(silver, "read_frame", live_rows)
    with pytest.raises(RuntimeError, match="현재 RDS.+다릅니다"):
        run_script._verify_confirmation_live_identity(object(), panel)


def test_prospective_confirmation_does_not_match_future_rows_to_start_snapshot():
    start = Panel(
        _identity_rows().iloc[:2].copy(),
        pd.Series(dtype="datetime64[ns]"),
    )
    bind_asset_identity(start)
    confirmation = Panel(
        _identity_rows().copy(),
        pd.Series(dtype="datetime64[ns]"),
    )
    confirmation_identity = bind_asset_identity(confirmation)

    observed = run_script._assert_confirmation_asset_identity(
        confirmation,
        mode="prospective_holdout",
        historical_snapshot_identity_digest=start.meta["asset_identity_digest"],
    )
    assert observed == confirmation_identity

    with pytest.raises(ValueError, match="confirmation asset identity"):
        run_script._assert_confirmation_asset_identity(
            confirmation,
            mode="trailing_historical_holdout",
            historical_snapshot_identity_digest=(
                start.meta["asset_identity_digest"]
            ),
        )


def test_live_query_rejects_overlapping_pit_tickers(monkeypatch):
    ambiguous = _identity_rows().iloc[:2].copy()
    ambiguous["ticker_match_count"] = [2, 1]
    monkeypatch.setattr(
        silver, "read_frame", lambda conn, sql, params=None: ambiguous.copy(),
    )

    with pytest.raises(RuntimeError, match="유효기간 중첩"):
        silver.load_asset_identity_snapshot(object(), cutoff="2024-01-31")

    sql = re.sub(r"\s+", " ", silver.ASSET_IDENTITY_SQL.lower())
    assert "count(ai.identifier) as ticker_match_count" in sql
    assert "limit 1" not in sql


def test_read_only_connections_use_one_repeatable_read_snapshot(monkeypatch):
    class FakeConnection:
        isolation_level = None
        read_only = None

    connections = []

    def fake_connect(*args, **kwargs):
        del args, kwargs
        connection = FakeConnection()
        connections.append(connection)
        return connection

    monkeypatch.setattr(silver, "database_url", lambda: "postgresql://local/db")
    monkeypatch.setattr(silver.psycopg, "connect", fake_connect)

    read_connection = silver.connect(read_only=True)
    assert read_connection.read_only is True
    assert read_connection.isolation_level == (
        silver.psycopg.IsolationLevel.REPEATABLE_READ
    )

    write_connection = silver.connect(read_only=False)
    assert write_connection.read_only is False
    assert write_connection.isolation_level is None


def test_panel_activation_archives_previous_cache_and_is_atomic(
    monkeypatch, tmp_path,
):
    cache = tmp_path / "cache"
    active = cache / "panel.pkl"
    archive = cache / "panels"
    monkeypatch.setattr(run_script, "CACHE", cache)
    monkeypatch.setattr(run_script, "PANEL_CACHE", active)
    monkeypatch.setattr(run_script, "PANEL_ARCHIVE", archive)
    cache.mkdir()

    previous = _cache_panel(_identity_rows())
    with active.open("wb") as handle:
        pickle.dump(previous, handle)
    previous_bytes = active.read_bytes()

    changed_rows = _identity_rows().copy()
    changed_rows["asset_id"] = changed_rows["asset_id"] + 10
    current = _cache_panel(changed_rows)
    current_identity = verify_asset_identity(current)
    active_path, previous_archive = run_script._activate_panel_cache(current)

    assert active_path == active
    assert previous_archive is not None
    assert previous_archive.read_bytes() == previous_bytes
    with active.open("rb") as handle:
        activated = pickle.load(handle)
    assert verify_asset_identity(activated) == current_identity
    versioned = (
        archive / current_identity["asset_identity_digest"]
        / run_script._file_sha256(active) / "panel.pkl"
    )
    assert versioned.read_bytes() == active.read_bytes()

    active_bytes = active.read_bytes()
    invalid = _cache_panel(changed_rows, bind=False)
    with pytest.raises(RuntimeError, match="메타데이터가 없습니다"):
        run_script._activate_panel_cache(invalid)
    assert active.read_bytes() == active_bytes


def test_same_identity_can_archive_different_panel_contents(monkeypatch, tmp_path):
    cache = tmp_path / "cache"
    monkeypatch.setattr(run_script, "CACHE", cache)
    monkeypatch.setattr(run_script, "PANEL_CACHE", cache / "panel.pkl")
    monkeypatch.setattr(run_script, "PANEL_ARCHIVE", cache / "panels")

    first = _cache_panel(_identity_rows())
    first.monthly["fundamental"] = 1.0
    run_script._activate_panel_cache(first)

    second = _cache_panel(_identity_rows())
    second.monthly["fundamental"] = 2.0
    run_script._activate_panel_cache(second)

    identity = first.meta["asset_identity_digest"]
    versions = sorted((cache / "panels" / identity).glob("*/panel.pkl"))
    assert len(versions) == 2
    assert len({run_script._file_sha256(path) for path in versions}) == 2
