"""Cross-check full rendered member sets against separately downloaded KRX CSV."""
import argparse
from pathlib import Path
import pandas as pd
from scripts.stage_krx_membership_dom import identity,validate
from scripts.publish_reference_expansion import load_json,save_json,sha

def run(root):
 root=Path(root);checks=[]
 for path in sorted((root/'krx-membership').glob('*/*/raw.csv')):
  index=path.parent.parent.name;day=path.parent.name
  observation=root/'krx-daily-membership/observations'/index/(day+'.json')
  if not observation.exists():raise ValueError('CSV without observed DOM date')
  f=pd.read_csv(path,encoding='cp949',dtype=str);members=f[['종목코드','종목명']].values.tolist();validate(members)
  receipt=load_json(observation)
  if identity(members)!=receipt['members_sha256']:raise ValueError('Full CSV/DOM membership mismatch')
  checks.append(dict(index=index,date=receipt['date'],rows=len(members),raw_path=str(path.resolve()),raw_sha256=sha(path),observation_sha256=sha(observation)))
 if {x['index'] for x in checks}!={'KOSPI200','KOSDAQ150'}:raise ValueError('Both index cross-checks required')
 result=dict(status='ALL_STAGED_FULL_CSV_DOM_MEMBERSHIP_MATCHED',checks=checks,checked_dates=len(checks),
  checked_member_rows=sum(x['rows'] for x in checks),first_vintage_verified=False)
 save_json(root/'krx-daily-membership/csv-crosscheck.json',result);print({k:v for k,v in result.items() if k!='checks'})

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);run(p.parse_args().root)
