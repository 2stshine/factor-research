from copy import deepcopy
import pandas as pd
import pytest
from engine import reference_new_information as lib,reference_gold as gold

def row(segment,sex,n):
 return dict(fo_bbm=segment,sexdstn=sex,sm=str(n),rgllbr_co=str(n),cnttk_co='0')

def test_employee_explicit_totals_not_double_counted():
 rows=[row('A','남',30),row('A','여',20),row('B','남',10),row('B','여',5),row('성별합계','남',40),row('성별합계','여',25)]
 assert lib.employee_count(rows)==(65,'EXPLICIT_SEX_TOTALS_RECONCILED')
 rows[-1]=row('성별합계','여',26)
 with pytest.raises(ValueError,match='TOTAL_MISMATCH'):lib.employee_count(rows)

def test_employee_details_ditto_and_ambiguity():
 assert lib.employee_count([row('A','남',4),row('〃','여',2)])[0]==6
 with pytest.raises(ValueError,match='DUPLICATE'):lib.employee_count([row('A','남',4),row('A','남',4),row('A','여',2)])
 with pytest.raises(ValueError,match='MISSING'):lib.employee_count([row('A','남','-'),row('A','여',2)])
 with pytest.raises(ValueError,match='SUBTOTAL'):lib.employee_count([row('A소계','남',4),row('A소계','여',2)])
 r=row('A','남',4);r['cnttk_co']='1'
 with pytest.raises(ValueError,match='COMPONENT'):lib.employee_count([r,row('A','여',2)])
 assert lib.employee_count([row('전사','남',4),row('-','여',2)])[0]==6
 assert lib.employee_count([row('A','남',4),row('A','여',2),row('성별 총계','남',4),row('성별 총계','여',2)])[0]==6

def test_receipt_clock_not_period_end_or_provider_acceptance():
 assert str(lib.receipt_known_at('2020-03-31','20200331000123','2019-12-31'))=='2020-03-31 15:00:00+00:00'
 with pytest.raises(ValueError):lib.receipt_known_at('2019-12-31','20191231000123','2019-12-31')
 with pytest.raises(ValueError):lib.receipt_known_at('2020-03-30','20200331000123','2019-12-31')

def test_rd_requires_positive_exact_fy_krw_and_cfs_revenue():
 r=dict(date='2020-12-31',period='FY',reportedCurrency='KRW',revenue=1000,researchAndDevelopmentExpenses=100)
 a=dict(period_end='2020-12-31',currency='KRW',fs_type='CFS',revenue=1000)
 assert lib.rd_matches(r,a)
 for updates in (dict(researchAndDevelopmentExpenses=0),dict(reportedCurrency='USD'),dict(revenue=2000),dict(period='Q4')):
  assert not lib.rd_matches({**r,**updates},a)
 assert not lib.rd_matches(r,{**a,'fs_type':'OFS'})

def test_latest_fy_missing_must_not_fallback_or_use_future():
 identity=pd.DataFrame(dict(asset_id=[1]*4,stock_code=['000001']*4,market=['KOSPI']*4,
  date=pd.to_datetime(['2020-03-31','2020-04-30','2021-03-31','2021-04-30'])))
 anchors=pd.DataFrame(dict(asset_id=[1,1],period_end=pd.to_datetime(['2019-12-31','2020-12-31']),
  filed=['2020-03-31','2021-03-15'],filing_id=['20200331000123','20210315000123']))
 annual=pd.DataFrame(dict(asset_id=[1],period_end=pd.to_datetime(['2019-12-31']),
  known_at=pd.to_datetime(['2020-03-31T15:00:00Z']),employees=[110],prev_employees=[90]))
 p=lib.monthly_panel(identity,anchors,annual)
 assert p.date.tolist()==[pd.Timestamp('2020-04-30')]
 assert lib.calculate(p,'kr_employee_hiring_fy_reference_v1').tolist()==[.2]
 cut=lib.monthly_panel(identity.iloc[:2],anchors.iloc[:1],annual)
 pd.testing.assert_frame_equal(p,cut)

def test_source_and_definition_gate_does_not_approve_alpha():
 d=lib.definitions();assert all(x['alpha_approved'] is False for x in d)
 gold._validate_definition_source({'source_type':lib.SOURCE_TYPE},d)
 changed=deepcopy(d);changed[0]['orientation']=1
 with pytest.raises(ValueError,match='mismatch'):gold._validate_definition_source({'source_type':lib.SOURCE_TYPE},changed)
 with pytest.raises(ValueError,match='PIT'):gold._validate_source_attestation({'source_type':lib.SOURCE_TYPE,'status':'CERTIFIED'})
