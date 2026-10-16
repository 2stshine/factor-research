"""Conditional arithmetic and refusal cases. These are synthetic index points."""
from copy import deepcopy
import json,hashlib
import pandas as pd
import pytest
from strategies.monthly_input_preparation import PreparationBlocked
from strategies.monthly_benchmark_preparation import conditional_open_level,build_benchmark_draft,required_opening_months


@pytest.fixture
def sample():
    contract={'index_id':'KRX300_TR','price_index_id':'KRX300','currency':'KRW','return_type':'gross_total_return',
        'data_kind':'SYNTHETIC_TEST','component_status':'REVIEWED_OFFICIAL_INDEX_COMPONENTS',
        'dividend_basis':'OFFICIAL_INDEX_DIVIDEND_POINTS','revision_basis':'AS_PUBLISHED_AT_INDEX_OPEN',
        'opening_basis':'REVIEWED_SCHEDULED_OPEN_INDEX_MARK','methodology_ref':'synthetic-rule',
        'review_ref':'synthetic-review','series_revision_id':'synthetic-coherent-series','allowed_data_time':'2030-01-01T00:00:00+09:00','source_hashes':{'synthetic':'a'*64}}
    point={'series_revision_id':'synthetic-coherent-series','session_month':'2025-01','scheduled_open_at':'2025-01-02T10:00:00+09:00',
        'index_observed_at':'2025-01-02T10:00:00+09:00','previous_close_at':'2024-12-30T15:30:00+09:00',
        'component_vintage_as_of':'2025-01-02T10:00:00+09:00','calendar_relation':'VERIFIED_FIRST_AND_PREVIOUS_SESSIONS',
        'history_kind':'LIVE_DISSEMINATED','source_refs':['synthetic'],'price_previous_close':100.,
        'tr_previous_close':200.,'price_open':98.,'dividend_points_at_open':2.}
    return point,contract


def test_dividend_day_reconstruction_is_not_close_ratio_scaling(sample):
    p,c=sample;before=deepcopy(sample);result=conditional_open_level(p,c)
    assert result['conditional_tr_open']==pytest.approx(200.)
    # Same synthetic day's price close=108 implies TR close=220. Scaling is wrong.
    wrong_close_scaling=220/108*98
    assert result['conditional_tr_open']!=pytest.approx(wrong_close_scaling)
    assert not result['execution_certified'] and not result['actual_fill_verified']
    assert not result['provider_rounding_reconciled'] and sample==before


def test_explicit_zero_and_negative_official_correction(sample):
    p,c=sample;p['dividend_points_at_open']=0
    assert conditional_open_level(p,c)['conditional_tr_open']==196
    p.update(price_open=101,dividend_points_at_open=-1)
    assert conditional_open_level(p,c)['conditional_tr_open']==200


@pytest.mark.parametrize('where,key,value,code',[
 ('point','dividend_points_at_open',None,'DIVIDEND'),('point','dividend_points_at_open',False,'DIVIDEND'),
 ('point','dividend_points_at_open',float('nan'),'DIVIDEND'),('point','price_previous_close',0,'POSITIVE'),
 ('point','price_open',-1,'POSITIVE'),('point','tr_previous_close',float('inf'),'POSITIVE'),
 ('point','dividend_points_at_open',-1000,'INVALID_TR'),
 ('point','index_observed_at','2025-01-02T10:00:02+09:00','TIME_MISMATCH'),
 ('point','component_vintage_as_of','2025-02-02T10:00:00+09:00','TIME_MISMATCH'),
 ('point','previous_close_at','2025-01-02T09:00:00+09:00','TIME_MISMATCH'),
 ('point','calendar_relation','INFERRED_FROM_DAILY_ROWS','CALENDAR'),
 ('point','source_refs',['unknown'],'SOURCE_REFERENCE'),('point','session_month','2025-02','MONTH_MISMATCH'),
 ('contract','return_type','price_return','IDENTITY'),('contract','currency','USD','IDENTITY'),
 ('contract','index_id','KRX300_NTR','IDENTITY'),('contract','data_kind','REAL_IF_PASSES','DATA_KIND'),
 ('contract','dividend_basis','STOCK_TOTAL_RETURN_CLOSE_RATIO','OFFICIAL_COMPONENTS'),
 ('contract','revision_basis','LATEST_CORRECTED','VINTAGE'),
 ('contract','opening_basis','DAILY_OHLC','OPENING_SEMANTICS'),
 ('point','series_revision_id','different-vintage','SERIES_REVISION'),
 ('contract','series_revision_id',None,'SERIES_REVISION'),
 ('contract','review_ref',None,'SOURCE_REVIEW'),('contract','source_hashes',{},'SOURCE_HASH'),
])
def test_unsupported_or_unbound_input_rejected(sample,where,key,value,code):
    p,c=sample;(p if where=='point' else c)[key]=value
    with pytest.raises(PreparationBlocked,match=code):conditional_open_level(p,c)


