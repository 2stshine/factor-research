import copy

import numpy as np
import pandas as pd
import pytest

from engine.reference_library import (
    FEATURE_CONTRACTS, FEATURE_UNITS, IDENTITY_CONTRACT, INPUT_SCOPE,
    calculate_reference_panel, definition_hash, input_panel_digest, load_catalog,
    validate_catalog,
)


def panel():
    dates = pd.date_range("2023-01-31", periods=26, freq="ME")
    rows = []
    for asset, code, initial in [(7, "005930", 100.0), (9, "000660", 300.0)]:
        for month, day in enumerate(dates):
            price = initial * (1.02 ** month)
            rows.append(dict(asset_id=asset, stock_code=code, date=day,
                             known_at=day.tz_localize("Asia/Seoul") + pd.Timedelta(hours=16),
                             market="KOSPI", adj_close=price, market_cap=price * 1e6,
                             daily_volatility_252d=.02, daily_return_observations_252d=252,
                             amihud_illiquidity_1m=1e-10, amihud_observations_1m=20,
                             price_high_252d=price * 1.25, price_high_observations_252d=252,
                             max_daily_return_1m=.12, max_daily_return_observations_1m=20))
    return pd.DataFrame(rows)


def attestation(frame):
    return dict(status="CERTIFIED", source_version="synthetic-contract-test-only",
                source_contract="TEST_PRICE_INPUT", evidence_sha256="a" * 64,
                input_sha256=input_panel_digest(frame), identity_contract=IDENTITY_CONTRACT,
                scope=INPUT_SCOPE, feature_contracts=copy.deepcopy(FEATURE_CONTRACTS),
                units=copy.deepcopy(FEATURE_UNITS))


def calculate(frame, **kwargs):
    return calculate_reference_panel(frame, input_attestation=attestation(frame), **kwargs)


def test_catalog_has_sixteen_curated_references_without_alpha_approval():
    catalog = load_catalog()
    assert len(catalog) == 16
    assert sum(d["readiness"]["status"] == "IMPLEMENTED_REQUIRES_ATTESTATION" for d in catalog) == 7
    assert all(not d["alpha_approved"] and len(d["definition_hash"]) == 64 for d in catalog)
    assert all(d["adaptation"] and d["sources"] for d in catalog)


def test_definition_hash_stable_and_covers_changes():
    item = load_catalog()[0]
    assert definition_hash(item) == definition_hash(dict(reversed(list(item.items()))))
    changed = {**item, "orientation": 1}
    assert definition_hash(item) != definition_hash(changed)
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_catalog([changed])


def test_all_seven_measurements_match_independent_closed_form():
    result = calculate(panel())
    latest = result.values.query("asset_id == '7'").sort_values("date").groupby("reference_id").tail(1).set_index("reference_id")
    expected = {"kr_size_issue_v1": np.log(100 * 1.02 ** 25 * 1e6),
                "kr_momentum_12_2_price_v1": 1.02 ** 11 - 1,
                "kr_reversal_1m_price_v1": .02, "kr_low_volatility_252d_v1": .02,
                "kr_amihud_1m_v1": 1e-10, "kr_high_252d_v1": .8, "kr_max_1m_v1": .12}
    for ref, value in expected.items():
        assert latest.loc[ref, "value"] == pytest.approx(value)
    for definition in load_catalog():
        if definition["id"] in latest.index:
            row = latest.loc[definition["id"]]
            assert row.oriented_value == pytest.approx(row.value * definition["orientation"])
    assert len(result.blocked) == 9
    assert result.validation["alpha_approved"] is False


def test_exact_month_alignment_and_skip_latest_month():
    frame = panel()
    ref = ["kr_momentum_12_2_price_v1"]
    baseline = calculate(frame, definitions=ref).values
    changed = frame.copy()
    latest = changed.date.max()
    changed.loc[changed.date.eq(latest), "adj_close"] *= 10
    pd.testing.assert_frame_equal(baseline[["asset_id", "date", "value"]],
                                  calculate(changed, definitions=ref).values[["asset_id", "date", "value"]])
    missing_date = frame.date.unique()[15]
    with_gap = frame.loc[~((frame.asset_id == 7) & (frame.date == missing_date))]
    result = calculate(with_gap, definitions=ref).values
    assert not ((result.asset_id == "7") & (result.date > missing_date)).any()
    assert (result.asset_id == "9").sum() == 14


