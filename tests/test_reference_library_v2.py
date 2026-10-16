"""Expanded measurement contracts: synthetic features only, no DB or labels."""
from copy import deepcopy
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from engine import reference_library as base
from engine import reference_library_v2 as lib
from engine.reference_expansion_formulas import FINANCIAL_FORMULAS
from engine.reference_price_expansion import REFERENCE_SPECS


def panel():
    rows = []
    for asset, code, initial in [(7, "005930", 100.), (9, "0037T0", 300.)]:
        for month, date in enumerate(pd.date_range("2020-01-31", periods=40, freq="ME")):
            row = {column: 20. for column in lib.FEATURE_COLUMNS}
            row.update(asset_id=asset, stock_code=code, date=date,
                       known_at=date.tz_localize("Asia/Seoul") + pd.Timedelta(hours=16),
                       market="KOSPI", adj_close=initial * 1.02 ** month,
                       market_cap=initial * 1.02 ** month * 1e6,
                       daily_volatility_252d=.02, daily_return_observations_252d=252.,
                       price_high_252d=initial * 1.02 ** month * 1.25,
                       price_high_observations_252d=252., amihud_illiquidity_1m=1e-10,
                       max_daily_return_1m=.12, share_turnover_1m=.03,
                       share_turnover_cv_1m=.5, mean_traded_value_1m=1e8,
                       traded_value_cv_1m=.3, zero_volume_fraction_1m=.1,
                       downside_semideviation_252d=.015, return_skew_252d=-.2,
                       parkinson_variance_1m=.001, overnight_return_1m=.02,
                       intraday_return_1m=.01, positive_return_days_1m=12.,
                       negative_return_days_1m=8., nominal_close=initial)
            for column in lib.FINANCIAL_COLUMNS:
                row[column] = 80. if column.startswith("prev_") else 100.
            row.update(fy_total_assets=200., prev_fy_total_assets=160.,
                       fy_revenue=100., prev_fy_revenue=60., fy_net_income=20.,
                       fy_operating_income=30., fy_operating_cash_flow=25.,
                       fy_gross_profit=40., fy_current_assets=120.,
                       fy_current_liabilities=60.)
            rows.append(row)
    return pd.DataFrame(rows).loc[:, lib.ALL_COLUMNS]


def attestation(frame):
    return dict(status="CERTIFIED", source_type=lib.SOURCE_TYPE,
                source_contract=lib.SOURCE_CONTRACT, pit_status=lib.PIT_STATUS,
                first_vintage_independently_verified=False,
                identity_contract=base.IDENTITY_CONTRACT, scope=base.INPUT_SCOPE,
                feature_contracts=deepcopy(lib.FEATURE_CONTRACTS),
                feature_units=deepcopy(lib.FEATURE_UNITS),
                source_version="a" * 64, evidence_sha256="a" * 64,
                input_sha256=lib.input_digest(frame))


def calculate(frame, ref):
    return lib.calculate_one(frame, ref, attestation=attestation(frame))


def test_frozen_catalog_45_ids_hashes_and_original_seven_unchanged():
    catalog = base.load_catalog(lib.CATALOG_PATH)
    generated = lib.make_catalog()
    assert {d["id"] for d in catalog} == base._EXECUTABLE | set(REFERENCE_SPECS) | set(FINANCIAL_FORMULAS)
    assert len(catalog) == 45
    assert all(d["role"] == "MEASUREMENT_CONTROL" and d["alpha_approved"] is False for d in catalog)
    assert [d["definition_hash"] for d in catalog] == [base.definition_hash(d) for d in generated["definitions"]]
    original = {d["id"]: d["definition_hash"] for d in base.load_catalog()}
    for definition in catalog:
        if definition["id"] in base._EXECUTABLE:
            assert definition["definition_hash"] == original[definition["id"]]
    raw = json.loads(lib.CATALOG_PATH.read_bytes())
    literature = lib.ROOT / "research/phenomena/reference-expansion-literature.json"
    assert raw["literature_sha256"] == hashlib.sha256(literature.read_bytes()).hexdigest()


