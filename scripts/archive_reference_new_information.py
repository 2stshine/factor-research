"""Private immutable Bronze archive of explicitly enumerated source snapshots."""
import argparse
import base64
import gzip
import io
import json
from pathlib import Path
import subprocess
import tarfile
from scripts.archive_dart_historical_evidence import file_digest,_reject_secret_fields
from scripts.publish_reference_expansion import load_json,save_json,sha
from engine.research_generation import digest

def cli(args):
 r=subprocess.run(['aws',*args,'--profile','teamalpha','--region','ap-northeast-2','--output','json'],capture_output=True,text=True,timeout=120)
 return r

def prepare(source,output,kind,bucket,*,checkpoint_receipt=None):
 source,out=Path(source),Path(output);out.mkdir(parents=True,exist_ok=True)
 manifest_name='manifest.json'
 if checkpoint_receipt is not None:
  if kind!='dart-employee-checkpoint' or Path(checkpoint_receipt).name!=checkpoint_receipt or not checkpoint_receipt.startswith('receipt-'):raise ValueError('Explicit employee checkpoint receipt required')
  manifest_name=checkpoint_receipt
 m=load_json(source/manifest_name)
 if checkpoint_receipt is None:
  if m['status']!='COMPLETE':raise ValueError('Complete frozen source manifest required')
 else:
  if m['status']!='INCOMPLETE' or not 0<m['completed']<m['jobs'] or len(m['files'])!=m['completed']:raise ValueError('Incomplete checkpoint scope required')
 paths={manifest_name}
 if (source/'raw-audit.json').exists():
  audit=load_json(source/'raw-audit.json')
  if audit.get('source_manifest_sha256')!=sha(source/'manifest.json') or audit.get('status')!='FIXED_RAW_DAILY_RECONSTRUCTION_PASSED':raise ValueError('Invalid raw audit binding')
  paths.add('raw-audit.json')
 if 'files' in m:
  for f in m['files']:
   name=f['path']
   if Path(name).name!=name or sha(source/name)!=f['sha256']:raise ValueError('Changed or unsafe source member')
   paths.add(name)
 elif 'path' in m:
  if Path(m['path']).name!=m['path'] or sha(source/m['path'])!=m['sha256']:raise ValueError('Changed source member')
  paths.add(m['path'])
 else:raise ValueError('Unsupported source manifest')
 if (source/'plan.json').exists():
  if m.get('plan_sha256')!=sha(source/'plan.json'):raise ValueError('Source plan changed')
  paths.add('plan.json')
  plan=load_json(source/'plan.json')
  for endpoint,h in plan.get('symbol_list_sha256',{}).items():
   if endpoint not in ('stock-list','financial-statement-symbol-list') or sha(source/(endpoint+'.json'))!=h:raise ValueError('Changed FMP symbol list')
   paths.add(endpoint+'.json')
 members=[]
 for name in sorted(paths):
  p=source/name
  if p.suffix=='.json':_reject_secret_fields(load_json(p))
  h,size=file_digest(p);members.append(dict(path=name,sha256=h,bytes=size))
 if sum(m['bytes'] for m in members)>1_000_000_000:raise ValueError('Archive byte budget exceeded')
 inventory=dict(schema_version='reference-new-information-bronze-v1',kind=kind,files=members,private_internal_only=True,
  source_manifest_sha256=sha(source/manifest_name),first_vintage_verified=False,pit_status='PIT_ASSUMED')
 if checkpoint_receipt is not None:
  inventory.update(source_status='INCOMPLETE',gold_eligible=False,requested_jobs=m['jobs'],completed_jobs=m['completed'],
   purpose='Recoverable raw checkpoint only; not a complete acquisition or Gold source')
 bundle=digest(inventory);save_json(out/'inventory.json',inventory)
 path=out/'raw.tar.gz'
 if not path.exists():
  with path.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as compressed,tarfile.open(fileobj=compressed,mode='w|') as tar:
   for item in members:
    p=source/item['path'];body=p.read_bytes()
    if sha(p)!=item['sha256']:raise ValueError('Source changed while archiving')
    info=tarfile.TarInfo(item['path']);info.size=len(body);info.mtime=0;info.mode=0o444
    tar.addfile(info,io.BytesIO(body))
   body=(out/'inventory.json').read_bytes();info=tarfile.TarInfo('archive-inventory.json');info.size=len(body);info.mtime=0;info.mode=0o444;tar.addfile(info,io.BytesIO(body))
 # Validate the existing/generated archive; no filesystem extraction.
 with tarfile.open(path,'r:gz') as tar:
  expected={r['path']:r for r in members}
  if set(tar.getnames())!=set(expected)|{'archive-inventory.json'}:raise ValueError('Archive member mismatch')
  import hashlib
  for name,item in expected.items():
   raw=tar.extractfile(name).read()
   if hashlib.sha256(raw).hexdigest()!=item['sha256'] or len(raw)!=item['bytes']:raise ValueError('Archive content mismatch')
 prefix=f'reference_sources/new_information/{kind}/bundle={bundle}'
 manifest=dict(**inventory,bundle_id=bundle,bucket=bucket,key=prefix+'/raw.tar.gz',archive_sha256=sha(path),archive_bytes=path.stat().st_size)
 save_json(out/'manifest.json',manifest);return manifest

