"""Monthly KRX-only KIS measurements with explicit assumed availability.

Latest observed revisions are frozen today, NOT strict historical vintages.
The next-calendar-day 08:30 KST policy excludes unavailable month-end trades.
Missing source days invalidate a month; no zero-filling or market mixing.
"""
import numpy as np
import pandas as pd
from engine.reference_library import validate_catalog

SOURCE_TYPE='RDS_CERTIFIED_KIS_MONTHLY_REFERENCE_V1'
SOURCE_CONTRACT='KRX_J_KIS_NEXT_DAY_MONTH_END_FULL_COVERAGE_V1'
PIT_STATUS='PIT_ASSUMED'
SOURCE_URL='https://www.sciencedirect.com/science/article/pii/S0927538X24003743'
POLICY_URL='https://www.fsc.go.kr/po010101/84216'
SPECS={
 'kr_foreign_net_buy_balance_1m_v1':('외국인 월간 순매수 균형','(fb-fs)/NULLIF(fb+fs,0)', ['fb','fs']),
 'kr_institution_net_buy_balance_1m_v1':('기관 월간 순매수 균형','(ib-isell)/NULLIF(ib+isell,0)', ['ib','isell']),
 'kr_foreign_net_buy_persistence_1m_v1':('외국인 순매수 일수 지속성','(fp-fn)/NULLIF(investor_days,0)', ['fp','fn','investor_days']),
 'kr_institution_net_buy_persistence_1m_v1':('기관 순매수 일수 지속성','(ip-inneg)/NULLIF(investor_days,0)', ['ip','inneg','investor_days']),
 'kr_short_volume_share_unrestricted_1m_v1':('전면허용기 KRX 공매도 거래비중','sq/NULLIF(sv,0)', ['sq','sv']),
 'kr_short_volume_share_change_1m_v1':('전면허용기 KRX 공매도 거래비중 변화','sq/NULLIF(sv,0)-prev_short_share',['sq','sv','prev_short_share']),
}

def definitions():
 result=[]
 for ref,(name,formula,cols) in SPECS.items():
  short='short_volume' in ref
  result.append(dict(id=ref,name_ko=name,family='short_sale_activity' if short else 'investor_behavior',
   formula=formula,required_columns=cols,object_type='STOCK_CHARACTERISTIC',role='MEASUREMENT_CONTROL',
   alpha_approved=False,orientation=1,lookback={'calendar_months':2 if 'change' in ref else 1,'minimum_days':15},
   sources=[{'title':'Kim, Kang, Roh: Korean investor behavior (motivation, not identical formula)', 'url':SOURCE_URL},
            {'title':'FSC short selling resumption and prior restrictions','url':POLICY_URL}],
   adaptation='한국 수급·공매도 측정 제안이며 논문 원식 완전 복제나 알파 방향 승인이 아님. KRX J만 사용. 순매수 균형은 주체 자체 매수+매도 대비 순매수 수량. 지속성은 양수일-음수일/유효일. 금액 단위 반올림을 피하기 위해 수량 사용. 최소 15개 가용 거래일과 모든 예상일 관측 필요. 실제 관측된 최신 수정값을 동결한 PIT_ASSUMED. 연구 가용시각은 공급자 보장 아닌 다음 달력일 08:30 KST 정책; 월말 이후 가용 거래는 제외. 공매도는 잔고가 아닌 거래비중. 2020-03~2025-03은 금지/부분허용과 구성종목 이력 미연결로 비교가능 표본에서 제외; 원본은 보존. 변화는 연속 달만 비교. 수익률 보고 부호를 선택하지 않음.',
   evidence_tier='KOREAN_LITERATURE_MOTIVATED_MEASUREMENT_NOT_ALPHA',readiness={'status':'IMPLEMENTED_REQUIRES_ATTESTATION','blockers':[]}))
 validate_catalog(result);return result

def prepare(frame):
 p=frame.copy().sort_values(['asset_id','date']).reset_index(drop=True)
 p['date']=pd.to_datetime(p.date)
 if p.duplicated(['asset_id','date']).any():raise ValueError('Duplicate source asset month')
 if not p.date.dt.is_month_end.all():raise ValueError('Calendar month-end source required')
 for col in ('expected_days','investor_days','short_days','bad_investor','bad_short'):
  if p[col].isna().any() or (p[col]<0).any() or (p[col]!=np.floor(p[col])).any():raise ValueError('Invalid source counts')
 if (p.investor_days>p.expected_days).any() or (p.short_days>p.expected_days).any():raise ValueError('Too many source days')
 inv=(p.expected_days>=15)&(p.investor_days==p.expected_days)&(p.bad_investor==0)
 sh=(p.expected_days>=15)&(p.short_days==p.expected_days)&(p.bad_short==0)
 if 'investor_known_at' in p:inv=inv&p.investor_known_at.notna()
 if 'short_known_at' in p:sh=sh&p.short_known_at.notna()
 inv=inv&(p[['fb','fs','ib','isell','fp','fn','ip','inneg']]>=0).all(axis=1)
 inv=inv&(p.fp+p.fn<=p.investor_days)&(p.ip+p.inneg<=p.investor_days)
 sh=sh&(p.sq>=0)&(p.sv>=0)&(p.sq<=p.sv)
 unrestricted=(p.date<pd.Timestamp('2020-03-01'))|(p.date>=pd.Timestamp('2025-04-01'))
 p['short_regime_eligible']=unrestricted
 for col in ('fb','fs','ib','isell','fp','fn','ip','inneg'):
  p[col]=pd.to_numeric(p[col]).where(inv)
 for col in ('sq','sv'):p[col]=pd.to_numeric(p[col]).where(sh&unrestricted)
 ratio=p.sq/p.sv.where(p.sv>0)
 previous=p.groupby('asset_id').date.shift()
 adjacent=(p.date.dt.year*12+p.date.dt.month)-(previous.dt.year*12+previous.dt.month)==1
 p['prev_short_share']=ratio.groupby(p.asset_id).shift().where(adjacent)
 return p

def calculate(panel,ref):
 if ref not in SPECS:raise ValueError('Unregistered flow')
 if 'foreign' in ref:
  numerator=panel.fp-panel.fn if 'persistence' in ref else panel.fb-panel.fs
  denominator=panel.investor_days if 'persistence' in ref else panel.fb+panel.fs
 elif 'institution' in ref:
  numerator=panel.ip-panel.inneg if 'persistence' in ref else panel.ib-panel.isell
  denominator=panel.investor_days if 'persistence' in ref else panel.ib+panel.isell
 else:numerator,denominator=panel.sq,panel.sv
 values=numerator/denominator.where(denominator>0)
 if 'change' in ref:values=values-panel.prev_short_share
 return values.where(np.isfinite(values))
