"""Synthetic unit/accounting contracts; never reported as market returns."""
from copy import deepcopy
import json

import pandas as pd
import pytest

from strategies.monthly_input_preparation import (
    PreparationBlocked, compute_open_window, draft_status, prepare_pit_scores,
)


@pytest.fixture
def path():
    dates = ['2025-01-02', '2025-01-03', '2025-02-03']
    prices = [dict(date=d, asset_id=1, listing_episode_id='episode-1', open=100., close=100.,
                   open_status='VERIFIED_TRADABLE', close_status='VERIFIED_TRADABLE', source_ref='synthetic-price') for d in dates]
    coverage = dict(asset_id=1, listing_episode_id='episode-1', status='REVIEWED_COMPLETE',
                    session_dates=dates, evidence_refs=['synthetic-complete-inventory'],
                    raw_share_basis='RAW_UNADJUSTED', event_cash_basis='PRE_EVENT_RAW_SHARE')
    return prices, [], coverage


def action(kind, date='2025-01-03', **fields):
    return dict(type=kind, ex_date=date, asset_id=1, listing_episode_id='episode-1',
                economic_event_id='synthetic-event', canonical=True, resolution_status='VERIFIED',
                source_ref='synthetic-canonical-decision', **fields)


def test_no_event_raw_open_return_and_no_input_mutation(path):
    prices, events, coverage = path
    prices[-1]['open'] = 110
    before = deepcopy(path)
    result = compute_open_window(*path)
    assert result['gross_total_return_multiplier'] == pytest.approx(1.1)
    assert path == before
    assert result['execution_certified'] is False


def test_interior_dividend_reinvested_at_close(path):
    prices, events, _ = path
    prices[1].update(open=90, close=90)
    prices[-1]['open'] = 99
    events.append(action('CASH_DIVIDEND', cash_per_pre_action_share=10))
    result = compute_open_window(*path)
    assert result['audit'][1]['shares_after'] == pytest.approx(1+10/90)
    assert result['gross_total_return_multiplier'] == pytest.approx(1.1)


def test_entry_ex_date_buyer_has_no_dividend_entitlement(path):
    prices, events, _ = path
    prices[0]['open'] = 90
    events.append(action('CASH_DIVIDEND', date=prices[0]['date'], cash_per_pre_action_share=10))
    result = compute_open_window(*path)
    assert result['gross_total_return_multiplier'] == pytest.approx(100/90)
    assert result['audit'][0]['entitlement_cash'] == 0


def test_exit_ex_date_entitlement_uses_receivable_not_future_close(path):
    prices, events, _ = path
    prices[-1].update(open=90, close=None, close_status='UNAVAILABLE_AFTER_EXIT')
    events.append(action('CASH_DIVIDEND', date=prices[-1]['date'], cash_per_pre_action_share=10))
    result = compute_open_window(*path)
    assert result['gross_total_return_multiplier'] == pytest.approx(1)
    assert result['audit'][-1]['cash_after'] == 10


@pytest.mark.parametrize('kind,ratio,raw_price', [('SPLIT',2,50),('REVERSE_SPLIT',.5,200),('BONUS_SHARES',1.25,80)])
def test_share_transform_has_no_spurious_profit(path, kind, ratio, raw_price):
    prices, events, _ = path
    prices[1].update(open=raw_price,close=raw_price)
    prices[-1]['open']=raw_price
    events.append(action(kind,new_shares_per_old_share=ratio))
    assert compute_open_window(*path)['gross_total_return_multiplier'] == pytest.approx(1)


def test_split_and_cash_same_day_use_pre_event_raw_shares(path):
    prices, events, _=path
    prices[1].update(open=45,close=45);prices[-1]['open']=45
    events.extend([action('SPLIT',new_shares_per_old_share=2),
                   dict(action('CASH_DIVIDEND',cash_per_pre_action_share=10),economic_event_id='cash')])
    assert compute_open_window(*path)['gross_total_return_multiplier'] == pytest.approx(1)


@pytest.mark.parametrize('kind',['DELISTING','MERGER','RIGHTS_ISSUE','SPINOFF','HALT','TERMINAL_MINUS_50_PERCENT'])
def test_unsupported_or_terminal_actions_fail_entire_window(path,kind):
    path[1].append(action(kind))
    with pytest.raises(PreparationBlocked,match='UNSUPPORTED_CORPORATE_ACTION'):
        compute_open_window(*path)


