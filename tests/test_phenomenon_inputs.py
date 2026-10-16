from copy import deepcopy
import hashlib
import json

import pytest

from engine import research_data_sources as d
from engine.phenomenon_inputs import import_discovery_snapshot,assert_source_bindings,load_source_rows
from engine.phenomenon_research import GraphStore
from scripts.phenomena import act

NOW='2030-10-02T12:00:00+09:00'  # Synthetic research clock, after live snapshot validation.
SCOPE=dict(universe='SYNTHETIC_DEMO',start='2020-01-01T00:00:00+09:00',end='2020-01-31T23:59:59+09:00')
ROLES=dict(x='FEATURE',y='OUTCOME')


def setup(tmp_path):
    rows=[dict(row_id=str(i),observation_date=day,observation_at=day+'T15:00:00+09:00',
               feature_known_at=day+'T16:00:00+09:00',decision_at=day+'T17:00:00+09:00',
               outcome_known_at='2020-02-28T16:00:00+09:00',x=float(i),y=float(i+1))
          for i,day in enumerate(['2020-01-01','2020-01-31'])]
    raw=json.dumps(rows).encode();path=tmp_path/'synthetic.json';path.write_bytes(raw)
    case=d.create_requirement(tmp_path/'discovery',dict(requirement_id='synthetic',question_id='question',
        research_question='synthetic contract',discriminates='measured vs absent',market='SYNTHETIC_DEMO',frequency='monthly',
        start_date='2020-01-01',end_date='2020-01-31',variables=['x','y'],known_at_column='feature_known_at'))
    d.register_source(case,dict(source_id='synthetic-source',title='Synthetic',url='https://example.com/synthetic',
        provenance_url='https://example.com/synthetic',format='json',pit_status='verified',pit_evidence='Synthetic fixture contract only',
        market='SYNTHETIC_DEMO',frequency='monthly',expected_sha256=hashlib.sha256(raw).hexdigest()))
    review=dict(reviewer='fixture-reviewer',authorization_reference='Unit test only',license_reference='Synthetic test fixture',
                public_download_permitted=True,research_use_permitted=True,pit_approved=True)
    d.review_source(case,'synthetic-source',review)
    capture=d.capture_local(case,'synthetic-source',path);snap=d.validate_artifact(case,capture['artifact_id'])
    graph=GraphStore(tmp_path/'graph',actors={'curator':['curator'],'researcher':['researcher']})
    return graph,case,snap,rows,review


def import_it(g,case,snap,**overrides):
    return import_discovery_snapshot(g,case,snap['snapshot_id'],scope=overrides.get('scope',SCOPE),
        field_roles=ROLES,origin='SYNTHETIC',stage='EXPLORATORY',actor='curator',known_at=NOW)


def test_discovery_to_graph_exact_rows_and_origins(tmp_path):
    g,case,snap,rows,_=setup(tmp_path);result=import_it(g,case,snap)
    projected=[{k:v for k,v in row.items() if k!='observation_date'} for row in rows]
    assert result['rows']==projected
    source=result['source'];assert source['payload']['origin']=='SYNTHETIC'
    assert assert_source_bindings(g)==[source['id']]
    assert load_source_rows(g,source['id'])==projected


def test_permission_revocation_after_import_blocks_use(tmp_path):
    g,case,snap,rows,review=setup(tmp_path);import_it(g,case,snap)
    d.review_source(case,'synthetic-source',{**review,'research_use_permitted':False})
    with pytest.raises(ValueError,match='revoked'):assert_source_bindings(g)


def test_scope_cannot_be_expanded_at_import(tmp_path):
    g,case,snap,*_=setup(tmp_path)
    with pytest.raises(ValueError,match='scope dates'):import_it(g,case,snap,scope={**SCOPE,'start':'2019-01-01T00:00:00+09:00'})


def test_tampered_raw_invalidates_downstream(tmp_path):
    g,case,snap,*_=setup(tmp_path);import_it(g,case,snap)
    path=case/'objects'/snap['artifact_sha256'];path.chmod(0o600);path.write_bytes(b'[]')
    with pytest.raises(ValueError,match='hash'):assert_source_bindings(g)


def test_broker_no_arbitrary_code_and_no_legacy_source_fallback(tmp_path):
    g,case,snap,*_=setup(tmp_path)
    with pytest.raises(ValueError,match='Unsupported'):act(g,dict(command='exec',code='print(1)'))
    q=act(g,dict(command='append',kind='question',payload=dict(title='Question',question='What is measured?'),
                actor='researcher',role='researcher',known_at=NOW))
    with pytest.raises(ValueError,match='trusted adapter'):load_source_rows(g,q['id'])


def test_synthetic_origin_cannot_be_claimed_observed(tmp_path):
    g,case,snap,*_=setup(tmp_path)
    with pytest.raises(ValueError,match='relabeled'):
        import_discovery_snapshot(g,case,snap['snapshot_id'],scope=SCOPE,field_roles=ROLES,
                                  origin='OBSERVED',stage='EXPLORATORY',actor='curator',known_at=NOW)


def test_source_import_cannot_be_backdated(tmp_path):
    g,case,snap,*_=setup(tmp_path)
    with pytest.raises(ValueError,match='predate'):
        import_discovery_snapshot(g,case,snap['snapshot_id'],scope=SCOPE,field_roles=ROLES,
                                  origin='SYNTHETIC',stage='EXPLORATORY',actor='curator',known_at='2020-10-02T12:00:00+09:00')


@pytest.mark.parametrize('field,value',[('pit_policy','PIT_ASSUMED'),('source_ref','https://wrong.example'),
                                      ('readiness','PENDING')])
def test_copied_binding_cannot_relabel_verified_source(tmp_path,field,value):
    g,case,snap,*_=setup(tmp_path);source=import_it(g,case,snap)['source']
    p={**source['payload'],field:value}
    g.append_node('source',p,actor='curator',role='curator',known_at=NOW)
    with pytest.raises(ValueError,match='binding'):assert_source_bindings(g)
