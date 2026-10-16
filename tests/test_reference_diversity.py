from copy import deepcopy
import sqlite3
import numpy as np
import pandas as pd
import pytest
from engine import reference_expansion_100 as lib, reference_gold as gold

def test_all_financial_sql_matches_independent_pandas_with_missing_and_zero():
    rng=np.random.default_rng(73)
    cols=sorted({c for s in lib.SPECS.values() for c in s['columns']} - {'quality_profitability_score'})
    p=pd.DataFrame({c:rng.normal(40,90,40) for c in cols})
    for c in cols:p.loc[0,c]=np.nan;p.loc[1,c]=0;p.loc[2,c]=10
    actual=lib.financial_values(p)
    with sqlite3.connect(':memory:') as db:
        p.to_sql('reference_input',db,index=False)
        for ref,v in actual.items():
            expected=pd.read_sql_query('SELECT '+lib.SPECS[ref]['sql']+' AS value FROM reference_input',db).value
            np.testing.assert_allclose(v,expected.astype(float),rtol=1e-10,atol=0,equal_nan=True,err_msg=ref)

def test_registered_new_definitions_do_not_collide_or_confer_alpha():
    defs=lib.definitions()
    assert len(defs)==15
    assert len({d['formula'] for d in defs})==15
    assert all(d['alpha_approved'] is False for d in defs)
    gold._validate_definition_source({'source_type':lib.SOURCE_TYPE},defs)
    changed=deepcopy(defs);changed[0]['formula']='made up'
    with pytest.raises(ValueError,match='mismatch'):
        gold._validate_definition_source({'source_type':lib.SOURCE_TYPE},changed)

def test_no_partial_history_for_earnings_stability_or_payout():
    cols=sorted({c for s in lib.SPECS.values() for c in s['columns']} - {'quality_profitability_score'})
    p=pd.DataFrame({c:[10.] for c in cols})
    p.loc[0,'fy3_net_income']=np.nan
    values=lib.financial_values(p)
    assert pd.isna(values['kr_earnings_stability_5fy_v1'].iloc[0])
    assert pd.isna(values['kr_net_payout_profit_5fy_v1'].iloc[0])
