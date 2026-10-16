import base64
import io
import json
from pathlib import Path
import tarfile

import pytest

from scripts import archive_dart_historical_evidence as archive


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(archive.canonical(value))
    return archive.digest(path.read_bytes())


def evidence(tmp_path):
    raw, stage, identity = (tmp_path / name for name in ("raw", "stage", "identity"))
    plan_path = tmp_path / "corpus-plan.json"
    plan_sha = write(plan_path, {"schema_version":"synthetic-input", "issuers":[]})
    contract_sha = write(raw / "contract.json", {"schema_version":"dart-statement-corpus-v1","manifest_sha256":plan_sha})
    run_sha = write(raw / "runs/000001.json", {"status":"RAW_CORPUS_COMPLETE_PIT_UNVERIFIED"})
    write(raw / "attempts/000001/request.json", {"endpoint":"list.json", "params":{"corp_code":"00126380"}})
    write(raw / "attempts/000001/outcome.json", {"status":"VALID_RAW_RESPONSE"})
    write(raw / "attempts/000001/response.json", {"status":"013"})
    stage_sha = write(stage / "staged-revenue.json", {"schema_version":"dart-historical-revenue-staging-v1", "rows":[],
               "source_collection_finished":True,"all_planned_issuer_lists_complete":True,
               "source_contract_sha256":contract_sha,"source_run_sha256":run_sha})
    corpus_sha = write(stage / "corpus.json", {"schema_version":"dart-original-corpus-v1","all_planned_issuer_lists_complete":True})
    lineage_sha = write(stage / "lineage.json", {"schema_version":"dart-original-lineage-v1"})
    write(stage / "artifact-index.json", {"artifacts":{contract_sha:{},run_sha:{}}})
    identity_sha = write(identity / "identity.json", {"schema_version":"dart-historical-identity-v1","mappings":[]})
    write(identity / "listing.json", {"rows":[]})
    checked_path = tmp_path / "checked-manifest.json"
    write(checked_path, {"schema_version":"dart-revenue-checked-manifest-v1","stage_sha256":stage_sha,
                        "corpus_sha256":corpus_sha,"lineage_sha256":lineage_sha,"identity_sha256":identity_sha,
                        "approved_row_sha256":["a"*64],"review":{"decision":"ACCEPT"}})
    return raw,stage,identity,checked_path,plan_path


def frozen_plan(tmp_path, **kwargs):
    raw,stage,identity,checked,corpus_plan = evidence(tmp_path)
    result = archive.build_plan(raw,stage,identity,bucket="test-bronze-bucket",checked_manifest=checked,corpus_plan=corpus_plan,**kwargs)
    path = tmp_path / "archive-plan.json"
    write(path,result)
    return path,result


def packed(tmp_path):
    plan,_ = frozen_plan(tmp_path)
    directory=tmp_path / "packed"
    archive.prepare(plan,directory)
    return directory


class S3Error(Exception):
    def __init__(self,code,status):
        self.response={"Error":{"Code":code},"ResponseMetadata":{"HTTPStatusCode":status}}
        super().__init__("do not persist sdk secret exception")


class FakeS3:
    def __init__(self):
        self.objects={}
        self.calls=[]
        self.native_checksum=True
        self.fail=None
    def put_object(self,**kw):
        self.calls.append(("put",kw["Key"]))
        assert kw["IfNoneMatch"] == "*" and "ACL" not in kw
        if self.fail:
            raise S3Error(*self.fail)
        key=kw["Key"]
        if key in self.objects:
            raise S3Error("PreconditionFailed",412)
        body=kw["Body"].read()
        assert len(body)==kw["ContentLength"]
        assert base64.b64encode(bytes.fromhex(archive.digest(body))).decode()==kw["ChecksumSHA256"]
        self.objects[key]=body
        return {"ChecksumSHA256":kw["ChecksumSHA256"]}
    def head_object(self,**kw):
        self.calls.append(("head",kw["Key"]))
        body=self.objects[kw["Key"]]
        response={"ContentLength":len(body)}
        if self.native_checksum:
            response["ChecksumSHA256"]=base64.b64encode(bytes.fromhex(archive.digest(body))).decode()
        return response
    def get_object(self,**kw):
        self.calls.append(("get",kw["Key"]))
        return {"Body":io.BytesIO(self.objects[kw["Key"]])}