def test_all_45_software_measurements_compute_without_alpha_promotion():
    frame = panel()
    proof = attestation(frame)
    for definition in base.load_catalog(lib.CATALOG_PATH):
        values, summary = lib.calculate_one(frame, definition["id"], attestation=proof)
        assert summary["status"] == "MEASUREMENT_VALIDATED"
        assert summary["input_rows"] == len(frame)
        assert summary["value_rows"] + summary["missing_or_invalid_rows"] == len(frame)
        assert set(values) == set(base._OUTPUT)
        assert np.isfinite(values.value).all()
        assert np.allclose(values.oriented_value, values.value * definition["orientation"])
        assert set(values.stock_code) == {"005930", "0037T0"}
        assert set(values.source_version) == {"a" * 64}


def test_financial_closed_form_and_exact_fiscal_pair_fields():
    frame = panel()
    expected = {"kr_roa_fy_v1": .1, "kr_cfo_assets_fy_v1": .125,
                "kr_cashflow_accruals_fy_v1": -.025, "kr_asset_growth_fy_v1": .25,
                "kr_asset_turnover_change_fy_v1": .125,
                "kr_inventory_investment_fy_v1": .125}
    for ref, value in expected.items():
        values, _ = calculate(frame, ref)
        assert np.allclose(values.value, value)
    # Fiscal history comes from attested explicit prior-FY fields, not monthly shifts.
    one_month = frame.loc[frame.date.eq(frame.date.min())]
    values, _ = calculate(one_month, "kr_asset_growth_fy_v1")
    assert len(values) == 2 and np.allclose(values.value, .25)


@pytest.mark.parametrize("extra", ["fwd_return", "total_return_close", "future_label", "legacy_factor", "f_factor"])
def test_labels_and_unreviewed_extra_columns_rejected(extra):
    frame = panel(); frame[extra] = .1
    with pytest.raises(ValueError, match="Exact v2 feature-only schema"):
        lib.prepare(frame)


def test_missing_and_duplicate_columns_rejected():
    frame = panel()
    for changed in [frame.drop(columns="fy_net_income"), pd.concat([frame, frame[["fy_net_income"]]], axis=1)]:
        with pytest.raises(ValueError, match="Exact v2 feature-only schema"):
            lib.prepare(changed)


@pytest.mark.parametrize("column", ["fy_total_assets", "share_turnover_1m", "daily_return_observations_252d"])
@pytest.mark.parametrize("value", ["100", True])
def test_non_numeric_and_boolean_features_rejected(column, value):
    frame = panel(); frame[column] = value
    with pytest.raises(ValueError, match="Numeric attested feature"):
        lib.prepare(frame)


@pytest.mark.parametrize("code", [5930, "0037t0", "００３７Ｔ０", "0037T", None])
def test_identity_is_exact_and_never_silently_repaired(code):
    frame = panel(); frame["stock_code"] = frame.stock_code.astype(object)
    frame.loc[frame.asset_id.eq(7), "stock_code"] = code
    with pytest.raises(ValueError, match="six-character|Null identity"):
        lib.prepare(frame)


def test_duplicate_month_and_late_or_naive_known_at_rejected():
    frame = panel()
    with pytest.raises(ValueError, match="Duplicate"):
        lib.prepare(pd.concat([frame, frame.iloc[[0]]]))
    for stamp in ["2020-02-01T00:00:00+09:00", "2020-01-31T16:00:00"]:
        changed = frame.copy(); changed["known_at"] = changed.known_at.astype(object)
        changed.loc[0, "known_at"] = stamp
        with pytest.raises(ValueError, match="month-end|timezone"):
            lib.prepare(changed)


def test_digest_is_row_order_invariant_but_feature_and_identity_sensitive():
    frame = panel(); expected = lib.input_digest(frame)
    assert lib.input_digest(frame.sample(frac=1, random_state=3)) == expected
    for column, value in [("fy_net_income", 21.), ("stock_code", "0038T0")]:
        changed = frame.copy(); changed.loc[0, column] = value
        assert lib.input_digest(changed) != expected


@pytest.mark.parametrize("field,value", [
    ("status", "PIT_ASSUMED"), ("source_type", "RDS_CERTIFIED_KRX_PRICE_ONLY"),
    ("source_contract", "UNVERIFIED"), ("pit_status", "FIRST_RELEASE_VERIFIED"),
    ("first_vintage_independently_verified", True),
    ("first_vintage_independently_verified", 0), ("identity_contract", "CURRENT_TICKER"),
    ("scope", "ALL_STOCKS"), ("input_sha256", "b" * 64), ("source_version", "c" * 64),
])
def test_explicit_assumed_not_first_vintage_verified_attestation(field, value):
    frame = panel(); proof = attestation(frame); proof[field] = value
    with pytest.raises(ValueError):
        lib.calculate_one(frame, "kr_roa_fy_v1", attestation=proof)


