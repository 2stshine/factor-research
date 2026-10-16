"""Immutable internal Bronze archive of an explicitly reviewed DART bundle.

Three separate stages: plan (SHA/size inventory), pack (deterministic TAR
shards, no network), upload (--apply required). Source ZIPs remain intact.
The Bronze bucket is itself the layer: no extra bronze/ prefix is inserted.
AWS uses the existing default credential chain or an explicit profile only.
This module never contacts DART, modifies the source, extracts an archive,
creates a bucket, sets a public ACL, or writes RDS/Gold/certification records.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import time


SCHEMA = "dart-historical-evidence-archive-v1"
PREFIX = "financials/dart_historical_documents"
SHARD_TARGET = 128 * 1024 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024 * 1024
ALLOWED = {
    "raw": re.compile(r"(?:contract\.json|runs/[0-9]{6}\.json|objects/[0-9a-f]{64}\.json|attempts/[0-9]{6}/(?:request\.json|outcome\.json|response\.(?:json|zip|html)))"),
    "stage": re.compile(r"(?:(?:staged-revenue|corpus|lineage|artifact-index|bundle|review)\.json|source/[0-9a-f]{64}-[A-Za-z0-9_-]+\.py)"),
    "identity": re.compile(r"(?:identity|fy-reference|fy-reference-scoped|listing|listing-source)\.json"),
}
SECRET_FIELDS = {"crtfc_key", "api_key", "access_key_id", "aws_access_key_id", "secret_access_key", "aws_secret_access_key", "aws_session_token", "password"}


class ArchiveError(RuntimeError):
    """Fixed diagnostics; never include credential values or SDK exception text."""


def require(condition, reason):
    if not condition:
        raise ArchiveError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def safe_file(path):
    path = Path(path).absolute()
    require(path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents), "MISSING_OR_UNSAFE_SOURCE_FILE")
    require(path.stat().st_size <= MAX_FILE_BYTES, "SOURCE_FILE_TOO_LARGE")
    return path


def read_json(path):
    try:
        value = json.loads(safe_file(path).read_bytes())
    except (OSError, ValueError):
        raise ArchiveError("INVALID_SOURCE_JSON") from None
    require(isinstance(value, dict), "INVALID_SOURCE_JSON_SHAPE")
    return value


def _known_secrets():
    # Do not discover credentials or inspect dotenv/key files. If the caller
    # already exposed a secret in this process, reject a literal leaked value.
    return [value.encode() for name in ("DART_API_KEY", "FMP_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
            if (value := os.environ.get(name)) and len(value) >= 8]


def file_digest(path):
    path = safe_file(path)
    hasher, total, tail = hashlib.sha256(), 0, b""
    secrets = _known_secrets()
    overlap = max(map(len, secrets), default=1) - 1
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            require(not any(secret in tail + block for secret in secrets), "SECRET_VALUE_DETECTED_IN_SOURCE")
            hasher.update(block)
            total += len(block)
            tail = (tail + block)[-overlap:] if overlap else b""
    require(total == path.stat().st_size, "SOURCE_CHANGED_DURING_HASHING")
    return hasher.hexdigest(), total


def immutable_write(path, body):
    path = Path(path)
    require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), "UNSAFE_OUTPUT_PATH")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == body, "IMMUTABLE_OUTPUT_CONFLICT")
        return
    with path.open("xb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())


def source_roots(raw, stage, identity):
    roots = {name: Path(value).absolute() for name, value in (("raw", raw), ("stage", stage), ("identity", identity))}
    for role, path in roots.items():
        require(path.is_dir() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents), "UNSAFE_SOURCE_ROOT")
        require(path != Path(path.anchor) and path.parent != Path(path.anchor), "OVERBROAD_SOURCE_ROOT")
        # Prevent accidentally scanning a home/workspace rather than a corpus.
        required = {"raw": "contract.json", "stage": "staged-revenue.json", "identity": "identity.json"}[role]
        require((path / required).is_file(), "SOURCE_ROOT_NOT_EXPECTED_EVIDENCE_NAMESPACE")
    require(len({str(p) for p in roots.values()}) == 3, "SOURCE_ROOTS_MUST_BE_DISTINCT")
    return roots


def _reject_secret_fields(value):
    if isinstance(value, dict):
        require(not (set(map(str.lower, map(str, value))) & SECRET_FIELDS), "SECRET_FIELD_IN_REQUEST_OR_REVIEW")
        for child in value.values():
            _reject_secret_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secret_fields(child)


def inventory(roots):
    files, excluded = [], Counter()
    for role, root in roots.items():
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if not path.is_file() and not path.is_symlink():
                continue
            # No hidden files, locks, dotenv/credentials, arbitrary attachments,
            # shell history or workspace traversal can enter this allowlist.
            if ALLOWED[role].fullmatch(relative) is None:
                excluded[role] += 1
                continue
            sha, size = file_digest(path)
            if relative.endswith("request.json"):
                _reject_secret_fields(read_json(path))
            files.append({"logical_path": role + "/" + relative, "source_role": role,
                          "relative_path": relative, "sha256": sha, "bytes": size})
    require(sum(f["bytes"] for f in files) <= MAX_TOTAL_BYTES, "ARCHIVE_TOTAL_SIZE_LIMIT")
    return sorted(files, key=lambda f: f["logical_path"]), dict(excluded)


def build_plan(raw, stage, identity, *, bucket=None, checked_manifest=None, corpus_plan=None, preview=False):
    roots = source_roots(raw, stage, identity)
    bucket = bucket or os.environ.get("S3_BRONZE_BUCKET")
    require(isinstance(bucket, str) and re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket), "S3_BRONZE_BUCKET_REQUIRED")
    files, excluded = inventory(roots)
    by_path = {f["logical_path"]: f for f in files}
    blockers = []
    if (roots["raw"] / ".corpus.lock").exists():
        blockers.append("SOURCE_COLLECTION_RUNNING")
    stage_data = read_json(roots["stage"] / "staged-revenue.json")
    corpus = read_json(roots["stage"] / "corpus.json")
    contract = read_json(roots["raw"] / "contract.json")
    identity_data = read_json(roots["identity"] / "identity.json")
    require(stage_data.get("schema_version") == "dart-historical-revenue-staging-v1"
            and corpus.get("schema_version") == "dart-original-corpus-v1"
            and identity_data.get("schema_version") == "dart-historical-identity-v1", "UNEXPECTED_EVIDENCE_SCHEMA")
    if not (stage_data.get("source_collection_finished") is True
            and stage_data.get("all_planned_issuer_lists_complete") is True
            and corpus.get("all_planned_issuer_lists_complete") is True):
        blockers.append("STAGING_IS_NOT_COMPLETE_SOURCE_SNAPSHOT")
    require(stage_data.get("source_contract_sha256") == by_path["raw/contract.json"]["sha256"], "STAGE_RAW_CONTRACT_MISMATCH")
    source_run = stage_data.get("source_run_sha256")
    if not source_run or not any(f["sha256"] == source_run and f["logical_path"].startswith("raw/runs/") for f in files):
        blockers.append("BOUND_COMPLETION_RUN_MISSING")
    # Every explicitly indexed staging dependency must be in the archive. Final
    # stage bundles snapshot implementation files instead of mutable repo paths.
    index = read_json(roots["stage"] / "artifact-index.json")
    inventory_shas = {f["sha256"] for f in files}
    missing_dependencies = sorted(set(index.get("artifacts", {})) - inventory_shas)
    if missing_dependencies:
        blockers.append("STAGE_DEPENDENCIES_NOT_IN_EXACT_ALLOWLIST")
    review_files = {}
    if checked_manifest:
        path = safe_file(checked_manifest)
        checked = read_json(path)
        _reject_secret_fields(checked)
        require(checked.get("schema_version") == "dart-revenue-checked-manifest-v1", "WRONG_CHECKED_MANIFEST_SCHEMA")
        for key, logical in (("stage_sha256", "stage/staged-revenue.json"), ("corpus_sha256", "stage/corpus.json"),
                             ("lineage_sha256", "stage/lineage.json"), ("identity_sha256", "identity/identity.json")):
            require(checked.get(key) == by_path[logical]["sha256"], "CHECKED_MANIFEST_ARTIFACT_MISMATCH")
        if checked.get("review", {}).get("decision") != "ACCEPT" or not checked.get("approved_row_sha256"):
            blockers.append("INDEPENDENT_SOURCE_REVIEW_NOT_ACCEPTED")
        sha, size = file_digest(path)
        review_files["checked-manifest.json"] = str(path)
        files.append({"logical_path": "review/checked-manifest.json", "source_role": "review", "relative_path": "checked-manifest.json",
                      "sha256": sha, "bytes": size})
    else:
        blockers.append("CHECKED_MANIFEST_NOT_PROVIDED")
    if corpus_plan:
        path = safe_file(corpus_plan)
        sha, size = file_digest(path)
        require(sha == contract.get("manifest_sha256"), "ORIGINAL_CORPUS_PLAN_SHA_MISMATCH")
        review_files["corpus-plan.json"] = str(path)
        files.append({"logical_path": "review/corpus-plan.json", "source_role": "review", "relative_path": "corpus-plan.json",
                      "sha256": sha, "bytes": size})
    else:
        blockers.append("ORIGINAL_CORPUS_PLAN_NOT_PROVIDED")
    require(preview or not blockers, "FINAL_ARCHIVE_PREREQUISITES_NOT_MET")
    files.sort(key=lambda f: f["logical_path"])
    require(sum(f["bytes"] for f in files) <= MAX_TOTAL_BYTES, "ARCHIVE_TOTAL_SIZE_LIMIT")
    frozen = {"schema_version": SCHEMA, "files": [{k: f[k] for k in ("logical_path", "sha256", "bytes")} for f in files],
              "archive_format": "deterministic-uncompressed-posix-tar-shards-v1", "target_shard_bytes": SHARD_TARGET,
              "source_only_archive_does_not_certify_or_publish": True}
    bundle_id = digest(canonical(frozen))
    return {"schema_version": "dart-historical-archive-plan-v1", "bundle_id": bundle_id,
            "bucket": bucket, "prefix": PREFIX + "/bundle=" + bundle_id,
            "source_roots": {k: str(v) for k,v in roots.items()}, "review_files": review_files,
            "files": files, "frozen_inventory": frozen, "executable": not blockers and not preview,
            "preview_only": preview, "blockers": blockers, "missing_dependency_sha256": missing_dependencies,
            "excluded_non_allowlisted_file_counts": excluded, "file_count": len(files),
            "total_source_bytes": sum(f["bytes"] for f in files), "source_api_calls": 0,
            "s3_calls": 0, "rds_writes": False, "gold_writes": False}


def source_file(plan, item):
    require(item["logical_path"] == item["source_role"] + "/" + item["relative_path"], "LOGICAL_ARCHIVE_PATH_MISMATCH")
    if item["source_role"] == "review":
        require(item["relative_path"] in {"checked-manifest.json", "corpus-plan.json"}, "UNALLOWLISTED_REVIEW_ARTIFACT")
        return safe_file(plan["review_files"][item["relative_path"]])
    role = item["source_role"]
    require(role in ALLOWED and ALLOWED[role].fullmatch(item["relative_path"]), "UNALLOWLISTED_PLAN_SOURCE")
    return safe_file(Path(plan["source_roots"][role]) / item["relative_path"])


def validate_plan(plan):
    require(plan.get("schema_version") == "dart-historical-archive-plan-v1" and plan.get("executable") is True
            and not plan.get("preview_only") and not plan.get("blockers"), "PREVIEW_OR_INCOMPLETE_PLAN_CANNOT_EXECUTE")
    require(digest(canonical(plan["frozen_inventory"])) == plan["bundle_id"], "FROZEN_INVENTORY_SHA_MISMATCH")
    require(plan["prefix"] == PREFIX + "/bundle=" + plan["bundle_id"], "UNSAFE_ARCHIVE_PREFIX")
    projected = [{k:f[k] for k in ("logical_path", "sha256", "bytes")} for f in plan["files"]]
    require(projected == plan["frozen_inventory"]["files"], "PLAN_FILE_INVENTORY_CHANGED")
    require(len({f["logical_path"] for f in plan["files"]}) == len(plan["files"]), "DUPLICATE_ARCHIVE_MEMBER")
    require(not (Path(plan["source_roots"]["raw"]) / ".corpus.lock").exists(), "SOURCE_COLLECTION_RUNNING")


def _shard_groups(files):
    group, size = [], 10_240
    for item in files:
        needed = 512 + ((item["bytes"] + 511) // 512) * 512
        if group and size + needed > SHARD_TARGET:
            yield group
            group, size = [], 10_240
        group.append(item)
        size += needed
    if group:
        yield group


class VerifyingReader:
    def __init__(self, handle):
        self.handle, self.hash, self.count = handle, hashlib.sha256(), 0
    def read(self, count=-1):
        data = self.handle.read(count)
        self.hash.update(data)
        self.count += len(data)
        return data


def prepare(plan_path, output):
    plan = read_json(plan_path)
    validate_plan(plan)
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "PREPARED_NAMESPACE_MUST_BE_NEW_AND_SAFE")
    # Verify the entire frozen inventory before creating any archive shard.
    for item in plan["files"]:
        sha, size = file_digest(source_file(plan, item))
        require((sha, size) == (item["sha256"], item["bytes"]), "SOURCE_CHANGED_AFTER_PLAN")
    output.mkdir(parents=True)
    immutable_write(output / "frozen-plan.json", canonical(plan))
    shards = []
    for number, group in enumerate(_shard_groups(plan["files"]), 1):
        name = f"part-{number:05d}.tar"
        path = output / name
        with path.open("xb") as stream:
            with tarfile.open(fileobj=stream, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for item in group:
                    source = source_file(plan, item)
                    info = tarfile.TarInfo(item["logical_path"])
                    info.size, info.mtime, info.mode = item["bytes"], 0, 0o444
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with source.open("rb") as handle:
                        verifying = VerifyingReader(handle)
                        archive.addfile(info, verifying)
                        require(verifying.count == item["bytes"] and verifying.hash.hexdigest() == item["sha256"], "SOURCE_CHANGED_DURING_PACKING")
                    require(source.stat().st_size == item["bytes"], "SOURCE_CHANGED_DURING_PACKING")
            stream.flush()
            os.fsync(stream.fileno())
        sha, size = file_digest(path)
        require(size < 5 * 1024**3, "SHARD_EXCEEDS_SINGLE_PUT_LIMIT")
        shards.append({"name": name, "sha256": sha, "bytes": size,
                       "key": plan["prefix"] + "/shards/sha256=" + sha + ".tar",
                       "members": [f["logical_path"] for f in group]})
    remote = {**plan["frozen_inventory"], "bundle_id": plan["bundle_id"], "shards": shards,
              "complete": True, "files_are_original_bytes": True,
              "no_source_zip_extraction": True, "archive_does_not_grant_pit_or_silver_approval": True}
    immutable_write(output / "manifest.json", canonical(remote))
    prepared = {"schema_version": "dart-historical-prepared-archive-v1", "bundle_id": plan["bundle_id"],
                "bucket": plan["bucket"], "prefix": plan["prefix"], "shards": shards,
                "manifest_sha256": digest(canonical(remote)), "manifest_bytes": len(canonical(remote)),
                "manifest_key": plan["prefix"] + "/manifest.json", "file_count": plan["file_count"],
                "total_source_bytes": plan["total_source_bytes"], "s3_calls": 0}
    immutable_write(output / "prepared.json", canonical(prepared))
    return prepared


def _error_code(exc):
    response = getattr(exc, "response", {})
    return str(response.get("Error", {}).get("Code", "UNKNOWN")), response.get("ResponseMetadata", {}).get("HTTPStatusCode")


class S3Writer:
    def __init__(self, client, *, sleeper=time.sleep, monotonic=time.monotonic):
        self.client, self.sleeper, self.monotonic = client, sleeper, monotonic
        self.next_request = 0.0
        self.counts = Counter()

    def call(self, method, **kwargs):
        delay = self.next_request - self.monotonic()
        if delay > 0:
            self.sleeper(delay)
        self.next_request = max(self.next_request, self.monotonic()) + 0.5
        self.counts[method] += 1
        return getattr(self.client, method)(**kwargs)

    def existing_matches(self, bucket, key, sha, size):
        try:
            head = self.call("head_object", Bucket=bucket, Key=key, ChecksumMode="ENABLED")
            require(head.get("ContentLength") == size, "EXISTING_S3_OBJECT_SIZE_MISMATCH")
            checksum = head.get("ChecksumSHA256")
            if checksum:
                require(checksum == base64.b64encode(bytes.fromhex(sha)).decode(), "EXISTING_S3_OBJECT_SHA_MISMATCH")
                return
            # Metadata/ETag alone is not cryptographic proof of bytes. Older
            # objects without a native full SHA are read once and rehashed.
            response = self.call("get_object", Bucket=bucket, Key=key)
            hasher, actual = hashlib.sha256(), 0
            with response["Body"] as stream:
                while block := stream.read(min(1024 * 1024, size - actual + 1)):
                    actual += len(block)
                    require(actual <= size, "EXISTING_S3_OBJECT_SIZE_MISMATCH")
                    hasher.update(block)
            require(actual == size and hasher.hexdigest() == sha, "EXISTING_S3_OBJECT_SHA_MISMATCH")
        except ArchiveError:
            raise
        except Exception:
            raise ArchiveError("EXISTING_S3_OBJECT_VERIFICATION_FAILED") from None

    def put(self, bucket, key, path, sha, size):
        expected = base64.b64encode(bytes.fromhex(sha)).decode()
        for attempt in range(4):
            if attempt:
                self.sleeper(2 ** (attempt - 1))
            try:
                with safe_file(path).open("rb") as handle:
                    response = self.call("put_object", Bucket=bucket, Key=key, Body=handle, ContentLength=size,
                                         IfNoneMatch="*", ChecksumAlgorithm="SHA256", ChecksumSHA256=expected,
                                         Metadata={"sha256": sha, "source": "dart-historical-evidence"},
                                         ContentType="application/json" if key.endswith(".json") else "application/x-tar")
                require(response.get("ChecksumSHA256", expected) == expected, "S3_WRITE_CHECKSUM_RESPONSE_MISMATCH")
                return "UPLOADED"
            except ArchiveError:
                raise
            except Exception as exc:
                code, status = _error_code(exc)
                if code in {"PreconditionFailed", "412"} or status == 412:
                    self.existing_matches(bucket, key, sha, size)
                    return "REUSED_HASH_VERIFIED"
                if not (code in {"ConditionalRequestConflict", "SlowDown", "RequestTimeout", "InternalError", "ServiceUnavailable"}
                        or status == 409 or status == 429 or (isinstance(status, int) and status >= 500)):
                    raise ArchiveError("S3_CONDITIONAL_WRITE_FAILED") from None
        raise ArchiveError("S3_CONDITIONAL_WRITE_RETRIES_EXHAUSTED")


def upload(prepared_dir, *, apply=False, profile=None, client=None, sleeper=time.sleep, monotonic=time.monotonic):
    root = Path(prepared_dir).absolute()
    prepared = read_json(root / "prepared.json")
    require(prepared.get("schema_version") == "dart-historical-prepared-archive-v1", "INVALID_PREPARED_SCHEMA")
    require(prepared["prefix"] == PREFIX + "/bundle=" + prepared["bundle_id"], "UNSAFE_PREPARED_PREFIX")
    plan = read_json(root / "frozen-plan.json")
    require(plan["bundle_id"] == prepared["bundle_id"] and plan["bucket"] == prepared["bucket"], "PREPARED_PLAN_MISMATCH")
    require(plan.get("executable") is True and not plan.get("preview_only"), "PREVIEW_CANNOT_UPLOAD")
    require(digest(canonical(plan["frozen_inventory"])) == prepared["bundle_id"], "FROZEN_INVENTORY_SHA_MISMATCH")
    remote = read_json(root / "manifest.json")
    require(remote.get("complete") is True and remote.get("shards") == prepared["shards"], "PREPARED_MANIFEST_MISMATCH")
    require(all(remote.get(k) == v for k,v in plan["frozen_inventory"].items()), "REMOTE_MANIFEST_INVENTORY_MISMATCH")
    members = [member for shard in prepared["shards"] for member in shard["members"]]
    require(members == [item["logical_path"] for item in plan["frozen_inventory"]["files"]], "SHARD_MEMBER_INVENTORY_MISMATCH")
    require(len({s["name"] for s in prepared["shards"]}) == len(prepared["shards"]), "DUPLICATE_SHARD_NAME")
    require(prepared["file_count"] == len(members)
            and prepared["total_source_bytes"] == sum(f["bytes"] for f in plan["frozen_inventory"]["files"]), "PREPARED_INVENTORY_COUNTS_MISMATCH")
    verify = [("manifest.json", prepared["manifest_sha256"], prepared["manifest_bytes"])]
    for shard in prepared["shards"]:
        require(re.fullmatch(r"part-[0-9]{5}\.tar", shard["name"]) and re.fullmatch(r"[0-9a-f]{64}", shard["sha256"]), "UNSAFE_SHARD_NAME_OR_SHA")
        require(shard["key"] == prepared["prefix"] + "/shards/sha256=" + shard["sha256"] + ".tar", "UNSAFE_SHARD_KEY")
        verify.append((shard["name"], shard["sha256"], shard["bytes"]))
    require(prepared["manifest_key"] == prepared["prefix"] + "/manifest.json", "UNSAFE_MANIFEST_KEY")
    for name, sha, size in verify:
        require(file_digest(root / name) == (sha, size), "PREPARED_ARCHIVE_SHA_MISMATCH")
    result = {"schema_version": "dart-historical-archive-upload-v1", "bundle_id": prepared["bundle_id"],
              "manifest_uri": "s3://" + prepared["bucket"] + "/" + prepared["manifest_key"],
              "file_count": prepared["file_count"], "shard_count": len(prepared["shards"]),
              "new_upload_request_count": len(prepared["shards"]) + 1, "s3_calls": 0,
              "status": "DRY_RUN_NO_S3_CALLS", "rds_writes": False, "gold_writes": False, "objects": []}
    if not apply:
        return result
    if client is None:
        try:
            import boto3
            from botocore.config import Config
            client = boto3.Session(profile_name=profile).client("s3", config=Config(
                retries={"total_max_attempts": 1}, connect_timeout=15, read_timeout=120))
        except Exception:
            raise ArchiveError("AWS_EXISTING_CREDENTIAL_CHAIN_UNAVAILABLE") from None
    writer = S3Writer(client, sleeper=sleeper, monotonic=monotonic)
    try:
        for shard in prepared["shards"]:
            status = writer.put(prepared["bucket"], shard["key"], root / shard["name"], shard["sha256"], shard["bytes"])
            result["objects"].append({"key": shard["key"], "sha256": shard["sha256"], "status": status})
        # Only this final object advertises a complete archive. Interrupted
        # shard uploads stay orphaned/uncommitted and can be resumed safely.
        status = writer.put(prepared["bucket"], prepared["manifest_key"], root / "manifest.json",
                            prepared["manifest_sha256"], prepared["manifest_bytes"])
        result["objects"].append({"key": prepared["manifest_key"], "sha256": prepared["manifest_sha256"], "status": status})
        result["status"] = "ARCHIVED_HASH_VERIFIED"
    except ArchiveError as exc:
        result.update(status="ARCHIVE_INCOMPLETE", reason=str(exc))
    result.update(s3_calls=sum(writer.counts.values()), request_counts=dict(writer.counts), completed_at=datetime.now(timezone.utc).isoformat())
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    planning = commands.add_parser("plan")
    for name in ("raw", "stage", "identity", "output"):
        planning.add_argument("--" + name, type=Path, required=True)
    planning.add_argument("--checked-manifest", type=Path)
    planning.add_argument("--corpus-plan", type=Path)
    planning.add_argument("--bucket")
    planning.add_argument("--preview", action="store_true")
    packing = commands.add_parser("pack")
    packing.add_argument("--plan", type=Path, required=True)
    packing.add_argument("--output", type=Path, required=True)
    publishing = commands.add_parser("upload")
    publishing.add_argument("--prepared", type=Path, required=True)
    publishing.add_argument("--report", type=Path)
    publishing.add_argument("--profile")
    publishing.add_argument("--apply", action="store_true")
    args = cli.parse_args()
    try:
        if args.command == "plan":
            result = build_plan(args.raw, args.stage, args.identity, bucket=args.bucket,
                                checked_manifest=args.checked_manifest, corpus_plan=args.corpus_plan, preview=args.preview)
            immutable_write(args.output, canonical(result))
        elif args.command == "pack":
            result = prepare(args.plan, args.output)
        else:
            result = upload(args.prepared, apply=args.apply, profile=args.profile)
            if args.report:
                immutable_write(args.report, canonical(result))
        keys = ("status", "bundle_id", "executable", "blockers", "file_count", "total_source_bytes", "s3_calls", "manifest_uri", "reason")
        print(json.dumps({k:result[k] for k in keys if k in result}, ensure_ascii=False, indent=2))
        if result.get("status") == "ARCHIVE_INCOMPLETE":
            raise SystemExit(2)
    except ArchiveError as exc:
        print(json.dumps({"status": "FAILED", "reason": str(exc)}))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
