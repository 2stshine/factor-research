from pathlib import Path
import json
import pandas as pd
import pytest
from scripts.audit_reference_flow_raw import aggregate
from scripts.audit_reference_new_information import pair,indexed,baseline
from scripts.archive_reference_new_information import prepare
from scripts.publish_reference_expansion import save_json,sha

def test_daily_reconstruction_uses_korean_calendar_cutoff_and_latest_revision():
 prices=pd.DataFrame(dict(asset_id=[1,1,1],trade_date=['2015-03-30','2015-03-31','2015-05-29']))
 def obs(day,quantity,revision):
  p=dict(frgn_shnu_vol=quantity,frgn_seln_vol=1,orgn_shnu_vol=2,orgn_seln_vol=1,frgn_ntby_qty=quantity-1,orgn_ntby_qty=1)
  return dict(asset_id=1,trade_date=day,kind='investor',payload=p,
   first_observed_at=pd.Timestamp('2026-01-01T00:00:00Z')+pd.Timedelta(seconds=revision),
   research_available_at=(pd.Timestamp(day)+pd.Timedelta(days=1,hours=8,minutes=30)).tz_localize('Asia/Seoul').tz_convert('UTC'),revision=revision)
 observations=pd.DataFrame([obs('2015-03-30',3,1),obs('2015-03-30',4,2),obs('2015-03-31',100,1),obs('2015-05-29',5,1)])
 actual=aggregate(prices,observations)
 march=actual.loc[actual.date.eq(pd.Timestamp('2015-03-31'))].iloc[0]
 may=actual.loc[actual.date.eq(pd.Timestamp('2015-05-31'))].iloc[0]
 assert march.expected_days==1 and march.fb==4
 assert may.expected_days==1 and may.fb==5 # Friday becomes available Saturday, before Sunday cutoff.

def test_duplicate_audit_detects_affine_equivalence_not_just_names():
 a=pd.Series(range(1001),dtype=float);b=a*4+3
 result=pair(a,b);assert result['affine_equivalent'] and not result['identical']
 assert pair(a,a)['identical']
 assert not pair(a,a*a)['affine_equivalent']
 assert pair(a.iloc[:2],b.iloc[:2])['checked'] is False

def test_bronze_archive_complete_enumerated_and_reproducible(tmp_path):
 source=tmp_path/'source';source.mkdir();save_json(source/'sample.json',dict(payload=[dict(value=3)]))
 save_json(source/'manifest.json',dict(status='COMPLETE',files=[dict(path='sample.json',sha256=sha(source/'sample.json'))]))
 (source/'.env').write_text('not part of explicit inventory')
 one=prepare(source,tmp_path/'one','test','reviewed-private-bucket')
 two=prepare(source,tmp_path/'two','test','reviewed-private-bucket')
 assert one['archive_sha256']==two['archive_sha256']
 assert {r['path'] for r in one['files']}=={'manifest.json','sample.json'}
 save_json(source/'other.json',dict(payload=[]))
 # Unlisted files cannot silently enter the archive.
 assert prepare(source,tmp_path/'one','test','reviewed-private-bucket')==one

def test_changed_or_partial_source_cannot_be_archived(tmp_path):
 source=tmp_path/'source';source.mkdir();save_json(source/'manifest.json',dict(status='INCOMPLETE',files=[]))
 with pytest.raises(ValueError,match='Complete'):prepare(source,tmp_path/'out','test','reviewed-private-bucket')

def test_additive_baseline_must_certify_exact_parent_and_all_datasets(tmp_path):
 program=dict(program_sha256='parent',reference_datasets=[dict(dataset_id='d')])
 evidence=dict(candidate_program_sha256='parent',live_database_verified=True,
  dataset_rows={'d':100},cache_file_sha256={'d':'hash'})
 save_json(tmp_path/'completion.json',evidence)
 prior,paths=baseline(program,'parent',tmp_path)
 assert paths['d']==tmp_path/'collection-cache/d.parquet'
 with pytest.raises(ValueError,match='parent changed'):baseline(program,'different',tmp_path)
 other=tmp_path/'different';other.mkdir()
 save_json(other/'completion.json',{**evidence,'candidate_program_sha256':'different'})
 with pytest.raises(ValueError,match='certify'):baseline(program,'parent',other)
 incomplete=tmp_path/'incomplete';incomplete.mkdir()
 save_json(incomplete/'completion.json',{**evidence,'cache_file_sha256':{}})
 with pytest.raises(ValueError,match='scope'):baseline(program,'parent',incomplete)

def test_additive_baseline_can_reuse_exact_previously_verified_cache_paths(tmp_path):
 p=tmp_path/'original/d.parquet'
 save_json(tmp_path/'completion.json',dict(candidate_program_sha256='parent',live_database_verified=True,
  dataset_rows={'d':100},cache_file_sha256={'d':'hash'},cache_paths={'d':str(p)}))
 _,paths=baseline(dict(program_sha256='parent',reference_datasets=[dict(dataset_id='d')]),'parent',tmp_path)
 assert paths['d']==p

def test_partial_employee_archive_is_explicit_and_never_gold_eligible(tmp_path):
 source=tmp_path/'source';source.mkdir()
 save_json(source/'sample.json',dict(payload=[]))
 save_json(source/'plan.json',dict(jobs=[1,2]))
 receipt='receipt-stopped.json'
 save_json(source/receipt,dict(status='INCOMPLETE',jobs=2,completed=1,
  plan_sha256=sha(source/'plan.json'),files=[dict(path='sample.json',sha256=sha(source/'sample.json'))]))
 out=prepare(source,tmp_path/'archive','dart-employee-checkpoint','private-bucket',checkpoint_receipt=receipt)
 assert out['source_status']=='INCOMPLETE' and out['gold_eligible'] is False
 assert out['completed_jobs']==1 and out['requested_jobs']==2
 assert 'manifest.json' not in {f['path'] for f in out['files']}
 with pytest.raises(ValueError,match='Explicit'):prepare(source,tmp_path/'invalid','dart-employees','private-bucket',checkpoint_receipt=receipt)
