import pandas as pd
import pytest
from engine.reference_consensus_history import validate_history,observable_at

def sample():
 return pd.DataFrame(dict(asset_id=[1,1],stock_code=['005930']*2,snapshot_at=['2020-01-15T00:00:00Z','2020-03-15T00:00:00Z'],
  available_at=['2020-01-16T00:00:00Z','2020-03-16T00:00:00Z'],fiscal_period_end=['2020-12-31']*2,
  eps_mean=[100.,110.],analyst_count=[5,6],currency=['KRW']*2,provider_snapshot_id=['a','b']))

META=dict(snapshot_semantics='ACTUAL_PROVIDER_CONSENSUS_VINTAGE',research_use_permitted=True,internal_storage_permitted=True,pit_status='PIT_ASSUMED')

def test_fmp_target_years_are_not_historical_snapshots():
 with pytest.raises(ValueError,match='target years'):
  validate_history(pd.DataFrame([dict(symbol='005930.KS',date='2020-12-31',epsAvg=100)]),META)

def test_vintage_selection_never_uses_later_revision():
 p=validate_history(sample(),META)
 assert observable_at(p,'2020-02-01T00:00:00Z').eps_mean.tolist()==[100.]
 assert observable_at(p,'2020-03-15T12:00:00Z').eps_mean.tolist()==[100.]
 assert observable_at(p,'2020-04-01T00:00:00Z').eps_mean.tolist()==[110.]

def test_ambiguous_clock_and_scope_rejected():
 p=sample();p.loc[0,'available_at']='2020-01-14T00:00:00Z'
 with pytest.raises(ValueError,match='before'):validate_history(p,META)
 with pytest.raises(ValueError,match='semantics'):validate_history(sample(),{**META,'snapshot_semantics':'FISCAL_TARGET_DATE'})
 with pytest.raises(ValueError,match='permission'):validate_history(sample(),{**META,'research_use_permitted':False})

def test_research_login_does_not_imply_database_storage_permission():
 with pytest.raises(ValueError,match='storage permission'):validate_history(sample(),{**META,'internal_storage_permitted':False})
 missing={k:v for k,v in META.items() if k!='internal_storage_permitted'}
 with pytest.raises(ValueError,match='storage permission'):validate_history(sample(),missing)

@pytest.mark.parametrize('column,value',[
 ('stock_code','００５９３０'),('stock_code','0037t0'),('asset_id',-1),
 ('asset_id',1.5),('eps_mean',True),('analyst_count',True),
 ('fiscal_period_end','2020-12-31T12:00:00'),
])
def test_invalid_identity_units_and_target_clock_rejected(column,value):
 p=sample();p[column]=value
 with pytest.raises(ValueError):validate_history(p,META)
