"""Diverse literature measurements from exact price and as-of annual accounts.

This extension preserves v1's existing definitions and does not inspect market
outcomes, legacy signals, or historical research lessons. It computes one
definition at a time so a 16GB research host can publish bounded immutable sets.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from engine import reference_library as base,reference_price_expansion as price
from engine import reference_expansion_formulas as financial
from engine import reference_financial_inputs as financial_inputs
from engine.research_generation import digest

ROOT=Path(__file__).resolve().parents[1]
CATALOG_PATH=ROOT/'research/phenomena/reference-catalog-expansion-20261003.json'
SOURCE_TYPE='RDS_CERTIFIED_KRX_DART_FY_REFERENCE_V2'
SOURCE_CONTRACT='KRX_PRICE_AND_EXACT_DART_FY_ASOF_V2'
PIT_STATUS='PIT_ASSUMED_ACCEPTED_VINTAGE_NOT_FIRST_RELEASE_PROOF'
FINANCIAL_COLUMNS=tuple(sorted({c for spec in financial.FINANCIAL_FORMULAS.values() for c in spec[1:-1] if c!='market_cap'}))
FEATURE_CONTRACTS={**base.FEATURE_CONTRACTS,**price.FEATURE_CONTRACTS,
    **{c:'EXACT_KRW_DART_FY_ASOF_SAME_FILING_SCOPE_550D_MAX_AGE' for c in FINANCIAL_COLUMNS}}
FEATURE_UNITS={**base.FEATURE_UNITS,**price.FEATURE_UNITS,**{c:'KRW' for c in FINANCIAL_COLUMNS}}
FEATURE_COLUMNS=tuple(dict.fromkeys([*base.FEATURE_CONTRACTS,*base._COUNTS,*price.ADDITIONAL_COLUMNS,*FINANCIAL_COLUMNS]))
ALL_COLUMNS=(*base._BASE,*FEATURE_COLUMNS)


def make_catalog():
    literature=json.loads((ROOT/'research/phenomena/reference-expansion-literature.json').read_bytes())
    existing=[{k:v for k,v in d.items() if k!='definition_hash'} for d in base.load_catalog() if d['id'] in base._EXECUTABLE]
    definitions=list(existing)
    for ref in [*price.REFERENCE_SPECS,*financial.FINANCIAL_FORMULAS]:
        lit=literature['definitions'][ref]
        if ref in price.REFERENCE_SPECS:
            spec=price.REFERENCE_SPECS[ref]
            formula=spec['formula'];columns=spec['required_columns'];orientation=spec['orientation']
            lookback={'measurement_contract':formula}
        else:
            spec=financial.FINANCIAL_FORMULAS[ref]
            formula=financial.sql_expression(ref);columns=financial.required_columns(ref);orientation=spec[-1]
            lookback={'fiscal_basis':'LATEST_AVAILABLE_FY_SAME_FILING_SCOPE_CURRENCY',
                      'prior_fiscal_year_required':any(c.startswith('prev_fy_') for c in columns),
                      'maximum_statement_age_days':550}
        if lit['orientation']!=orientation:raise ValueError('Literature direction and implementation disagree')
        definitions.append({'id':ref,'name_ko':lit['name_ko'],'family':lit['family'],
            'object_type':'STOCK_CHARACTERISTIC','role':'MEASUREMENT_CONTROL','alpha_approved':False,
            'formula':formula,'orientation':orientation,'lookback':lookback,'required_columns':columns,
            'sources':lit['sources'],'adaptation':lit['adaptation'],'evidence_tier':lit['evidence_tier'],
            'orientation_rationale':lit['orientation_rationale'],
            'readiness':{'status':'IMPLEMENTED_REQUIRES_ATTESTATION','blockers':[]}})
    base.validate_catalog(definitions)
    return {'schema_version':base.LIBRARY_VERSION,'reviewed_at':'2026-10-03',
            'purpose':'Diverse reference measurements, not 45 independent or Korean profitable alphas',
            'selection_policy':'Primary literature plus predeclared source feasibility, never Korean future-return selection',
            'literature_sha256':hashlib.sha256((ROOT/'research/phenomena/reference-expansion-literature.json').read_bytes()).hexdigest(),
            'definitions':definitions}


def prepare(panel):
    if set(panel)!=set(ALL_COLUMNS) or not panel.columns.is_unique:
        raise ValueError('Exact v2 feature-only schema required; labels/unreviewed columns forbidden')
    # Reuse strict historical identity, market and month-end availability gates.
    identity=base._prepare(panel.loc[:,base._BASE])
    keyed=panel.copy();keyed['asset_id']=keyed.asset_id.astype(str)
    keyed['date']=pd.to_datetime(keyed.date)
    keyed=keyed.set_index(['asset_id','date'])
    result=identity.copy()
    keys=pd.MultiIndex.from_frame(result[['asset_id','date']])
    for column in FEATURE_COLUMNS:
        values=keyed[column].reindex(keys)
        if not pd.api.types.is_numeric_dtype(values) or pd.api.types.is_bool_dtype(values):
            raise ValueError(f'Numeric attested feature required: {column}')
        result[column]=values.to_numpy(dtype=float,na_value=np.nan)
    return result


def input_digest(panel):
    frame=prepare(panel).reindex(sorted(ALL_COLUMNS),axis=1)
    h=hashlib.sha256(json.dumps(list(frame),separators=(',',':')).encode())
    h.update(pd.util.hash_pandas_object(frame,index=False).to_numpy(dtype='uint64').tobytes())
    return h.hexdigest()


def implementation_hash():
    modules=[Path(__file__),Path(base.__file__),Path(price.__file__),Path(financial.__file__),Path(financial_inputs.__file__)]
    return digest({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in modules})


def validate_attestation(panel,attestation):
    if (attestation.get('status')!='CERTIFIED' or attestation.get('source_type')!=SOURCE_TYPE
        or attestation.get('source_contract')!=SOURCE_CONTRACT or attestation.get('pit_status')!=PIT_STATUS
        or attestation.get('first_vintage_independently_verified') is not False
        or attestation.get('scope')!=base.INPUT_SCOPE or attestation.get('identity_contract')!=base.IDENTITY_CONTRACT):
        raise ValueError('Explicit trusted v2 source and PIT limitations required')
    if attestation.get('feature_contracts')!=FEATURE_CONTRACTS or attestation.get('feature_units')!=FEATURE_UNITS:
        raise ValueError('Exact feature measurement contracts and units required')
    for key in ('input_sha256','source_version','evidence_sha256'):
        if not isinstance(attestation.get(key),str) or not re.fullmatch('[a-f0-9]{64}',attestation[key]):
            raise ValueError('Exact lowercase SHA256 source provenance required')
    actual=input_digest(panel)
    if actual!=attestation.get('input_sha256') or attestation.get('source_version')!=attestation.get('evidence_sha256'):
        raise ValueError('Expanded source snapshot hash mismatch')
    return actual


def calculate_one(panel,reference_id,*,attestation,validated=False):
    # validated is a caller optimization only; digest/provenance always checked
    # by the preparation/publisher boundary before any database writes.
    if not validated:validate_attestation(panel,attestation)
    definitions={d['id']:d for d in base.load_catalog(CATALOG_PATH)}
    if reference_id not in definitions:raise ValueError('Unknown expansion reference')
    definition=definitions[reference_id]
    frame=panel if validated else prepare(panel)
    if reference_id in base._EXECUTABLE:raw=base._calculate(frame,reference_id)
    elif reference_id in price.REFERENCE_SPECS:raw=price.calculate(frame,reference_id)
    else:raw=financial.calculate(frame,reference_id)
    raw=raw.where(np.isfinite(raw));valid=raw.notna()
    values=frame.loc[valid,list(base._BASE)].copy()
    values['reference_id']=reference_id;values['value']=raw.loc[valid]
    values['oriented_value']=raw.loc[valid]*definition['orientation']
    values['definition_hash']=definition['definition_hash']
    values['source_version']=attestation['source_version'];values['input_sha256']=attestation['input_sha256']
    values=values.loc[:,base._OUTPUT].sort_values(['reference_id','asset_id','date']).reset_index(drop=True)
    summary={'reference_id':reference_id,'definition_hash':definition['definition_hash'],
        'status':'MEASUREMENT_VALIDATED' if len(values) else 'NO_VALID_ROWS',
        'input_rows':len(frame),'value_rows':len(values),'missing_or_invalid_rows':int((~valid).sum()),
        'assets':int(values.asset_id.nunique()),'months':int(values.date.nunique()),
        'first_date':str(values.date.min().date()) if len(values) else None,
        'last_date':str(values.date.max().date()) if len(values) else None}
    depth=values.groupby('asset_id').date.nunique()
    summary.update(median_observed_months_per_asset=float(depth.median()) if len(depth) else None,
                   assets_with_60_observed_months=int(depth.ge(60).sum()),
                   assets_with_120_observed_months=int(depth.ge(120).sum()),
                   input_coverage_fraction=float(valid.mean()))
    summary['raw_value_diagnostics']={
        'quantiles':{str(q):float(values.value.quantile(q)) for q in (0,.01,.5,.99,1)} if len(values) else {},
        'negative_fraction':float(values.value.lt(0).mean()) if len(values) else None,
        'zero_fraction':float(values.value.eq(0).mean()) if len(values) else None,
        'policy':'DIAGNOSTICS_ONLY_NO_RETURN_BASED_SELECTION_OR_WINSORIZATION'}
    return values,summary
