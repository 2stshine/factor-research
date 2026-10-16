import numpy as np
import pandas as pd
import pytest
from engine.reference_expansion_formulas import calculate,FINANCIAL_FORMULAS,sql_expression


def test_financial_closed_form_cases():
    frame=pd.DataFrame({'fy_net_income':[10.],'fy_total_assets':[100.], 'fy_revenue':[50.],
        'fy_operating_cash_flow':[15.],'prev_fy_total_assets':[80.],'prev_fy_revenue':[48.]})
    assert calculate(frame,'kr_roa_fy_v1').iloc[0]==.1
    assert calculate(frame,'kr_cashflow_accruals_fy_v1').iloc[0]==-.05
    assert calculate(frame,'kr_asset_growth_fy_v1').iloc[0]==.25
    assert calculate(frame,'kr_asset_turnover_change_fy_v1').iloc[0]==pytest.approx(-.1)


@pytest.mark.parametrize('denominator',[0.,-1.,np.nan,np.inf])
def test_invalid_denominator_never_fabricated(denominator):
    frame=pd.DataFrame({'fy_net_income':[2.],'fy_total_assets':[denominator]})
    assert calculate(frame,'kr_roa_fy_v1').isna().all()


@pytest.mark.parametrize('reference_id',list(FINANCIAL_FORMULAS))
def test_python_and_sql_all_frozen_financial_definitions(reference_id):
    import sqlite3
    columns=FINANCIAL_FORMULAS[reference_id][1:-1]
    frame=pd.DataFrame({col:[(i+1)*10.,-(i+1)*10.,np.nan,0.] for i,col in enumerate(columns)})
    with sqlite3.connect(':memory:') as db:
        frame.to_sql('input',db,index=False)
        got=pd.read_sql_query('SELECT '+sql_expression(reference_id)+' AS value FROM input',db)['value']
    np.testing.assert_allclose(calculate(frame,reference_id),got,equal_nan=True,rtol=1e-12)
