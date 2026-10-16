import copy

import numpy as np
import pandas as pd
import pytest

from engine import reference_snapshot_strategy as s
from engine import reference_snapshot_turnover as t
from engine import snapshot_cost_diagnostics as d
from tests.test_reference_snapshot_strategy import fixture

CONFIG = s.read_json('research/phenomena/korean-equity-cost-schedule-20261016.json')


@pytest.mark.parametrize('day,bps', [('2019-05-29',30),('2019-05-30',25),('2020-12-28',25),('2020-12-29',23),
    ('2022-12-27',23),('2022-12-28',20),('2023-12-26',20),('2023-12-27',18),('2024-12-26',18),('2024-12-27',15),('2025-12-28',15),('2025-12-29',20)])
def test_trade_date_tax_boundaries(day,bps):
    assert d.tax_bps(day,CONFIG)==bps


def test_tax_does_not_extrapolate_beyond_reviewed_dates():
    with pytest.raises(ValueError):d.tax_bps('2027-01-01',CONFIG)


def test_dated_cost_components_initial_buy_no_tax():
    targets=[('2024-11',{1:1.}),('2024-12',{2:1.})]
    lookup={('2024-11',1):0.,('2024-12',2):0.}
    dates={'2024-11':'2024-11-29','2024-12':'2024-12-30'}
    rates={m:(6.5,6.5+d.tax_bps(day,CONFIG)) for m,day in dates.items()}
    p=t.replay_path(targets,lookup,assumption=t.ASSUMPTIONS[0],buy_bps=0,sell_bps=0,rates_by_month=rates)
    d.components(p,CONFIG,5,dates)
    assert p['monthly'][0]['tax_cost']==0
    assert p['monthly'][1]['sell_tax_bps']==15
    assert p['monthly'][1]['tax_cost']==pytest.approx(p['monthly'][1]['sell_notional']*.0015)
    assert p['monthly'][1]['nav_after_cost']==pytest.approx(p['monthly'][1]['nav_before']*(1-.00215)/(1+.00065))
    with pytest.raises(ValueError,match='every target month'):
        t.replay_path(targets,lookup,assumption=t.ASSUMPTIONS[0],buy_bps=0,sell_bps=0,rates_by_month={})


def test_size_thresholds():
    assert d.size_labels(np.array([299999999999,300000000000,999999999999,1000000000000])).tolist()==[d.SIZE_NAMES[2],d.SIZE_NAMES[1],d.SIZE_NAMES[1],d.SIZE_NAMES[0]]


def test_linked_attribution_is_terminal_wealth_difference():
    rows=[{'net_return':.1,'benchmark_return':.05,'effects':{'a':.08,'cost':-.03}},
          {'net_return':-.2,'benchmark_return':.1,'effects':{'a':-.28,'cost':-.02}}]
    result=d.link_effects(rows)
    assert sum(result['linked_effects'].values())==pytest.approx(1.1*.8-1.05*1.1)


def test_hierarchical_attribution_reconciles_and_missing_stays_visible():
    panel,settings=fixture()
    panel.loc[panel.asset_id.mod(2).eq(0),'market']='KOSDAQ'
    panel['market_cap']=np.where(panel.asset_id.lt(8),1e11,np.where(panel.asset_id.lt(15),5e11,2e12))
    folds=[s.run_month(panel,['f_a','f_b'],settings,m,round_trip_bps=50) for m in ['2019-05','2019-06']]
    before=copy.deepcopy(folds)
    dates={'2019-05':'2019-05-31','2019-06':'2019-06-28'}
    rates={m:(1.5,26.5) for m in dates}
    result=t.evaluate(panel,folds,buy_bps=1.5,sell_bps=1.5,rates_by_month=rates)
    key='selected_pca_ridge/q20_equal'
    for a,path in result['paths'][key]['scenarios'].items():
        d.components(path,CONFIG,0,dates)
        z=d.attribute(panel,folds,key,path,{m:{'KOSPI':.05,'KOSDAQ':-.02} for m in dates},a)
        assert sum(z['periods']['FULL']['linked_effects'].values())==pytest.approx(z['periods']['FULL']['terminal_wealth_gap'])
        assert z['industry_attribution'].startswith('NOT_IDENTIFIED')
    assert folds==before


def test_higher_slippage_cannot_improve_fixed_target_return():
    targets=[('2024-11',{1:.5,2:.5}),('2024-12',{2:.5,3:.5})]
    lookup={(m,a):.1*a for m,w in targets for a in w}
    results=[t.replay_path(targets,lookup,assumption=t.ASSUMPTIONS[0],buy_bps=1.5+v,sell_bps=16.5+v)['summary']['annualized_net_return'] for v in [0,5,10,25]]
    assert results==sorted(results,reverse=True)


def mini_attribution(markets, caps, returns, weights, benchmarks):
    panel=pd.DataFrame({'asset_id':[1,2],'month':['2020-01']*2,'eligible':[True]*2,
                        'market':markets,'market_cap':caps,'outcome':returns})
    p={'portfolio':'q20_equal','selected_assets':[i+1 for i,w in enumerate(weights) if w],
       'weights':[w for w in weights if w]}
    fold={'signal_month':'2020-01','models':{'m':{'portfolios':[p]}}}
    gross=float(np.dot(returns,weights))
    path={'monthly':[{'signal_month':'2020-01','gross_return':gross,'net_return':gross,'nav_before':1.,
                       'commission_cost':0.,'tax_cost':0.,'slippage_cost':0.}]}
    return d.attribute(panel,[fold],'m/q20_equal',path,{'2020-01':benchmarks},t.ASSUMPTIONS[0])['monthly'][0]['effects']


def test_market_allocation_known_example():
    e=mini_attribution(['KOSPI','KOSDAQ'],[1e11,1e11],[.1,0.],[.5,.5],{'KOSPI':.1,'KOSDAQ':0.})
    assert e['market_allocation']==pytest.approx(-.05)
    assert e['index_proxy_residual']==0
    assert e['size_allocation_within_market']==0
    assert e['stock_selection_within_market_size']==0


def test_size_allocation_known_example():
    benchmark=2/11
    e=mini_attribution(['KOSPI','KOSPI'],[1e12,1e11],[.2,0.],[0.,1.],{'KOSPI':benchmark,'KOSDAQ':0.})
    assert e['market_allocation']==0
    assert e['index_proxy_residual']==pytest.approx(0)
    assert e['size_allocation_within_market']==pytest.approx(-benchmark)
    assert e['stock_selection_within_market_size']==0
