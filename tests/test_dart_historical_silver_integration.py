"""Cross-repository synthetic collection/staging/parser/publication contracts.

Only fake HTTP responses, temporary source files, and pure preparation run.
No real DART/RDS calls, user caches, historical returns or OOS are accessed.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / "TeamAlpha-data"
if not (DATA_ROOT / "pipeline/silver/dart_historical_revenue.py").exists():
    pytest.skip("sibling TeamAlpha-data bounded source module is unavailable", allow_module_level=True)
sys.path.insert(0, str(DATA_ROOT))
try:
    from pipeline.silver import dart_historical_revenue as publisher
finally:
    sys.path.remove(str(DATA_ROOT))
from engine import dart_historical_revenue_parser as parser
from scripts import stage_dart_statement_corpus as stage


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


producer = _load("_stage_integration_fixtures", ROOT / "tests/test_stage_dart_statement_corpus.py")
consumer = _load("_silver_integration_fixtures", DATA_ROOT / "tests/silver/test_dart_historical_revenue.py")


def checked_bundle(tmp_path, monkeypatch, *, parser_version="v1", **kwargs):
    raw = producer.make_corpus(tmp_path, monkeypatch, **kwargs)
    output = tmp_path / "stage"
    stage.write_bundle(raw, output, parser_version=parser_version)
    index = json.loads((output / "artifact-index.json").read_bytes())
    artifacts = {digest: (Path(index["roots"][row["root"]]) / row["path"]).read_bytes()
                 for digest, row in index["artifacts"].items()}
    identity = consumer.Fixture()
    # Match the producer's synthetic asset, preserving an independent certified
    # FY/listing proof rather than trusting stage.asset_ids as historical truth.
    identity.mapping["asset_id"] = 1
    identity.fy["rows"][0]["asset_id"] = 1
    identity.listing["rows"][0]["asset_id"] = 1
    payload = identity.listing_proof["payload"]
    payload["periods"][0]["asset_id"] = 1
    body = {k: v for k, v in payload.items() if k != "snapshot_id"}
    payload["snapshot_id"] = publisher.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
    identity.listing_proof["snapshot_id"] = payload["snapshot_id"]
    identity.listing["identity_evidence_sha256"] = identity.add(identity.listing_proof)
    identity.args()
    artifacts.update(identity.artifacts)
    identity_sha = identity.add(identity.identity)
    artifacts[identity_sha] = identity.artifacts[identity_sha]
    stage_bytes = (output / "staged-revenue.json").read_bytes()
    staged = json.loads(stage_bytes)
    selected = stage.selected_parser(parser_version)
    manifest = {"schema_version": "dart-revenue-checked-manifest-v1", "dataset_version": "synthetic-producer-consumer-v1",
                "stage_sha256": publisher.sha256(stage_bytes), "parser_source_sha256": selected.source_sha256(),
                "corpus_sha256": publisher.sha256((output / "corpus.json").read_bytes()),
                "lineage_sha256": publisher.sha256((output / "lineage.json").read_bytes()),
                "identity_sha256": identity_sha,
                "approved_row_sha256": [publisher.object_sha256(r) for r in staged["rows"] if r["source_publication_candidate"]],
                "review": {"decision": "ACCEPT", "reviewer": "synthetic independent reviewer",
                           "reviewed_at": "2026-10-02T12:00:00+09:00"}}
    return stage_bytes, manifest, artifacts


def test_real_producer_to_real_parser_to_publisher_original(tmp_path, monkeypatch):
    prepared = publisher.prepare(*checked_bundle(tmp_path, monkeypatch), parse_document=parser.parse_document)
    assert len(prepared.rows) == 2
    assert {r["value"] for r in prepared.rows} == {"1234000000.000000"}
    assert {r["fiscal_period"] for r in prepared.rows} == {"Q2"}
    assert {r["available_date"] for r in prepared.rows} == {"2015-08-18"}
    assert {r["valid_until_exclusive"] for r in prepared.rows} == {"2023-08-01"}
    assert all(r["evidence"]["current_ytd_evidence"]["amount_krw_decimal"] == "2000000000" for r in prepared.rows)
    assert prepared.evidence["full_history_certified"] is False


def test_official_correction_family_producer_to_consumer(tmp_path, monkeypatch):
    prepared = publisher.prepare(*checked_bundle(tmp_path, monkeypatch, corrected=True), parse_document=parser.parse_document)
    assert len(prepared.rows) == 4
    assert {r["valid_until_exclusive"] for r in prepared.rows if r["filing_id"] == producer.ORIGINAL} == {"2016-09-02"}
    assert {r["available_date"] for r in prepared.rows if r["filing_id"] == producer.CORRECTION} == {"2016-09-02"}


@pytest.mark.parametrize("options", [{"partial": True}, {"corrected": True, "no_main": True}])
def test_unresolved_producer_cannot_be_force_approved(tmp_path, monkeypatch, options):
    raw, manifest, artifacts = checked_bundle(tmp_path, monkeypatch, **options)
    staged = json.loads(raw)
    manifest["approved_row_sha256"] = [publisher.object_sha256(r) for r in staged["rows"] if r["amount_role"] == "CURRENT_QUARTER"]
    with pytest.raises(publisher.EvidenceError, match="unresolved|withdrawn"):
        publisher.prepare(raw, manifest, artifacts, parse_document=parser.parse_document)


@pytest.mark.parametrize("where,field", [("stage", "source_collection_finished"),
                                         ("stage", "all_planned_issuer_lists_complete"),
                                         ("corpus", "all_planned_issuer_lists_complete")])
def test_three_completion_flags_not_review_overridable(tmp_path, monkeypatch, where, field):
    raw, manifest, artifacts = checked_bundle(tmp_path, monkeypatch)
    if where == "stage":
        staged = json.loads(raw)
        staged[field] = False
        raw = publisher.canonical_bytes(staged)
        manifest["stage_sha256"] = publisher.sha256(raw)
    else:
        corpus = json.loads(artifacts[manifest["corpus_sha256"]])
        corpus[field] = False
        body = publisher.canonical_bytes(corpus)
        manifest["corpus_sha256"] = publisher.sha256(body)
        artifacts[manifest["corpus_sha256"]] = body
    with pytest.raises(publisher.EvidenceError, match="incomplete"):
        publisher.prepare(raw, manifest, artifacts, parse_document=parser.parse_document)


def test_v2_explicit_cfs_absence_is_source_bound_not_inferred(tmp_path, monkeypatch):
    from engine import dart_historical_revenue_parser_v2 as v2
    original = producer.xml
    def absent_xml(*, partial=False):
        return original(partial=True).replace(b"<TITLE>4.", "<P>해당사항 없습니다.</P><TITLE>4.".encode())
    monkeypatch.setattr(producer, "xml", absent_xml)
    args = checked_bundle(tmp_path, monkeypatch, parser_version="v2", partial=True)
    prepared = publisher.prepare(*args, parse_document=v2.parse_document)
    assert len(prepared.rows) == 1 and prepared.rows[0]["fs_type"] == "OFS"
    evidence = prepared.rows[0]["evidence"]
    assert evidence["statement_scope_status"] == {"CFS": "EXPLICITLY_ABSENT", "OFS": "PARSED"}
    proof = evidence["statement_scope_details"]["CFS"]["absence_evidence"][0]
    assert proof["exact_text"] == "해당사항 없습니다."
    raw = absent_xml()
    replay = v2.parse_document(raw, "Q2", producer.CORP)
    replay["scope_details"]["CFS"]["absence_evidence"][0]["source_slice_sha256"] = "0" * 64
    with pytest.raises(publisher.EvidenceError, match="source slice"):
        publisher._parsed_scopes(replay, raw)


@pytest.mark.parametrize("field,value", [("completed_at", None), ("complete_issuer_list_count", 0),
                                         ("manifest_sha256", "0" * 64)])
def test_true_booleans_cannot_replace_complete_official_run_receipt(tmp_path, monkeypatch, field, value):
    raw, manifest, artifacts = checked_bundle(tmp_path, monkeypatch)
    staged = json.loads(raw)
    corpus = json.loads(artifacts[manifest["corpus_sha256"]])
    run = json.loads(artifacts[corpus["source_run_sha256"]])
    run[field] = value
    run_raw = publisher.canonical_bytes(run)
    run_sha = publisher.sha256(run_raw)
    artifacts[run_sha] = run_raw
    staged["source_run_sha256"] = corpus["source_run_sha256"] = run_sha
    corpus_raw = publisher.canonical_bytes(corpus)
    manifest["corpus_sha256"] = publisher.sha256(corpus_raw)
    artifacts[manifest["corpus_sha256"]] = corpus_raw
    raw = publisher.canonical_bytes(staged)
    manifest["stage_sha256"] = publisher.sha256(raw)
    with pytest.raises(publisher.EvidenceError, match="completed official collection"):
        publisher.prepare(raw, manifest, artifacts, parse_document=parser.parse_document)
