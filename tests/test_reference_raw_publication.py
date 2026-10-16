from copy import deepcopy
import numpy as np
import pandas as pd
import pytest
from engine import reference_gold as gold,reference_library as base,reference_daily_diversity as daily
from engine import reference_risk_catalog as risk
from engine.research_generation import digest

@pytest.mark.parametrize('library',[daily,risk])
def test_raw_source_requires_registered_definition_and_explicit_pit(library):
    a=dict(status='CERTIFIED',source_type=library.SOURCE_TYPE,source_contract=library.SOURCE_CONTRACT,
        pit_status='PIT_ASSUMED',first_vintage_independently_verified=False,scope='KRX_COMMON_STOCK',
        identity_contract='HISTORICAL_ASSET_ID',source_version='a'*64,evidence_sha256='a'*64)
    gold._validate_source_attestation(a)
    gold._validate_definition_source(a,library.definitions())
    d=deepcopy(library.definitions());d[0]['formula']='0'
    with pytest.raises(ValueError):gold._validate_definition_source(a,d)
    a['first_vintage_independently_verified']=True
    with pytest.raises(ValueError):gold._validate_source_attestation(a)

def test_numerical_full_raw_parity_has_strict_separate_contract():
    d=daily.definitions()[0]
    a=dict(status='CERTIFIED',source_type=daily.SOURCE_TYPE,source_contract=daily.SOURCE_CONTRACT,
        pit_status='PIT_ASSUMED',first_vintage_independently_verified=False,scope='KRX_COMMON_STOCK',
        identity_contract='HISTORICAL_ASSET_ID',source_version='a'*64,evidence_sha256='a'*64,input_sha256='b'*64)
    values=pd.DataFrame(dict(asset_id=['1'],stock_code=['005930'],date=pd.to_datetime(['2020-01-31']),
        known_at=pd.to_datetime(['2020-01-31T07:00Z']),market=['KOSPI'],reference_id=[d['id']],value=[1.],oriented_value=[1.],
        definition_hash=[base.definition_hash(d)],source_version=['a'*64],input_sha256=['b'*64]))
    rows=gold.canonical_values(values)
    p=dict(kind=daily.PARITY_KIND,passed=True,rtol=1e-7,atol=1e-8,rows_compared=1,values_sha256=digest(rows),
        oracle_sha256='c'*64,raw_input_sha256='b'*64,all_input_null_patterns_compared=True,
        comparison_scope='ALL_PUBLISHED_ASSET_MONTHS_TWO_RAW_DAILY_INTERPRETERS')
    v=dict(source_version='a'*64,input_sha256='b'*64,source_evidence_sha256='a'*64,implementation_sha256='d'*64,
        role='MEASUREMENT_CONTROL',alpha_approved=False,value_rows=1,references=[dict(reference_id=d['id'],definition_hash=base.definition_hash(d),value_rows=1,status='MEASUREMENT_VALIDATED')])
    pub,rows=gold.build_publication(values,[d],attestation=a,validation=v,parity=p)
    gold.validate_publication(pub,rows)
    for key,value in [('rows_compared',0),('raw_input_sha256','f'*64),('all_input_null_patterns_compared',False),('rtol',1e-4),('comparison_scope','SAMPLE_ONLY')]:
        changed=deepcopy(pub);changed['parity'][key]=value
        changed['dataset_id']=digest({k:v for k,v in changed.items() if k!='dataset_id'})
        with pytest.raises(ValueError):gold.validate_publication(changed,rows)

def test_edge_rejects_unfiltered_prepublication_definition():
    definition=next(d for d in risk.definitions() if d['id']=='kr_edge_spread_reference_v1')
    assert 'price-adjustment-factor change>1e-6' in definition['formula']
    old=deepcopy(definition)
    old['formula']=old['formula'].split('; exclude closed months')[0]
    with pytest.raises(ValueError):
        gold._validate_definition_source({'source_type':risk.SOURCE_TYPE},[old])