def test_future_perturbation_does_not_change_past_measurements():
    frame = panel()
    cutoff = pd.Timestamp("2024-03-31")
    original = calculate(frame, as_of=cutoff).values
    changed = frame.copy()
    future = changed.date.gt(cutoff)
    for column in FEATURE_CONTRACTS:
        changed.loc[future, column] *= 2
    actual = calculate(changed, as_of=cutoff).values
    columns = [c for c in original if c != "input_sha256"]
    pd.testing.assert_frame_equal(original[columns], actual[columns])


def test_identifier_zeros_and_ticker_reuse_do_not_stitch_assets():
    frame = panel()
    frame.loc[frame.asset_id.eq(9), "date"] += pd.DateOffset(years=3)
    frame.loc[frame.asset_id.eq(9), "date"] = frame.loc[frame.asset_id.eq(9), "date"] + pd.offsets.MonthEnd(0)
    frame.loc[frame.asset_id.eq(9), "known_at"] = frame.loc[frame.asset_id.eq(9), "date"].dt.tz_localize("Asia/Seoul")
    frame.loc[frame.asset_id.eq(9), "stock_code"] = "005930"
    result = calculate(frame, definitions=["kr_momentum_12_2_price_v1"]).values
    assert set(result.stock_code) == {"005930"}
    assert result.groupby("asset_id").size().to_dict() == {"7": 14, "9": 14}
    broken = panel()
    broken.stock_code = broken.stock_code.astype(int)
    with pytest.raises(ValueError, match="six-character"):
        input_panel_digest(broken)


@pytest.mark.parametrize("code", ["0037T0", "0007K0", "005930"])
def test_canonical_krx_alphanumeric_codes_preserved_exactly(code):
    frame = panel()
    frame.loc[frame.asset_id.eq(7), "stock_code"] = code
    result = calculate(frame, definitions=["kr_size_issue_v1"]).values
    assert set(result.loc[result.asset_id.eq("7"), "stock_code"]) == {code}


@pytest.mark.parametrize("code", ["0037t0", "００３７Ｔ０", "٠٠٥٩٣٠", "0037T", "00037T0", 5930, None])
def test_noncanonical_or_coerced_krx_codes_rejected(code):
    frame = panel()
    frame["stock_code"] = frame["stock_code"].astype(object)
    frame.loc[frame.asset_id.eq(7), "stock_code"] = code
    with pytest.raises(ValueError, match="six-character|Null identity"):
        input_panel_digest(frame)


@pytest.mark.parametrize("column,value", [("market_cap", np.inf), ("market_cap", 0),
                                           ("daily_volatility_252d", -1), ("amihud_illiquidity_1m", np.nan),
                                           ("max_daily_return_1m", -1), ("price_high_252d", 0)])
def test_nonfinite_and_invalid_values_are_not_published(column, value):
    frame = panel()
    frame[column] = value
    result = calculate(frame)
    assert np.isfinite(result.values.value).all()
    relevant = next(d["id"] for d in load_catalog() if column in d["required_columns"])
    summary = next(d for d in result.validation["references"] if d["reference_id"] == relevant)
    assert summary["status"] == "NO_VALID_ROWS"
    assert summary["value_rows"] == 0
    assert relevant not in set(result.values.reference_id)


@pytest.mark.parametrize("column,value", [("daily_return_observations_252d", 199),
                                           ("daily_return_observations_252d", 253),
                                           ("amihud_observations_1m", 14),
                                           ("price_high_observations_252d", 251),
                                           ("max_daily_return_observations_1m", 20.5)])
