from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from engine import reference_profit_growth as lib, reference_gold as gold


def panel():
    return pd.DataFrame(dict(asset_id=[1, 2], stock_code=["005930", "0037T0"],
        market=["KOSPI", "KOSDAQ"], date=pd.to_datetime(["2020-01-31"] * 2),
        known_at=pd.to_datetime(["2020-01-31T07:00:00Z"] * 2),
        fy_total_assets=[200., 0.], prev_fy_total_assets=[100., 100.],
        fy_operating_cash_flow=[30., 10.], prev_fy_operating_cash_flow=[10., 10.],
        fy_income_tax_expense=[8., 2.], prev_fy_income_tax_expense=[2., 1.]))


def test_formulas_and_invalid_denominators():
    p = panel()
    _, cfo = lib.calculate(p, "kr_cfo_assets_change_fy_v1")
    _, tax = lib.calculate(p, "kr_tax_expense_change_assets_fy_v1")
    assert np.isclose(cfo[0], .05) and pd.isna(cfo[1])
    assert np.isclose(tax[0], .03) and pd.isna(tax[1])
    # Missing is not zero; negative tax credits remain meaningful.
    p.loc[0, "fy_income_tax_expense"] = -2
    assert lib.calculate(p, "kr_tax_expense_change_assets_fy_v1")[1][0] == -.02
    p.loc[0, "prev_fy_income_tax_expense"] = np.nan
    assert pd.isna(lib.calculate(p, "kr_tax_expense_change_assets_fy_v1")[1][0])


def test_future_input_and_labels_rejected():
    p = panel()
    p["fwd_return"] = 1.
    with pytest.raises(ValueError, match="schema"):
        lib.prepare(p)
    p = panel()
    p.loc[0, "known_at"] = pd.Timestamp("2020-02-01T01:00:00Z")
    with pytest.raises(ValueError):
        lib.prepare(p)


def test_definition_binding_rejects_changed_formula():
    defs = lib.definitions()
    a = {"source_type": lib.SOURCE_TYPE}
    gold._validate_definition_source(a, defs)
    changed = deepcopy(defs)
    changed[0]["formula"] = "0"
    with pytest.raises(ValueError, match="mismatch"):
        gold._validate_definition_source(a, changed)


def test_source_requires_explicit_pit_limitation():
    with pytest.raises(ValueError, match="PIT"):
        gold._validate_source_attestation({"status": "CERTIFIED", "source_type": lib.SOURCE_TYPE})


def test_digest_order_invariance_and_change_detection():
    p = panel()
    assert lib.input_digest(p) == lib.input_digest(p.iloc[::-1])
    q = p.copy()
    q.loc[0, "fy_total_assets"] += 1
    assert lib.input_digest(p) != lib.input_digest(q)