def test_prelaunch_needs_explicit_backcast_review(sample):
    p,c=sample;p.update(session_month='2018-04',scheduled_open_at='2018-04-02T09:00:00+09:00',
        index_observed_at='2018-04-02T09:00:00+09:00',previous_close_at='2018-03-30T15:30:00+09:00',
        component_vintage_as_of='2018-04-02T09:00:00+09:00')
    with pytest.raises(PreparationBlocked,match='PRELAUNCH'):conditional_open_level(p,c)
    p['history_kind']='OFFICIAL_BACKCALCULATED'
    with pytest.raises(PreparationBlocked,match='BACKCALCULATED_HISTORY_REVIEW'):conditional_open_level(p,c)
    c.update(backcalculated_history='EXPLICITLY_REVIEWED',backcast_revision_basis='OFFICIAL_RELEASE_VERSION_BOUND',backcast_series_release_at='2018-12-24T09:00:00+09:00')
    p['backcast_release_at']='2018-12-24T09:00:00+09:00'
    with pytest.raises(PreparationBlocked,match='BACKCAST_VINTAGE'):conditional_open_level(p,c)
    p['component_vintage_as_of']=p['backcast_release_at']
    result=conditional_open_level(p,c)
    assert result['history_kind']=='OFFICIAL_BACKCALCULATED' and not result['historically_live_observation']
    c['allowed_data_time']='2018-12-01T00:00:00+09:00'
    with pytest.raises(PreparationBlocked,match='OUTSIDE_DATA_BOUNDARY'):conditional_open_level(p,c)


def test_frozen_99_signals_require_100_openings_through_july_not_june():
    signals=list(map(str,pd.period_range('2018-03','2026-05',freq='M')))
    result=build_benchmark_draft(signals,[])
    assert len(signals)==99 and len(result['required_opening_months'])==100
    assert result['required_opening_months'][0]=='2018-04'
    assert result['required_opening_months'][-1]=='2026-07'
    assert result['missing_windows']==signals and len(result['missing_opening_months'])==100
    assert not result['real_performance_computed'] and not result['execution_certified']


def test_partial_input_never_drops_requested_months(sample):
    p,c=sample;result=build_benchmark_draft(['2024-12','2025-01'],[p],c)
    assert result['missing_windows']==['2024-12','2025-01']
    assert result['missing_opening_months']==['2025-02','2025-03']
    assert result['windows']==[] and result['data_kind']=='SYNTHETIC_TEST'


def test_adjacent_points_produce_only_conditional_window(sample):
    p,c=sample;q=deepcopy(p);q.update(session_month='2025-02',scheduled_open_at='2025-02-03T09:00:00+09:00',
        index_observed_at='2025-02-03T09:00:00+09:00',previous_close_at='2025-01-31T15:30:00+09:00',
        component_vintage_as_of='2025-02-03T09:00:00+09:00',price_previous_close=120,tr_previous_close=240,price_open=120,dividend_points_at_open=0)
    result=build_benchmark_draft(['2024-12'],[p,q],c)
    assert result['windows'][0]['conditional_gross_multiplier']==pytest.approx(1.2)
    assert result['missing_windows']==[] and result['blockers']==[]
    assert result['status']=='DRAFT_NOT_EXECUTION_CERTIFIED' and not result['real_performance_computed']


def test_duplicate_and_out_of_scope_points_are_not_silently_deduplicated(sample):
    p,c=sample
    with pytest.raises(PreparationBlocked,match='EXTRA_OR_DUPLICATE'):build_benchmark_draft(['2024-12'],[p,p],c)
    with pytest.raises(PreparationBlocked,match='EXTRA_OR_DUPLICATE'):build_benchmark_draft(['2020-12'],[p],c)


def test_cli_checks_plan_before_any_source_read(tmp_path,monkeypatch):
    from scripts.check_monthly_benchmark import prepare
    def sealed(*a):raise ValueError('SEALED_BOUNDARY')
    monkeypatch.setattr('scripts.check_monthly_benchmark.load_plan',sealed)
    with pytest.raises(ValueError,match='SEALED_BOUNDARY'):
        prepare(tmp_path/'plan',tmp_path/'output',tmp_path/'missing-private-source')
    assert not (tmp_path/'output').exists()


def test_cli_missing_source_stays_draft_and_refuses_overwrite(tmp_path,monkeypatch):
    from scripts.check_monthly_benchmark import prepare
    monkeypatch.setattr('scripts.check_monthly_benchmark.load_plan',lambda *a:({'bounds':{'decision_start':'2018-03','decision_end':'2026-05'}},{'plan_sha256':'a'*64}))
    target=tmp_path/'draft.json';result=prepare(tmp_path/'plan',target)
    assert len(result['missing_windows'])==99 and not result['execution_certified']
    before=target.read_bytes()
    with pytest.raises(PreparationBlocked,match='OUTPUT_EXISTS'):prepare(tmp_path/'plan',target)
    assert target.read_bytes()==before
