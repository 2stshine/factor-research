"""Independently reconstruct fixed KIS asset/month aggregates from daily rows."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from engine.reference_db import connect
from scripts.publish_reference_expansion import load_json,save_json,sha

MONTHS=['2015-01','2015-02','2015-03','2019-08','2020-02','2020-03','2025-03','2025-04','2025-05','2026-09']

def aggregate(prices,observations):
 result=[]
 prices=prices.copy();prices.trade_date=pd.to_datetime(prices.trade_date)
 for (asset,month),g in prices.groupby(['asset_id',prices.trade_date.dt.to_period('M')]):
  end=month.to_timestamp(how='end').normalize();cutoff=(end+pd.Timedelta(days=1)).tz_localize('Asia/Seoul').tz_convert('UTC')
  expected=[d for d in g.trade_date if (d+pd.Timedelta(days=1,hours=8,minutes=30)).tz_localize('Asia/Seoul').tz_convert('UTC')<cutoff]
  if not expected:continue
  selected=observations.loc[observations.asset_id.eq(asset)&pd.to_datetime(observations.trade_date).isin(expected)]
  selected=selected.sort_values(['first_observed_at','revision']).drop_duplicates(['asset_id','trade_date','kind'],keep='last')
  inv=selected.loc[selected.kind.eq('investor')];short=selected.loc[selected.kind.eq('short')]
  ip=inv.payload.tolist();sp=short.payload.tolist()
  def total(rows,key):return float(sum(float(r[key]) for r in rows)) if rows else np.nan
  row=dict(asset_id=asset,date=end,expected_days=len(expected),investor_days=len(inv),short_days=len(short),
   fb=total(ip,'frgn_shnu_vol'),fs=total(ip,'frgn_seln_vol'),ib=total(ip,'orgn_shnu_vol'),isell=total(ip,'orgn_seln_vol'),
   fp=float(sum(float(r['frgn_ntby_qty'])>0 for r in ip)),fn=float(sum(float(r['frgn_ntby_qty'])<0 for r in ip)),
   ip=float(sum(float(r['orgn_ntby_qty'])>0 for r in ip)),inneg=float(sum(float(r['orgn_ntby_qty'])<0 for r in ip)),
   sq=total(sp,'short_volume'),sv=total(sp,'original_daily_volume'))
  for rows,key in ((inv,'investor_known_at'),(short,'short_known_at')):
   row[key]=pd.to_datetime(rows.research_available_at,utc=True).max()
  result.append(row)
 return pd.DataFrame(result)

def run(source,output):
 source=Path(source);m=load_json(source/'manifest.json');parts=[]
 for f in m['files']:
  if sha(source/f['path'])!=f['sha256']:raise ValueError('Changed source')
  parts.append(pd.read_parquet(source/f['path']))
 p=pd.concat(parts);assets=sorted(p.asset_id.unique());sample=[int(assets[(len(assets)-1)*i//4]) for i in range(5)]
 target=p.loc[p.asset_id.isin(sample)&pd.to_datetime(p.date).dt.strftime('%Y-%m').isin(MONTHS)]
 with connect() as conn,conn.cursor() as q:
  q.execute("SET LOCAL statement_timeout='5min'")
  q.execute("""SELECT p.asset_id,p.trade_date FROM public.price_daily p JOIN public.dq_run d ON d.run_id=p.quality_run_id AND d.status='CERTIFIED'
   WHERE p.asset_id=ANY(%s::bigint[]) AND p.source='KRX' AND p.market IN ('KOSPI','KOSDAQ') AND to_char(p.trade_date,'YYYY-MM')=ANY(%s::text[])
   AND p.trade_date BETWEEN '2015-01-01' AND '2026-09-30'""",(sample,MONTHS))
  prices=pd.DataFrame(q.fetchall(),columns=[d.name for d in q.description])
  q.execute("""SELECT k.asset_id,k.trade_date,k.kind,k.payload,k.first_observed_at,k.research_available_at,k.revision
   FROM public.kis_market_observation k JOIN public.dq_run d ON d.run_id=k.quality_run_id AND d.status='CERTIFIED'
   WHERE k.asset_id=ANY(%s::bigint[]) AND k.venue='J' AND to_char(k.trade_date,'YYYY-MM')=ANY(%s::text[])
   AND k.trade_date BETWEEN '2015-01-01' AND '2026-09-30' AND k.first_observed_at<=%s::timestamptz""",(sample,MONTHS,m['captured_at']))
  observations=pd.DataFrame(q.fetchall(),columns=[d.name for d in q.description])
 actual=aggregate(prices,observations)
 key=['asset_id','date'];target['date']=pd.to_datetime(target.date)
 check=actual.merge(target,on=key,validate='one_to_one',suffixes=('_py','_sql'),how='outer',indicator=True)
 if not check._merge.eq('both').all() or len(check)<10:raise ValueError('Independent source sample coverage mismatch')
 numeric=['expected_days','investor_days','short_days','fb','fs','ib','isell','fp','fn','ip','inneg','sq','sv']
 for col in numeric:
  np.testing.assert_allclose(check[col+'_py'],check[col+'_sql'],rtol=1e-12,atol=0,equal_nan=True,err_msg=col)
 for col in ('investor_known_at','short_known_at'):
  left=pd.to_datetime(check[col+'_py'],utc=True);right=pd.to_datetime(check[col+'_sql'],utc=True)
  if not ((left==right)|(left.isna()&right.isna())).all():raise ValueError('Known-at reconstruction differs')
 result=dict(status='FIXED_RAW_DAILY_RECONSTRUCTION_PASSED',source_manifest_sha256=sha(source/'manifest.json'),
  sampled_asset_ids=sample,sampled_months=MONTHS,asset_months=len(check),price_rows=len(prices),kis_rows=len(observations),
  validated_fields=numeric+['investor_known_at','short_known_at'],full_raw_reconstruction=False)
 save_json(output,result);print(result,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.source,a.output)