@pytest.mark.parametrize('fault,code',[
    ('missing_date','MISSING_PRICE_SESSION'),('zero_open','POSITIVE_VALUE_REQUIRED'),
    ('halt','TRADABILITY_UNVERIFIED'),('episode','ASSET_EPISODE_MISMATCH'),
    ('unknown_coverage','EVENT_COVERAGE_REQUIRED'),('adjusted_cash','SHARE_BASIS_REQUIRED'),
    ('duplicate_event','DUPLICATE_EVENT'),('raw_receipt','EVENT_RESOLUTION_REQUIRED'),
    ('shifted_ex_date','EVENT_OUTSIDE_SESSION_PATH'),('cash_close_missing','POSITIVE_VALUE_REQUIRED')])
def test_incomplete_market_inputs_cannot_be_guessed(path,fault,code):
    p,e,c=path
    if fault=='missing_date':p.pop(1)
    elif fault=='zero_open':p[1]['open']=0
    elif fault=='halt':p[1]['open_status']='SUSPENDED'
    elif fault=='episode':p[-1]['listing_episode_id']='relisted'
    elif fault=='unknown_coverage':c['status']='UNKNOWN'
    elif fault=='adjusted_cash':c['event_cash_basis']='TERMINAL_ADJUSTED_DPS'
    elif fault=='duplicate_event':e.extend([action('SPLIT',new_shares_per_old_share=2)]*2)
    elif fault=='raw_receipt':e.append(dict(action('CASH_DIVIDEND',cash_per_pre_action_share=10),canonical=False))
    elif fault=='shifted_ex_date':e.append(action('CASH_DIVIDEND',date='2025-01-04',cash_per_pre_action_share=10))
    else:e.append(action('CASH_DIVIDEND',cash_per_pre_action_share=10));p[1]['close']=None
    with pytest.raises(PreparationBlocked,match=code):compute_open_window(*path)


@pytest.fixture
def pit():
    source=lambda at:dict(status='VERIFIED_SOURCE_AVAILABILITY',available_at=at,
                         evidence_ref='synthetic-evidence',availability_basis='OFFICIAL_PUBLICATION')
    sources={'old':source('2025-01-30T18:00:00+09:00'),
             'new':source('2025-02-01T08:30:00+09:00'),
             'universe':source('2025-01-30T20:00:00+09:00'),'cap':source('2025-01-30T20:00:00+09:00')}
    candidates=[dict(factor_id='factor',definition_hash='a'*16,asset_id=1,as_of_date='2025-01-30',
                     signed_score=-3.,input_refs=['old'],dependency_coverage='COMPLETE_REVIEWED'),
                dict(factor_id='factor',definition_hash='a'*16,asset_id=1,as_of_date='2025-01-31',
                     signed_score=999.,input_refs=['new'],dependency_coverage='COMPLETE_REVIEWED')]
    universe=[dict(signal_month='2025-01',asset_id=i,eligible=True,market_cap=100,
                   universe_refs=['universe'],cap_refs=['cap'],dependency_coverage='COMPLETE_REVIEWED') for i in [1,2]]
    return candidates,universe,sources,[dict(factor_id='factor',definition_hash='a'*16)]


def test_latest_observable_score_missing_retention_and_no_double_sign(pit):
    result=prepare_pit_scores(*pit)
    assert result['scores'][0]['signed_score']==-3
    assert result['audit'][0]['selected_as_of_date']=='2025-01-30'
    assert result['scores'][1]['signed_score'] is None
    assert result['scores'][1]['eligible'] is True
    assert len(result['scores'])==2
    assert not result['execution_certified']


@pytest.mark.parametrize('fault,code',[
    ('unverified_source','INPUT_LINEAGE_REQUIRED'),('loaded_at','INPUT_LINEAGE_REQUIRED'),
    ('missing_dependencies','INPUT_LINEAGE_REQUIRED'),('late_universe','PIT_AFTER_CUTOFF'),
    ('wrong_definition','FACTOR_BINDING'),('duplicate_vintage','DUPLICATE_SCORE'),
    ('nan_score','INVALID_SCORE'),('duplicate_universe','DUPLICATE_UNIVERSE')])
def test_pit_cannot_certify_bare_gold_dates_or_ambiguous_revisions(pit,fault,code):
    c,u,s,b=pit
    if fault=='unverified_source':s['old']['status']='UNKNOWN'
    elif fault=='loaded_at':s['old']['availability_basis']='LOADED_AT'
    elif fault=='missing_dependencies':c[0]['dependency_coverage']='UNKNOWN'
    elif fault=='late_universe':s['universe']['available_at']='2025-02-01T00:00:00+09:00'
    elif fault=='wrong_definition':c[0]['definition_hash']='b'*16
    elif fault=='duplicate_vintage':c.append(deepcopy(c[0]))
    elif fault=='nan_score':c[0]['signed_score']=float('nan')
    else:u.append(deepcopy(u[0]))
    with pytest.raises(PreparationBlocked,match=code):prepare_pit_scores(*pit)


