"""Exact-FY lags from the frozen filing ledger, never monthly-row lags."""
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from engine import reference_financial_inputs as source

METRICS = ('revenue','gross_profit','net_income','total_equity','total_assets',
           'purchase_of_ppe','inventories','trade_and_other_current_receivables')

def attach(current, capture, years=5):
    manifest = source.verify_capture(capture)
    out = current.copy().reset_index(drop=True)
    out.asset_id = out.asset_id.astype('int64')
    out.date = pd.to_datetime(out.date)
    for lag in range(2, years+1):
        for metric in METRICS:
            out[f'fy{lag}_{metric}'] = np.nan
    clocks = pd.to_datetime(out.financial_known_at, utc=True).copy()
    for item in manifest['files']:
        if not item['path'].endswith('.parquet'):
            continue
        subset = out.loc[out.asset_id.isin(item['asset_ids'])]
        if subset.empty:
            continue
        ledger = pd.read_parquet(Path(capture)/item['path'])
        bundles = defaultdict(list)
        for (asset, period, filing), group in ledger.groupby(['asset_id','period_end','filing_id'],sort=False):
            bundle = source._bundle(group.to_dict('records'))
            if bundle['available_at'] is None:
                raise ValueError('No clock on filing')
            bundles[int(asset)].append(bundle)
        for row in subset.itertuples():
            if row.financial_status != 'AVAILABLE' or pd.isna(row.fy_period_end):
                continue
            cutoff = (row.date+pd.Timedelta(days=1)).tz_localize('Asia/Seoul').tz_convert('UTC')-pd.Timedelta(nanoseconds=1)
            visible = [b for b in bundles[row.asset_id] if b['available_at']<=cutoff]
            for lag in range(2, years+1):
                end = row.fy_period_end-pd.DateOffset(years=lag)
                if row.fy_period_end.is_month_end:
                    end += pd.offsets.MonthEnd(0)
                candidates = [b for b in visible if b['period_end']==end]
                if not candidates:
                    continue
                b = max(candidates,key=lambda x:(x['available_at'],x['filing_id']))
                if b['reasons'] or b['fs_type']!=row.fy_fs_type or b['currency']!='KRW':
                    continue
                for metric in METRICS:
                    out.at[row.Index,f'fy{lag}_{metric}'] = b['values'].get(metric,np.nan)
                clocks.at[row.Index] = max(clocks.at[row.Index],b['available_at'])
        print(dict(multiyear_chunk=item['path'],asset_months=len(subset)),flush=True)
    out['multiyear_known_at'] = clocks
    return out, dict(source_manifest_sha256=manifest['manifest_sha256'],
        contract='EXACT_FY_END_LAGS_2_TO_5_LATEST_VISIBLE_FILING_SAME_SCOPE_KRW',
        first_vintage_verified=False,pit_status='PIT_ASSUMED',current_max_age_days=550)
