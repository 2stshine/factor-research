"""Synthetic software checks, not evidence of Korean market profitability."""
import math
import re
import sqlite3

import numpy as np
import pandas as pd
import pytest

from engine import reference_price_expansion as expansion


def daily(rows=850, assets=2):
    dates = pd.bdate_range("2015-01-01", periods=rows)
    output = []
    for asset in range(1, assets+1):
        returns = np.resize(np.array([-.01, .005, .001, -.003, .007, -.001, .006]), rows)
        returns = returns + asset*.0001
        adjusted = (100*asset)*np.cumprod(1+returns)
        # Raw and adjusted prices differ by a consistent split factor.
        raw = adjusted*np.where(np.arange(rows)<200, 2, 1)
        intraday = np.resize(np.array([1.01, .995, 1.002]), rows)
        volume = np.where(np.arange(rows)%13==0, 0, 1000+np.arange(rows)%300).astype(float)
        for i, date in enumerate(dates):
            output.append(dict(asset_id=asset, stock_code=f"{asset:05d}0", trade_date=date,
                known_at=date.tz_localize("Asia/Seoul")+pd.Timedelta(hours=16),
                market="KOSPI" if asset==1 else "KOSDAQ", adj_close=adjusted[i],
                market_cap=raw[i]*100000, open=raw[i]/intraday[i], close=raw[i],
                high=raw[i]*1.02, low=raw[i]*.97, volume=volume[i], shares=100000.,
                trading_value=raw[i]*volume[i]))
    return pd.DataFrame(output)


@pytest.fixture(scope="module")
def raw():
    return daily()


@pytest.fixture(scope="module")
def monthly(raw):
    return expansion.aggregate_daily_for_validation(raw)


def test_thirteen_distinct_frozen_specs_and_input_columns():
    assert len(expansion.REFERENCE_SPECS)==13
    assert set(expansion.FEATURE_CONTRACTS)==set(expansion.FEATURE_UNITS)
    assert len(expansion.ADDITIONAL_COLUMNS)==len(set(expansion.ADDITIONAL_COLUMNS))
    assert all(spec["orientation"] in (-1,1) for spec in expansion.REFERENCE_SPECS.values())
    # Keep publication/evidence status out of this calculator.
    assert not any("alpha_approved" in spec for spec in expansion.REFERENCE_SPECS.values())


def test_all_thirteen_have_finite_eligible_values(monthly):
    for ref in expansion.REFERENCE_SPECS:
        values=expansion.calculate(monthly,ref).dropna()
        assert len(values)>0, ref
        assert np.isfinite(values).all(), ref


def test_direct_month_estimates_closed_form(raw,monthly):
    last=monthly[monthly.asset_id.eq("1")].iloc[-2]
    selected=raw[(raw.asset_id==1)&raw.trade_date.dt.to_period("M").eq(last.date.to_period("M"))]
    turn=selected.volume/selected.shares
    assert last.share_turnover_1m==pytest.approx(turn.mean())
    assert last.share_turnover_cv_1m==pytest.approx(turn.std(ddof=1)/turn.mean())
    assert last.mean_traded_value_1m==pytest.approx(selected.trading_value.mean())
    assert last.traded_value_cv_1m==pytest.approx(selected.trading_value.std(ddof=1)/selected.trading_value.mean())
    assert last.zero_volume_fraction_1m==pytest.approx(selected.volume.eq(0).mean())
    assert last.parkinson_variance_1m==pytest.approx(math.log(1.02/.97)**2/(4*math.log(2)))
    assert expansion.calculate(monthly,"kr_traded_value_1m_v1").loc[last.name]==pytest.approx(math.log(last.mean_traded_value_1m))
    assert expansion.calculate(monthly,"kr_nominal_price_v1").loc[last.name]==pytest.approx(math.log(last.nominal_close))


