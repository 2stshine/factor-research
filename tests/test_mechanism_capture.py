from types import SimpleNamespace

import numpy as np
import pandas as pd

from engine.mechanism_capture import capture_discovery


def fixture():
    months = pd.period_range("2018-03", "2022-12", freq="M")
    rows = []
    for t, month in enumerate(months):
        for asset in range(40):
            rows.append({"asset_id": asset, "ym": month, "trade_date": month.to_timestamp("M"),
                         "available_date": month.to_timestamp(), "f_test": asset / 40,
                         "fwd_mid": .001 * asset + np.sin(t) * .01,
                         "market_cap": 100 + asset, "adv20": 10 + asset, "market": "KOSPI",
                         "total_assets": 1000., "net_income_ttm": 20 + asset + .1 * t * asset})
    frame = pd.DataFrame(rows)
    panel = SimpleNamespace(monthly=frame, investable=pd.Series(True, index=frame.index))
    factor = SimpleNamespace(name="test", definition_hash="d", needs=("net_income_ttm", "total_assets"))
    result = SimpleNamespace(checks=[])
    campaign = {"campaign_id": "c", "discovery": {"data_cutoff": "2021-06-30"},
                "oos": {"start": "2021-07"}, "snapshot": {"discovery_input_digest": "s"}}
    return panel, frame, factor, result, campaign


def test_capture_reuses_signed_signal_and_never_reads_oos_or_support():
    panel, frame, factor, result, campaign = fixture()
    original = frame.copy(deep=True)
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    assert study["status"] == "COLLECTED"
    monthly = study["sections"]["monthly_performance"]["data"]["monthly"]
    assert monthly[-1]["month"] == "2021-05"
    assert monthly[0]["rank_ic"] > .99
    pd.testing.assert_frame_equal(frame, original)
    altered = frame.copy()
    mask = altered.ym.ge(pd.Period("2021-06"))
    altered.loc[mask, ["fwd_mid", "net_income_ttm", "f_test"]] = -1e9
    assert capture_discovery(panel, altered, factor, result, campaign, {}) == study


def test_forward_financials_calendar_matched_and_not_filled():
    panel, frame, factor, result, campaign = fixture()
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    economic = study["sections"]["economic_outcomes"]["data"]["outcomes"][0]
    assert economic["name"] == "public_roa_change_12m"
    assert economic["monthly"][0]["top_minus_bottom"] > 0
    assert economic["monthly"][-1]["n_outcome_available"] == 0
    assert economic["top_minus_bottom"]["ci95"] is None


def test_invalid_signal_not_interpreted_as_failed_economics():
    panel, frame, factor, result, campaign = fixture()
    result.checks = [SimpleNamespace(tier="T0.11", passed=False)]
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    assert study == {"status": "NOT_COLLECTED", "reason": "SIGNAL_INTEGRITY_FAILED"}


def test_missing_fundamentals_not_fabricated():
    panel, frame, factor, result, campaign = fixture()
    frame = frame.drop(columns=["available_date", "net_income_ttm"])
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    assert study["sections"]["economic_outcomes"]["status"] == "NOT_COLLECTED"