@pytest.mark.parametrize("bad_sha", [None, "", "not-a-hash", "G" * 64, 123])
def test_source_and_evidence_must_be_real_sha_not_merely_equal(bad_sha):
    frame = panel(); proof = attestation(frame)
    proof["source_version"] = proof["evidence_sha256"] = bad_sha
    with pytest.raises(ValueError):
        lib.validate_attestation(frame, proof)


def test_missing_attestation_hashes_cannot_compare_equal():
    frame = panel(); proof = attestation(frame)
    del proof["source_version"]; del proof["evidence_sha256"]
    with pytest.raises(ValueError):
        lib.validate_attestation(frame, proof)


@pytest.mark.parametrize("field,column,value", [
    ("feature_units", "fy_total_assets", "USD"),
    ("feature_units", "fy_revenue", "MILLION_KRW"),
    ("feature_contracts", "fy_net_income", "LATEST_REVISED_BACKDATED"),
    ("feature_contracts", "adj_close", "EX_POST_TOTAL_RETURN"),
])
def test_unit_and_estimator_contract_mutations_rejected(field, column, value):
    frame = panel(); proof = attestation(frame)
    proof[field][column] = value
    with pytest.raises(ValueError):
        lib.validate_attestation(frame, proof)


@pytest.mark.parametrize("field", ["feature_units", "feature_contracts"])
def test_missing_feature_attestation_dict_rejected(field):
    frame = panel(); proof = attestation(frame); del proof[field]
    with pytest.raises(ValueError):
        lib.validate_attestation(frame, proof)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 0., -1.])
def test_invalid_financial_denominators_produce_no_rows_not_zero(value):
    frame = panel(); frame["fy_total_assets"] = value
    values, summary = calculate(frame, "kr_roa_fy_v1")
    assert values.empty and summary["status"] == "NO_VALID_ROWS"
    assert summary["missing_or_invalid_rows"] == len(frame)


def test_nonfinite_numerator_not_published_and_true_zero_preserved():
    frame = panel(); frame["fy_net_income"] = np.inf
    assert calculate(frame, "kr_roa_fy_v1")[0].empty
    frame["fy_net_income"] = 0.
    values, summary = calculate(frame, "kr_roa_fy_v1")
    assert len(values) == len(frame) and (values.value == 0).all()
    assert summary["status"] == "MEASUREMENT_VALIDATED"


@pytest.mark.parametrize("ref", ["kr_momentum_12_2_price_v1", "kr_reversal_36_13_price_v1",
                                   "kr_information_discreteness_12_2_v1", "kr_roa_fy_v1",
                                   "kr_asset_growth_fy_v1", "kr_downside_risk_252d_v1"])
def test_future_perturbation_does_not_change_prior_values(ref):
    frame = panel(); cutoff = pd.Timestamp("2022-12-31")
    original, _ = calculate(frame, ref)
    changed = frame.copy()
    changed.loc[changed.date.gt(cutoff), list(lib.FEATURE_COLUMNS)] *= 2
    later, _ = calculate(changed, ref)
    columns = [c for c in original if c != "input_sha256"]
    pd.testing.assert_frame_equal(original.loc[original.date.le(cutoff), columns].reset_index(drop=True),
                                  later.loc[later.date.le(cutoff), columns].reset_index(drop=True))


def test_calendar_gap_cannot_stitch_price_history_or_affect_other_asset():
    frame = panel(); missing = pd.Timestamp("2022-01-31")
    baseline, _ = calculate(frame, "kr_momentum_12_2_price_v1")
    gap = frame.loc[~(frame.asset_id.eq(7) & frame.date.eq(missing))]
    actual, _ = calculate(gap, "kr_momentum_12_2_price_v1")
    invalid = actual.asset_id.eq("7") & actual.date.gt(missing) & actual.date.le(missing + pd.DateOffset(months=12))
    assert not invalid.any()
    assert actual.loc[actual.asset_id.eq("9"), "value"].tolist() == baseline.loc[baseline.asset_id.eq("9"), "value"].tolist()


def test_unknown_reference_rejected():
    frame = panel()
    with pytest.raises(ValueError, match="Unknown expansion reference"):
        lib.calculate_one(frame, "legacy_alpha", attestation=attestation(frame))
