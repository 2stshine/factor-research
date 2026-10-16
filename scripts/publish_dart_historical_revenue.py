"""Review-gated bridge to the separate append-only historical revenue source.

plan writes a DRAFT proposal only. check replays an independently accepted
manifest without any database access. apply additionally requires --apply and
an explicit read_only=False Silver connection; it never installs migrations.
No legacy fundamental/Gold table, research campaign or panel is modified.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import date, timedelta
import importlib
import inspect
import json
from pathlib import Path, PurePosixPath
import sys

from engine import silver
from engine.research_memory_transfer import write_artifact

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_FILES = ("identity.json", "listing.json", "listing-source.json", "fy-reference-scoped.json", "fy-reference.json")


def publisher_module(teamalpha_root=None):
    root = Path(teamalpha_root or ROOT.parent / "TeamAlpha-data").absolute()
    expected = root / "pipeline/silver/dart_historical_revenue.py"
    if not expected.is_file() or expected.is_symlink():
        raise ValueError("Explicit TeamAlpha-data bounded-source publisher is unavailable")
    sys.path.insert(0, str(root))
    try:
        module = importlib.import_module("pipeline.silver.dart_historical_revenue")
    finally:
        sys.path.remove(str(root))
    if Path(module.__file__).resolve() != expected.resolve():
        raise ValueError("Loaded publisher does not match requested TeamAlpha-data repository")
    return module


def parser_module(version):
    if version not in {"v1", "v2"}:
        raise ValueError("Explicit parser choice v1/v2 required")
    name = "engine.dart_historical_revenue_parser" + ("_v2" if version == "v2" else "")
    return importlib.import_module(name)


class Artifacts(Mapping):
    """Hash-addressed lazy file reader; every touched file is rehashed at end."""
    def __init__(self, stage_dir, identity_dir, publisher):
        self.publisher = publisher
        self.paths, self.observed = {}, {}
        self.stage_dir, self.identity_dir = Path(stage_dir).absolute(), Path(identity_dir).absolute()
        index = json.loads(self.read_path(self.stage_dir / "artifact-index.json"))
        if index.get("schema_version") != "dart-original-artifact-index-v1":
            raise ValueError("Unsupported artifact-index schema")
        self.stage_bytes = self.read_path(self.stage_dir / "staged-revenue.json")
        self.stage = json.loads(self.stage_bytes)
        roots = {key: Path(value).absolute() for key, value in index["roots"].items()}
        if (set(roots) != {"corpus", "repository", "output"} or roots["repository"] != ROOT
                or roots["output"] != self.stage_dir or roots["corpus"] != Path(self.stage["source_root"]).absolute()
                or not roots["corpus"].is_relative_to(self.stage_dir.parent)):
            raise ValueError("Artifact roots are outside the declared sibling corpus/staging scope")
        for digest, row in index["artifacts"].items():
            rel = PurePosixPath(row["path"])
            if (not publisher.HASH_RE.fullmatch(digest) or row["root"] not in roots or rel.is_absolute()
                    or ".." in rel.parts or "\\" in str(rel) or ":" in str(rel)):
                raise ValueError("Unsafe artifact-index entry")
            self.paths[digest] = roots[row["root"]] / rel
        for filename in IDENTITY_FILES:
            path = self.identity_dir / filename
            if path.is_file():
                raw = self.read_path(path)
                self.paths[publisher.sha256(raw)] = path
        self.identity_bytes = self.read_path(self.identity_dir / "identity.json")
        self.identity = json.loads(self.identity_bytes)
        if self.identity.get("schema_version") != "dart-historical-identity-v1":
            raise ValueError("Expected separate historical identity artifact")

    def read_path(self, path):
        path = Path(path).absolute()
        if not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("Artifact path is missing or symlinked")
        raw = path.read_bytes()
        digest = self.publisher.sha256(raw)
        if path in self.observed and self.observed[path] != digest:
            raise ValueError("Artifact file changed during validation")
        self.observed[path] = digest
        return raw

    def __getitem__(self, digest):
        if digest not in self.paths:
            raise KeyError(digest)
        raw = self.read_path(self.paths[digest])
        if self.publisher.sha256(raw) != digest:
            raise ValueError("Indexed artifact content hash changed")
        return raw

    def __iter__(self):
        return iter(self.paths)

    def __len__(self):
        return len(self.paths)

    def verify_unchanged(self):
        for path, digest in tuple(self.observed.items()):
            if self.publisher.sha256(self.read_path(path)) != digest:
                raise ValueError("Source artifact changed before transaction completion")


def _source_contract(store, publisher, parser, parser_version):
    live_parser_sha = publisher.sha256(store.read_path(Path(parser.__file__)))
    if store.stage.get("parser_source_sha256") != live_parser_sha or parser.source_sha256() != live_parser_sha:
        raise ValueError("Stage and explicitly selected live parser source hashes differ")
    quality_path = Path(inspect.getsourcefile(publisher.check_document_revenue))
    for file in (Path(publisher.__file__), quality_path, Path(__file__)):
        store.read_path(file)
    return {"parser_choice": parser_version, "parser_source_sha256": live_parser_sha,
            "publisher_source_sha256": publisher.sha256(Path(publisher.__file__).read_bytes()),
            "quality_rules_source_sha256": publisher.sha256(quality_path.read_bytes()),
            "bridge_source_sha256": publisher.sha256(Path(__file__).read_bytes()),
            "artifact_index_sha256": publisher.sha256(store.read_path(store.stage_dir / "artifact-index.json")),
            "stage_directory": str(store.stage_dir), "identity_directory": str(store.identity_dir)}


def plan(stage_dir, identity_dir, *, dataset_version, parser_version, output, teamalpha_root=None):
    publisher, parser = publisher_module(teamalpha_root), parser_module(parser_version)
    store = Artifacts(stage_dir, identity_dir, publisher)
    source = _source_contract(store, publisher, parser, parser_version)
    corpus_raw, lineage_raw = store.read_path(store.stage_dir / "corpus.json"), store.read_path(store.stage_dir / "lineage.json")
    corpus, lineage = json.loads(corpus_raw), json.loads(lineage_raw)
    if (store.stage.get("source_collection_finished") is not True
            or store.stage.get("all_planned_issuer_lists_complete") is not True
            or corpus.get("all_planned_issuer_lists_complete") is not True):
        raise ValueError("Incomplete source collection: no publication plan can be approved")
    evidence = publisher._EvidenceStore(store)
    receipts, horizons, _ = publisher._validate_corpus(corpus, evidence)
    scopes = publisher._validate_lineage(lineage, receipts, horizons, evidence)
    event_index = {}
    for scope in scopes.values():
        events = scope["events"]
        for i, event in enumerate(events):
            until = (date.fromisoformat(receipts[events[i + 1]["receipt_no"]]["filed"]) + timedelta(days=1)
                     if i + 1 < len(events) else horizons[scope["corp_code"]][1])
            event_index[event["receipt_no"]] = (scope, event, until)
    document_status = {d["receipt_no"]: d.get("scope_status") for d in store.stage["documents"]}
    rows_by_receipt = defaultdict(list)
    for row in store.stage["rows"]:
        if row["amount_role"] == "CURRENT_QUARTER":
            rows_by_receipt[row["receipt_no"]].append(row)
    proposed, excluded = [], []
    for receipt, rows in sorted(rows_by_receipt.items()):
        scope, event, until = event_index.get(receipt, (None, None, None))
        statuses = document_status.get(receipt)
        reason = None
        if not all(r.get("source_publication_candidate") is True for r in rows):
            reason = "SOURCE_LINEAGE_OR_STATEMENT_SCOPE_NOT_ELIGIBLE"
        elif scope is None or event["kind"] not in {"ORIGINAL", "CORRECTION"}:
            reason = "UNRESOLVED_OR_WITHDRAWN_LINEAGE"
        elif len({r["fs_type"] for r in rows}) != len(rows):
            reason = "DUPLICATE_CURRENT_QUARTER_STATEMENT_SCOPE"
        elif not statuses or {r["fs_type"] for r in rows} != {fs for fs, status in statuses.items() if status == "PARSED"}:
            reason = "CURRENT_QUARTER_PARSED_SCOPE_PAIR_INCOMPLETE"
        else:
            available = date.fromisoformat(receipts[receipt]["filed"]) + timedelta(days=1)
            if until <= available:
                reason = "EMPTY_SAME_DAY_SUPERSEDED_REVISION"
            else:
                try:
                    publisher._identity(store.identity, scope, available, evidence)
                except (ValueError, KeyError, TypeError) as exc:
                    reason = "HISTORICAL_IDENTITY_UNVERIFIED: " + str(exc)
        if reason:
            excluded.append({"receipt_no": receipt, "corp_code": rows[0]["corp_code"],
                             "stock_code": rows[0]["stock_code"], "quarter": rows[0]["quarter"],
                             "current_quarter_rows": len(rows), "reason": reason})
        else:
            proposed.extend(publisher.object_sha256(row) for row in rows)
    if len(proposed) != len(set(proposed)):
        raise ValueError("Duplicate proposed approval row hash")
    manifest = {"schema_version": "dart-revenue-checked-manifest-v1", "dataset_version": dataset_version,
                "stage_sha256": publisher.sha256(store.stage_bytes), "parser_source_sha256": source["parser_source_sha256"],
                "corpus_sha256": publisher.sha256(corpus_raw), "lineage_sha256": publisher.sha256(lineage_raw),
                "identity_sha256": publisher.sha256(store.identity_bytes), "approved_row_sha256": sorted(proposed),
                "review": {"decision": "DRAFT", "reviewer": None, "reviewed_at": None},
                "bridge": source,
                "plan": {"status": "DRAFT_PROPOSAL_NOT_APPROVAL", "proposed_current_quarter_rows": len(proposed),
                         "excluded_receipts": len(excluded), "excluded_by_reason": dict(sorted(Counter(x["reason"] for x in excluded).items())),
                         "excluded": excluded, "database_writes": False, "pit_certified": False,
                         "interpretation": "Independent review must explicitly accept exact proposed row hashes; plan is not certification."}}
    store.verify_unchanged()
    write_artifact(output, manifest)
    return {"output": str(output), "decision": "DRAFT", "proposed_current_quarter_rows": len(proposed),
            "excluded_receipts": len(excluded), "pit_certified": False}


def check_or_apply(stage_dir, identity_dir, checked_manifest, *, parser_version, output,
                   teamalpha_root=None, apply=False, connect=None):
    if Path(output).exists():
        raise ValueError("Receipt output must be a new immutable path")
    publisher, parser = publisher_module(teamalpha_root), parser_module(parser_version)
    store = Artifacts(stage_dir, identity_dir, publisher)
    manifest = json.loads(store.read_path(checked_manifest))
    if manifest.get("review", {}).get("decision") != "ACCEPT":
        raise ValueError("Only a separately reviewed ACCEPT manifest can be checked/applied; DRAFT is not approval")
    source = _source_contract(store, publisher, parser, parser_version)
    if manifest.get("bridge") != source:
        raise ValueError("Accepted bridge/parser/publisher/index source contract changed; obtain a new review")
    if publisher.sha256(store.identity_bytes) != manifest["identity_sha256"]:
        raise ValueError("Accepted historical identity differs from supplied identity directory")
    prepared = publisher.prepare(store.stage_bytes, manifest, store, parse_document=parser.parse_document)
    store.verify_unchanged()
    receipt = {"schema_version": "dart-historical-publication-receipt-v1", "dataset_version": prepared.dataset_version,
               "manifest_sha256": prepared.manifest_sha256, "bundle_sha256": prepared.bundle_sha256,
               "rows": len(prepared.rows), "blocking_windows": len(prepared.blocking_windows),
               "source_only": True, "legacy_fundamental_writes": False, "gold_writes": False,
               "panel_activation": False, "migrations_executed": False,
               "input_artifacts_unchanged": True, "source_contract": source}
    if apply:
        connector = connect or silver.connect
        with connector(read_only=False) as conn:
            if conn.read_only or conn.autocommit:
                raise ValueError("Explicit read/write caller-owned Silver transaction required")
            with conn.transaction():
                written = publisher.publish(conn, stage_bytes=store.stage_bytes, checked_manifest=manifest, artifacts=store,
                                            parse_document=parser.parse_document, authorize_write=True)
                store.verify_unchanged()  # Last check is inside transaction, before commit.
            receipt.update(written)
        receipt.update(status="SOURCE_VERSION_PUBLISHED", database_writes=True, committed=True)
    else:
        receipt.update(status="SOURCE_PREPARE_CHECK_PASSED_NOT_PUBLISHED", database_writes=False, committed=False)
    write_artifact(output, receipt)
    return receipt


def main():
    arguments = argparse.ArgumentParser(description=__doc__)
    sub = arguments.add_subparsers(dest="command", required=True)
    for command in ("plan", "check", "apply"):
        p = sub.add_parser(command)
        p.add_argument("--stage-dir", required=True, type=Path)
        p.add_argument("--identity-dir", required=True, type=Path)
        p.add_argument("--parser", required=True, choices=("v1", "v2"))
        p.add_argument("--teamalpha-root", type=Path, default=ROOT.parent / "TeamAlpha-data")
        p.add_argument("--output", required=True, type=Path)
        if command == "plan":
            p.add_argument("--dataset-version", required=True)
        else:
            p.add_argument("--checked-manifest", required=True, type=Path)
        if command == "apply":
            p.add_argument("--apply", action="store_true", help="Explicitly authorize this separate source-table transaction")
    a = arguments.parse_args()
    if a.command == "plan":
        result = plan(a.stage_dir, a.identity_dir, dataset_version=a.dataset_version, parser_version=a.parser,
                      output=a.output, teamalpha_root=a.teamalpha_root)
    else:
        if a.command == "apply" and not a.apply:
            arguments.error("apply requires the explicit --apply flag")
        result = check_or_apply(a.stage_dir, a.identity_dir, a.checked_manifest, parser_version=a.parser,
                                output=a.output, teamalpha_root=a.teamalpha_root, apply=a.command == "apply")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