def test_risk_moments_centered_definition(raw,monthly):
    last=monthly[monthly.asset_id.eq("1")].iloc[-1]
    selected=raw[(raw.asset_id==1)&raw.trade_date.le(last.trade_date)]
    returns=selected.adj_close.pct_change(fill_method=None).iloc[-252:].to_numpy()
    centered=returns-returns.mean()
    assert last.downside_semideviation_252d==pytest.approx(np.sqrt(np.mean(np.minimum(returns,0)**2)))
    assert last.return_skew_252d==pytest.approx(np.mean(centered**3)/np.mean(centered**2)**1.5)
    assert last.daily_volatility_252d==pytest.approx(np.std(returns,ddof=1))


def test_overnight_intraday_multiply_to_price_return_even_across_split(raw,monthly):
    asset=raw[raw.asset_id.eq(1)].reset_index(drop=True)
    for _, row in monthly[monthly.asset_id.eq("1")].iloc[1:].iterrows():
        positions=asset.index[asset.trade_date.dt.to_period("M").eq(row.date.to_period("M"))]
        expected=asset.adj_close.iloc[positions[-1]]/asset.adj_close.iloc[positions[0]-1]
        assert (1+row.overnight_return_1m)*(1+row.intraday_return_1m)==pytest.approx(expected)
    # The split must not manufacture a ~-50% overnight loss.
    split_month=asset.trade_date.iloc[200].to_period("M")
    split=monthly[monthly.asset_id.eq("1") & monthly.date.dt.to_period("M").eq(split_month)].iloc[0]
    assert split.overnight_return_1m>-.5


def test_invalid_overnight_day_is_not_silently_compounded_as_full_month(raw):
    frame=raw.copy()
    frame.loc[50,"open"]=0
    panel=expansion.aggregate_daily_for_validation(frame)
    target=(panel.asset_id.eq("1") & panel.date.dt.to_period("M").eq(frame.trade_date.iloc[50].to_period("M")))
    for ref in ["kr_overnight_momentum_1m_v1","kr_intraday_momentum_1m_v1"]:
        assert expansion.calculate(panel,ref)[target].isna().all()
    # First observed month lacks its prior closing price, hence no overnight result.
    assert pd.isna(expansion.calculate(panel,"kr_overnight_momentum_1m_v1").iloc[0])


def test_information_discreteness_count_path_and_skip_recent_month(monthly):
    ref="kr_information_discreteness_12_2_v1"
    values=expansion.calculate(monthly,ref)
    group=monthly[monthly.asset_id.eq("1")].reset_index()
    row=group.iloc[20]
    history=group.iloc[9:20]
    sign=np.sign(group.iloc[19].adj_close/group.iloc[8].adj_close-1)
    expected=sign*(history.negative_return_days_1m.sum()-history.positive_return_days_1m.sum())/history.price_return_observations_1m.sum()
    assert values.loc[row["index"]]==pytest.approx(expected)
    changed=monthly.copy()
    latest=changed.date.max()
    mask=changed.date.eq(latest)
    changed.loc[mask,"adj_close"]*=100
    changed.loc[mask,["positive_return_days_1m","negative_return_days_1m"]]=0
    pd.testing.assert_series_equal(values,expansion.calculate(changed,ref))


def test_long_reversal_exact_month_lags_and_missing_interior_month(monthly):
    ref="kr_reversal_36_13_price_v1"
    group=monthly[monthly.asset_id.eq("1")]
    values=expansion.calculate(monthly,ref)
    last=group.iloc[36]
    assert values.loc[last.name]==pytest.approx(group.iloc[24].adj_close/group.iloc[0].adj_close-1)
    assert values.loc[group.iloc[:36].index].isna().all()
    broken=monthly.drop(group.index[15])
    broken_values=expansion.calculate(broken,ref)
    assert broken_values[broken.asset_id.eq("1")].isna().all()
    assert broken_values[broken.asset_id.eq("2")].notna().any()


def test_future_daily_mutation_does_not_change_prior_features(raw):
    baseline=expansion.aggregate_daily_for_validation(raw)
    future=raw.copy()
    cutoff=pd.Timestamp("2017-03-31")
    for col in ["adj_close","market_cap","trading_value","open","high","low","close","volume","shares"]:
        future.loc[future.trade_date.gt(cutoff),col]*=1.7
    actual=expansion.aggregate_daily_for_validation(future)
    pd.testing.assert_frame_equal(baseline[baseline.date.le(cutoff)],actual[actual.date.le(cutoff)])
    for ref in expansion.REFERENCE_SPECS:
        pd.testing.assert_series_equal(expansion.calculate(baseline,ref)[baseline.date.le(cutoff)],
                                       expansion.calculate(actual,ref)[actual.date.le(cutoff)])


