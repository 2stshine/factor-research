"""Reconcile raw provider evidence before immutable Gold measurement builds."""
import argparse
from collections import Counter
from pathlib import Path
import re
import pandas as pd
from engine import reference_new_information as lib,reference_library as base,reference_gold as gold
from engine.reference_db import connect
from engine.research_generation import digest
from scripts.build_reference_flows import parity
from scripts.capture_reference_filing_anchors import SQL as FILING_SQL
from scripts.publish_reference_expansion import load_json,save_json,sha

def verified_manifest(path):
 path=Path(path);m=load_json(path/'manifest.json')
 if m['status']!='COMPLETE':raise ValueError('Incomplete source collection')
 for f in m.get('files',[]):
  if sha(path/f['path'])!=f['sha256']:raise ValueError('Changed source response')
 if 'plan_sha256' in m and sha(path/'plan.json')!=m['plan_sha256']:raise ValueError('Source plan changed')
 return m

def employee_annual(source,anchors):
 rows=[];excluded=[]
 grouped={(str(c),int(y)):g for (c,y),g in anchors.groupby(['corp_code',anchors.period_end.dt.year])}
 for path in sorted(Path(source).glob('[0-9]*-[0-9]*.json')):
  envelope=load_json(path);corp=envelope['parameters']['corp_code'];year=int(envelope['parameters']['bsns_year'])
  candidates=grouped.get((corp,year));raw=envelope['payload'].get('list',[])
  if candidates is None:raise ValueError('Employee response outside source plan')
  target=f'{year}-12-31'
  raw=[r for r in raw if r.get('stlm_dt')==target and r.get('corp_code')==corp]
  receipts=sorted({r.get('rcept_no','') for r in raw},reverse=True)
  if not receipts:excluded.append(dict(corp_code=corp,fiscal_year=year,reason='NO_EXACT_DECEMBER_FY_EMPLOYEE_RESPONSE'));continue
  receipt=receipts[0] # Never substitute older numbers if the latest report fails.
  matched=candidates.loc[candidates.filing_id.eq(receipt)&candidates.period_end.eq(pd.Timestamp(target))]
  if matched.asset_id.nunique()!=1:
   excluded.append(dict(corp_code=corp,fiscal_year=year,reason='NO_UNIQUE_CERTIFIED_RECEIPT_IDENTITY'));continue
  try:
   n,method=lib.employee_count([r for r in raw if r.get('rcept_no')==receipt])
   clocks={lib.receipt_known_at(r.filed,r.filing_id,r.period_end) for r in matched.itertuples()}
   if len(clocks)!=1:raise ValueError('CONFLICTING_RECEIPT_CLOCK')
  except ValueError as e:
   excluded.append(dict(corp_code=corp,fiscal_year=year,reason=str(e)));continue
  rows.append(dict(asset_id=int(matched.asset_id.iloc[0]),corp_code=corp,period_end=pd.Timestamp(target),
   employees=n,known_at=next(iter(clocks)),receipt=receipt,aggregation=method,response_sha256=sha(path)))
 frame=pd.DataFrame(rows)
 if frame.empty:raise ValueError('No certified employee observations')
 if frame.duplicated(['asset_id','period_end']).any():raise ValueError('Conflicting employee issuer identity')
 lookup={(r.asset_id,r.period_end):r for r in frame.itertuples()};growth=[]
 for r in frame.itertuples():
  previous=lookup.get((r.asset_id,r.period_end-pd.DateOffset(years=1)))
  if previous is None or previous.corp_code!=r.corp_code:continue
  growth.append(dict(asset_id=r.asset_id,period_end=r.period_end,employees=r.employees,prev_employees=previous.employees,
   known_at=max(r.known_at,previous.known_at),receipt=r.receipt,previous_receipt=previous.receipt,
   corp_code=r.corp_code,response_sha256=r.response_sha256,previous_response_sha256=previous.response_sha256))
 return pd.DataFrame(growth),dict(valid_level_years=len(frame),valid_growth_years=len(growth),
  excluded_reason_counts=dict(Counter(r['reason'] for r in excluded)),excluded=excluded),frame

