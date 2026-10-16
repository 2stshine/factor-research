"""Reviewed handoff of a COMPLETED extraction that failed input validation.

Never auto-resume arbitrary partial chunks. The caller must explicitly attest
that all declared batches completed in one authenticated read-only transaction,
binding the actual executed SQL, exact file list/hashes and source period.
This is a trusted operator recovery boundary, not proof from filenames alone.
No Gold writes occur here. Normal publish re-calculates and independently checks
SQL parity before a separately explicit --apply.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

from engine import reference_gold as g,reference_library as lib,silver
from engine.research_generation import canonical,digest,_immutable


def recover(chunks,output,*,review_path):
    chunks=Path(chunks);output=Path(output);review=json.loads(Path(review_path).read_bytes())
    required={'reviewer','completed_session','query_sha256','asset_count','batch_size','start','end','complete_read_only_transaction','limitations'}
    if set(review)!=required or review['complete_read_only_transaction'] is not True or not review['reviewer'] or not review['completed_session']:
        raise ValueError('Explicit complete-extraction operator review required')
    if review['query_sha256']!=hashlib.sha256(g.PRICE_SQL.encode()).hexdigest() or review['batch_size']!=150:
        raise ValueError('Reviewed query/batch protocol differs')
    paths=sorted(chunks.glob('*.parquet'))
    expected=[f'price-{n:06d}.parquet' for n in range(0,review['asset_count'],150)]
    if [p.name for p in paths]!=expected:raise ValueError('Partial/unexpected extraction checkpoints')
    with silver.connect() as conn:
        assets=silver.read_frame(conn,"SELECT asset_id FROM public.asset WHERE exchange='KRX' AND asset_type='stock' AND instrument_type='common_stock' ORDER BY asset_id").asset_id.tolist()
        identity=silver.read_frame(conn,"SELECT asset_id,name,instrument_type FROM public.asset WHERE exchange='KRX' AND asset_type='stock' AND instrument_type='common_stock' ORDER BY asset_id")
    if len(assets)!=review['asset_count']:raise ValueError('Asset enumeration changed; fresh extraction required')
    frames=[];files=[]
    for offset,path in zip(range(0,len(assets),150),paths,strict=True):
        frame=pd.read_parquet(path)
        if not set(frame.asset_id.astype(int))<=set(assets[offset:offset+150]):raise ValueError('Chunk does not belong to declared asset batch')
        if not frame.empty:
            dates=pd.to_datetime(frame.trade_date)
            if dates.min()<pd.Timestamp(review['start']) or dates.max()>pd.Timestamp(review['end']):raise ValueError('Chunk outside declared period')
        frames.append(frame);files.append(dict(name=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(frame)))
    panel,evidence=g.normalize_price_frame(pd.concat(frames,ignore_index=True),start=review['start'],safe_end=review['end'],assets=assets)
    evidence.update(recovery_review=review,checkpoint_files=files,recovered_at=datetime.now(timezone.utc).isoformat(),
                    source_latest_observation=None,source_latest_observation_not_reconstructed=True)
    if output.exists():raise ValueError('Fresh recovery output directory required')
    output.mkdir(parents=True)
    _immutable(output/'source-evidence.json',canonical(evidence)+b'\n')
    identity.to_parquet(output/'current-identity-review.parquet',index=False)
    panel.to_parquet(output/'input.parquet',index=False)
    att=dict(status='CERTIFIED',source_type=evidence['source_type'],source_version=digest(evidence),
             source_contract='CERTIFIED_KRX_FEATURE_ONLY_MONTHLY_V1',evidence_sha256=digest(evidence),
             input_sha256=lib.input_panel_digest(panel),identity_contract=lib.IDENTITY_CONTRACT,
             scope=lib.INPUT_SCOPE,units=lib.FEATURE_UNITS,feature_contracts=lib.FEATURE_CONTRACTS)
    _immutable(output/'input-attestation.json',canonical(att)+b'\n')
    result=lib.calculate_reference_panel(panel,input_attestation=att)
    result.values.to_parquet(output/'values.parquet',index=False)
    _immutable(output/'validation.json',canonical(result.validation)+b'\n')
    _immutable(output/'blocked.json',canonical(result.blocked)+b'\n')
    report=dict(status='RECOVERED_INPUT_REQUIRES_PARITY_BEFORE_GOLD',monthly_rows=len(panel),assets=int(panel.asset_id.nunique()),
                value_rows=len(result.values),quarantine=evidence['identity_quarantine'],reference_count=len(result.validation['references']),
                blocked_count=len(result.blocked),database_writes=False,output=str(output))
    _immutable(output/'recovery-receipt.json',canonical(report)+b'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--chunks',required=True);p.add_argument('--output',required=True);p.add_argument('--review',required=True)
    a=p.parse_args();print(json.dumps(recover(a.chunks,a.output,review_path=a.review),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
