from copy import deepcopy

import pandas as pd
import pytest

from engine import fundamental_contract as fc, fundamentals
from engine.panel import Panel
from scripts.build_historical_revenue_panel import replace_financials
from tests.test_historical_fundamental_overlay import base, bundle


def parent():
    dates = pd.to_datetime(["2016-03-31", "2016-04-29", "2023-08-31"])
    frame = pd.DataFrame(dict(asset_id=[1]*3, Code=["000001"]*3, trade_date=dates,
        ym=dates.to_period("M"), adj_close=[10., 11., 12.], fwd_mid=[.1, .2, .3]))
    result = Panel(frame, pd.Series(dtype="datetime64[ns]"), {"source": "SYNTHETIC"})
    raw = base()
    fund = fc.materialize(raw, verbose=False)
    result.monthly = fundamentals.attach(result.monthly, fund, sorted(fundamentals.PIT_FEATURES))
    fc.bind(result, raw, materialized=fund)
    return result


def test_real_replay_switches_source_contract_and_preserves_parent_and_labels():
    old = parent()
    original = deepcopy(old)
    new = replace_financials(old, base(), bundle())
    pd.testing.assert_frame_equal(old.monthly, original.monthly)
    assert old.meta == original.meta
    assert fc.META_KEY not in new.meta
    assert fc.OVERLAY_META_KEY in new.meta
    assert fc.verify(new)["status"] == "VERIFIED_EXPIRY_AWARE_OVERLAY_REPLAY"
    assert new.monthly.revenue_ttm.iloc[0] == 100
    assert pd.isna(new.monthly.revenue_ttm.iloc[-1])
    assert new.monthly.fwd_mid.tolist() == old.monthly.fwd_mid.tolist()


def test_invalid_parent_is_not_blessed_by_overlay():
    old = parent()
    old.monthly.loc[0, "revenue_ttm"] = 999
    with pytest.raises(RuntimeError):
        replace_financials(old, base(), bundle())


def test_different_base_financials_cannot_change_non_revenue_columns():
    altered = base()
    altered.loc[altered.metric.eq("total_assets"), "value"] = "999"
    with pytest.raises(ValueError, match="does not reproduce"):
        replace_financials(parent(), altered, bundle())


def test_old_precomputed_signals_are_removed_but_return_labels_preserved():
    old = parent()
    old.monthly["f_old_signal"] = 123.
    new = replace_financials(old, base(), bundle())
    assert "f_old_signal" not in new.monthly
    assert "fwd_mid" in new.monthly
    assert "f_old_signal" in old.monthly