def rd_annual(source,anchors):
 plan=load_json(Path(source)/'plan.json');identity=pd.DataFrame(plan['identities'])
 identity.asset_id=identity.asset_id.astype(int)
 mapping=identity.groupby('symbol').asset_id.unique().to_dict()
 ag={(int(a),p):g for (a,p),g in anchors.loc[anchors.fs_type.eq('CFS')].groupby(['asset_id','period_end'])}
 result=[];excluded=[];badclock=0
 for symbol in plan['symbols']:
  path=Path(source)/(symbol+'.json');env=load_json(path);raw=env['payload']
  assets=mapping[symbol]
  if len(assets)!=1:excluded.append(dict(symbol=symbol,reason='REUSED_SYMBOL_IDENTITY'));continue
  counts=Counter(r.get('date') for r in raw if isinstance(r,dict))
  for row in raw:
   period=str(row.get('date',''))
   if not re.fullmatch(r'20\d\d-12-31',period) or not '2015-12-31'<=period<='2025-12-31':continue
   reason=None
   if row.get('symbol')!=symbol or counts[period]!=1:reason='AMBIGUOUS_PROVIDER_YEAR'
   anchor=ag.get((int(assets[0]),pd.Timestamp(period)))
   if reason is None and anchor is None:reason='NO_CERTIFIED_DART_CFS_ANCHOR'
   if reason is None:
    matches=[r for r in anchor.to_dict('records') if lib.rd_matches(row,r)]
    if not matches:reason='RD_MISSING_ZERO_OR_CFS_REVENUE_MISMATCH'
   if reason is not None:excluded.append(dict(symbol=symbol,period_end=period,reason=reason));continue
   try:
    clocks=[lib.receipt_known_at(r['filed'],r['filing_id'],r['period_end']) for r in matches]
   except ValueError:
    excluded.append(dict(symbol=symbol,period_end=period,reason='INVALID_OFFICIAL_FILING_CLOCK'));continue
   # Latest matched certified receipt, not the often erroneous FMP filingDate.
   latest=max(zip(clocks,matches),key=lambda p:p[0]);known,chosen=latest
   if not row.get('filingDate') or str(row['filingDate'])[:10]<=period:badclock+=1
   result.append(dict(asset_id=int(assets[0]),period_end=pd.Timestamp(period),rd_expense=float(row['researchAndDevelopmentExpenses']),
    revenue=float(row['revenue']),known_at=known,receipt=chosen['filing_id'],corp_code=chosen['corp_code'],
    response_sha256=sha(path),source_symbol=symbol))
 frame=pd.DataFrame(result)
 if not frame.empty and frame.duplicated(['asset_id','period_end']).any():
  # A historical market transfer can supply both suffixes. Do not pick one.
  dupe=frame.duplicated(['asset_id','period_end'],keep=False)
  excluded.extend(dict(asset_id=int(r.asset_id),period_end=str(r.period_end.date()),reason='MULTIPLE_PROVIDER_SYMBOLS_FOR_ASSET_YEAR') for r in frame.loc[dupe].itertuples())
  frame=frame.loc[~dupe].copy()
 return frame,dict(valid_years=len(frame),ignored_nonhistorical_provider_clock_rows=badclock,
  excluded_reason_counts=dict(Counter(r['reason'] for r in excluded)),excluded=excluded)

