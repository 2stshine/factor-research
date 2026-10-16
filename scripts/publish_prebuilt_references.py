"""Commit already dual-validated, immutable reference measurements, with readback."""
import argparse
from pathlib import Path
import pandas as pd
from engine.reference_db import connect
from engine import reference_gold as gold
from scripts.publish_reference_expansion import load_json,save_json,legacy_metadata_digest

def run(directory,apply=False,exclude=(),include=()):
    paths=sorted(Path(directory).glob('*/publication.json'))
    if not paths:raise ValueError('No verified builds')
    for path in paths:
        out=path.parent
        pub=load_json(path)
        if set(pub['definitions'])&set(exclude):continue
        if include and not set(pub['definitions'])<=set(include):continue
        values=pd.read_parquet(out/'values.parquet')
        rows=gold.canonical_values(values)
        gold.validate_publication(pub,rows)
        if (out/'committed-verification.json').exists():
            receipt=load_json(out/'receipt-applied.json')
            if receipt['dataset_id']!=pub['dataset_id'] or not receipt['outer_transaction_committed']:
                raise ValueError('Committed checkpoint mismatch')
            print(dict(resume='ALREADY_COMMITTED',dataset_id=pub['dataset_id']),flush=True)
            continue
        if apply and (out/'receipt-applied.json').exists():
            # A disconnect after commit must resume verification, not replace
            # an immutable PUBLISHED receipt with ALREADY_PUBLISHED metadata.
            receipt=load_json(out/'receipt-applied.json')
            if (receipt.get('dataset_id')!=pub['dataset_id'] or not receipt.get('outer_transaction_committed')
                or receipt.get('values_sha256')!=pub['values_sha256'] or receipt.get('readback_rows')!=len(rows)):
                raise ValueError('Unverified interrupted commit receipt')
            with connect() as conn:
                actual,metadata=gold.load_library(conn,dataset_id=pub['dataset_id'],snapshot_path=out/'values.parquet')
                if metadata!=pub or len(actual)!=len(rows):raise ValueError('Interrupted commit readback failed')
            save_json(out/'committed-verification.json',dict(passed=True,dataset_id=pub['dataset_id'],rows=len(rows),
                reference_ids=sorted(pub['definitions']),profitability_approved=False))
            print(dict(resume='POST_COMMIT_READBACK_VERIFIED',dataset_id=pub['dataset_id']),flush=True)
            continue
        with connect(read_only=False) as conn:
            legacy=legacy_metadata_digest(conn)
            receipt=gold.publish(conn,pub,rows,apply=apply)
            if legacy_metadata_digest(conn)!=legacy:raise ValueError('Legacy changed')
        receipt.update(outer_transaction_committed=apply,legacy_metadata_before=legacy,legacy_metadata_after=legacy)
        save_json(out/('receipt-applied.json' if apply else 'receipt-dry-run.json'),receipt)
        if apply:
            with connect() as conn:
                actual,metadata=gold.load_library(conn,dataset_id=pub['dataset_id'],snapshot_path=out/'values.parquet')
                if metadata!=pub or len(actual)!=len(rows):raise ValueError('Committed readback failed')
            save_json(out/'committed-verification.json',dict(passed=True,dataset_id=pub['dataset_id'],rows=len(rows),
                reference_ids=sorted(pub['definitions']),profitability_approved=False))
        print(receipt,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True);p.add_argument('--apply',action='store_true')
    p.add_argument('--exclude-reference',action='append',default=[])
    p.add_argument('--reference',action='append',default=[])
    a=p.parse_args();run(a.directory,a.apply,a.exclude_reference,a.reference)