@pytest.mark.parametrize("ref,column,value",[
    ("kr_turnover_1m_v1","turnover_observations_1m",14),
    ("kr_turnover_cv_1m_v1","turnover_observations_1m",20.5),
    ("kr_traded_value_1m_v1","mean_traded_value_1m",0),
    ("kr_zero_volume_1m_v1","zero_volume_fraction_1m",1.1),
    ("kr_downside_risk_252d_v1","daily_return_observations_252d",199),
    ("kr_return_skew_252d_v1","daily_return_observations_252d",253),
    ("kr_parkinson_1m_v1","parkinson_variance_1m",-1),
    ("kr_nominal_price_v1","nominal_close",np.inf),
    ("kr_information_discreteness_12_2_v1","positive_return_days_1m",50),
])
def test_invalid_values_counts_do_not_create_measurements(monthly,ref,column,value):
    changed=monthly.copy()
    changed[column]=value
    assert expansion.calculate(changed,ref).isna().all()


def test_zero_trade_is_valid_but_zero_mean_cv_log_are_undefined(raw):
    frame=raw.copy()
    frame["volume"],frame["trading_value"]=0.,0.
    panel=expansion.aggregate_daily_for_validation(frame)
    assert expansion.calculate(panel,"kr_zero_volume_1m_v1").dropna().eq(1).all()
    assert expansion.calculate(panel,"kr_turnover_1m_v1").dropna().eq(0).all()
    for ref in ["kr_turnover_cv_1m_v1","kr_traded_value_1m_v1","kr_traded_value_cv_1m_v1"]:
        assert expansion.calculate(panel,ref).isna().all()


@pytest.mark.parametrize("kind",["naive","future","preclose","label","duplicate","integer_ticker","strings"])
def test_daily_oracle_rejects_unbound_schema_clock_identity(raw,kind):
    changed=raw.iloc[:80].copy()
    if kind=="naive":changed.known_at=changed.known_at.dt.tz_localize(None)
    elif kind=="future":changed.loc[0,"known_at"]+=pd.Timedelta(days=1)
    elif kind=="preclose":changed.loc[0,"known_at"]-=pd.Timedelta(hours=2)
    elif kind=="label":changed["total_return_close"]=123.
    elif kind=="duplicate":changed=pd.concat([changed,changed.iloc[:1]])
    elif kind=="integer_ticker":changed.stock_code=changed.stock_code.astype(int)
    elif kind=="strings":changed.volume=changed.volume.astype(str)
    with pytest.raises(ValueError):expansion.aggregate_daily_for_validation(changed)


def test_no_cross_asset_windows_or_ticker_reuse_stitching(raw,monthly):
    left=expansion.aggregate_daily_for_validation(raw[raw.asset_id.eq(1)])
    pd.testing.assert_frame_equal(left,monthly[monthly.asset_id.eq("1")].reset_index(drop=True))
    changed=raw.copy()
    changed.loc[changed.asset_id.eq(2),"stock_code"]="0037T0"
    actual=expansion.aggregate_daily_for_validation(changed)
    assert set(actual[actual.asset_id.eq("2")].stock_code)=={"0037T0"}
    for ref in expansion.REFERENCE_SPECS:
        pd.testing.assert_series_equal(expansion.calculate(monthly,ref),expansion.calculate(actual,ref))


class StddevWindow:
    """Independent centered SQLite sample-std aggregate/window implementation."""
    def __init__(self):self.values=[]
    def step(self,value):
        if value is not None:self.values.append(value)
    def inverse(self,value):
        if value is not None:self.values.remove(value)
    def value(self):
        return float(np.std(self.values,ddof=1)) if len(self.values)>1 else None
    def finalize(self):return self.value()