def test_exact_allowlist_excludes_env_keys_locks_and_unrelated_files(tmp_path):
    raw,stage,identity,checked,corpus_plan=evidence(tmp_path)
    (raw/".env").write_bytes(b"secret not archived")
    (raw/"api-key.txt").write_bytes(b"also not archived")
    (stage/"other-document.txt").write_bytes(b"unrelated")
    plan=archive.build_plan(raw,stage,identity,bucket="test-bronze-bucket",checked_manifest=checked,corpus_plan=corpus_plan)
    assert plan["executable"] and len(plan["bundle_id"])==64
    assert all(not any(part.startswith(".") for part in f["logical_path"].split("/")) for f in plan["files"])
    assert plan["excluded_non_allowlisted_file_counts"]=={"raw":2,"stage":1}
    assert plan["prefix"].startswith("financials/dart_historical_documents/bundle=")
    assert not plan["prefix"].startswith("bronze/")


def test_running_partial_and_missing_review_can_only_preview(tmp_path):
    raw,stage,identity,_,_=evidence(tmp_path)
    (raw/".corpus.lock").write_bytes(b"")
    with pytest.raises(archive.ArchiveError,match="PREREQUISITES"):
        archive.build_plan(raw,stage,identity,bucket="test-bronze-bucket")
    plan=archive.build_plan(raw,stage,identity,bucket="test-bronze-bucket",preview=True)
    assert not plan["executable"] and "SOURCE_COLLECTION_RUNNING" in plan["blockers"]
    assert "CHECKED_MANIFEST_NOT_PROVIDED" in plan["blockers"]
    path=tmp_path/"preview.json"
    write(path,plan)
    with pytest.raises(archive.ArchiveError,match="CANNOT_EXECUTE"):
        archive.prepare(path,tmp_path/"pack")


def test_missing_stage_dependency_blocks_final_plan(tmp_path):
    raw,stage,identity,checked,corpus_plan=evidence(tmp_path)
    write(stage/"artifact-index.json",{"artifacts":{"b"*64:{}}})
    with pytest.raises(archive.ArchiveError,match="PREREQUISITES"):
        archive.build_plan(raw,stage,identity,bucket="test-bronze-bucket",checked_manifest=checked,corpus_plan=corpus_plan)


def test_secret_field_request_rejected(tmp_path):
    raw,stage,identity,checked,corpus_plan=evidence(tmp_path)
    write(raw/"attempts/000001/request.json",{"params":{"crtfc_key":"never archive"}})
    with pytest.raises(archive.ArchiveError,match="SECRET_FIELD"):
        archive.build_plan(raw,stage,identity,bucket="test-bronze-bucket",checked_manifest=checked,corpus_plan=corpus_plan)


def test_literal_environment_secret_rejected_without_echo(tmp_path,monkeypatch):
    monkeypatch.setenv("DART_API_KEY","synthetic-secret-key-value")
    raw,stage,identity,checked,corpus_plan=evidence(tmp_path)
    (raw/"attempts/000001/response.json").write_bytes(b'{"text":"synthetic-secret-key-value"}')
    with pytest.raises(archive.ArchiveError,match="SECRET_VALUE") as err:
        archive.build_plan(raw,stage,identity,bucket="test-bronze-bucket",checked_manifest=checked,corpus_plan=corpus_plan)
    assert "synthetic-secret" not in str(err.value)


def test_deterministic_shards_preserve_all_member_bytes_without_extraction(tmp_path):
    plan_path,plan=frozen_plan(tmp_path)
    first=archive.prepare(plan_path,tmp_path/"pack1")
    second=archive.prepare(plan_path,tmp_path/"pack2")
    assert first==second
    assert first["s3_calls"]==0
    for shard in first["shards"]:
        assert (tmp_path/"pack1"/shard["name"]).read_bytes()==(tmp_path/"pack2"/shard["name"]).read_bytes()
        with tarfile.open(tmp_path/"pack1"/shard["name"]) as container:
            for member in container:
                item=next(f for f in plan["files"] if f["logical_path"]==member.name)
                assert archive.digest(container.extractfile(member).read())==item["sha256"]
                assert member.mtime==0 and not member.issym()


def test_changed_source_fails_before_any_pack_output(tmp_path):
    path,plan=frozen_plan(tmp_path)
    Path(plan["source_roots"]["raw"],"attempts/000001/response.json").write_bytes(b"changed")
    with pytest.raises(archive.ArchiveError,match="SOURCE_CHANGED_AFTER_PLAN"):
        archive.prepare(path,tmp_path/"pack")
    assert not (tmp_path/"pack").exists()


def test_dry_upload_never_touches_s3(tmp_path):
    directory=packed(tmp_path)
    s3=FakeS3()
    result=archive.upload(directory,client=s3)
    assert result["status"]=="DRY_RUN_NO_S3_CALLS" and s3.calls==[]


def test_new_objects_no_head_and_manifest_published_last(tmp_path):
    directory=packed(tmp_path)
    s3=FakeS3()
    result=archive.upload(directory,apply=True,client=s3,sleeper=lambda _:None)
    assert result["status"]=="ARCHIVED_HASH_VERIFIED"
    assert all(kind=="put" for kind,_ in s3.calls)
    assert s3.calls[-1][1].endswith("/manifest.json")
    assert len(s3.calls)==result["shard_count"]+1


