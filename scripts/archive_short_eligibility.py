"""Private content-addressed archive of the completed short-policy evidence."""
import argparse
import gzip
import hashlib
import io
from pathlib import Path
import tarfile
from engine.research_generation import digest
from scripts.archive_reference_new_information import upload
from scripts.archive_dart_historical_evidence import _reject_secret_fields
from scripts.capture_reference_short_eligible import load_policy
from scripts.publish_reference_expansion import load_json,save_json,sha

BUCKET='soma-quant-bronze-31-159372032315-ap-northeast-2-an'

def prepare(root,output,monthly='monthly-source'):
 root=Path(root);out=Path(output);out.mkdir(parents=True,exist_ok=True)
 if monthly not in ['monthly-source','monthly-source-v3']:raise ValueError('Explicit reviewed monthly snapshot required')
 load_policy(root/'policy-source')
 for part in ['daily-short-source',monthly]:
  m=load_json(root/part/'manifest.json')
  if m['status']!='COMPLETE':raise ValueError('Source incomplete')
  for f in m['files']:
   if Path(f['path']).name!=f['path'] or sha(root/part/f['path'])!=f['sha256']:raise ValueError('Source changed')
 audit=load_json(root/monthly/'raw-audit.json')
 if audit['status']!='DAILY_POLICY_RECONSTRUCTION_PASSED' or audit['source_manifest_sha256']!=sha(root/monthly/'manifest.json'):raise ValueError('Raw audit mismatch')
 members=[]
 for folder in ['krx-membership','krx-daily-membership','policy-source','daily-short-source',monthly]:
  for p in sorted((root/folder).rglob('*')):
   if not p.is_file():continue
   if p.is_symlink() or p.suffix not in ['.json','.parquet','.csv']:raise ValueError('Unexpected source file')
   if p.suffix=='.json':_reject_secret_fields(load_json(p))
   members.append(dict(path=str(p.relative_to(root)),sha256=sha(p),bytes=p.stat().st_size))
 if sum(x['bytes'] for x in members)>1_000_000_000:raise ValueError('Archive size budget exceeded')
 inventory=dict(schema_version='short-eligibility-bronze-v1',kind='krx-short-eligibility',files=members,
  private_internal_only=True,first_vintage_verified=False,pit_status='PIT_ASSUMED',
  source_manifest_sha256=sha(root/monthly/'manifest.json'),policy_manifest_sha256=sha(root/'policy-source/manifest.json'))
 bundle=digest(inventory);save_json(out/'inventory.json',inventory);path=out/'raw.tar.gz'
 if not path.exists():
  with path.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as compressed,tarfile.open(fileobj=compressed,mode='w|') as tar:
   for item in members:
    body=(root/item['path']).read_bytes()
    if hashlib.sha256(body).hexdigest()!=item['sha256']:raise ValueError('Source changed during archive')
    info=tarfile.TarInfo(item['path']);info.size=len(body);info.mtime=0;info.mode=0o444;tar.addfile(info,io.BytesIO(body))
 with tarfile.open(path,'r:gz') as tar:
  if set(tar.getnames())!={x['path'] for x in members}:raise ValueError('Archive scope mismatch')
  for item in members:
   body=tar.extractfile(item['path']).read()
   if len(body)!=item['bytes'] or hashlib.sha256(body).hexdigest()!=item['sha256']:raise ValueError('Archive bytes mismatch')
 prefix=f'reference_sources/new_information/krx-short-eligibility/bundle={bundle}'
 manifest=dict(**inventory,bundle_id=bundle,bucket=BUCKET,key=prefix+'/raw.tar.gz',archive_sha256=sha(path),archive_bytes=path.stat().st_size)
 save_json(out/'manifest.json',manifest);return manifest

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--output',required=True);p.add_argument('--monthly-source',default='monthly-source');p.add_argument('--apply',action='store_true');a=p.parse_args()
 manifest=prepare(a.root,a.output,a.monthly_source)
 if a.apply:upload(a.output,manifest)
