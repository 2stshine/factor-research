"""Synthetic new-campaign context wiring; no factor result or OOS reads."""
from copy import deepcopy
import hashlib

import pandas as pd
import pytest

from engine.regime_inputs import digest as macro_digest, freeze_context
from engine.research_regime_production import (
    _digest, freeze_regime_context, load_adoption_contract, macro_catalog,
    project_regime_context, validate_frozen_context,
)
from tests.test_research_regime_adoption import adopt, encode, inputs  # noqa: F401
from tests.test_regime_inputs import bundle


def frozen(inputs, **kwargs):
    options = dict(signal_start="2016-01", data_cutoff="2018-04-30", oos_start="2018-05",
                   frozen_at="2018-05-01T10:00:00+09:00")
    options.update(kwargs)
    return freeze_regime_context(adopt(inputs), **options)


def test_market_specific_mapping_and_missing_history(inputs):
    # Deliberately make the two source markets differ, preserving rule integrity.
    shadow, _policy, original, _ = inputs
    for row in original["markets"]["KOSDAQ"]["rows"]:
        if row["status"] == "READY_SHADOW":
            row["close"] = row["sma_10m"] * (.9 if row["trend"] == "UP" else 1.1)
            row["trend"] = "UP" if row["close"] >= row["sma_10m"] else "DOWN"
            row["trend_distance"] = row["close"] / row["sma_10m"] - 1
            row["regime"] = row["trend"] + "_" + row["relative_risk"]
    shadow.write_bytes(encode(original))
    contract = frozen(inputs)
    frame = pd.DataFrame({"month": ["2017-12", "2017-12", "2018-03", "2017-12"],
                          "market": ["KOSPI", "KOSDAQ", "KOSPI", "KONEX"]}, index=[3, 7, 1, 2])
    before = frame.copy()
    projected, metadata = project_regime_context(frame, contract)
    pd.testing.assert_frame_equal(frame, before)
    assert projected.iloc[0].market_regime != projected.iloc[1].market_regime
    assert list(projected.iloc[2:].market_regime) == ["UNKNOWN", "UNKNOWN"]
    assert list(projected.iloc[2:].regime_input_status) == ["OUTSIDE_FROZEN_SOURCE_SCOPE", "UNSUPPORTED_MARKET"]
    assert metadata["market_views"]["KOSPI"]["row_indices"] == [0, 2]
    assert metadata["market_views"]["KOSPI"]["unknown_months"] == ["2018-03"]
    assert metadata["market_views"]["KOSDAQ"]["row_indices"] == [1]
    assert metadata["pooled_regime_analysis_allowed"] is False
    assert "UNKNOWN" not in metadata["regime"]["labels"]
    assert metadata["macro_specs"] == {}


def test_frozen_copy_scopes_before_embargo_and_survives_source_changes(inputs):
    source = adopt(inputs)
    before = deepcopy(source)
    contract = freeze_regime_context(source, signal_start="2016-01", data_cutoff="2017-07-31",
                                     oos_start="2017-08", frozen_at="2018-05-01T10:00:00+09:00")
    assert source == before
    assert contract["signal_end"] == "2017-06"
    for entry in contract["markets"].values():
        assert entry["rows"][-1]["month"] == "2017-06"
    source["markets"]["KOSPI"]["rows"][-1]["regime"] = "BAD"
    validate_frozen_context(contract, data_cutoff="2017-07-31", oos_start="2017-08")


def test_no_overlap_is_unknown_not_claimed_future_coverage(inputs):
    contract = frozen(inputs, signal_start="2018-02")
    assert all(not entry["rows"] for entry in contract["markets"].values())
    frame, _metadata = project_regime_context(pd.DataFrame({"month": ["2018-03"], "market": ["KOSPI"]}), contract)
    assert frame.iloc[0].market_regime == "UNKNOWN"
    assert pd.isna(frame.iloc[0].regime_known_at)


