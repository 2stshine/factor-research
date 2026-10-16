from contextlib import nullcontext
import json
import pandas as pd
import pytest
from scripts import publish_prebuilt_references as p
from scripts.publish_reference_expansion import save_json

def fixture_files(tmp_path):
    out=tmp_path/'one';out.mkdir()
    pub=dict(dataset_id='a'*64,values_sha256='b'*64,definitions={'reference_one':{}},row_count=1)
    receipt=dict(dataset_id='a'*64,values_sha256='b'*64,outer_transaction_committed=True,
                 readback_rows=1,status='PUBLISHED')
    save_json(out/'publication.json',pub);save_json(out/'receipt-applied.json',receipt)
    pd.DataFrame({'value':[1.]}).to_parquet(out/'values.parquet')
    return out,pub,receipt

def test_post_commit_resume_preserves_receipt_and_never_republishes(tmp_path,monkeypatch):
    out,pub,receipt=fixture_files(tmp_path)
    before=(out/'receipt-applied.json').read_bytes()
    monkeypatch.setattr(p.gold,'canonical_values',lambda x:[{'value':1.}])
    monkeypatch.setattr(p.gold,'validate_publication',lambda *a:None)
    monkeypatch.setattr(p,'connect',lambda **kw:nullcontext(object()))
    monkeypatch.setattr(p.gold,'load_library',lambda *a,**k:(pd.DataFrame({'value':[1.]}),pub))
    monkeypatch.setattr(p.gold,'publish',lambda *a,**k:pytest.fail('Must not republish a committed receipt'))
    p.run(tmp_path,apply=True)
    assert (out/'receipt-applied.json').read_bytes()==before
    assert json.loads((out/'committed-verification.json').read_text())['passed'] is True

def test_excluded_unpublished_definition_never_reaches_values_or_database(tmp_path,monkeypatch):
    out=tmp_path/'excluded';out.mkdir()
    save_json(out/'publication.json',dict(definitions={'old_edge':{}}))
    monkeypatch.setattr(p,'connect',lambda **kw:pytest.fail('No database access for excluded candidate'))
    p.run(tmp_path,apply=True,exclude=['old_edge'])
