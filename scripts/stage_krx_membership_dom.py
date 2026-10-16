"""Archive losslessly compressed, individually observed KRX daily UI snapshots.

An unchanged set is stored once, but each observation date MUST have been queried.
No effective interval, weekend fill, or forward fill is inferred. The initial
sets are independently verified against complete official CSV downloads.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

import pandas as pd


def encoded(members):
    return json.dumps(sorted(members), ensure_ascii=False, separators=(',', ':')).encode()


def identity(members):
    return hashlib.sha256(encoded(members)).hexdigest()


def validate(members):
    if not 100 <= len(members) <= 220:
        raise ValueError('Incomplete or unexpected index size')
    if not all(isinstance(x,(list,tuple)) and len(x)==2 and isinstance(x[0],str) for x in members):
        raise ValueError('Invalid member row')
    codes=[x[0] for x in members]
    if len(codes)!=len(set(codes)) or not all(re.fullmatch('[0-9A-Z]{6}',x) for x in codes):
        raise ValueError('Invalid/duplicate code')
    if not all(len(x)==2 and isinstance(x[1],str) and x[1] for x in members):
        raise ValueError('Invalid company name')


def save_set(output, members):
    validate(members)
    key=identity(members)
    target=output/'sets'/f'{key}.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    payload=encoded(members)
    if target.exists() and target.read_bytes()!=payload:
        raise ValueError('Immutable set differs')
    if not target.exists():target.write_bytes(payload)
    return key


def seed(output, csv_root):
    output=Path(output)
    result={}
    for index in ['KOSPI200','KOSDAQ150']:
        f=pd.read_csv(Path(csv_root)/index/'20210503'/'raw.csv',encoding='cp949',dtype=str)
        members=f[['종목코드','종목명']].values.tolist()
        result[index]=save_set(output,members)
    return result


def stage_batch(output, batch):
    output=Path(output)
    if batch.get('source')!='KRX_UI_11006_ALL_SCROLL_ROWS':raise ValueError('Wrong source')
    # Stage every delta before any date references; parent SHA pins complete names/codes.
    for change in batch['sets']:
        if not re.fullmatch('[a-f0-9]{64}',str(change.get('parent',''))) or not re.fullmatch('[a-f0-9]{64}',str(change.get('sha256',''))):
            raise ValueError('Invalid member set hash')
        parent=output/'sets'/f"{change['parent']}.json"
        members=json.loads(parent.read_text())
        if identity(members)!=change['parent']:raise ValueError('Corrupt parent')
        values=dict(members)
        for code in change['removed']:
            if code not in values:raise ValueError('Unknown removal')
            del values[code]
        for code,name in change['added']:
            if code in values:raise ValueError('Duplicate addition')
            values[code]=name
        for code,name in change['renamed']:
            if code not in values:raise ValueError('Unknown rename')
            values[code]=name
        members=sorted([list(x) for x in values.items()])
        if identity(members)!=change['sha256']:raise ValueError('Delta integrity failure')
        save_set(output,members)
    rows=0
    dates=0
    for observation in batch['observations']:
        index=observation['index']; key=observation['sha256']
        if index not in ('KOSPI200','KOSDAQ150'):raise ValueError('Unsupported index')
        if not re.fullmatch('[a-f0-9]{64}',str(key)):raise ValueError('Invalid member set hash')
        members=json.loads((output/'sets'/f'{key}.json').read_text())
        if identity(members)!=key:raise ValueError('Corrupt member set')
        validate(members)
        for day in observation['dates']:
            parsed=datetime.strptime(day,'%Y%m%d').date()
            if not '20210503'<=day<='20231103':raise ValueError('Outside authorized partial-resumption interval')
            target=output/'observations'/index/f'{day}.json'
            target.parent.mkdir(parents=True,exist_ok=True)
            receipt=dict(index=index,date=parsed.isoformat(),members_sha256=key,rows=len(members),
                         source=batch['source'],source_url='https://data.krx.co.kr',screen='11006',
                         completeness='UNION_OF_TOP_MIDDLE_BOTTOM_EQUALS_RENDERED_TOTAL_ROW_COUNT',
                         first_vintage_verified=False,scope='INDEX_MEMBERSHIP_NOT_INDIVIDUAL_SHORT_PERMISSION',
                         observed_between=[batch['started_at'],batch['completed_at']],
                         captured_at=datetime.now(timezone.utc).isoformat())
            if target.exists():
                previous=json.loads(target.read_text())
                if previous['members_sha256']!=key:raise ValueError('Immutable date differs')
            else:target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
            rows+=len(members);dates+=1
    raw=json.dumps(batch,ensure_ascii=False,sort_keys=True,indent=2).encode()
    archive=output/'batches'/f'{hashlib.sha256(raw).hexdigest()}.json'
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():archive.write_bytes(raw)
    return dict(observations=dates,member_days=rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True);p.add_argument('--seed-csv-root')
    a=p.parse_args()
    if a.seed_csv_root:print(json.dumps(seed(a.output,a.seed_csv_root)))
    else:print(json.dumps(stage_batch(a.output,json.load(sys.stdin))))
