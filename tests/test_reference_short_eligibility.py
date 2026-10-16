from copy import deepcopy
import numpy as np
import pandas as pd
import pytest
from engine import reference_short_eligibility as lib,reference_gold as gold
from scripts.audit_reference_short_eligible import aggregate
from scripts.stage_krx_membership_dom import save_set,stage_batch,identity

def sample():
 return pd.DataFrame(dict(asset_id=[1]*5,date=['2021-05-31','2021-06-30','2021-07-31','2021-08-31','2023-11-30'],
  expected_days=[20]*5,eligible_days=[20,19,20,20,3],excluded_regime_days=[0,0,0,0,17],excluded_individual_days=[0,1,0,0,0],
  short_days=[20,19,19,20,3],bad_short=[0]*5,bad_identity=[0]*5,sq=[0.,20.,30.,40.,1.],sv=[100.]*5,
  short_known_at=pd.to_datetime(['2021-05-29T00:00Z','2021-06-29T00:00Z','2021-07-29T00:00Z','2021-08-29T00:00Z','2023-11-04T00:00Z'])))

def test_zero_missing_ban_adjacent_change():
 p=lib.prepare(sample());level,change=[lib.calculate(p,r) for r in lib.SPECS]
 assert level[0]==0 and level[1]==.2 and level[3]==.4
 assert level.iloc[[2,4]].isna().all() and change[1]==.2
 assert change.iloc[[0,2,3,4]].isna().all()

def test_short_month_or_postcutoff_or_bad_source_rejected():
 for col,value in [('short_known_at',pd.Timestamp('2021-06-01T00:00Z')),('bad_short',1)]:
  f=sample();f.loc[0,col]=value;assert not lib.prepare(f).measurement_eligible[0]
 f=sample();f.loc[0,'eligible_days']=19
 with pytest.raises(ValueError,match='partition'):lib.prepare(f)
 f=sample();f.loc[0,'bad_identity']=1
 with pytest.raises(ValueError,match='identity'):lib.prepare(f)

def test_prefix_and_min15():
 f=sample();p=lib.prepare(f);part=lib.prepare(f.iloc[:2])
 for ref in lib.SPECS:np.testing.assert_allclose(lib.calculate(p,ref).iloc[:2],lib.calculate(part,ref),equal_nan=True)
 f.loc[0,['eligible_days','short_days','excluded_individual_days']]=[15,15,5]
 assert lib.prepare(f).measurement_eligible[0]
 f.loc[0,['eligible_days','short_days','excluded_individual_days']]=[14,14,6]
 assert not lib.prepare(f).measurement_eligible[0]

def test_all_banned_null_aggregate_columns_are_not_zero_filled():
 f=sample().iloc[:1].copy();f.loc[0,['eligible_days','short_days','excluded_regime_days']]=[0,0,20]
 f['sq']=None;f['sv']=None;f['short_known_at']=None
 p=lib.prepare(f)
 assert not p.measurement_eligible.any() and lib.calculate(p,next(iter(lib.SPECS))).isna().all()

def daily_sample():
 dates=pd.to_datetime(['2020-03-13','2020-03-16','2021-05-03','2021-05-04','2021-05-06','2023-11-03','2023-11-06','2025-03-31','2025-04-01'])
 return pd.DataFrame(dict(asset_id=[1]*len(dates),stock_code=['005930']*len(dates),trade_date=dates,market='KOSPI',
  cutoff=(dates.to_period('M')+1).to_timestamp().tz_localize('Asia/Seoul').tz_convert('UTC'),identity_matches=1,
  source_ticker='005930',source_exists=True,short_volume=1.,total_volume=10.,
  known_at=(dates+pd.Timedelta(days=1,hours=8,minutes=30)).tz_localize('Asia/Seoul').tz_convert('UTC'),
  policy_version='kis-krx-short-scope-v2',availability_basis='POLICY_ASSUMPTION',short_market='KRX',volume_market='KRX',volume_adjustment='UNADJUSTED'))

def test_daily_boundaries_actual_members_no_forward_fill_and_restriction():
 raw=daily_sample();raw=raw.loc[raw.trade_date.ne(pd.Timestamp('2025-03-31'))]
 m=pd.DataFrame(dict(stock_code=['005930']*4,trade_date=['2021-05-03','2021-05-04','2021-05-06','2023-11-03'],market=['KOSPI','KOSPI','KOSDAQ','KOSPI']))
 restrictions=pd.DataFrame(dict(stock_code=['005930'],trade_date=['2021-05-04']))
 a=aggregate(raw,m,restrictions).set_index('date')
 assert a.loc['2020-03-31','eligible_days']==1 and a.loc['2020-03-31','excluded_regime_days']==1
 assert a.loc['2021-05-31','eligible_days']==1 and a.loc['2021-05-31','excluded_individual_days']==1 and a.loc['2021-05-31','excluded_regime_days']==1
 assert a.loc['2023-11-30','eligible_days']==1 and a.loc['2023-11-30','excluded_regime_days']==1
 assert a.loc['2025-04-30','eligible_days']==1
 with pytest.raises(ValueError,match='Unavailable'):aggregate(daily_sample(),m,restrictions)

