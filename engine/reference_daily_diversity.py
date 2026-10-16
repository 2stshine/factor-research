"""Immutable metadata and raw-source verification for new daily measurements."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from engine import reference_formulaic as formulas, reference_library as base
from engine.research_generation import digest
from scripts.publish_reference_expansion import sha

SOURCE_TYPE='RDS_CERTIFIED_REFERENCE_FORMULAIC_V1'
SOURCE_CONTRACT='FROZEN_DAILY_KRX_TWO_INTERPRETERS_V1'
PIT_STATUS='PIT_ASSUMED'
PARITY_KIND='INDEPENDENT_PANDAS_NUMPY_FULL_RAW_DAILY'

def definitions():
    result=[]
    for number,formula in formulas.FORMULAS.items():
        result.append(dict(id=f'kr_wq_{number:03d}_daily_monthend_v1',
            name_ko=f'WQ {number:03d}: '+formulas.NAMES[number],family='price_volume_interaction',
            object_type='STOCK_CHARACTERISTIC',role='MEASUREMENT_CONTROL',alpha_approved=False,
            formula=formula,orientation=1,required_columns=['open','high','low','close','volume','adj_close']+(['trading_value'] if 'vwap' in formula else []),
            lookback={'daily_observations':formulas.required_history(formula)+1,'sampling':'LAST_KRX_SESSION_OF_CLOSED_MONTH',
                      'all_input_observations_required':True},
            sources=[{'title':'Kakushadze (2016), 101 Formulaic Alphas; WorldQuant formulas reproduced with permission',
                      'url':'https://arxiv.org/abs/1601.00991','review_scope':f'Appendix A Alpha #{number}, operators and daily inputs; Sections 2–3'}],
            adaptation='원형의 단기 일별 신호를 한국 월말에 표본화한 레퍼런스. 월 리밸런싱 수익성 근거 아님. 당일 KRX 보통주 전체 횡단면, 평균 동순위/백분위 순위, rank 입력 소수 12자리 동률 처리, 표본표준편차, 최초 argmax의 1-based 시점. 원화 원시 OHLC/거래량과 가격조정 수익률 사용; 전체 산식 lookback 중 조정계수 변동 >1e-6인 창은 제외. 결측창·상관 상수창 제외, 101의 0.001은 KRW 단위. 일별 확정 후 월초 실행의 별도 검증 필요. PIT_ASSUMED로 최초 빈티지·기업행위 당시 버전 미증명.',
            evidence_tier='PUBLIC_SHORT_HORIZON_FORMULA_MONTHLY_ADAPTATION',quota_bucket='other_quant_firm',
            readiness={'status':'IMPLEMENTED_REQUIRES_ATTESTATION','blockers':[]}))
    for definition in result:
        if 'vwap' in definition['formula']:
            definition['adaptation']+=' VWAP는 동일 일자의 KRW 거래대금/거래량으로 계산하며 OHLC 단순평균으로 대체하지 않음. 거래량 0 또는 VWAP가 당일 저가~고가 범위 밖이면 결측 처리.'
    base.validate_catalog(result)
    return result

def implementation_hash():
    return digest({Path(p).name:sha(p) for p in [__file__,formulas.__file__]})

def verify_capture(directory):
    directory=Path(directory)
    m=json.loads((directory/'manifest.json').read_text())
    h=m.pop('manifest_sha256')
    if digest(m)!=h or m['status']!='COMPLETE' or m['version']!='certified-reference-daily-v1':
        raise ValueError('Incomplete/changed daily capture')
    for f in m['files']:
        if Path(f['path']).name!=f['path'] or sha(directory/f['path'])!=f['sha256']:
            raise ValueError('Daily bytes mismatch')
    m['manifest_sha256']=h
    return m

def load_matrices(directory):
    directory=Path(directory);manifest=verify_capture(directory)
    columns=['asset_id','trade_date','open','high','low','close','volume','adj_close','market_cap','trading_value','shares']
    parts=[pd.read_parquet(directory/f['path'],columns=columns) for f in manifest['files'] if f['rows']]
    raw=pd.concat(parts,ignore_index=True);del parts
    raw.trade_date=pd.to_datetime(raw.trade_date)
    if raw.duplicated(['asset_id','trade_date']).any():raise ValueError('Duplicate daily identity')
    raw=raw.set_index(['trade_date','asset_id']).sort_index()
    matrices={}
    for name in columns[2:]:
        w=raw[name].unstack('asset_id').sort_index(axis=1)
        matrices[name]=w.to_numpy(dtype=float)
    dates,assets=w.index,w.columns.to_numpy(dtype=int)
    del raw,w
    valid=np.ones(matrices['close'].shape,dtype=bool)
    for c in ['open','high','low','close','adj_close']:
        valid &= np.isfinite(matrices[c]) & (matrices[c]>0)
    valid &= (matrices['high']>=matrices['low']) & (matrices['high']>=matrices['open']) & (matrices['high']>=matrices['close'])
    valid &= (matrices['low']<=matrices['open']) & (matrices['low']<=matrices['close'])
    valid &= np.isfinite(matrices['volume']) & (matrices['volume']>=0)
    for c in matrices:matrices[c]=np.where(valid,matrices[c],np.nan)
    factor=matrices['adj_close']/matrices['close']
    with np.errstate(all='ignore'):
        jump=np.vstack([np.ones((1,len(assets)),dtype=bool),abs(factor[1:]/factor[:-1]-1)>1e-6])
        ret=np.vstack([np.full((1,len(assets)),np.nan),matrices['adj_close'][1:]/matrices['adj_close'][:-1]-1])
    matrices['returns']=ret
    return matrices,dates,assets,valid,jump,manifest
