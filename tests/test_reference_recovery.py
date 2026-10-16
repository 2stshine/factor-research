import hashlib
import json
import pytest
from engine.reference_gold import PRICE_SQL
from scripts.recover_reference_build import recover


def review():
    return dict(reviewer='test',completed_session='explicit completed software capture',
                query_sha256=hashlib.sha256(PRICE_SQL.encode()).hexdigest(),asset_count=151,batch_size=150,
                start='2020-01-01',end='2020-01-31',complete_read_only_transaction=True,
                limitations=['Synthetic contract only'])


def test_recovery_partial_capture_rejected_before_db(tmp_path):
    chunks=tmp_path/'chunks';chunks.mkdir()
    path=tmp_path/'review.json';path.write_text(json.dumps(review()))
    with pytest.raises(ValueError,match='Partial'):recover(chunks,tmp_path/'out',review_path=path)


def test_recovery_different_query_rejected_before_db(tmp_path):
    chunks=tmp_path/'chunks';chunks.mkdir()
    path=tmp_path/'review.json';path.write_text(json.dumps({**review(),'query_sha256':'0'*64}))
    with pytest.raises(ValueError,match='query'):recover(chunks,tmp_path/'out',review_path=path)


def test_recovery_cannot_infer_operator_review(tmp_path):
    chunks=tmp_path/'chunks';chunks.mkdir()
    path=tmp_path/'review.json';path.write_text(json.dumps({**review(),'complete_read_only_transaction':False}))
    with pytest.raises(ValueError,match='review'):recover(chunks,tmp_path/'out',review_path=path)
