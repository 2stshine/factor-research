"""Freeze FMP annual statements for R&D, not historical consensus snapshots.

KRX historical monthly identities are cross-checked with both FMP symbol lists.
Provider filing timestamps are retained as raw data but NEVER used as PIT proof.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import json
from pathlib import Path
import threading
import time
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError
import pandas as pd
from scripts.capture_dart_employee_history import Limiter,QuotaError
from scripts.probe_reference_new_information import credentials
from scripts.publish_reference_expansion import load_json,save_json,sha

ROOT='https://financialmodelingprep.com/stable/'

def fetch(endpoint,params,key,limiter,stop):
 for attempt in range(5):
  if stop.is_set():return None
  limiter.wait()
  try:
   try:r=urlopen(Request(ROOT+endpoint+'?'+urlencode({**params,'apikey':key}),headers={'User-Agent':'TeamAlpha-Research/1'}),timeout=40)
   except HTTPError as error:r=error
   with r:status=r.code;raw=r.read(30_000_001)
   if len(raw)>30_000_000:raise ValueError('Oversized response')
   if status==429 or status>=500:time.sleep(min(30,2**attempt));continue
   if status in (401,402,403):stop.set();raise QuotaError('FMP access unavailable')
   if status!=200:raise ValueError('FMP HTTP failure')
   payload=json.loads(raw)
   if key in json.dumps(payload):raise ValueError('Reflected secret')
   if not isinstance(payload,list):raise ValueError('FMP non-list error response')
   return dict(endpoint=ROOT+endpoint,parameters=params,http_status=status,
    observed_at=datetime.now(timezone.utc).isoformat(),pit_status='LATEST_OBSERVED_NOT_FIRST_VINTAGE',payload=payload)
  except (URLError,TimeoutError):time.sleep(min(30,2**attempt))
 raise RuntimeError('FMP retry exhausted')

def run(identity,output):
 identity=Path(identity);out=Path(output);out.mkdir(parents=True,exist_ok=True)
 key=credentials(required=('FMP_API_KEY',))['FMP_API_KEY']
 if not key:raise RuntimeError('FMP_API_KEY environment variable unavailable')
 limiter=Limiter(3);stop=threading.Event()
 universes={}
 for endpoint in ('stock-list','financial-statement-symbol-list'):
  path=out/(endpoint+'.json')
  if not path.exists():save_json(path,fetch(endpoint,{},key,limiter,stop))
  universes[endpoint]={r['symbol'] for r in load_json(path)['payload'] if isinstance(r,dict) and isinstance(r.get('symbol'),str)}
 p=pd.read_parquet(identity,columns=['asset_id','stock_code','market']).drop_duplicates()
 p['symbol']=p.stock_code+p.market.map({'KOSPI':'.KS','KOSDAQ':'.KQ'})
 eligible=universes['stock-list']&universes['financial-statement-symbol-list']
 jobs=sorted(set(p.symbol)&eligible)
 save_json(out/'plan.json',dict(identity_sha256=sha(identity),symbol_list_sha256={k:sha(out/(k+'.json')) for k in universes},
  symbols=jobs,missing_symbols=sorted(set(p.symbol)-eligible),
  identities=p.astype({'asset_id':str}).to_dict('records'),scope='EXISTING_CERTIFIED_MONTHLY_KRX_COMMON_STOCK_UNIVERSE',
  endpoint='income-statement',period='annual',limit=100,first_vintage_verified=False))
 pending=[]
 for s in jobs:
  path=out/(s+'.json')
  if not path.exists():pending.append(s);continue
  cached=load_json(path)
  if cached.get('endpoint')!=ROOT+'income-statement' or cached.get('parameters')!=dict(symbol=s,period='annual',limit=100) or cached.get('http_status')!=200 or not isinstance(cached.get('payload'),list):
   raise ValueError('Invalid immutable FMP checkpoint')
 done=len(jobs)-len(pending);errors=[]
 print(dict(total=len(jobs),cached=done,excluded_symbols=len(set(p.symbol)-eligible)),flush=True)
 with ThreadPoolExecutor(max_workers=4) as pool:
  iterator=iter(pending);active={}
  def submit():
   s=next(iterator,None)
   if s is not None:active[pool.submit(fetch,'income-statement',dict(symbol=s,period='annual',limit=100),key,limiter,stop)]=s
  for _ in range(4):submit()
  while active:
   future=next(as_completed(active));s=active.pop(future)
   try:
    value=future.result()
    if value is not None:save_json(out/(s+'.json'),value);done+=1
   except Exception as error:
    errors.append(dict(symbol=s,error_type=type(error).__name__,safe_reason=str(error) if isinstance(error,QuotaError) else 'Fixed collector diagnostic'));stop.set()
   if done%100==0:print(dict(completed=done,total=len(jobs)),flush=True)
   if not stop.is_set():submit()
 files=[out/(s+'.json') for s in jobs if (out/(s+'.json')).exists()]
 receipt=dict(status='COMPLETE' if len(files)==len(jobs) and not errors else 'INCOMPLETE',
  jobs=len(jobs),completed=len(files),errors=errors,plan_sha256=sha(out/'plan.json'),
  files=[dict(path=p.name,sha256=sha(p)) for p in files],recorded_at=datetime.now(timezone.utc).isoformat())
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f');save_json(out/f'receipt-{stamp}.json',receipt)
 if receipt['status']=='COMPLETE':save_json(out/'manifest.json',receipt)
 print({k:v for k,v in receipt.items() if k!='files'},flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--identity',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.identity,a.output)