def test_existing_equal_objects_use_native_sha_not_get(tmp_path):
    directory=packed(tmp_path)
    s3=FakeS3()
    archive.upload(directory,apply=True,client=s3,sleeper=lambda _:None)
    s3.calls=[]
    result=archive.upload(directory,apply=True,client=s3,sleeper=lambda _:None)
    assert result["status"]=="ARCHIVED_HASH_VERIFIED"
    assert not any(k=="get" for k,_ in s3.calls)
    assert all(o["status"]=="REUSED_HASH_VERIFIED" for o in result["objects"])


def test_existing_object_sha_mismatch_fails_without_overwrite(tmp_path):
    directory=packed(tmp_path)
    s3=FakeS3()
    prepared=json.loads((directory/"prepared.json").read_bytes())
    first=prepared["shards"][0]
    s3.objects[first["key"]]=b"x"*first["bytes"]
    result=archive.upload(directory,apply=True,client=s3,sleeper=lambda _:None)
    assert result["status"]=="ARCHIVE_INCOMPLETE"
    assert result["reason"]=="EXISTING_S3_OBJECT_SHA_MISMATCH"
    assert not any(k.endswith("/manifest.json") for _,k in s3.calls)
    assert s3.objects[first["key"]]==b"x"*first["bytes"]


def test_older_object_without_native_checksum_gets_one_actual_hash_check(tmp_path):
    directory=packed(tmp_path)
    s3=FakeS3()
    archive.upload(directory,apply=True,client=s3,sleeper=lambda _:None)
    s3.calls=[];s3.native_checksum=False
    result=archive.upload(directory,apply=True,client=s3,sleeper=lambda _:None)
    assert result["status"]=="ARCHIVED_HASH_VERIFIED"
    assert sum(k=="get" for k,_ in s3.calls)==result["shard_count"]+1


def test_transient_409_retried_but_auth_not_retried(tmp_path):
    directory=packed(tmp_path)
    s3=FakeS3();s3.fail=("AccessDenied",403)
    result=archive.upload(directory,apply=True,client=s3,sleeper=lambda _:None)
    assert result["status"]=="ARCHIVE_INCOMPLETE" and len(s3.calls)==1
    s3=FakeS3();original=s3.put_object;first=[True]
    def transient(**kwargs):
        if first.pop() if first else False:
            raise S3Error("ConditionalRequestConflict",409)
        return original(**kwargs)
    s3.put_object=transient
    result=archive.upload(directory,apply=True,client=s3,sleeper=lambda _:None)
    assert result["status"]=="ARCHIVED_HASH_VERIFIED"
    assert result["request_counts"]["put_object"]==result["shard_count"]+2


def test_pack_tampering_fails_before_s3_request(tmp_path):
    directory=packed(tmp_path)
    next(directory.glob("*.tar")).write_bytes(b"corrupt")
    s3=FakeS3()
    with pytest.raises(archive.ArchiveError,match="SHA_MISMATCH"):
        archive.upload(directory,apply=True,client=s3)
    assert s3.calls==[]


def test_missing_shard_rejected_even_if_manifest_checksum_updated(tmp_path):
    directory=packed(tmp_path)
    prepared=json.loads((directory/"prepared.json").read_bytes())
    remote=json.loads((directory/"manifest.json").read_bytes())
    prepared["shards"]=remote["shards"]=[]
    prepared["manifest_sha256"]=write(directory/"manifest.json",remote)
    prepared["manifest_bytes"]=(directory/"manifest.json").stat().st_size
    write(directory/"prepared.json",prepared)
    s3=FakeS3()
    with pytest.raises(archive.ArchiveError,match="MEMBER_INVENTORY"):
        archive.upload(directory,apply=True,client=s3)
    assert s3.calls==[]


def test_symlink_source_not_archived(tmp_path):
    raw,stage,identity,checked,corpus_plan=evidence(tmp_path)
    target=raw/"attempts/000001/response.json"
    target.unlink();target.symlink_to(checked)
    with pytest.raises(archive.ArchiveError,match="UNSAFE"):
        archive.build_plan(raw,stage,identity,bucket="test-bronze-bucket",checked_manifest=checked,corpus_plan=corpus_plan)


def test_immutable_local_plan_never_overwritten(tmp_path):
    path=tmp_path/"plan.json"
    archive.immutable_write(path,b"one")
    archive.immutable_write(path,b"one")
    with pytest.raises(archive.ArchiveError,match="IMMUTABLE"):
        archive.immutable_write(path,b"two")
    assert path.read_bytes()==b"one"
