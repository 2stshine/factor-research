import pandas as pd
import pytest
from engine import reference_library as lib
from scripts.reference_library import check_full_sqlite_parity


def fixture():
    rows=[]
    for asset,code in [(1,'005930'),(2,'0037T0')]:
        for i,day in enumerate(pd.date_range('2020-01-31',periods=16,freq='ME')):
            rows.append(dict(asset_id=asset,stock_code=code,date=day,known_at=day.tz_localize('Asia/Seoul')+pd.Timedelta(hours=20),
                market='KOSPI',adj_close=100.+i,market_cap=1e10+i,daily_volatility_252d=.02,
                daily_return_observations_252d=252,amihud_illiquidity_1m=1e-12,amihud_observations_1m=20,
                price_high_252d=150.,price_high_observations_252d=252,max_daily_return_1m=.05,max_daily_return_observations_1m=20))
    return pd.DataFrame(rows)


def calculate(panel):
    att=dict(status='CERTIFIED',source_version='synthetic-test',source_contract='TEST_ONLY',evidence_sha256='a'*64,
             input_sha256=lib.input_panel_digest(panel),identity_contract=lib.IDENTITY_CONTRACT,scope=lib.INPUT_SCOPE,
             units=lib.FEATURE_UNITS,feature_contracts=lib.FEATURE_CONTRACTS)
    return lib.calculate_reference_panel(panel,input_attestation=att).values


def test_full_independent_sqlite_all_seven_and_gaps():
    panel=fixture();values=calculate(panel)
    receipt=check_full_sqlite_parity(panel,values)
    assert receipt['passed'] and receipt['rows_compared']==len(values) and values.reference_id.nunique()==7
    panel=panel.loc[~((panel.asset_id==1)&(panel.date==pd.Timestamp('2020-06-30')))]
    assert check_full_sqlite_parity(panel,calculate(panel))['passed']


def test_missing_or_incorrect_value_rejected_even_tiny_units():
    panel=fixture();values=calculate(panel)
    with pytest.raises(ValueError,match='parity'):check_full_sqlite_parity(panel,values.iloc[:-1])
    values.loc[values.reference_id=='kr_amihud_1m_v1','value']+=1e-14
    with pytest.raises(ValueError,match='parity'):check_full_sqlite_parity(panel,values)
