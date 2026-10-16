"""Checkpoint authorized KRX UI exports without treating a date as an interval.

The caller binds the observed UI index/date to each download. CSV itself does
not contain those filters. No cookies, credentials, or price outcomes are read.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pandas as pd


def stage(source, output, index, date, expected_code=None, expected_close=None):
    if index not in ('KOSPI200', 'KOSDAQ150'):
        raise ValueError('Unsupported index')
    day = datetime.strptime(date, '%Y%m%d').date()
    source, output = Path(source), Path(output)
    raw = source.read_bytes()
    frame = pd.read_csv(source, encoding='cp949', dtype=str)
    required = ['종목코드', '종목명', '종가', '대비', '등락률', '상장시가총액']
    if list(frame.columns) != required or frame.empty:
        raise ValueError('Empty or unexpected KRX export')
    codes = frame['종목코드']
    if expected_code is not None:
        if codes.iloc[0] != expected_code or float(frame['종가'].iloc[0]) != float(expected_close):
            raise ValueError('Downloaded data differs from observed query result')
    if not codes.str.fullmatch(r'[0-9A-Z]{6}').all() or codes.duplicated().any():
        raise ValueError('Invalid/duplicate security code')
    # Corporate actions can temporarily make KOSPI200 contain >200 issues.
    if not (100 <= len(frame) <= 220):
        raise ValueError('Unexpected membership count: review source')
    target = output / index / date
    target.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()
    receipt = dict(index=index, date=day.isoformat(), rows=len(frame),
                   raw_sha256=digest, source='KRX_AUTHENTICATED_UI_CSV_11006',
                   filters_binding='HOST_OBSERVED_UI_INDEX_AND_QUERY_DATE',
                   status='SINGLE_DATE_SNAPSHOT_NOT_AN_EFFECTIVE_INTERVAL',
                   first_vintage_verified=False,
                   captured_at=datetime.now(timezone.utc).isoformat())
    if (target/'receipt.json').exists():
        previous=json.loads((target/'receipt.json').read_text())
        if previous['raw_sha256'] != digest:
            raise ValueError('Immutable checkpoint differs; retain both vintages separately')
        if hashlib.sha256((target/'raw.csv').read_bytes()).hexdigest() != digest:
            raise ValueError('Existing raw checkpoint is corrupt')
        return previous
    shutil.copyfile(source, target/'raw.csv')
    frame[['종목코드','종목명']].rename(columns={'종목코드':'stock_code','종목명':'company_name'}).to_parquet(target/'members.parquet', index=False)
    (target/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    return receipt


def visible_signature(frame, count=80):
    """File-routing checksum; SHA256 remains the full archival integrity hash."""
    pairs = [str(row['종목코드']) + ':' + str(row['종가']).replace(',', '')
             for _, row in frame.head(count).iterrows()]
    value = 14695981039346656037
    for byte in '|'.join(pairs).encode('utf-8'):
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return format(value, '016x')


def stage_fingerprints(lines, output, downloads, capture_date):
    candidates = []
    for path in Path(downloads).glob(f'data_*_{capture_date}*.csv'):
        try:
            frame = pd.read_csv(path, encoding='cp949', dtype=str)
            if len(frame) < 100 or '종목코드' not in frame or '종가' not in frame:
                continue
            candidates.append((path,frame))
        except (UnicodeError, pd.errors.ParserError, ValueError):
            continue
    receipts = []
    for line in lines:
        if not line.strip():continue
        market, day, first_code, signature = line.strip().split('|')
        matches = []
        for path,frame in candidates:
            positions=frame.index[frame['종목코드'].eq(first_code)].tolist()
            if len(positions)==1 and visible_signature(frame.iloc[positions[0]:positions[0]+80])==signature:
                matches.append(path)
        if not matches:
            raise ValueError(f'No downloaded file matches 80 visible grid rows: {market} {day}')
        hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in matches}
        if len(hashes) != 1:
            raise ValueError(f'Ambiguous full files for visible grid: {market} {day}')
        index={'P':'KOSPI200','Q':'KOSDAQ150'}[market]
        receipts.append(stage(matches[0], output, index, day))
        (Path(output)/index/day/'ui-binding.json').write_text(json.dumps(dict(
            index=index,date=day,observed_grid_first_code=first_code,
            observed_grid_rows=80,observed_grid_fnv64=signature,
            binding='80_CONSECUTIVE_VISIBLE_QUERY_GRID_ROWS_MATCH_COMPLETE_CSV'),indent=2)+'\n')
    return receipts


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source');p.add_argument('--output',required=True)
    p.add_argument('--index');p.add_argument('--date')
    p.add_argument('--batch-stdin',action='store_true',help='P/Q|YYYYMMDD|download basename|observed first code|observed close')
    p.add_argument('--fingerprints-stdin',action='store_true',help='P/Q|YYYYMMDD|first code|80-row visible grid FNV64')
    p.add_argument('--downloads',default='/Users/mac/Downloads')
    p.add_argument('--capture-date',default='20261003')
    a=p.parse_args()
    if a.fingerprints_stdin:
        receipts=stage_fingerprints(sys.stdin,a.output,a.downloads,a.capture_date)
        print(json.dumps(dict(staged=len(receipts),member_rows=sum(x['rows'] for x in receipts))))
    elif a.batch_stdin:
        receipts=[]
        for line in sys.stdin:
            if not line.strip():continue
            market,day,name,code,close=line.strip().split('|')
            if Path(name).name != name:raise ValueError('Basename required')
            receipts.append(stage(Path('/Users/mac/Downloads')/name,a.output,{'P':'KOSPI200','Q':'KOSDAQ150'}[market],day,code,close))
        print(json.dumps(dict(staged=len(receipts),member_rows=sum(x['rows'] for x in receipts))))
    else:
        if not all([a.source,a.index,a.date]):p.error('source, index and date required')
        print(json.dumps(stage(a.source,a.output,a.index,a.date),ensure_ascii=False))
