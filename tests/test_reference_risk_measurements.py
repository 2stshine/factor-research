import numpy as np
import pandas as pd
from engine.reference_risk_measurements import monthly_risk,price_delay,volume_trend

def test_vector_and_scalar_on_missing_constant_and_regular_returns():
    rng=np.random.default_rng(553)
    dates=pd.bdate_range('2010-01-01',periods=1300)
    ret=rng.normal(0,.02,(1300,12));ret[:,0]=0;ret[100:160,1]=np.nan
    close=100*np.exp(np.nancumsum(ret,axis=0))
    data=dict(returns=ret,open=close*(1+rng.normal(0,.005,ret.shape)),high=close*1.04,low=close*.96,
              close=close,trading_value=rng.uniform(1e8,1e10,ret.shape))
    market=rng.normal(.0002,.008,1300)
    a=monthly_risk(data,dates,1299,market)
    b=monthly_risk(data,dates,1299,market,oracle=True)
    for key in a:
        np.testing.assert_allclose(a[key],b[key],rtol=1e-7,atol=1e-8,equal_nan=True,err_msg=key)

def test_calendar_volume_and_weekly_delay_independent():
    rng=np.random.default_rng(776)
    vol=rng.uniform(10,100,(80,9));vol[1:8,0]=np.nan
    np.testing.assert_allclose(volume_trend(vol,70),volume_trend(vol,70,True),rtol=1e-9,atol=1e-12)
    dates=pd.date_range('2010-01-01',periods=80,freq='W-FRI')
    m=pd.Series(rng.normal(0,.03,80),index=dates)
    r=pd.DataFrame(rng.normal(0,.03,(80,9)),index=dates)
    np.testing.assert_allclose(price_delay(r,m,dates[-1]),price_delay(r,m,dates[-1],True),rtol=1e-9,atol=1e-12)
