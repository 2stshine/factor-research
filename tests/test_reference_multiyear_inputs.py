import pandas as pd
from engine import reference_multiyear_inputs as m


def test_exact_fy_and_visible_filing_not_future_or_missing_year_fallback(monkeypatch):
    current=pd.DataFrame([dict(asset_id=1,date=pd.Timestamp('2021-01-31'),
        financial_known_at=pd.Timestamp('2020-04-01',tz='UTC'),financial_status='AVAILABLE',
        fy_period_end=pd.Timestamp('2019-12-31'),fy_fs_type='CFS')])
    rows=[]
    for year,filing,clock,value in [(2017,'old','2018-04-01',12.),(2017,'future','2022-04-01',999.),
                                    (2015,'different_year','2016-04-01',55.)]:
        rows.append(dict(asset_id=1,period_end=pd.Timestamp(f'{year}-12-31'),filing_id=filing,
            available_at=pd.Timestamp(clock,tz='UTC'),values={'revenue':value},fs_type='CFS',currency='KRW',reasons=[]))
    monkeypatch.setattr(m.source,'verify_capture',lambda p:dict(manifest_sha256='a'*64,
        files=[dict(path='fixture.parquet',asset_ids=[1])]))
    monkeypatch.setattr(m.pd,'read_parquet',lambda p:pd.DataFrame(rows))
    monkeypatch.setattr(m.source,'_bundle',lambda records:records[0])
    result,_=m.attach(current,'unused',years=3)
    assert result.loc[0,'fy2_revenue']==12.
    assert pd.isna(result.loc[0,'fy3_revenue'])  # 2016 absent; never substitute 2015.
    assert result.loc[0,'multiyear_known_at']==current.loc[0,'financial_known_at']


def test_latest_visible_invalid_scope_does_not_resurrect_stale_value(monkeypatch):
    current=pd.DataFrame([dict(asset_id=1,date=pd.Timestamp('2021-01-31'),
        financial_known_at=pd.Timestamp('2020-04-01',tz='UTC'),financial_status='AVAILABLE',
        fy_period_end=pd.Timestamp('2019-12-31'),fy_fs_type='CFS')])
    rows=[dict(asset_id=1,period_end=pd.Timestamp('2017-12-31'),filing_id=key,
        available_at=pd.Timestamp(clock,tz='UTC'),values={'revenue':12.},fs_type=scope,currency='KRW',reasons=[])
        for key,clock,scope in [('old','2018-04-01','CFS'),('new','2020-10-01','OFS')]]
    monkeypatch.setattr(m.source,'verify_capture',lambda p:dict(manifest_sha256='a'*64,
        files=[dict(path='fixture.parquet',asset_ids=[1])]))
    monkeypatch.setattr(m.pd,'read_parquet',lambda p:pd.DataFrame(rows))
    monkeypatch.setattr(m.source,'_bundle',lambda records:records[0])
    result,_=m.attach(current,'unused',years=2)
    assert pd.isna(result.loc[0,'fy2_revenue'])
