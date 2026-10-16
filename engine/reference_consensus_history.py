"""Fail-closed readiness gate for licensed historical consensus snapshots.

This is not a Gold factor and does not manufacture a history from FMP's
fiscal-target dates. A provider must supply actual dated consensus vintages.
"""
import re
import pandas as pd
import numpy as np

REQUIRED=frozenset({'asset_id','stock_code','snapshot_at','available_at','fiscal_period_end',
 'eps_mean','analyst_count','currency','provider_snapshot_id'})

def validate_history(frame,metadata):
 if not isinstance(frame,pd.DataFrame) or frame.empty or REQUIRED-set(frame):
  raise ValueError('Historical consensus needs snapshot_at AND fiscal_period_end; target years are not vintages')
 if metadata.get('snapshot_semantics')!='ACTUAL_PROVIDER_CONSENSUS_VINTAGE':raise ValueError('Undocumented snapshot semantics')
 if metadata.get('research_use_permitted') is not True:raise ValueError('Provider research permission required')
 if metadata.get('internal_storage_permitted') is not True:raise ValueError('Provider internal database storage permission required')
 if metadata.get('pit_status') not in ('PIT_VERIFIED','PIT_ASSUMED'):raise ValueError('Explicit vintage uncertainty required')
 p=frame.copy()
 if p[list(REQUIRED)].isna().any().any():raise ValueError('Missing consensus identity/value/time')
 if not p.stock_code.map(lambda x:isinstance(x,str) and re.fullmatch(r'[0-9A-Z]{6}',x) is not None).all():raise ValueError('Six-character uppercase ASCII stock identifiers required')
 if pd.api.types.is_bool_dtype(p.asset_id) or not pd.api.types.is_numeric_dtype(p.asset_id) or not np.isfinite(p.asset_id).all() or (p.asset_id<=0).any() or (p.asset_id!=np.floor(p.asset_id)).any():raise ValueError('Positive integer historical asset identity required')
 for col in ('snapshot_at','available_at'):
  if not p[col].map(lambda x:pd.Timestamp(x).tzinfo is not None).all():raise ValueError('Timezone-aware consensus timestamps required')
  p[col]=pd.to_datetime(p[col],utc=True)
 if (p.available_at<p.snapshot_at).any():raise ValueError('Available before source snapshot')
 p.fiscal_period_end=pd.to_datetime(p.fiscal_period_end)
 if p.fiscal_period_end.dt.tz is not None:raise ValueError('Fiscal target is a date, not retrieval timestamp')
 if not p.fiscal_period_end.eq(p.fiscal_period_end.dt.normalize()).all():raise ValueError('Fiscal target must be a calendar date')
 if not p.currency.eq('KRW').all():raise ValueError('Currency/unit bridge required')
 for col in ('eps_mean','analyst_count'):
  if pd.api.types.is_bool_dtype(p[col]) or not pd.api.types.is_numeric_dtype(p[col]) or not np.isfinite(p[col]).all():raise ValueError('Invalid numeric consensus fields')
 if (p.analyst_count<1).any() or (p.analyst_count!=np.floor(p.analyst_count)).any():raise ValueError('Invalid analyst count')
 if p.duplicated(['asset_id','snapshot_at','fiscal_period_end']).any() or p.provider_snapshot_id.duplicated().any():raise ValueError('Ambiguous consensus vintage')
 # This validates input semantics only. A historical issuer bridge, provider
 # license evidence and publication/SQL parity are still required for Gold.
 return p.sort_values(['asset_id','fiscal_period_end','snapshot_at']).reset_index(drop=True)

def observable_at(validated,decision_at):
 cutoff=pd.Timestamp(decision_at)
 if cutoff.tzinfo is None:raise ValueError('Timezone-aware decision timestamp required')
 eligible=validated.loc[(validated.available_at<=cutoff)&(validated.snapshot_at<=cutoff)]
 return eligible.sort_values('snapshot_at').drop_duplicates(['asset_id','fiscal_period_end'],keep='last').copy()