def test_missing_external_data_are_explicit_failures_and_draft_rejected_by_runner(tmp_path):
    from strategies import run_monthly_comparison as runner
    result=draft_status()
    assert result['external_blockers']==['OFFICIAL_SESSION_TIMESTAMPS_REQUIRED','KRX300_OPEN_TOTAL_RETURN_REQUIRED']
    assert result['schema_version']!='monthly-comparison-inputs-v1'
    assert not result['execution_certified'] and not result['real_performance_computed']
    path=tmp_path/'draft.json';path.write_text(json.dumps(result))
    with pytest.raises(ValueError,match='Unsupported input bundle schema'):
        runner.load_inputs(path,{})


def test_existing_certified_dividend_pit_fixture_keeps_late_announcements_out():
    # Exercise the existing evidence validator/fixture rather than weaken it in
    # this preparation layer. These helpers produce synthetic certified inputs.
    from test_dividends import _history, _event
    from engine import dividends
    history=_history([_event(announcement_date='2025-02-03',applied_trade_date='2025-01-03')])
    monthly=pd.DataFrame({'asset_id':[1,1],'trade_date':['2025-01-31','2025-02-28']})
    output=dividends.attach(monthly,history)
    assert output.dividend_event_count_ttm.tolist()==[0,1]
    assert output.dividend_cash_ttm.tolist()==[0.,100.]


@pytest.fixture
def external():
    calendar=dict(status='VERIFIED_OFFICIAL_SESSIONS',source_refs=['synthetic-calendar'],sessions=[
        dict(session_month='2025-09',open_at='2025-09-03T10:00:00+09:00'),
        dict(session_month='2025-10',open_at='2025-10-03T09:00:00+09:00')])
    market=dict(status='VERIFIED_OFFICIAL_TOTAL_RETURN',source_refs=['synthetic-market'],market_id='KRX300_TR',
                return_type='gross_total_return',currency='KRW',interval='same_entry_open_to_exit_open',windows=[
                dict(signal_month='2025-08',entry_at=calendar['sessions'][0]['open_at'],exit_at=calendar['sessions'][1]['open_at'],
                     return_available_at='2025-10-03T18:00:00+09:00',gross_total_return_multiplier=1.01)])
    return calendar,market


def test_even_complete_external_metadata_cannot_certify_execution(external):
    result=draft_status(*external)
    assert not result['external_blockers']
    assert not result['execution_certified']
    assert result['status']=='DRAFT_COMPONENTS_NOT_EXECUTION_CERTIFIED'


@pytest.mark.parametrize('fault,code',[('duplicate_calendar','DUPLICATE_SESSION'),('wrong_open','MARKET_TIME_MISMATCH'),
                                     ('early_return','MARKET_TIME_MISMATCH'),('negative_multiplier','INVALID_MARKET_RETURN')])
def test_external_data_validation_does_not_guess_clock_or_market_interval(external,fault,code):
    c,m=external
    if fault=='duplicate_calendar':c['sessions'].append(deepcopy(c['sessions'][0]))
    elif fault=='wrong_open':m['windows'][0]['entry_at']='2025-09-03T09:00:00+09:00'
    elif fault=='early_return':m['windows'][0]['return_available_at']='2025-09-03T10:00:00+09:00'
    else:m['windows'][0]['gross_total_return_multiplier']=-1
    with pytest.raises(PreparationBlocked,match=code):draft_status(c,m)


def test_preparation_cli_obeys_frozen_plan_guard_and_immutable_output(tmp_path):
    from test_monthly_comparison_runner import package
    from scripts.prepare_monthly_inputs import prepare
    root,plan,_,_,_=package.__wrapped__(tmp_path)
    out=tmp_path/'draft.json'
    result=prepare(plan,None,out,research_root=root)
    assert len(result['component_errors'])==2
    with pytest.raises(PreparationBlocked,match='OUTPUT_EXISTS'):prepare(plan,None,out,research_root=root)
    campaign=root/'campaigns'/'new-seal';campaign.mkdir()
    (campaign/'manifest.json').write_text(json.dumps({'campaign_id':'new-seal','oos':{
        'status':'SEALED','start':'2025-10','signal_end':'2028-09','return_end':'2028-10'}}))
    with pytest.raises(ValueError,match='overlaps sealed'):
        prepare(plan,tmp_path/'must-not-read.json',tmp_path/'not-created.json',research_root=root)
    assert not (tmp_path/'not-created.json').exists()


