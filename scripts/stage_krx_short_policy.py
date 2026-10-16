"""Validate official daily membership and official temporary restriction periods."""
import argparse
import json
from pathlib import Path
import shutil

import pandas as pd

from scripts.stage_krx_membership_dom import identity,validate
from scripts.publish_reference_expansion import save_json,sha
from engine.research_generation import digest

REQUIRED_PERIODS={('20170101','20171231'),('20180101','20181231'),('20190101','20191231'),
 ('20200101','20201231'),('20210101','20211231'),('20220101','20221231'),
 ('20230101','20231103'),('20250101','20251231'),('20260101','20260930')}

def expand_restrictions(restrictions):
    """Inclusive actual restriction dates; do not truncate at detection year."""
    days=set()
    for r in restrictions.itertuples(index=False):
        if pd.Timestamp(r.end_date)<pd.Timestamp(r.start_date):raise ValueError('Invalid restriction interval')
        for day in pd.date_range(r.start_date,r.end_date):days.add((r.stock_code,day.date().isoformat()))
    return pd.DataFrame(sorted(days),columns=['stock_code','trade_date'])


def stage(membership,calendar,overheat,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise ValueError('Fresh policy source directory required')
    membership=Path(membership);calendar=Path(calendar)
    cm=json.loads((calendar/'manifest.json').read_text())
    # Independently observed trading days, not an assumed business-day calendar.
    dates=[]
    for item in cm['files']:
        path=calendar/item['path']
        if sha(path)!=item['sha256']:raise ValueError('Calendar source changed')
        dates.extend(pd.read_parquet(path,columns=['trade_date']).trade_date.astype(str).unique())
    expected={d for d in dates if '2021-05-03'<=d<='2023-11-03'}
    rows=[];evidence=[]
    for index,market in [('KOSPI200','KOSPI'),('KOSDAQ150','KOSDAQ')]:
        seen=set()
        for path in sorted((membership/'observations'/index).glob('*.json')):
            receipt=json.loads(path.read_text());day=receipt['date']
            if receipt['index']!=index or day in seen:raise ValueError('Duplicate/mixed index receipt')
            members=json.loads((membership/'sets'/(receipt['members_sha256']+'.json')).read_text())
            validate(members)
            if identity(members)!=receipt['members_sha256'] or len(members)!=receipt['rows']:
                raise ValueError('Member set integrity mismatch')
            seen.add(day);evidence.append(dict(path=str(path.resolve()),sha256=sha(path)))
            rows.extend((market,day,code,name) for code,name in members)
        if seen!=expected:raise ValueError(f'Membership calendar incomplete for {index}: {expected-seen}')
    members=pd.DataFrame(rows,columns=['market','trade_date','stock_code','company_name'])
    if members.duplicated(['market','trade_date','stock_code']).any():raise ValueError('Duplicate member')
    members.to_parquet(output/'members.parquet',index=False)
    periods=set();raw_files=[];frames=[]
    for start,end,source in overheat:
        if (start,end) in periods:raise ValueError('Duplicate overheat period')
        periods.add((start,end));source=Path(source)
        raw=pd.read_csv(source,encoding='cp949',dtype=str)
        mapping={'적출일':'detected_date','공매도 거래제한일_시작일':'start_date',
                 '공매도 거래제한일_종료일':'end_date','종목코드':'stock_code','종목명':'company_name','시장구분':'market'}
        f=raw[list(mapping)].rename(columns=mapping)
        if not f.stock_code.str.fullmatch('[0-9A-Z]{6}').all():raise ValueError('Invalid short restriction ticker')
        for c in ['detected_date','start_date','end_date']:f[c]=pd.to_datetime(f[c],format='%Y/%m/%d')
        if not f.detected_date.between(pd.Timestamp(start),pd.Timestamp(end)).all():raise ValueError('Query range mismatch')
        if (f.start_date<=f.detected_date).any() or (f.end_date<f.start_date).any():raise ValueError('Invalid restriction interval')
        target=output/f'overheat-{start}-{end}.csv';shutil.copyfile(source,target)
        raw_files.append(dict(path=target.name,sha256=sha(target),start=start,end=end,rows=len(f),screen='34001'))
        frames.append(f)
    if periods!=REQUIRED_PERIODS:raise ValueError('Incomplete overheat source periods')
    restrictions=pd.concat(frames,ignore_index=True)
    restrictions.to_parquet(output/'restriction-events.parquet',index=False)
    restriction_days=expand_restrictions(restrictions)
    restriction_days.to_parquet(output/'restriction-days.parquet',index=False)
    manifest=dict(status='COMPLETE',membership_dates_per_index=len(expected),membership_rows=len(members),
                  members_sha256=sha(output/'members.parquet'),membership_receipts=evidence,
                  calendar_manifest_sha256=sha(calendar/'manifest.json'),
                  restriction_events=len(restrictions),restriction_days=len(restriction_days),
                  restriction_days_sha256=sha(output/'restriction-days.parquet'),raw_exports=raw_files,
                  first_vintage_verified=False,pit_status='PIT_ASSUMED',
                  not_a_borrow_or_execution_availability_certificate=True,
                  pre_2017_rule='OVERHEAT_DESIGNATION_INTRODUCED_2017_03_27',
                  omitted_2024_rule='ENTIRE_YEAR_GENERAL_SHORT_SALE_BAN',
                  sources=['https://data.krx.co.kr/contents/MDC/STAT/srt/MDCSTAT317.jsp',
                           'https://www.fsc.go.kr/po010106/75290',
                           'https://www.fsc.go.kr/no010101/72792',
                           'https://www.fsc.go.kr/po010101/84216'])
    manifest['manifest_sha256']=digest(manifest);save_json(output/'manifest.json',manifest)
    return {k:v for k,v in manifest.items() if k not in ['membership_receipts','raw_exports']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--membership',required=True);p.add_argument('--calendar',required=True)
    p.add_argument('--overheat-export',nargs=3,action='append',required=True,metavar=('START','END','PATH'))
    p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(stage(a.membership,a.calendar,a.overheat_export,a.output),ensure_ascii=False))