def build(kind,source,filings,identity,output):
 source,filings,identity,out=map(Path,(source,filings,identity,output));out.mkdir(parents=True,exist_ok=True)
 implementation={str(Path(f).relative_to(Path(__file__).resolve().parents[1])):dict(sha256=sha(f),source=Path(f).read_text()) for f in
  (__file__,lib.__file__,str(Path(__file__).with_name('build_reference_flows.py')),str(Path(__file__).with_name('capture_reference_filing_anchors.py')))}
 save_json(out/'implementation-source.json',implementation)
 m=verified_manifest(source);fm=verified_manifest(filings)
 if sha(filings/fm['path'])!=fm['sha256'] or fm['query_sha256']!=digest(FILING_SQL):raise ValueError('Filing anchors changed')
 identity_evidence=load_json(identity.with_name('input-evidence.json'))
 if identity_evidence['input_file_sha256']!=sha(identity):raise ValueError('Certified monthly identity source changed')
 anchors=pd.read_parquet(filings/fm['path']);anchors.period_end=pd.to_datetime(anchors.period_end)
 p=pd.read_parquet(identity,columns=list(base._BASE))
 if kind=='employee':
  annual,audit,levels=employee_annual(source,anchors);levels.to_parquet(out/'employee-levels.parquet',index=False)
 else:annual,audit=rd_annual(source,anchors)
 if annual.empty:raise ValueError('No qualified annual source rows')
 panel=lib.monthly_panel(p,anchors,annual)
 annual.to_parquet(out/'annual-input.parquet',index=False);panel.to_parquet(out/'monthly-input.parquet',index=False)
 save_json(out/'exclusion-audit.json',audit)
 evidence=dict(provider_manifest_sha256=sha(source/'manifest.json'),filing_manifest_sha256=sha(filings/'manifest.json'),
  identity_sha256=sha(identity),annual_sha256=sha(out/'annual-input.parquet'),monthly_sha256=sha(out/'monthly-input.parquet'),
  exclusion_audit_sha256=sha(out/'exclusion-audit.json'),source_type=lib.SOURCE_TYPE,kind=kind,
  pit_status=lib.PIT_STATUS,first_vintage_verified=False,forward_labels_read=False,legacy_gold_used=False,
  coverage_scope=fm['scope'],limitation=fm['limitation'])
 save_json(out/'source-evidence.json',evidence)
 att=dict(status='CERTIFIED',source_type=lib.SOURCE_TYPE,source_contract=lib.SOURCE_CONTRACT,pit_status=lib.PIT_STATUS,
  scope=base.INPUT_SCOPE,identity_contract=base.IDENTITY_CONTRACT,first_vintage_independently_verified=False,
  source_version=digest(evidence),evidence_sha256=digest(evidence),input_sha256=evidence['monthly_sha256'],
  availability_policy='CERTIFIED_DART_RECEIPT_NEXT_DAY_KST',fmp_filing_timestamp_used=False,
  employee_consolidation_scope='DISCLOSING_ISSUER_NOT_GROUP',rd_currency='KRW',rd_revenue_bridge='DART_CFS_EXACT_FY_REL1E6_ABS1KRW')
 d=next(d for d in lib.definitions() if ('hiring' in d['id'])==(kind=='employee'));ref=d['id']
 v=panel[list(base._BASE)].copy();base._prepare(v);v['reference_id']=ref;v['value']=lib.calculate(panel,ref);v['oriented_value']=v.value*d['orientation']
 v['definition_hash']=base.definition_hash(d);v['source_version']=att['source_version'];v['input_sha256']=att['input_sha256'];v=v[base._OUTPUT]
 if v.value.isna().any() or v.asset_id.nunique()<100 or v.date.nunique()<60:raise ValueError('Insufficient coverage or invalid output')
 with connect(read_only=False) as conn:check=parity(panel,v,ref,conn,specs=lib.SPECS)
 summary=dict(reference_id=ref,definition_hash=base.definition_hash(d),status='MEASUREMENT_VALIDATED',value_rows=len(v),
  assets=int(v.asset_id.nunique()),months=int(v.date.nunique()),first_date=str(v.date.min().date()),last_date=str(v.date.max().date()))
 validation=dict(source_version=att['source_version'],input_sha256=att['input_sha256'],source_evidence_sha256=att['evidence_sha256'],
  implementation_sha256=digest({Path(f).name:sha(f) for f in (__file__,lib.__file__)}),role='MEASUREMENT_CONTROL',alpha_approved=False,value_rows=len(v),references=[summary])
 pub,_=gold.build_publication(v,[d],attestation=att,validation=validation,parity=check)
 dest=out/ref;dest.mkdir(exist_ok=True);save_json(dest/'publication.json',pub);v.to_parquet(dest/'values.parquet',index=False)
 print(summary,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kind',required=True,choices=('employee','rd'))
 for arg in ('source','filings','identity','output'):p.add_argument('--'+arg,required=True)
 a=p.parse_args();build(a.kind,a.source,a.filings,a.identity,a.output)