def test_attestation_and_definition_binding():
 a=dict(status='CERTIFIED',source_type=lib.SOURCE_TYPE,source_contract=lib.SOURCE_CONTRACT,pit_status='PIT_ASSUMED',
  first_vintage_independently_verified=False,identity_contract='HISTORICAL_ASSET_ID',scope='KRX_COMMON_STOCK',
  source_version='a'*64,evidence_sha256='a'*64,availability_policy='NEXT_CALENDAR_DAY_0830_KST_EXCLUDE_POST_CUTOFF_TRADES',
  venue='J',daily_official_membership_complete=True,individual_restrictions_applied=True,policy_manifest_sha256='b'*64)
 gold._validate_source_attestation(a);gold._validate_definition_source(a,lib.definitions())
 for key in ['first_vintage_independently_verified','daily_official_membership_complete','individual_restrictions_applied']:
  bad={**a,key:not a[key]}
  with pytest.raises(ValueError,match='PIT'):gold._validate_source_attestation(bad)
 d=deepcopy(lib.definitions());d[0]['formula']='0'
 with pytest.raises(ValueError,match='mismatch'):gold._validate_definition_source(a,d)

def test_both_existing_policy_names_require_actual_krx_scope():
 raw=daily_sample().iloc[[-1]].copy();raw['policy_version']='kis-provider-trust-v1'
 m=pd.DataFrame(columns=['stock_code','trade_date','market']);r=pd.DataFrame(columns=['stock_code','trade_date'])
 assert aggregate(raw,m,r).bad_short.iloc[0]==0
 raw['short_market']='NXT'
 assert aggregate(raw,m,r).bad_short.iloc[0]==1
 raw['short_market']='KRX';raw['policy_version']='UNKNOWN'
 assert aggregate(raw,m,r).bad_short.iloc[0]==1

def test_immutable_individually_observed_members(tmp_path):
 members=[[f'{i:06d}',f'회사{i}'] for i in range(100)]
 key=save_set(tmp_path,members)
 batch=dict(source='KRX_UI_11006_ALL_SCROLL_ROWS',started_at='2026-10-03T00:00:00Z',completed_at='2026-10-03T00:00:01Z',sets=[],observations=[dict(index='KOSPI200',sha256=key,dates=['20210503'])])
 stage_batch(tmp_path,batch)
 assert (tmp_path/'observations/KOSPI200/20210503.json').exists()
 assert not (tmp_path/'observations/KOSPI200/20210504.json').exists()
 changed=[*members[:-1],['999999','새회사']];key2=save_set(tmp_path,changed)
 batch['observations'][0]['sha256']=key2
 with pytest.raises(ValueError,match='changed|differs|Immutable'):stage_batch(tmp_path,batch)
 assert key==identity(members) and members[0][0]=='000000'

def test_inclusive_cross_year_restrictions_and_no_double_count():
 from scripts.stage_krx_short_policy import expand_restrictions
 f=pd.DataFrame(dict(stock_code=['005930','005930'],start_date=['2021-12-31','2022-01-02'],end_date=['2022-01-03','2022-01-03']))
 r=expand_restrictions(f)
 assert r.trade_date.tolist()==['2021-12-31','2022-01-01','2022-01-02','2022-01-03']
 assert r.stock_code.eq('005930').all()

def test_prepublication_blocks_silent_latest_month_loss(tmp_path,monkeypatch):
 from scripts import audit_short_reference_replacement as audit
 from scripts.publish_reference_expansion import sha
 old,new=next(iter(lib.REPLACEMENTS.items()))
 f=pd.DataFrame(dict(reference_id=[old]*2,asset_id=[1,1],date=pd.to_datetime(['2026-08-31','2026-09-30']),value=[.1,.2]))
 path=tmp_path/'old.parquet';f.to_parquet(path,index=False)
 fresh=f.iloc[:1].assign(reference_id=new)
 monkeypatch.setattr(audit,'inputs',lambda _:({'reference_datasets':[{'dataset_id':'old','reference_ids':[old]}]}, {},
  {'cache_file_sha256':{'old':sha(path)}},{'old':path},{},{new:fresh},{}))
 with pytest.raises(ValueError,match='latest measurement month'):audit.preflight(tmp_path,tmp_path/'must-not-publish.json')
 assert not (tmp_path/'must-not-publish.json').exists()
