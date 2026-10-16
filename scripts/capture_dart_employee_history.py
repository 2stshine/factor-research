"""Checkpoint official employee responses; bounded concurrency, no quota bypass.

Each immutable envelope preserves sanitized request, actual retrieval time and
raw response. These are current backfills, not first-vintage certification.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import json
from pathlib import Path
import threading
import time
from urllib.request import urlopen,Request
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError
from scripts.probe_reference_new_information import credentials
from scripts.publish_reference_expansion import load_json,save_json,sha

ENDPOINT='https://opendart.fss.or.kr/api/empSttus.json'

class QuotaError(RuntimeError):pass

class Limiter:
 def __init__(self,rate):self.lock=threading.Lock();self.next=0.;self.interval=1./rate
 def wait(self):
  with self.lock:
   wait=max(0.,self.next-time.monotonic());self.next=max(time.monotonic(),self.next)+self.interval
  if wait:time.sleep(wait)

def fetch(job,key,limiter,stop):
 params=dict(corp_code=job['corp_code'],bsns_year=str(job['fiscal_year']),reprt_code='11011')
 for attempt in range(5):
  if stop.is_set():return None
  limiter.wait()
  try:
   try:r=urlopen(Request(ENDPOINT+'?'+urlencode({**params,'crtfc_key':key}),headers={'User-Agent':'TeamAlpha-Research/1'}),timeout=35)
   except HTTPError as error:r=error
   with r:status=r.code;raw=r.read(4_000_001)
   if len(raw)>4_000_000:raise ValueError('Oversized provider response')
   if status==429 or status>=500:
    time.sleep(min(30,2**attempt));continue
   if status in (401,403):stop.set();raise QuotaError('Provider authorization unavailable')
   if status!=200:raise ValueError('Unexpected provider HTTP status')
   payload=json.loads(raw)
   if key in json.dumps(payload):raise ValueError('Reflected secret rejected')
   code=payload.get('status')
   if code in ('020','010','011','012','800','900','901'):
    stop.set();raise QuotaError('Provider access/quota stop: '+str(code))
   if code not in ('000','013'):raise ValueError('Unexpected DART response: '+str(code))
   return dict(endpoint=ENDPOINT,parameters=params,http_status=status,
    observed_at=datetime.now(timezone.utc).isoformat(),pit_status='PIT_ASSUMED_LATEST_BACKFILL',payload=payload)
  except (URLError,TimeoutError):
   time.sleep(min(30,2**attempt))
 raise RuntimeError('Provider retry budget exhausted')

def run(plan,output,workers=4,rate=4):
 plan=Path(plan);out=Path(output);out.mkdir(parents=True,exist_ok=True)
 manifest=load_json(plan);jobs=manifest['jobs'];key=credentials()['DART_API_KEY']
 if not key:raise RuntimeError('DART_API_KEY unavailable')
 save_json(out/'plan.json',dict(source_manifest_sha256=sha(plan),jobs=jobs,endpoint=ENDPOINT,workers=workers,requests_per_second=rate))
 pending=[];cached=0
 for job in jobs:
  path=out/f"{job['corp_code']}-{job['fiscal_year']}.json"
  if path.exists():
   old=load_json(path)
   if old.get('endpoint')!=ENDPOINT or old.get('http_status')!=200 or old['parameters']!=dict(corp_code=job['corp_code'],bsns_year=str(job['fiscal_year']),reprt_code='11011') or old['payload'].get('status') not in ('000','013'):raise ValueError('Invalid checkpoint')
   cached+=1
  else:pending.append((job,path))
 print(dict(total=len(jobs),cached=cached,pending=len(pending)),flush=True)
 stop=threading.Event();limiter=Limiter(rate);errors=[];done=cached;nonnull=0
 # Bounded submitted queue, so a provider stop does not leave thousands queued.
 with ThreadPoolExecutor(max_workers=workers) as pool:
  iterator=iter(pending);active={}
  def submit():
   item=next(iterator,None)
   if item is not None:active[pool.submit(fetch,item[0],key,limiter,stop)]=item
  for _ in range(workers):submit()
  while active:
   future=next(as_completed(active));job,path=active.pop(future)
   try:
    value=future.result()
    if value is not None:
     save_json(path,value);done+=1;nonnull+=value['payload']['status']=='000'
   except Exception as error:
    # Never include urllib exception strings; they can contain credential URLs.
    errors.append(dict(job=job,error_type=type(error).__name__,
     safe_reason=str(error) if isinstance(error,QuotaError) else 'Fixed collector diagnostic; credential-bearing exception text omitted'));stop.set()
   if done%100==0:print(dict(completed=done,total=len(jobs),new_nonempty=nonnull),flush=True)
   if not stop.is_set():submit()
 files=sorted(out.glob('[0-9]*-[0-9]*.json'))
 receipt=dict(status='COMPLETE' if len(files)==len(jobs) and not errors else 'INCOMPLETE',
  jobs=len(jobs),completed=len(files),errors=errors,plan_sha256=sha(out/'plan.json'),
  files=[dict(path=p.name,sha256=sha(p)) for p in files],recorded_at=datetime.now(timezone.utc).isoformat())
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
 save_json(out/f'receipt-{stamp}.json',receipt)
 if receipt['status']=='COMPLETE':save_json(out/'manifest.json',receipt)
 print({k:v for k,v in receipt.items() if k!='files'},flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',required=True);p.add_argument('--output',required=True)
 p.add_argument('--workers',type=int,default=4);p.add_argument('--rate',type=float,default=4)
 a=p.parse_args()
 if not 1<=a.workers<=4 or not 0<a.rate<=4:raise ValueError('Collector concurrency/rate bound')
 run(a.plan,a.output,a.workers,a.rate)
