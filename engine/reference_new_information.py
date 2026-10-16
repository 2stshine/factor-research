"""New information references: issuer employee hiring and positive R&D intensity.

No returns or outcome-based thresholds. Current backfills are PIT_ASSUMED;
receipt dates limit availability but cannot certify unrevised first vintages.
"""
from __future__ import annotations
import re
import math
import pandas as pd
import numpy as np
from engine.reference_library import validate_catalog

SOURCE_TYPE='OFFICIAL_DART_FMP_NEW_INFORMATION_REFERENCE_V1'
SOURCE_CONTRACT='DART_RECEIPT_ANCHORED_ANNUAL_EMPLOYEE_RD_V1'
PIT_STATUS='PIT_ASSUMED'
SPECS={
 'kr_employee_hiring_fy_reference_v1':('공시 직원 수 순고용률','2.0*(employees-prev_employees)/NULLIF(employees+prev_employees,0)', ['employees','prev_employees']),
 'kr_rd_expense_sales_fy_reference_v1':('양의 연구개발비 매출액 비율','rd_expense/NULLIF(revenue,0)', ['rd_expense','revenue']),
}

def definitions():
 out=[]
 for ref,(name,formula,cols) in SPECS.items():
  hiring='hiring' in ref
  out.append(dict(id=ref,name_ko=name,family='labor_hiring' if hiring else 'innovation',formula=formula,required_columns=cols,
   object_type='STOCK_CHARACTERISTIC',role='MEASUREMENT_CONTROL',alpha_approved=False,orientation=-1 if hiring else 1,
   lookback={'fiscal_years':2 if hiring else 1,'maximum_age_days':549},
   sources=([dict(title='Belo, Lin and Bazdresch (2014), JPE, equation in section II.A',url='https://www.journals.uchicago.edu/doi/abs/10.1086/674549'),
             dict(title='OpenDART employee disclosure API',url='https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS002&apiId=2019011')] if hiring else
            [dict(title='Chan, Lakonishok and Sougiannis, R&D and stock valuation',url='https://www.nber.org/papers/w7223'),
             dict(title='FMP annual income statement API',url='https://site.financialmodelingprep.com/developer/docs/stable/income-statement'),
             dict(title='Samsung official R&D accounting scope example, p16',url='https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_3Q_Interim_Report.pdf')]),
   adaptation=('순고용률 원식 2*(N_t-N_t-1)/(N_t+N_t-1). DART 공시 제출법인 직원 수 기준이며 Compustat 연결 고용과 동일 범위라고 주장하지 않음. 12월 결산·연속 FY·같은 법인만 사용. 성별 합계와 사업부 소계 중복을 제거하고 합계 모순은 제외. 연결 매출을 본사 인원으로 나누지 않음. 낮은 고용률 방향은 문헌 사전 부호이며 한국 수익성 승인이 아님.' if hiring else
    'FMP researchAndDevelopmentExpenses 중 양수만 사용. 0은 실제 무지출과 미보고를 구분할 수 없어 결측 취급. 같은 FY·KRW·동일 기업의 인증 DART 연결 매출과 1e-6 상대허용오차/1원 이내 일치한 응답만 사용. FMP 결산일형 filingDate/acceptedDate는 무시하고 DART 해당 FY 공시 다음날을 가정 가용시각으로 사용. 원논문의 모든 정렬·포트폴리오 조건을 복제한 알파가 아닌 혁신 투입 측정값.' )+
    ' 최신 조회 응답을 동결한 PIT_ASSUMED이며 최초 발표값 검증 아님. 신규 FY 자료가 없거나 검증 실패하면 과거 FY로 소급 대체하지 않음. 공시 기준 다음날 00:00 KST부터 월말 사용, 결산 후 최대 549일. 기존 100개 정의와 별개 측정이며 실증 수익률을 보고 선택하지 않음.',
   evidence_tier='LITERATURE_MEASUREMENT_KOREAN_ADAPTATION_NOT_ALPHA',readiness={'status':'IMPLEMENTED_REQUIRES_ATTESTATION','blockers':[]}))
 validate_catalog(out);return out

def count(value):
 if isinstance(value,bool):return None
 s=str(value).strip().replace(',','')
 return int(s) if re.fullmatch(r'\d+',s) else None