def upload(output,manifest):
 out=Path(output);results=[]
 protection=cli(['s3api','get-public-access-block','--bucket',manifest['bucket']])
 if protection.returncode or not all(json.loads(protection.stdout).get('PublicAccessBlockConfiguration',{}).get(k) is True for k in
  ('BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets')):raise RuntimeError('Private Bronze public-access protection not verified')
 for filename,key in [('raw.tar.gz',manifest['key']),('manifest.json',manifest['key'].rsplit('/',1)[0]+'/manifest.json')]:
  path=out/filename;h=sha(path);size=path.stat().st_size;checksum=base64.b64encode(bytes.fromhex(h)).decode()
  def head():return cli(['s3api','head-object','--bucket',manifest['bucket'],'--key',key,'--checksum-mode','ENABLED'])
  r=head()
  if r.returncode:
   if not any(t in r.stderr for t in ('(404)','Not Found','NotFound')):raise RuntimeError('Private Bronze head check failed')
   r=cli(['s3api','put-object','--bucket',manifest['bucket'],'--key',key,'--body',str(path),
    '--if-none-match','*','--checksum-algorithm','SHA256','--checksum-sha256',checksum,'--metadata','sha256='+h])
   if r.returncode:raise RuntimeError('Conditional private Bronze upload failed')
   r=head()
  if r.returncode:raise RuntimeError('Bronze readback unavailable')
  metadata=json.loads(r.stdout)
  if metadata.get('ContentLength')!=size or metadata.get('ChecksumSHA256')!=checksum or metadata.get('Metadata',{}).get('sha256')!=h:raise ValueError('Bronze checksum/size mismatch')
  results.append(dict(uri='s3://'+manifest['bucket']+'/'+key,sha256=h,bytes=size,checksum_verified=True))
 receipt=dict(status='PRIVATE_BRONZE_ARCHIVE_VERIFIED',objects=results,bundle_id=manifest['bundle_id'],first_vintage_verified=False)
 save_json(out/'upload-receipt.json',receipt);print(receipt,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for arg in ('source','output','kind','bucket'):p.add_argument('--'+arg,required=True)
 p.add_argument('--apply',action='store_true');p.add_argument('--checkpoint-receipt');a=p.parse_args()
 if a.kind not in ('kis-flows','dart-filing-anchors','fmp-rd-income','dart-employees','dart-employee-checkpoint'):raise ValueError('Unsupported source namespace')
 if (a.kind=='dart-employee-checkpoint')!=(a.checkpoint_receipt is not None):raise ValueError('Checkpoint requires separate explicit namespace and receipt')
 if a.bucket!='soma-quant-bronze-31-159372032315-ap-northeast-2-an':raise ValueError('Unexpected reviewed Bronze destination')
 manifest=prepare(a.source,a.output,a.kind,a.bucket,checkpoint_receipt=a.checkpoint_receipt)
 if a.apply:upload(a.output,manifest)
