import hashlib
import json

import pytest

from scripts.prepare_dart_historical_identity import validate_snapshot


def snapshot(periods, **updates):
    payload = dict(schema="asset-listing-snapshot-v1", coverage_start="2015-01-01",
                   verified_through="2023-07-31", periods=periods, **updates)
    payload["snapshot_id"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return (payload["snapshot_id"], payload, "7b6db911-1aaa-43fa-b085-947f9c2c650d", "CERTIFIED")


def test_clamps_verified_window_and_preserves_zeroes():
    rows = validate_snapshot(snapshot([dict(asset_id=1, ticker="005930", start="1975-06-11", end=None)]))
    assert rows[0]["stock_code"] == "005930"
    assert rows[0]["valid_from"] == "2015-01-01"
    assert rows[0]["valid_until_exclusive"] == "2023-08-01"


def test_inclusive_listing_end_becomes_exclusive():
    rows = validate_snapshot(snapshot([dict(asset_id=1, ticker="005930", start="2015-02-01", end="2018-01-31")]))
    assert rows[0]["valid_until_exclusive"] == "2018-02-01"


def test_outside_window_does_not_backdate():
    assert validate_snapshot(snapshot([dict(asset_id=1, ticker="005930", start="2024-01-01", end=None)])) == []


def test_ticker_reuse_overlap_fails():
    with pytest.raises(ValueError, match="Overlapping"):
        validate_snapshot(snapshot([dict(asset_id=1, ticker="005930", start="2015-01-01", end=None),
                                    dict(asset_id=2, ticker="005930", start="2016-01-01", end=None)]))


def test_tamper_and_uncertified_fail():
    row = snapshot([])
    with pytest.raises(ValueError, match="certification"):
        validate_snapshot((*row[:3], "FAILED"))
    row[1]["verified_through"] = "2026-01-01"
    with pytest.raises(ValueError, match="fingerprint"):
        validate_snapshot(row)


def test_valid_alphanumeric_source_ticker_is_preserved_not_coerced():
    rows = validate_snapshot(snapshot([dict(asset_id=1, ticker="00104K", start="2015-01-01", end=None)]))
    assert rows[0]["stock_code"] == "00104K"


def test_malformed_six_character_ticker_fails():
    with pytest.raises(ValueError, match="malformed"):
        validate_snapshot(snapshot([dict(asset_id=1, ticker="00593!", start="2015-01-01", end=None)]))
