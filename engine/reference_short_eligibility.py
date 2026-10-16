"""Versioned eligible-day short activity, not borrowability or approved alpha."""
import numpy as np
import pandas as pd
from engine.reference_library import validate_catalog

SOURCE_TYPE='RDS_CERTIFIED_KIS_KRX_SHORT_ELIGIBILITY_V2'
SOURCE_CONTRACT='KRX_DAILY_INDEX_MEMBERSHIP_AND_INDIVIDUAL_RESTRICTIONS_V2'
PIT_STATUS='PIT_ASSUMED'
REPLACEMENTS={
 'kr_short_volume_share_unrestricted_1m_v1':'kr_short_volume_share_eligible_1m_v2',
 'kr_short_volume_share_change_1m_v1':'kr_short_volume_share_change_1m_v2',
}
SPECS={
 'kr_short_volume_share_eligible_1m_v2':('허용 거래일 KRX 공매도 거래비중','sq/NULLIF(sv,0)',['sq','sv']),
 'kr_short_volume_share_change_1m_v2':('허용 거래일 KRX 공매도 거래비중 변화','sq/NULLIF(sv,0)-prev_short_share',['sq','sv','prev_short_share']),
}

def definitions():
 result=[]
 for ref,(name,formula,cols) in SPECS.items():
  result.append(dict(id=ref,name_ko=name,family='short_sale_activity',formula=formula,required_columns=cols,
   object_type='STOCK_CHARACTERISTIC',role='MEASUREMENT_CONTROL',alpha_approved=False,orientation=1,
   lookback={'calendar_months':2 if 'change' in ref else 1,'minimum_eligible_days':15},
   sources=[{'title':'FSC: 2021 partial short-sale resumption for KOSPI200/KOSDAQ150','url':'https://www.fsc.go.kr/po010106/75290'},
    {'title':'KRX: daily index constituents [11006] and short-sale overheat restriction intervals [34001]','url':'https://data.krx.co.kr/'},
    {'title':'FSC: 2025 general short-sale resumption','url':'https://www.fsc.go.kr/po010101/84216'}],
   adaptation='공매도 잔고 아닌 거래수량 비중의 한국 시장 측정값. 일반 허용일 및 2021-05-03~2023-11-05 당시 KOSPI200/KOSDAQ150 편입일만 사용. KRX 공식 일별 구성종목으로 확인하며 보간하지 않음. 개별 과열 공매도 제한의 실제 시작~종료일을 모든 기간에서 제외. 분자·분모 모두 같은 허용일만 합산. 가용 허용일 최소15일, 전일 관측과 일별 정합성 필요. 실제 0은 유지하고 결측/금지는 0으로 대체하지 않음. 변화는 인접 달만 계산. 익일08:30 KST 가용 가정으로 월말 이후 가용 거래 제외. 최신 수정자료를 동결한 PIT_ASSUMED이며 당시 최초 빈티지 검증 아님. 대차 가능성/주문별 규제/체결 보장이 아니며 제도 간 경제적 비교가능성이나 알파 승인 아님. 종전 blanket-exclusion v1을 대체하는 버전으로 별도 알파 수에 더하지 않음.',
   evidence_tier='OFFICIAL_POLICY_MATCHED_MEASUREMENT_NOT_ALPHA',
   readiness={'status':'IMPLEMENTED_REQUIRES_ATTESTATION','blockers':[]}))
 validate_catalog(result);return result

def prepare(frame):
 p=frame.copy().sort_values(['asset_id','date']).reset_index(drop=True);p['date']=pd.to_datetime(p.date)
 if p.duplicated(['asset_id','date']).any() or not p.date.dt.is_month_end.all():raise ValueError('Invalid source month keys')
 counts=['expected_days','eligible_days','excluded_regime_days','excluded_individual_days','short_days','bad_short','bad_identity']
 for c in counts:
  if p[c].isna().any() or (p[c]<0).any() or (p[c]!=np.floor(p[c])).any():raise ValueError('Invalid source counts')
 if (p.eligible_days+p.excluded_regime_days+p.excluded_individual_days!=p.expected_days).any():raise ValueError('Eligibility partition mismatch')
 if (p.short_days>p.eligible_days).any() or (p.bad_short>p.short_days).any() or p.bad_identity.ne(0).any():raise ValueError('Invalid source identity/counts')
 known=pd.to_datetime(p.short_known_at,utc=True)
 cutoff=(p.date+pd.Timedelta(days=1)).dt.tz_localize('Asia/Seoul').dt.tz_convert('UTC')
 for c in ('sq','sv'):p[c]=pd.to_numeric(p[c],errors='raise')
 valid=(p.eligible_days>=15)&p.short_days.eq(p.eligible_days)&p.bad_short.eq(0)&known.notna()&known.lt(cutoff)
 valid=valid&(p.sq>=0)&(p.sv>0)&(p.sq<=p.sv)&np.isfinite(p.sq)&np.isfinite(p.sv)
 p['measurement_eligible']=valid
 for c in ('sq','sv'):p[c]=pd.to_numeric(p[c]).where(valid)
 ratio=p.sq/p.sv;previous=p.groupby('asset_id').date.shift()
 adjacent=(p.date.dt.year*12+p.date.dt.month)-(previous.dt.year*12+previous.dt.month)==1
 p['prev_short_share']=ratio.groupby(p.asset_id).shift().where(adjacent)
 return p

def calculate(panel,ref):
 if ref not in SPECS:raise ValueError('Unregistered short measurement')
 values=panel.sq/panel.sv
 if 'change' in ref:values=values-panel.prev_short_share
 return values.where(np.isfinite(values))