def employee_count(rows):
 """Reject ambiguous/contradictory totals; never turn '-' into zero staff."""
 if not rows:raise ValueError('NO_EMPLOYEE_ROWS')
 clean=[];last=None
 for row in rows:
  sex={'남':'M','남자':'M','남성':'M','여':'F','여자':'F','여성':'F'}.get(str(row.get('sexdstn','')).strip())
  if sex is None:raise ValueError('UNSUPPORTED_SEX_OR_TOTAL_ROW')
  segment=re.sub(r'\s+','',str(row.get('fo_bbm','')))
  if segment in ('〃','"','”'):
   if last is None:raise ValueError('UNRESOLVED_DITTO_SEGMENT')
   segment=last
  else:last=segment
  n=count(row.get('sm'))
  if n is None:raise ValueError('MISSING_EMPLOYEE_COUNT')
  regular,contract=count(row.get('rgllbr_co')),count(row.get('cnttk_co'))
  if regular is not None and contract is not None and regular+contract!=n:raise ValueError('EMPLOYEE_COMPONENT_MISMATCH')
  aggregate=segment in ('성별합계','성별총계','합계','총계','계','전체','전사','전체합계','총합계')
  if not aggregate and any(token in segment for token in ('합계','소계','총계')):raise ValueError('AMBIGUOUS_SUBTOTAL')
  clean.append((segment,sex,n,aggregate))
 if len({(s,x) for s,x,_,_ in clean})!=len(clean):raise ValueError('DUPLICATE_SEGMENT_SEX')
 if len(clean)==2 and {r[1] for r in clean}=={'M','F'}:
  total=sum(r[2] for r in clean)
  if total<=0:raise ValueError('NONPOSITIVE_EMPLOYEE_COUNT')
  return total,'SINGLE_MALE_FEMALE_PAIR'
 totals=[r for r in clean if r[3]];detail=[r for r in clean if not r[3]]
 if totals:
  if len(totals)!=2 or {r[1] for r in totals}!={'M','F'}:raise ValueError('INCOMPLETE_OR_REPEATED_TOTAL')
  for _,sex,n,_ in totals:
   parts=[r[2] for r in detail if r[1]==sex]
   if parts and sum(parts)!=n:raise ValueError('EMPLOYEE_TOTAL_MISMATCH')
  selected=totals;method='EXPLICIT_SEX_TOTALS_RECONCILED'
 else:
  if {r[1] for r in clean}!={'M','F'}:raise ValueError('INCOMPLETE_SEX_COVERAGE')
  selected=clean;method='SUM_UNIQUE_SEGMENT_SEX_ROWS'
 total=sum(r[2] for r in selected)
 if total<=0:raise ValueError('NONPOSITIVE_EMPLOYEE_COUNT')
 return total,method

def receipt_known_at(filed,receipt,period):
 if not re.fullmatch(r'\d{14}',str(receipt)):raise ValueError('INVALID_RECEIPT')
 filed=pd.Timestamp(filed).normalize();period=pd.Timestamp(period).normalize()
 if filed.strftime('%Y%m%d')!=str(receipt)[:8] or filed<=period:raise ValueError('INVALID_FILING_CLOCK')
 return (filed+pd.Timedelta(days=1)).tz_localize('Asia/Seoul').tz_convert('UTC')

def rd_matches(row,anchor):
 """Provider amounts plus official consolidated sales/receipt identity bridge."""
 if row.get('period')!='FY' or row.get('reportedCurrency')!='KRW' or anchor['currency']!='KRW' or anchor['fs_type']!='CFS':return False
 if str(row.get('date'))!=str(pd.Timestamp(anchor['period_end']).date()):return False
 revenue=row.get('revenue');rd=row.get('researchAndDevelopmentExpenses')
 if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (revenue,rd)):return False
 return math.isclose(float(revenue),float(anchor['revenue']),rel_tol=1e-6,abs_tol=1.)

def monthly_panel(identity,anchors,annual):
 """Use latest public FY even if its measurement is missing (no stale fallback)."""
 p=identity[['asset_id','stock_code','market','date']].copy();p.asset_id=p.asset_id.astype(int);p.date=pd.to_datetime(p.date)
 a=anchors.copy();a.period_end=pd.to_datetime(a.period_end)
 a=a.loc[a.period_end.dt.month.eq(12)&a.period_end.dt.day.eq(31)]
 schedules=[]
 for (asset,period),group in a.groupby(['asset_id','period_end']):
  clocks=[]
  for row in group.to_dict('records'):
   try:clocks.append(receipt_known_at(row['filed'],row['filing_id'],period))
   except ValueError:pass
  if clocks:schedules.append(dict(asset_id=int(asset),period_end=period,first_known_at=min(clocks)))
 schedule=pd.DataFrame(schedules);annual=annual.copy()
 if annual.duplicated(['asset_id','period_end']).any():raise ValueError('Ambiguous annual measurement')
 lookup={(int(r.asset_id),pd.Timestamp(r.period_end)):r._asdict() for r in annual.itertuples(index=False)}
 result=[]
 groups={int(k):g.sort_values('period_end') for k,g in schedule.groupby('asset_id')}
 for r in p.itertuples(index=False):
  s=groups.get(r.asset_id)
  if s is None:continue
  cutoff=(r.date+pd.Timedelta(days=1)).tz_localize('Asia/Seoul').tz_convert('UTC')
  eligible=s.loc[(s.first_known_at<cutoff)&((r.date-s.period_end).dt.days<=549)]
  if eligible.empty:continue
  period=eligible.period_end.max();v=lookup.get((r.asset_id,period))
  if v is None or pd.Timestamp(v['known_at'])>=cutoff:continue
  result.append(dict(asset_id=r.asset_id,stock_code=r.stock_code,market=r.market,date=r.date,**{k:x for k,x in v.items() if k!='asset_id'}))
 return pd.DataFrame(result)

def calculate(panel,ref):
 if ref=='kr_employee_hiring_fy_reference_v1':v=2*(panel.employees-panel.prev_employees)/(panel.employees+panel.prev_employees)
 elif ref=='kr_rd_expense_sales_fy_reference_v1':v=panel.rd_expense/panel.revenue
 else:raise ValueError('Unregistered new-information reference')
 return v.where(np.isfinite(v))
