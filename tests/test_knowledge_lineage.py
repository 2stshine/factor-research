"""Synthetic schema/identity tests; no new or retroactively registered research."""
from copy import deepcopy
import hashlib
import json
import pytest

from engine.knowledge_lineage import validate_lineage, canonical_hash, VERSION, AUTHENTICATION


@pytest.fixture
def bundle():
    raw = 'Qualitative knowledge snapshot\n'.encode()
    review = {'general_lesson': 'Separate a measured proxy from its proposed mechanism.'}
    rid = 'campaign-synthetic/epoch-synthetic/source-lesson'
    record = {'record_id': rid, 'visibility': 'RELEASED_QUALITATIVE', 'review_status': 'REVIEWED_CURRENT',
              'review': review, 'provenance': {'authentication': AUTHENTICATION, 'packet_sha256': 'b'*64}}
    meta = {'schema_version': VERSION, 'knowledge_snapshot_hash': hashlib.sha256(raw).hexdigest(),
            'snapshot_captured_at': '2030-01-01T09:00:00+09:00', 'declared_at': '2030-01-01T09:01:00+09:00',
            'referenced_lesson_record_ids': [rid], 'lesson_references': [{'record_id': rid,
                'review_hash': canonical_hash(review), 'packet_sha256': 'b'*64, 'relation': 'DECLARED_QUALITATIVE_LESSON_USE'}]}
    return meta, raw, [record], '2030-01-01T09:02:00+09:00'


def validate(bundle):
    m, raw, records, cutoff = bundle
    return validate_lineage(m, raw, records, cutoff=cutoff)


def test_legacy_omission_is_not_recorded_and_does_not_read_inputs():
    result = validate_lineage(None, None, None, cutoff=None)
    assert result['status'] == 'NOT_RECORDED'
    assert not result['historical_backfill']


def test_valid_declaration_no_mutation_no_raw_evidence_output(bundle):
    before = deepcopy(bundle)
    bundle[2][0]['performance'] = {'oos_ic': 9.87654321}
    result = validate(bundle)
    assert result['status'] == 'VALID_DECLARATION_NOT_REGISTRATION'
    assert not result['independent_evidence'] and not result['follow_up_executed']
    assert 'oos_ic' not in json.dumps(result) and '9.87654321' not in json.dumps(result)
    assert 'general_lesson' not in json.dumps(result)
    assert bundle[0] == before[0] and bundle[1] == before[1]


@pytest.mark.parametrize('change,error', [
    ('snapshot','snapshot hash'), ('review','Review hash'), ('packet','packet hash'),
    ('duplicate','Unique'), ('mismatched_ids','match exactly'), ('pending','Pending'),
    ('stale','Pending'), ('authentication','Pending'), ('missing','absent'),
    ('relation','causality'), ('late','cutoff'), ('naive','timezone'),
    ('unknown_field','versioned'), ('numeric_payload','identity hashes'),
])
def test_malformed_or_stale_references_fail_closed(bundle,change,error):
    meta, raw, records, cutoff = bundle
    ref = meta['lesson_references'][0]
    if change == 'snapshot': raw += b'changed'
    elif change == 'review': records[0]['review']['general_lesson'] += ' changed'
    elif change == 'packet': ref['packet_sha256'] = 'c'*64
    elif change == 'duplicate': meta['referenced_lesson_record_ids'] *= 2
    elif change == 'mismatched_ids': meta['referenced_lesson_record_ids'] = []
    elif change == 'pending': records[0]['visibility'] = 'PENDING'
    elif change == 'stale': records[0]['review_status'] = 'STALE_OR_INVALID'
    elif change == 'authentication': records[0]['provenance']['authentication'] = 'SELF_ASSERTED'
    elif change == 'missing': records.clear()
    elif change == 'relation': ref['relation'] = 'FOLLOW_UP_EXECUTED'
    elif change == 'late': meta['declared_at'] = '2030-01-02T09:00:00+09:00'
    elif change == 'naive': meta['snapshot_captured_at'] = '2030-01-01'
    elif change == 'unknown_field': meta['oos_ic'] = .1
    elif change == 'numeric_payload': ref['follow_up'] = {'oos_return': .2}
    with pytest.raises(ValueError, match=error):
        validate_lineage(meta, raw, records, cutoff=cutoff)


def test_knowledge_snapshot_time_cannot_follow_declaration(bundle):
    bundle[0]['snapshot_captured_at'] = '2030-01-01T09:01:01+09:00'
    with pytest.raises(ValueError, match='cutoff'): validate(bundle)


def test_duplicate_authenticated_records_rejected(bundle):
    bundle[2].append(deepcopy(bundle[2][0]))
    with pytest.raises(ValueError, match='Duplicate'): validate(bundle)


def test_zero_references_explicit_but_not_independence(bundle):
    bundle[0]['referenced_lesson_record_ids'] = []
    bundle[0]['lesson_references'] = []
    result = validate(bundle)
    assert result['referenced_lesson_record_ids'] == [] and not result['independent_evidence']


def test_canonical_review_hash_matches_existing_contract():
    from engine.lesson_evidence import digest
    review = {'scope': '검토된 정성 범위', 'nested': {'b': 2, 'a': 1}}
    assert canonical_hash(review) == digest(review)


def test_cli_legacy_path_does_not_call_exporter(monkeypatch):
    from scripts.check_knowledge_lineage import check
    def no_export(*args): raise AssertionError('Legacy metadata must not trigger reads')
    monkeypatch.setattr('scripts.dashboard_exports.export_research_catalog.export', no_export)
    assert check(None, b'', None)['status'] == 'NOT_RECORDED'


def test_cli_reuses_current_authenticated_exporter_without_outputting_catalog(bundle,monkeypatch):
    from scripts.check_knowledge_lineage import check
    calls=[]
    def fake_export(root,as_of):
        calls.append((root,as_of))
        return {'records':bundle[2], 'secret_fixture':'never output this raw catalog'}
    monkeypatch.setattr('scripts.dashboard_exports.export_research_catalog.export',fake_export)
    result=check(bundle[0],bundle[1],bundle[3])
    assert len(calls)==1 and result['status']=='VALID_DECLARATION_NOT_REGISTRATION'
    assert 'secret_fixture' not in json.dumps(result)