def test_frozen_measurement_count_rules(column, value):
    frame = panel()
    frame[column] = value
    definition = next(d for d in load_catalog() if column in d["required_columns"])
    result = calculate(frame, definitions=[definition["id"]])
    assert result.values.empty
    assert result.validation["references"][0]["status"] == "NO_VALID_ROWS"


def test_mismatched_digest_blocks_reuse_of_attestation():
    frame = panel()
    proof = attestation(frame)
    frame.loc[0, "market_cap"] += 1
    with pytest.raises(ValueError, match="digest mismatch"):
        calculate_reference_panel(frame, input_attestation=proof)


@pytest.mark.parametrize("field,value", [("status", "PIT_ASSUMED"), ("scope", "ALL_STOCKS"),
                                        ("identity_contract", "CURRENT_TICKER"),
                                        ("evidence_sha256", "missing")])
def test_attestation_scope_status_identity_and_provenance_guards(field, value):
    frame = panel()
    proof = attestation(frame)
    proof[field] = value
    with pytest.raises(ValueError):
        calculate_reference_panel(frame, input_attestation=proof)


def test_aggregate_units_and_estimators_are_not_assumed_from_column_names():
    frame = panel()
    proof = attestation(frame)
    proof["units"]["amihud_illiquidity_1m"] = "PER_MILLION_KRW"
    proof["feature_contracts"]["daily_volatility_252d"] = "ANNUALIZED_STD"
    result = calculate_reference_panel(frame, input_attestation=proof)
    assert {"kr_amihud_1m_v1", "kr_low_volatility_252d_v1"} <= {d["reference_id"] for d in result.blocked}


@pytest.mark.parametrize("column", ["fwd_return", "total_return_close", "net_income"])
def test_labels_and_unattested_accounting_inputs_are_rejected(column):
    frame = panel()
    frame[column] = 1.0
    with pytest.raises(ValueError, match="forbidden"):
        input_panel_digest(frame)


def test_financial_definitions_stay_blocked_without_period_scope_and_vintage_adapter():
    result = calculate(panel(), definitions=["kr_gross_profitability_pit_v1", "kr_asset_growth_pit_v1"])
    assert result.values.empty and len(result.blocked) == 2
    assert all(d["status"] == "BLOCKED" for d in result.blocked)


def test_known_at_after_formation_and_naive_times_rejected():
    frame = panel()
    frame.loc[0, "known_at"] = pd.Timestamp("2023-02-01T00:00:00+09:00")
    with pytest.raises(ValueError, match="not known"):
        input_panel_digest(frame)
    frame = panel()
    frame.known_at = frame.known_at.dt.tz_localize(None)
    with pytest.raises(ValueError, match="timezone"):
        input_panel_digest(frame)


def test_duplicate_asset_month_or_ambiguous_ticker_rejected():
    frame = panel()
    with pytest.raises(ValueError, match="Duplicate asset-month"):
        input_panel_digest(pd.concat([frame, frame.iloc[:1]]))
    frame.stock_code = "005930"
    with pytest.raises(ValueError, match="Ambiguous ticker"):
        input_panel_digest(frame)


def test_digest_deterministic_under_row_and_column_permutation():
    frame = panel()
    assert input_panel_digest(frame) == input_panel_digest(frame.sample(frac=1, random_state=7)[list(reversed(frame.columns))])


def test_missing_columns_block_only_affected_reference():
    frame = panel().drop(columns=["price_high_252d"])
    result = calculate(frame)
    assert "kr_high_252d_v1" in {item["reference_id"] for item in result.blocked}
    assert "kr_momentum_12_2_price_v1" in set(result.values.reference_id)


def test_no_silent_numeric_string_or_boolean_conversion():
    frame = panel()
    frame.market_cap = frame.market_cap.astype(str)
    with pytest.raises(ValueError, match="Numeric feature"):
        input_panel_digest(frame)
    frame = panel()
    frame.market_cap = True
    with pytest.raises(ValueError, match="Numeric feature"):
        input_panel_digest(frame)
