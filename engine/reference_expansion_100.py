"""Separately versioned, literature-bound additions to the 47 reference measures.

These are measurements and controls. No alpha promotion or outcome selection.
Explicit accounting adaptations retain their source differences in every row's
hashed definition. Definitions are never counted by aliases/lookback variants.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from engine import reference_library as base
from engine.reference_profit_growth import JKP_URL
from engine.research_generation import digest

SOURCE_TYPE='RDS_CERTIFIED_REFERENCE_DIVERSITY_V1'
SOURCE_CONTRACT='FROZEN_KRX_DART_FEATURE_ONLY_DIVERSITY_V1'
PIT_STATUS='PIT_ASSUMED'
QMJ='https://d-nb.info/1174954515/34'
SIZE='https://doi.org/10.1016/j.jfineco.2018.05.006'
SPECS={}

def add(key,name,family,formula,sql,columns,url,title,bucket,orientation=1,adaptation=''):
    SPECS['kr_'+key+'_v1']=dict(name_ko=name,family=family,formula=formula,sql=sql,
        columns=columns,primary=url,title=title,quota_bucket=bucket,orientation=orientation,
        adaptation=adaptation+' 한국 KOSPI/KOSDAQ 보통주, DART KRW 현재 가용 FY. 연결범위/계정 정의의 원문 차이 및 최초 빈티지 미검증. 한국 수익성 미승인.')

for metric,label in [('total_assets','총자산'),('total_equity','장부자본'),('revenue','매출'),('property_plant_and_equipment','유형자산')]:
    col='fy_'+metric
    add('nonprice_size_'+metric,'비가격 기업규모: '+label,'nonprice_size',f'ln({col}); positive only',
        f'CASE WHEN {col}>0 THEN ln({col}) END',[col],SIZE,'Asness et al. (2018), Size matters, if you control your junk','aqr',-1,
        '첨부 AQR 20 for Twenty 16장 비가격 규모. 시장가격을 포함하지 않는 기업규모 통제이며 단독 초과수익 주장이 아님. 자본은 우선주/비지배지분 차감 전 총자본, PPE는 순장부가로 원문의 gross PPE와 다름.')

add('free_cashflow_yield_fy','잉여현금흐름 수익률','cash_distribution',
    '(CFO - positive PPE purchases)/issue market cap',
    'CASE WHEN market_cap>0 AND fy_purchase_of_ppe>=0 THEN (fy_operating_cash_flow-fy_purchase_of_ppe)/market_cap END',
    ['market_cap','fy_operating_cash_flow','fy_purchase_of_ppe'],
    'https://doi.org/10.1111/j.1540-6261.1994.tb04772.x','Lakonishok, Shleifer and Vishny (1994); JKP fcf_me','academic',1,
    'JKP FCF/ME의 DART 유형자산 취득 현금유출 기반 구현. 무형자산 취득은 포함하지 않으며 전체 기업 CAPEX와 동일하지 않음.')
add('capex_growth_2fy','설비투자 증가율','capital_expenditure','PPE purchases FY / purchases FY-2 - 1',
    'CASE WHEN fy_purchase_of_ppe>=0 AND fy2_purchase_of_ppe>0 THEN fy_purchase_of_ppe/fy2_purchase_of_ppe-1 END',
    ['fy_purchase_of_ppe','fy2_purchase_of_ppe'],'https://doi.org/10.1111/j.1540-6261.2006.00833.x',
    'Anderson and Garcia-Feijoo (2006), Empirical Evidence on Capital Investment, Growth Options, and Security Returns','academic',-1,
    'JKP capx_gr2, 정확히 두 FY 전 취득 현금유출 비교. 기존 총자산 증가율과 별개. 1년/3년 변형은 별도 등록하지 않음.')
add('abnormal_capex_fy','매출 대비 비정상 설비투자','capital_expenditure',
    '(CAPX/SALE)t / mean((CAPX/SALE)t-1,t-2,t-3) - 1',
    'CASE WHEN fy_revenue>0 AND prev_fy_revenue>0 AND fy2_revenue>0 AND fy3_revenue>0 AND fy_purchase_of_ppe>=0 AND prev_fy_purchase_of_ppe>=0 AND fy2_purchase_of_ppe>=0 AND fy3_purchase_of_ppe>=0 AND (prev_fy_purchase_of_ppe/prev_fy_revenue+fy2_purchase_of_ppe/fy2_revenue+fy3_purchase_of_ppe/fy3_revenue)>0 THEN 3*(fy_purchase_of_ppe/fy_revenue)/(prev_fy_purchase_of_ppe/prev_fy_revenue+fy2_purchase_of_ppe/fy2_revenue+fy3_purchase_of_ppe/fy3_revenue)-1 END',
    [p+m for p in ['fy_','prev_fy_','fy2_','fy3_'] for m in ['revenue','purchase_of_ppe']],
    'https://doi.org/10.1017/S0022109000003173','Titman, Wei and Xie (2004), Capital Investments and Stock Returns','academic',-1,
    '정확한 FY 4개 필요. DART 유형자산 취득을 CAPEX로 한정한 한국형 측정.')
add('ppe_inventory_investment_fy','유형자산·재고 투자','investment_composition',
    'delta(PPE net book + inventory)/prior assets',
    'CASE WHEN prev_fy_total_assets>0 THEN (fy_property_plant_and_equipment+fy_inventories-prev_fy_property_plant_and_equipment-prev_fy_inventories)/prev_fy_total_assets END',
    ['fy_property_plant_and_equipment','fy_inventories','prev_fy_property_plant_and_equipment','prev_fy_inventories','prev_fy_total_assets'],
    'https://doi.org/10.1093/rfs/hhm058','Lyandres, Sun and Zhang (2008), The New Issues Puzzle: Testing the Investment-Based Explanation','academic',-1,
    '원형의 gross PPE 대신 DART 순장부 PPE를 사용한 명시적 적응. 기존 재고 단독 변화/총자산 성장과 산식이 다름.')
for key,name,left,right,sign in [
    ('sales_inventory_gap','매출과 재고의 기대 대비 차이','revenue','inventories',1),
    ('sales_receivables_gap','매출과 채권의 기대 대비 차이','revenue','trade_and_other_current_receivables',-1),
    ('gross_profit_sales_gap','매출총이익과 매출의 기대 대비 차이','gross_profit','revenue',1)]:
    cond=' AND '.join(f'(prev_fy_{m}+fy2_{m})>0' for m in [left,right])
    expr=f'2*fy_{left}/(prev_fy_{left}+fy2_{left})-2*fy_{right}/(prev_fy_{right}+fy2_{right})'
    add(key+'_fy',name,'fundamental_divergence',expr,f'CASE WHEN {cond} THEN {expr} END',
        [p+m for m in [left,right] for p in ['fy_','prev_fy_','fy2_']],
        'https://www.jstor.org/stable/248340','Abarbanell and Bushee (1998), Abnormal Returns to a Fundamental Analysis Strategy','academic',sign,
        'JKP CHG_TO_EXP는 최근 두 FY 평균에 대한 비율. 채권은 매출채권 단독이 아닌 DART 기타유동채권 포함. 원문/JKP에서 개별 신호 유의성이 모두 지지된 것은 아님.')
add('percent_accruals_fy','이익 대비 발생액','earnings_quality','(NI-CFO)/abs(NI)',
    'CASE WHEN abs(fy_net_income)>0 THEN (fy_net_income-fy_operating_cash_flow)/abs(fy_net_income) END',
    ['fy_net_income','fy_operating_cash_flow'],'https://doi.org/10.2308/accr.00000011',
    'Hafzalla, Lundholm and Van Winkle (2011), Percent Accruals','academic',-1,
    '이익의 현금전환 비율 질문. 총자산으로 나눈 기존 발생액과 경제적 관련성은 있지만 동일하거나 단조변환인 산식은 아님. NI=0은 결측.')
add('external_financing_fy','외부조달 현금흐름 강도','external_financing','financing cash flow / mean(current,prior total assets)',
    'CASE WHEN fy_total_assets>0 AND prev_fy_total_assets>0 THEN 2*fy_financing_cash_flow/(fy_total_assets+prev_fy_total_assets) END',
    ['fy_financing_cash_flow','fy_total_assets','prev_fy_total_assets'],
    'https://www.sciencedirect.com/science/article/abs/pii/S0165410106000371',
    'Bradshaw, Richardson and Sloan (2006), The relation between corporate financing activities, analysts forecasts and stock returns','academic',-1,
    'DART 재무활동 순현금흐름으로 정의. 발행액 단독 아님. 원문 금융현금흐름 분류와 IFRS 이자/배당 분류 차이 가능. Cohen-Lys(2006)의 발생액 통제 후 효과 약화라는 반대 근거를 보존.')

ROES=[f'{p}net_income/{p}total_equity' for p in ['fy_','prev_fy_','fy2_','fy3_','fy4_']]
roe_mean='('+ '+'.join(ROES)+')/5'
roe_var='('+ '+'.join(f'(({x})-({roe_mean}))*(({x})-({roe_mean}))' for x in ROES)+')/4'
add('earnings_stability_5fy','5개 FY 이익 안정성','earnings_stability','sample std(NI/positive equity), five consecutive FY',
    'CASE WHEN '+' AND '.join(f'{p}total_equity>0' for p in ['fy_','prev_fy_','fy2_','fy3_','fy4_'])+f' THEN sqrt({roe_var}) END',
    [p+m for p in ['fy_','prev_fy_','fy2_','fy3_','fy4_'] for m in ['net_income','total_equity']],
    QMJ,'Asness, Frazzini and Pedersen (2019), Quality minus junk, annual EVOL fallback','aqr',-1,
    '최종판 연간 ROE 변동성 fallback. 5개 연속 FY 모두 필요하며 분기 60개 원형을 재현했다고 하지 않음. 총자본 ROE 사용.')

prefixes=['fy_','prev_fy_','fy2_','fy3_','fy4_','fy5_']
ni_sum='('+ '+'.join(p+'net_income' for p in prefixes[:5])+')'
gp_sum='('+ '+'.join(p+'gross_profit' for p in prefixes[:5])+')'
add('net_payout_profit_5fy','5년 이익 대비 순지급','payout_policy','sum5(NI - delta equity)/sum5(GP)',
    f'CASE WHEN {gp_sum}>0 THEN ({ni_sum}-fy_total_equity+fy5_total_equity)/{gp_sum} END',
    [p+m for p in prefixes[:5] for m in ['net_income','gross_profit']]+['fy_total_equity','fy5_total_equity'],
    QMJ,'Asness, Frazzini and Pedersen (2019), Quality minus junk, alternative payout NPOP','aqr',1,
    '대체 payout 정의의 5년 합산. 순자본 변화에는 OCI·비지배지분이 섞일 수 있으므로 실제 배당/자사주 현금액으로 해석하지 않음. 첨부 Size/Quality 논의와 최종 QMJ 부록 연결.')

def definitions():
    result=[]
    for ref,s in SPECS.items():
        result.append(dict(id=ref,name_ko=s['name_ko'],family=s['family'],
            object_type='STOCK_CHARACTERISTIC',role='MEASUREMENT_CONTROL',alpha_approved=False,
            formula=s['formula'],orientation=s['orientation'],required_columns=s['columns'],
            lookback={'basis':'EXACT_AVAILABLE_FY_OR_DECLARED_DAILY_HISTORY','no_future_labels':True},
            sources=[{'title':s['title'],'url':s['primary'],'review_scope':'해당 정의/구성요소와 한국 구현 차이'},
                     {'title':'JKP official replication documentation, pinned commit','url':JKP_URL}],
            adaptation=s['adaptation'],evidence_tier='LITERATURE_MEASUREMENT_NOT_KOREAN_ALPHA',
            quota_bucket=s['quota_bucket'],readiness={'status':'IMPLEMENTED_REQUIRES_ATTESTATION','blockers':[]}))
    base.validate_catalog(result)
    return result

def input_digest(panel):
    frame=panel.reindex(sorted(panel.columns),axis=1)
    h=hashlib.sha256(json.dumps(list(frame),separators=(',',':')).encode())
    h.update(pd.util.hash_pandas_object(frame,index=False).to_numpy(dtype='uint64').tobytes())
    return h.hexdigest()

def implementation_hash():
    from engine import reference_multiyear_inputs
    return digest({Path(p).name:hashlib.sha256(Path(p).read_bytes()).hexdigest()
                   for p in [__file__,base.__file__,reference_multiyear_inputs.__file__]})

def financial_values(p):
    """Pandas oracle deliberately independent of SQL expressions above."""
    d=lambda n: p[n]
    ratio=lambda x,y:x/y.where(y>0)
    out={}
    for m in ['total_assets','total_equity','revenue','property_plant_and_equipment']:
        out['nonprice_size_'+m]=np.log(d('fy_'+m).where(d('fy_'+m)>0))
    cap=d('fy_purchase_of_ppe').where(d('fy_purchase_of_ppe')>=0)
    out['free_cashflow_yield_fy']=ratio(d('fy_operating_cash_flow')-cap,d('market_cap'))
    out['capex_growth_2fy']=ratio(cap,d('fy2_purchase_of_ppe'))-1
    history=pd.concat([ratio(d(pre+'purchase_of_ppe').where(d(pre+'purchase_of_ppe')>=0),d(pre+'revenue')) for pre in ['prev_fy_','fy2_','fy3_']],axis=1)
    out['abnormal_capex_fy']=ratio(ratio(cap,d('fy_revenue')),history.mean(axis=1,skipna=False))-1
    out['ppe_inventory_investment_fy']=ratio(d('fy_property_plant_and_equipment')+d('fy_inventories')-d('prev_fy_property_plant_and_equipment')-d('prev_fy_inventories'),d('prev_fy_total_assets'))
    expected=lambda m:ratio(d('fy_'+m),(d('prev_fy_'+m)+d('fy2_'+m))/2)
    for key,left,right in [('sales_inventory_gap','revenue','inventories'),('sales_receivables_gap','revenue','trade_and_other_current_receivables'),('gross_profit_sales_gap','gross_profit','revenue')]:
        out[key+'_fy']=expected(left)-expected(right)
    out['percent_accruals_fy']=ratio(d('fy_net_income')-d('fy_operating_cash_flow'),abs(d('fy_net_income')))
    out['external_financing_fy']=ratio(d('fy_financing_cash_flow'),(d('fy_total_assets')+d('prev_fy_total_assets'))/2).where((d('fy_total_assets')>0)&(d('prev_fy_total_assets')>0))
    roes=pd.concat([ratio(d(pre+'net_income'),d(pre+'total_equity')) for pre in prefixes[:5]],axis=1)
    out['earnings_stability_5fy']=roes.std(axis=1,ddof=1,skipna=False)
    net=pd.concat([d(pre+'net_income') for pre in prefixes[:5]],axis=1).sum(axis=1,skipna=False)-d('fy_total_equity')+d('fy5_total_equity')
    gross=pd.concat([d(pre+'gross_profit') for pre in prefixes[:5]],axis=1).sum(axis=1,skipna=False)
    out['net_payout_profit_5fy']=ratio(net,gross)
    return {'kr_'+k+'_v1':v.where(np.isfinite(v)) for k,v in out.items()}
