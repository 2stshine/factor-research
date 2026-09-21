"""A partially tagged Gold catalog must never authorize a partial cache."""
import pandas as pd
import pytest

from engine import silver
from scripts import run


def generation_row(*, count=2, bound=2, distinct=1, digest="a" * 64):
    return pd.DataFrame([{
        "approved_factor_count": count,
        "generation_bound_factor_count": bound,
        "generation_digest_count": distinct,
        "gold_generation_digest": digest,
        "approved_factor_keys": ["alpha", "beta"][:count],
    }])


@pytest.mark.parametrize("bound", [0, 1])
def test_unbound_catalog_is_uncacheable(monkeypatch, bound):
    row = generation_row(bound=bound, distinct=int(bound > 0),
                         digest="a" * 64 if bound else None)
    monkeypatch.setattr(silver, "read_frame", lambda *_: row)
    assert silver.load_gold_generation(object()) is None


def test_fully_bound_catalog_can_use_cache(monkeypatch):
    monkeypatch.setattr(silver, "read_frame", lambda *_: generation_row())
    assert silver.load_gold_generation(object()) == {
        "gold_generation_digest": "a" * 64,
        "approved_factor_count": 2,
        "approved_factor_keys": ["alpha", "beta"],
    }


@pytest.mark.parametrize("kwargs", [
    {"bound": 1, "distinct": 2}, {"bound": 1, "digest": "invalid"},
    {"bound": 1, "distinct": 0, "digest": None}, {"bound": 3},
])
def test_conflicting_or_malformed_binding_still_fails_closed(monkeypatch, kwargs):
    monkeypatch.setattr(silver, "read_frame", lambda *_: generation_row(**kwargs))
    with pytest.raises(RuntimeError):
        silver.load_gold_generation(object())


def test_partial_generation_reads_all_approved_without_cache_or_writes(monkeypatch):
    monkeypatch.setattr(silver, "read_frame", lambda *_: generation_row(bound=1))
    monkeypatch.setattr(silver, "load_approved_factor_keys", lambda _: ["alpha", "beta"])
    calls = []
    values = pd.DataFrame({"factor_key": ["alpha", "beta"], "asset_id": [1, 1],
                           "as_of_date": pd.to_datetime(["2023-01-31"] * 2), "value": [.2, .7]})
    monkeypatch.setattr(silver, "load_approved_values_for_targets", lambda *_: calls.append("fresh") or values)
    def forbidden(*_):
        pytest.fail("Unbound generation must not read/write a cache or bind Gold")
    monkeypatch.setattr(run, "_load_gold_signal_cache", forbidden)
    monkeypatch.setattr(run, "_write_gold_signal_cache", forbidden)
    monkeypatch.setattr(silver, "bind_gold_generation", forbidden)
    frame = pd.DataFrame({"asset_id": [1], "ym": pd.PeriodIndex(["2023-01"], freq="M")})
    first = run._approved_signals(object(), frame)
    second = run._approved_signals(object(), frame)
    assert calls == ["fresh", "fresh"]
    assert set(first) == {"alpha", "beta"}
    assert first["beta"].iloc[0] == .7
    pd.testing.assert_series_equal(first["alpha"], second["alpha"])


@pytest.mark.parametrize("names", [["alpha", "alpha"], ["alpha", "unknown"]])
def test_legacy_values_cannot_hide_duplicate_or_unknown_keys(monkeypatch, names):
    monkeypatch.setattr(silver, "load_gold_generation", lambda _: None)
    monkeypatch.setattr(silver, "load_approved_factor_keys", lambda _: ["alpha"])
    monkeypatch.setattr(silver, "load_approved_values_for_targets", lambda *_: pd.DataFrame({
        "factor_key": names, "asset_id": [1, 1],
        "as_of_date": pd.to_datetime(["2023-01-30", "2023-01-31"]), "value": [.2, .7],
    }))
    frame = pd.DataFrame({"asset_id": [1], "ym": pd.PeriodIndex(["2023-01"], freq="M")})
    with pytest.raises(RuntimeError):
        run._approved_signals(object(), frame)


def test_target_lookup_uses_unique_whole_month_keys(monkeypatch):
    from datetime import date
    seen = []
    monkeypatch.setattr(silver, "read_frame", lambda c, sql, params: seen.append((sql, params)))
    silver.load_approved_values_for_targets(object(), pd.DataFrame({
        "asset_id": [2, 1, 2],
        "ym": pd.PeriodIndex(["2023-02", "2023-01", "2023-02"], freq="M"),
    }))
    assert seen == [(silver.APPROVED_TARGET_VALUES_SQL,
                     ([1, 2], [date(2023, 1, 1), date(2023, 2, 1)]))]
    assert "ORDER BY as_of_date DESC" in seen[0][0]
    assert "LIMIT 1" in seen[0][0]
    assert "WHERE f.status = 'APPROVED'" in seen[0][0]


@pytest.mark.parametrize("asset,month", [(None, "2023-01"), (1.5, "2023-01"),
                                         (-1, "2023-01"), (1, None),
                                         (True, "2023-01"), (2**63, "2023-01")])
def test_invalid_target_does_not_query(monkeypatch, asset, month):
    def forbidden(*_):
        pytest.fail("Invalid keys must not reach RDS")
    monkeypatch.setattr(silver, "read_frame", forbidden)
    with pytest.raises(ValueError):
        silver.load_approved_values_for_targets(object(), pd.DataFrame({
            "asset_id": [asset], "ym": [month],
        }))


def test_empty_target_does_not_query(monkeypatch):
    def forbidden(*_):
        pytest.fail("Empty scope needs no query")
    monkeypatch.setattr(silver, "read_frame", forbidden)
    result = silver.load_approved_values_for_targets(object(), pd.DataFrame(columns=["asset_id", "ym"]))
    assert result.empty
    assert list(result) == ["factor_key", "asset_id", "as_of_date", "value"]


def test_missing_legacy_gold_catalog_needs_no_value_query(monkeypatch):
    monkeypatch.setattr(silver, "load_gold_generation", lambda _: None)
    monkeypatch.setattr(silver, "load_approved_factor_keys", lambda _: [])
    def forbidden(*_):
        pytest.fail("Absent catalog must not query a missing factor_value table")
    monkeypatch.setattr(silver, "load_approved_values_for_targets", forbidden)
    assert run._approved_signals(object(), pd.DataFrame()) == {}
