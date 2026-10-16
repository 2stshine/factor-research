import numpy as np
import pytest
from engine.reference_formulaic import FORMULAS,evaluate,required_history

@pytest.mark.parametrize('number',list(FORMULAS))
def test_two_independent_interpreters_and_future_prefix(number):
    rng=np.random.default_rng(999)
    close=np.exp(rng.normal(0,.05,(310,8)).cumsum(axis=0))*100
    data=dict(close=close,open=close*rng.uniform(.97,1.03,close.shape),
        high=close*1.04,low=close*.96,volume=rng.uniform(1000,20000,close.shape),
        returns=np.vstack([np.full((1,8),np.nan),close[1:]/close[:-1]-1]))
    data['volume'][38,2]=np.nan
    data['vwap']=(data['high']+data['low']+data['close'])/3
    a=evaluate(FORMULAS[number],data)
    b=evaluate(FORMULAS[number],data,'numpy')
    np.testing.assert_allclose(a,b,rtol=1e-7,atol=1e-8,equal_nan=True)
    prefix=evaluate(FORMULAS[number],{k:v[:290] for k,v in data.items()})
    np.testing.assert_allclose(a[:290],prefix,rtol=0,atol=0,equal_nan=True)
    assert 0<=required_history(FORMULAS[number])<=251

def test_missing_condition_does_not_create_a_zero_measurement():
    data={'x':np.array([[np.nan,1.]])}
    assert np.isnan(evaluate('where(x>0,x,0)',data)[0,0])

def test_no_untrusted_code_execution():
    with pytest.raises(ValueError):evaluate('__import__("os")',{})