def execute_sqlite_dialect_of_production_sql(raw):
    """Execute actual estimator expressions; adapt only PG syntax/identity join."""
    conn=sqlite3.connect(":memory:")
    conn.execute("ATTACH DATABASE ':memory:' AS public")
    conn.create_window_function("stddev_samp",1,StddevWindow)
    conn.create_function("date_trunc",2,lambda _,v:v[:7]+"-01")
    conn.create_function("least",2,lambda a,b:None if a is None or b is None else min(a,b))
    for name,func,n in [("ln",math.log,1),("exp",math.exp,1),("sqrt",math.sqrt,1),("power",math.pow,2)]:
        conn.create_function(name,n,lambda *args,fn=func:None if any(v is None for v in args) else fn(*args))
    price=raw.drop(columns=["known_at","stock_code"]).copy()
    price.trade_date=price.trade_date.dt.strftime("%Y-%m-%d")
    price["source"],price["quality_run_id"]="KRX","fixture-certified-not-empirical"
    price.to_sql("price_daily",conn,index=False)
    conn.execute("CREATE TABLE public.price_daily AS SELECT * FROM main.price_daily")
    conn.execute("CREATE TABLE public.asset(asset_id INTEGER,exchange TEXT,asset_type TEXT,instrument_type TEXT)")
    conn.executemany("INSERT INTO public.asset VALUES(?,'KRX','stock','common_stock')",[(int(v),) for v in raw.asset_id.unique()])
    conn.execute("CREATE TABLE public.dq_run(run_id TEXT,status TEXT)")
    conn.execute("INSERT INTO public.dq_run VALUES('fixture-certified-not-empirical','CERTIFIED')")
    query=expansion.EXTENDED_PRICE_SQL
    query=re.sub(r"::(?:float8|numeric|text|date|bigint\[\])","",query)
    query=query.replace("p.asset_id=ANY(%s)","p.asset_id IN ("+",".join(str(v) for v in raw.asset_id.unique())+")")
    query=query.replace("%s","?",2)
    query=query.replace("i.stock_code,i.n AS ticker_match_count","'fixture' AS stock_code,1 AS ticker_match_count")
    query=re.sub(r"FROM f JOIN LATERAL \(.*?\) i ON true","FROM f",query,flags=re.S)
    try:return pd.read_sql_query(query,conn,params=(price.trade_date.min(),price.trade_date.max()))
    finally:conn.close()


def test_actual_sql_expressions_match_independent_daily_oracle(raw,monthly):
    observed=execute_sqlite_dialect_of_production_sql(raw)
    observed.asset_id=observed.asset_id.astype(str)
    observed.trade_date=pd.to_datetime(observed.trade_date)
    joined=monthly.merge(observed,on=["asset_id","trade_date"],suffixes=("_oracle","_sql"),validate="one_to_one")
    assert len(joined)==len(monthly)==len(observed)
    original=["adj_close","market_cap","daily_volatility_252d","daily_return_observations_252d",
              "price_high_252d","price_high_observations_252d","amihud_illiquidity_1m","amihud_observations_1m",
              "max_daily_return_1m","max_daily_return_observations_1m"]
    for column in original+list(expansion.ADDITIONAL_COLUMNS):
        np.testing.assert_allclose(joined[column+"_oracle"],joined[column+"_sql"],rtol=1e-10,atol=1e-13,
                                   equal_nan=True,err_msg=column)


def test_sql_is_feature_only_bounded_and_preserves_original_estimates():
    query=expansion.EXTENDED_PRICE_SQL.lower()
    assert query.count("%s")==3
    assert "total_return" not in query and "gold." not in query and "fwd_" not in query
    assert "q.status='certified'" in query
    assert "p.asset_id=any" in query
    assert "rows between 251 preceding and current row" in query
    assert "following" not in query


def test_constant_return_skew_is_undefined_not_cancellation_artifact():
    frame=daily(350,1)
    frame["adj_close"]=100*np.cumprod(np.repeat(1.01,len(frame)))
    observed=execute_sqlite_dialect_of_production_sql(frame)
    oracle=expansion.aggregate_daily_for_validation(frame)
    assert observed.return_skew_252d.isna().all()
    assert oracle.return_skew_252d.isna().all()
