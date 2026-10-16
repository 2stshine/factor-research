"""Reconstruct eligibility and monthly totals independently in Python.

All partial-resumption stock-days plus fixed assets over the complete history.
This tests measurement correctness, not first-vintage PIT or profitability.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from engine.reference_db import connect
from engine.research_generation import digest
from scripts.capture_reference_short_daily import SQL as RAW_SQL
from scripts.capture_reference_short_eligible import load_policy
from scripts.publish_reference_expansion import load_json,save_json,sha

COUNTS=['expected_days','eligible_days','excluded_regime_days','excluded_individual_days','short_days','bad_short','bad_identity']

def aggregate(raw,members,restrictions):
 p=raw.copy();p['trade_date']=pd.to_datetime(p.trade_date)
 if p.duplicated(['asset_id','trade_date']).any():raise ValueError('Duplicate daily row')
 m=members[['market','stock_code','trade_date']].copy();m.trade_date=pd.to_datetime(m.trade_date);m['member']=True
 r=restrictions[['stock_code','trade_date']].copy();r.trade_date=pd.to_datetime(r.trade_date);r['restricted']=True
 p=p.merge(m,on=['market','stock_code','trade_date'],how='left',validate='many_to_one').merge(r,on=['stock_code','trade_date'],how='left',validate='many_to_one')
 d=p.trade_date
 allowed=(d<pd.Timestamp('2020-03-16'))|(d>=pd.Timestamp('2025-03-31'))|(d.between('2021-05-03','2023-11-05')&p.member.eq(True))
 individual=allowed&p.restricted.eq(True);eligible=allowed&~individual
 p['date']=d+pd.offsets.MonthEnd(0)
 known=pd.to_datetime(p.known_at,utc=True);cutoff=pd.to_datetime(p.cutoff,utc=True)
 earliest=(d+pd.Timedelta(days=1,hours=8,minutes=30)).dt.tz_localize('Asia/Seoul').dt.tz_convert('UTC')
 if not earliest.lt(cutoff).all():raise ValueError('Unavailable month-end trades in raw capture')
 bad=(p.availability_basis.ne('POLICY_ASSUMPTION')|~p.policy_version.isin(['kis-krx-short-scope-v2','kis-provider-trust-v1'])|
  known.isna()|known.ge(cutoff)|known.lt(earliest)|p.source_ticker.ne(p.stock_code)|p.short_market.ne('KRX')|
  p.volume_market.ne('KRX')|p.volume_adjustment.ne('UNADJUSTED')|p.short_volume.isna()|p.total_volume.isna()|
  p.short_volume.lt(0)|p.total_volume.lt(0)|p.short_volume.gt(p.total_volume))
 p['expected_days']=1;p['eligible_days']=eligible.astype(int);p['excluded_regime_days']=(~allowed).astype(int)
 p['excluded_individual_days']=individual.astype(int);p['short_days']=(eligible&p.source_exists).astype(int)
 p['bad_short']=(eligible&p.source_exists&bad).astype(int);p['bad_identity']=p.identity_matches.ne(1).astype(int)
 p['sq']=p.short_volume.where(eligible);p['sv']=p.total_volume.where(eligible);p['short_known_at']=known.where(eligible)
 g=p.groupby(['asset_id','date']);out=g[COUNTS].sum()
 out=out.join(g[['sq','sv']].sum(min_count=1)).join(g.short_known_at.max()).reset_index()
 return out

def compare(actual,target,*,fields=None):
 target=target.copy();target.date=pd.to_datetime(target.date)
 j=actual.merge(target,on=['asset_id','date'],how='outer',validate='one_to_one',suffixes=('_py','_sql'),indicator=True)
 if not j._merge.eq('both').all():raise ValueError('Daily/monthly coverage differs')
 for c in fields or COUNTS+['sq','sv']:
  np.testing.assert_allclose(pd.to_numeric(j[c+'_py']).to_numpy(dtype=float),pd.to_numeric(j[c+'_sql']).to_numpy(dtype=float),rtol=1e-12,atol=0,equal_nan=True,err_msg=c)
 a=pd.to_datetime(j.short_known_at_py,utc=True);b=pd.to_datetime(j.short_known_at_sql,utc=True)
 if not (a.eq(b)|(a.isna()&b.isna())).all():raise ValueError('Known-at differs')
 return len(j)

def capture_fixed(source,sample):
 source=Path(source);sample_path=source/'fixed-raw-sample.parquet';receipt=source/'fixed-raw-sample.json'
 ids=','.join(str(int(a)) for a in sample)
 query=RAW_SQL.replace("AND p.market IN",f"AND p.asset_id IN ({ids}) AND p.market IN").replace("WHERE k.venue='J'",f"WHERE k.asset_id IN ({ids}) AND k.venue='J'")
 if receipt.exists():
  r=load_json(receipt)
  if r['asset_ids']!=sample or r['query_sha256']!=digest(query) or r['sha256']!=sha(sample_path):raise ValueError('Fixed raw checkpoint changed')
  return pd.read_parquet(sample_path)
 with connect() as conn,conn.cursor() as cur:
  cur.execute("SET LOCAL statement_timeout='10min'");cur.execute('SELECT pg_current_snapshot()::text,transaction_timestamp()');snapshot,at=cur.fetchone()
  cur.execute(query,('2015-01-01','2026-09-30')*2)
  fixed=pd.DataFrame(cur.fetchall(),columns=[d.name for d in cur.description])
 fixed.to_parquet(sample_path,index=False)
 save_json(receipt,dict(asset_ids=sample,query_sha256=digest(query),sha256=sha(sample_path),snapshot=snapshot,captured_at=at.isoformat(),rows=len(fixed)))
 return fixed

def run(source,policy,daily):
 source=Path(source);daily=Path(daily);m=load_json(source/'manifest.json');_,members,restrictions=load_policy(policy)
 parts=[]
 for f in m['files']:
  if sha(source/f['path'])!=f['sha256']:raise ValueError('Changed monthly source')
  parts.append(pd.read_parquet(source/f['path']))
 target=pd.concat(parts,ignore_index=True);target.date=pd.to_datetime(target.date)
 dm=load_json(daily/'manifest.json');raw=[]
 for f in dm['files']:
  if sha(daily/f['path'])!=f['sha256']:raise ValueError('Changed daily checkpoint')
  raw.append(pd.read_parquet(daily/f['path']))
 raw=pd.concat(raw,ignore_index=True);actual=aggregate(raw,members,restrictions)
 full=actual.date.lt('2023-11-01');partial=target.date.between('2021-05-31','2023-10-31')
 n=compare(actual.loc[full],target.loc[partial])
 # November's remaining days were generally banned; raw capture stops November 3.
 november=target.loc[target.date.eq('2023-11-30')]
 observed_assets=set(actual.loc[~full,'asset_id'])
 later_listings=november.loc[~november.asset_id.isin(observed_assets)]
 if later_listings.eligible_days.ne(0).any() or later_listings.short_days.ne(0).any() or later_listings.sq.notna().any():raise ValueError('Post-ban entrant has measurements')
 nov=compare(actual.loc[~full],november.loc[november.asset_id.isin(observed_assets)],fields=['eligible_days','excluded_individual_days','short_days','bad_short','bad_identity','sq','sv'])
 assets=sorted(target.asset_id.unique());sample=sorted({int(assets[(len(assets)-1)*i//19]) for i in range(20)})
 # Immutable deterministic sample includes every era, not selected by returns.
 sample_path=source/'fixed-raw-sample.parquet';fixed=capture_fixed(source,sample)
 nf=compare(aggregate(fixed,members,restrictions),target.loc[target.asset_id.isin(sample)])
 result=dict(status='DAILY_POLICY_RECONSTRUCTION_PASSED',source_manifest_sha256=sha(source/'manifest.json'),
  policy_manifest_sha256=sha(Path(policy)/'manifest.json'),partial_daily_manifest_sha256=sha(daily/'manifest.json'),
  partial_raw_days=len(raw),partial_full_asset_months=n,partial_november_asset_months=nov,
  november_post_ban_only_assets_verified_empty=len(later_listings),
  fixed_asset_ids=sample,fixed_raw_days=len(fixed),fixed_asset_months=nf,fixed_raw_sha256=sha(sample_path),
  validated_fields=COUNTS+['sq','sv','short_known_at'],first_vintage_verified=False,forward_labels_read=False)
 save_json(source/'raw-audit.json',result);print(result,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--policy',required=True);p.add_argument('--daily',required=True);a=p.parse_args();run(a.source,a.policy,a.daily)
