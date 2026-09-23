"""Source freshness is operational metadata, never a changed research gate."""
import pandas as pd
import pytest

from scripts.regime_snapshot import freshness, render, snapshot
from tests.test_assumed_regime_integration import assume_source
from tests.test_regime_readiness import setup


def test_historical_coverage_does_not_imply_current_readiness(tmp_path):
    source, _ = setup(tmp_path)
    report = snapshot(assume_source(tmp_path, source), as_of="2020-05-15")
    row = report["contexts"][0]
    assert report["configured_and_usable"]
    assert not report["all_current_states_ready"]
    assert report["stale_context_ids"] == [source["context_id"]]
    assert row["latest_state"] == "UNKNOWN"
    assert row["freshness"]["source_lag_months"] == 1
    assert "STALE / 1" in render(report)


def test_current_source_can_have_unknown_state():
    result = freshness("2026-08", None, pd.Period("2026-08", freq="M"), False)
    assert result["source_status"] == "CURRENT"
    assert not result["current_state_ready"]
    assert result["latest_usable_lag_months"] is None


def test_current_and_absent_sources_are_distinct():
    last = pd.Period("2026-08", freq="M")
    assert freshness("2026-08", "2026-08", last, True)["current_state_ready"]
    absent = freshness(None, None, last, False)
    assert absent["source_status"] == "NO_COMPLETED_INPUT"
    assert absent["source_lag_months"] is None
    assert not absent["current_state_ready"]


@pytest.mark.parametrize("kind", ["market_index", "macro_state"])
def test_prescope_warmup_is_source_coverage_not_usable_state(tmp_path, kind):
    source, _ = setup(tmp_path, kind=kind, start="2020-01", end="2020-03", history="2016-01")
    report = snapshot(assume_source(tmp_path, source), as_of="2019-12-31")
    row = report["contexts"][0]
    assert row["rows"] == []
    assert row["data_latest_month"] == "2019-12"
    assert row["freshness"]["source_status"] == "CURRENT"
    assert row["freshness"]["source_lag_months"] == 0
    assert not row["freshness"]["current_state_ready"]
    assert not report["configured_and_usable"]