@pytest.mark.parametrize("change", ["hash", "market", "policy", "rule", "scope", "authority", "row", "future"])
def test_tamper_rejected_even_if_envelope_is_rehashed(inputs, change):
    contract = frozen(inputs)
    if change == "hash":
        contract["signal_start"] = "2016-02"
    elif change == "market":
        contract["market_assignment"] = "POOLED_KOSPI"
    elif change == "policy":
        contract["adoption"]["policy"]["snapshot"]["historical_pit_verified"] = True
    elif change == "rule":
        contract["rules"]["reference_months"] = 6
    elif change == "scope":
        contract["markets"]["KOSPI"]["rows"].pop()
    elif change == "authority":
        contract["trading_allowed"] = True
    elif change == "row":
        contract["markets"]["KOSPI"]["rows"][-1]["decision_at"] = "2018-05-01T00:00:00+09:00"
    else:
        contract["frozen_at"] = "2018-01-02T00:00:00+09:00"
    if change != "hash":
        contract["sha256"] = _digest({k: v for k, v in contract.items() if k != "sha256"})
    with pytest.raises(ValueError):
        validate_frozen_context(contract)


def test_macro_catalog_and_at_most_two_predeclared_axes(inputs):
    data = bundle()
    macro = data["contexts"][1]
    next(row for row in macro["source"]["rows"] if row["month"] == "2017-12")["known_at"] = "2018-01-01"
    macro["approval"]["source_sha256"] = macro_digest(macro["source"])
    context = freeze_context(data, data_cutoff="2018-04-30", oos_start="2018-05")
    contract = frozen(inputs, macro_context=context)
    catalog = macro_catalog(contract)
    assert list(catalog) == ["test_macro"]
    assert "rows" not in catalog["test_macro"]
    frame = pd.DataFrame({"month": ["2017-11", "2017-12"], "market": ["KOSPI", "KOSDAQ"]})
    _plain, default = project_regime_context(frame, contract)
    assert default["macro_specs"] == {}
    projected, metadata = project_regime_context(frame, contract, macro_axes=["test_macro"])
    spec = metadata["macro_specs"]["test_macro"]
    assert projected.iloc[-1][spec["column"]] == "UNKNOWN"
    assert spec["pit_status"] == "VERIFIED"
    assert spec["contrast"] is None  # requires the hypothesis's explicit contrast
    for selection in (["test_macro"] * 2, ["a", "b", "c"], ["nonexistent"]):
        with pytest.raises(ValueError):
            project_regime_context(frame, contract, macro_axes=selection)


def test_unknown_input_rows_and_missing_markets_are_preserved(inputs):
    contract = frozen(inputs, signal_start="2015-01")
    projected, metadata = project_regime_context(pd.DataFrame({"month": ["2015-01"] * 3,
                                                  "market": ["KOSPI", None, pd.NA]}), contract)
    assert set(projected.market_regime) == {"UNKNOWN"}
    assert metadata["unrecognized_market_rows"] == 2


def test_projection_rejects_outside_discovery_and_column_overwrite(inputs):
    contract = frozen(inputs)
    for month in ("2015-12", "2018-04", "2018-05"):
        with pytest.raises(ValueError, match="Discovery"):
            project_regime_context(pd.DataFrame({"month": [month], "market": ["KOSPI"]}), contract)
    with pytest.raises(ValueError, match="overwrite"):
        project_regime_context(pd.DataFrame({"month": ["2017-12"], "market": ["KOSPI"],
                                             "market_regime": ["UP_LOW"]}), contract)
    with pytest.raises(ValueError, match="boundary"):
        validate_frozen_context(contract, data_cutoff="2018-03-31")


def test_loader_requires_explicit_actual_file_hash(inputs, tmp_path):
    path = tmp_path / "adopted.json"
    path.write_bytes(encode(adopt(inputs)))
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert load_adoption_contract(path, expected_sha256=actual)["pit_status"] == "PIT_ASSUMED"
    with pytest.raises(ValueError, match="file hash"):
        load_adoption_contract(path, expected_sha256="a" * 64)