def test_preparation_cli_hashes_sources_and_keeps_draft_components(tmp_path):
    import hashlib
    from test_monthly_comparison_runner import package
    from scripts.prepare_monthly_inputs import prepare
    root,plan,_,_,_=package.__wrapped__(tmp_path)
    artifact=tmp_path/'proof.json';artifact.write_text('{"synthetic":true}')
    source=dict(schema_version='monthly-preparation-source-v1',data_kind='SYNTHETIC_TEST',
        source_files=[{'path':artifact.name,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()}],
        availability_sources={'source':dict(status='VERIFIED_SOURCE_AVAILABILITY',evidence_ref='synthetic',
            availability_basis='OFFICIAL_PUBLICATION',available_at='2025-08-29T18:00:00+09:00')},
        score_candidates=[dict(factor_id='synthetic_factor',definition_hash='a'*16,asset_id=1,as_of_date='2025-08-29',
            signed_score=-2,dependency_coverage='COMPLETE_REVIEWED',input_refs=['source'])],
        universe=[dict(signal_month='2025-08',asset_id=1,eligible=True,market_cap=100,universe_refs=['source'],
            cap_refs=['source'],dependency_coverage='COMPLETE_REVIEWED')])
    source_path=tmp_path/'sources.json';source_path.write_text(json.dumps(source))
    result=prepare(plan,source_path,tmp_path/'draft.json',research_root=root)
    assert result['pit_components']['scores'][0]['signed_score']==-2
    assert result['missing_signal_months']==['2025-09']
    assert not result['execution_certified']
    artifact.write_text('tampered')
    with pytest.raises(PreparationBlocked,match='SOURCE_HASH_MISMATCH'):
        prepare(plan,source_path,tmp_path/'no-draft.json',research_root=root)


@pytest.mark.parametrize('fault,code', [
    ('shifted_month', 'ASSET_SIGNAL_WINDOW_MISMATCH'),
    ('same_month', 'ASSET_SIGNAL_WINDOW_MISMATCH'),
    ('wrong_day', 'ASSET_OFFICIAL_OPEN_DATE_MISMATCH'),
    ('missing_calendar_month', 'ASSET_CALENDAR_WINDOW_MISSING'),
    ('duplicate_calendar', 'DUPLICATE_SESSION'),
])
def test_preparation_rejects_wrong_asset_window_before_writing_draft(tmp_path, external, fault, code):
    import hashlib
    from test_monthly_comparison_runner import package
    from scripts.prepare_monthly_inputs import prepare
    root, plan, _, _, _ = package.__wrapped__(tmp_path)
    calendar, market = external
    dates = ['2025-09-03', '2025-10-03']
    if fault == 'shifted_month': dates = ['2025-10-03', '2025-11-03']
    if fault == 'same_month': dates = ['2025-09-03', '2025-09-30']
    if fault == 'wrong_day': dates = ['2025-09-04', '2025-10-03']
    if fault == 'missing_calendar_month': calendar['sessions'].pop()
    if fault == 'duplicate_calendar': calendar['sessions'].append(deepcopy(calendar['sessions'][0]))
    artifact = tmp_path/'synthetic-proof.json'; artifact.write_text('{"fixture":true}')
    source = dict(schema_version='monthly-preparation-source-v1', data_kind='SYNTHETIC_TEST',
        source_files=[{'path':artifact.name,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()}],
        calendar=calendar, market=market, asset_paths=[dict(signal_month='2025-08',
            prices=[dict(date=d, asset_id=1, listing_episode_id='episode-1', open=100., close=100.,
                open_status='VERIFIED_TRADABLE',close_status='VERIFIED_TRADABLE',source_ref='synthetic-price') for d in dates],
            events=[], coverage=dict(asset_id=1,listing_episode_id='episode-1',status='REVIEWED_COMPLETE',
                session_dates=dates,evidence_refs=['synthetic'],raw_share_basis='RAW_UNADJUSTED',
                event_cash_basis='PRE_EVENT_RAW_SHARE'))])
    file = tmp_path/'source.json';file.write_text(json.dumps(source))
    output = tmp_path/'draft.json'
    with pytest.raises(PreparationBlocked, match=code): prepare(plan, file, output, research_root=root)
    assert not output.exists()


def test_month_binding_without_calendar_never_invents_first_day_or_certifies(path):
    from scripts.prepare_monthly_inputs import _require_signal_window
    row = dict(signal_month='2024-12', coverage=path[2])
    _require_signal_window(row, None)
    assert 'OFFICIAL_SESSION_TIMESTAMPS_REQUIRED' in draft_status()['external_blockers']
    assert draft_status()['execution_certified'] is False


def test_exact_official_first_dates_match_but_are_not_actual_fills(external):
    from scripts.prepare_monthly_inputs import _require_signal_window
    calendar, market = external
    row=dict(signal_month='2025-08',coverage=dict(session_dates=['2025-09-03','2025-10-03']))
    _require_signal_window(row,calendar)
    assert draft_status(calendar,market)['execution_certified'] is False
