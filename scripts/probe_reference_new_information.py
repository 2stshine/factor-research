"""Bounded real provider probes; no credentials/credential URLs in evidence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime,timezone
from urllib.request import urlopen,Request
from urllib.parse import urlencode
from urllib.error import URLError,HTTPError
from engine.silver import _load_environment
from scripts.publish_reference_expansion import save_json,sha

def credentials(*,required=('DART_API_KEY','FMP_API_KEY')):
 _load_environment()
 result={k:os.environ.get(k) for k in ('DART_API_KEY','FMP_API_KEY')}
 if 'DART_API_KEY' in required and not result['DART_API_KEY']:
  r=subprocess.run(['aws','secretsmanager','get-secret-value','--secret-id','teamalpha/data-pipeline/env','--profile','teamalpha','--region','ap-northeast-2','--output','json'],capture_output=True,text=True,timeout=30)
  if r.returncode:raise RuntimeError('Authorized provider secret unavailable')
  secret=json.loads(json.loads(r.stdout)['SecretString'])
  result['DART_API_KEY']=secret.get('DART_API_KEY')
 return result

def run(output):
 out=Path(output);out.mkdir(parents=True,exist_ok=True);keys=credentials();receipts=[]
 jobs=[]
 for corp in ('00126380','00164779','00164742'):
  for year in (2015,2020,2025):
   jobs.append(('dart_employee',f'{corp}-{year}','https://opendart.fss.or.kr/api/empSttus.json',dict(corp_code=corp,bsns_year=str(year),reprt_code='11011'), 'crtfc_key',keys['DART_API_KEY']))
 for symbol in ('005930.KS','000660.KS','005380.KS','035420.KS','247540.KQ','AAPL'):
  jobs.append(('fmp_estimate',symbol,'https://financialmodelingprep.com/stable/analyst-estimates',dict(symbol=symbol,period='annual',page=0,limit=1000),'apikey',keys['FMP_API_KEY']))
 for kind,label,url,params,keyname,key in jobs:
  filename=f'{kind}-{label}.json';path=out/filename
  if path.exists():payload=json.loads(path.read_text());status='CACHED'
  else:
   if not key:raise RuntimeError('Missing authorized provider credential')
   try:
    try:
     r=urlopen(Request(url+'?'+urlencode({**params,keyname:key}),headers={'User-Agent':'TeamAlpha-Reference-Audit/1'}),timeout=35)
    except HTTPError as error:r=error
    with r:status=r.code;payload=json.loads(r.read(10_000_000))
   except (URLError,TimeoutError,ValueError):
    print({'probe':filename,'status':'NETWORK_OR_FORMAT_ERROR'},flush=True);continue
   # Never persist reflected secrets in a provider error.
   encoded=json.dumps(payload,ensure_ascii=False)
   if key in encoded:raise RuntimeError('Provider response contains credential')
   save_json(path,payload);time.sleep(.3)
  rows=payload if isinstance(payload,list) else payload.get('list',[])
  receipt=dict(kind=kind,public_endpoint=url,parameters=params,http_status=status,path=filename,sha256=sha(path),
   rows=len(rows),response_code=payload.get('status') if isinstance(payload,dict) else None,
   fields=sorted(rows[0]) if rows else [],observed_at=datetime.now(timezone.utc).isoformat(),
   interpretation='PROBE_ONLY_NOT_GOLD_OR_PIT_APPROVAL')
  receipts.append(receipt);print(receipt,flush=True)
 save_json(out/'probe-receipts.json',receipts)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();run(a.output)
