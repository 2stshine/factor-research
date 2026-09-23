import json
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
                         "adj_close": 100 + asset + t, "trading_value": 10 + asset, "shares": 1000 + asset,
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
    assert study["execution_timing_contract"]["same_close_execution_allowed"] is False
    assert study["execution_timing_contract"]["execution_certified"] is False
    monthly = study["sections"]["monthly_performance"]["data"]["monthly"]
    assert monthly[-1]["month"] == "2021-05"
    assert monthly[0]["rank_ic"] > .99
    pd.testing.assert_frame_equal(frame, original)
    altered = frame.copy()
    mask = altered.ym.ge(pd.Period("2021-06"))
    altered.loc[mask, ["fwd_mid", "net_income_ttm", "f_test", "adj_close", "adv20",
                       "market_cap", "trading_value", "shares"]] = -1e9
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


def test_price_only_factor_has_common_profiles_without_claiming_runtime_usage():
    panel, frame, factor, result, campaign = fixture()
    factor.needs = ()  # Price candidates often do not declare common panel fields.
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    quality = study["sections"]["input_quality"]["data"]
    rows = {row["name"]: row for row in quality["raw_input_profile"]}
    assert rows["adj_close"]["n_present"] == 40 * 39
    assert rows["adj_close"]["roles"] == ["COMMON_MARKET_INPUT"]
    assert rows["adj_close"]["factor_usage"] == "NOT_ESTABLISHED"
    assert rows["adj_close"]["unit"] == "UNKNOWN"
    assert rows["adv20"]["roles"] == ["COMMON_MARKET_INPUT", "AUXILIARY_CONTROL_SOURCE"]
    assert rows["adv20"]["auxiliary_control"] == "log_adv20"
    assert rows["market"]["profile_type"] == "CATEGORICAL"
    assert rows["market"]["n_unique"] == 1
    assert rows["market"]["n_nonnumeric"] is None  # A market label is not a failed numeric parse.
    assert "net_income_ttm" not in rows  # Available auxiliary financials are not claimed as factor inputs.
    assert "fwd_mid" not in rows and "f_test" not in rows and "total_return_close" not in rows
    contract = quality["raw_input_profile_contract"]
    assert contract["schema_version"] == "raw-input-profile-v2"
    assert contract["declared_factor_inputs"] == []
    assert contract["factor_runtime_input_usage"] == "NOT_TRACED"


def test_declared_inputs_deduplicated_and_missing_columns_not_imputed():
    panel, frame, factor, result, campaign = fixture()
    factor.needs = ("adj_close", "adv20", "unknown_declared_field", "adj_close")
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    profiles = study["sections"]["input_quality"]["data"]["raw_input_profile"]
    rows = {row["name"]: row for row in profiles}
    assert len(rows) == len(profiles)
    assert rows["adj_close"]["roles"] == ["DECLARED_FACTOR_INPUT", "COMMON_MARKET_INPUT"]
    assert rows["adv20"]["roles"] == ["DECLARED_FACTOR_INPUT", "COMMON_MARKET_INPUT", "AUXILIARY_CONTROL_SOURCE"]
    assert rows["adj_close"]["factor_usage"] == "DECLARED_NOT_RUNTIME_TRACED"
    absent = rows["unknown_declared_field"]
    assert absent["status"] == "NOT_COLLECTED" and absent["column_present"] is False
    assert absent["n_rows"] > 0 and absent["n_missing"] is None and absent["n_present"] is None
    assert absent["unit"] == "UNKNOWN" and all(value is None for value in absent["quantiles"].values())


def test_common_input_profile_counts_invalid_values_and_uses_only_eligible_rows():
    panel, frame, factor, result, campaign = fixture()
    frame["adj_close"] = frame["adj_close"].astype(object)
    frame.loc[:6, "adj_close"] = [None, np.inf, -np.inf, "bad", False, 0, 10000000]
    panel.investable.iloc[6] = False
    original = frame.copy(deep=True)
    study = capture_discovery(panel, frame, factor, result, campaign, {})
    rows = {row["name"]: row for row in study["sections"]["input_quality"]["data"]["raw_input_profile"]}
    price = rows["adj_close"]
    assert price["n_rows"] == 40 * 39 - 1
    assert price["n_missing"] == 1 and price["n_nonnumeric"] == 2 and price["n_nonfinite"] == 2
    assert price["n_missing_or_nonnumeric"] == 5
    assert price["n_present"] + price["n_missing_or_nonnumeric"] == price["n_rows"]
    assert price["n_zero"] == 1
    expected = pd.to_numeric(original.loc[:1559, "adj_close"], errors="coerce").drop(index=6)
    expected = expected.drop(index=4).replace([np.inf, -np.inf], np.nan).dropna()
    assert price["quantiles"] == {str(q): float(expected.quantile(q)) for q in (.01, .5, .99)}
    json.dumps(study, allow_nan=False)
    pd.testing.assert_frame_equal(frame, original)


def test_present_all_null_input_is_distinct_from_missing_column_and_units_stay_unknown():
    from engine.input_profiles import build_input_profiles

    data = pd.DataFrame({"adj_close": [None, np.nan], "custom_input": ["3", "4"]})
    rows = {row["name"]: row for row in build_input_profiles(data, ("custom_input", "absent"), {})}
    assert rows["adj_close"]["status"] == "NO_FINITE_VALUES"
    assert rows["adj_close"]["n_missing"] == 2 and rows["adj_close"]["n_present"] == 0
    assert rows["adj_close"]["n_nonnumeric"] == 0 and rows["adj_close"]["n_nonfinite"] == 0
    assert rows["absent"]["status"] == "NOT_COLLECTED" and rows["absent"]["n_missing"] is None
    assert rows["custom_input"]["quantiles"]["0.5"] == 3.5
    assert rows["custom_input"]["unit"] == "UNKNOWN"
    assert rows["custom_input"]["roles"] == ["DECLARED_FACTOR_INPUT"]
    json.dumps(rows, allow_nan=False)
