"""Future-only reviewer export boundaries; all new registrations are synthetic."""
from copy import deepcopy
import json

import pytest

from engine import knowledge_registration as kr
from engine.knowledge_lineage import canonical_hash
from scripts.dashboard_exports import registered_lineage as projection
from scripts.dashboard_exports.export_research_catalog import safe
from test_knowledge_registration import setup, epoch_start, write_candidate


@pytest.fixture
def registered(setup, monkeypatch):
    d = setup
    d.record["review"]["packet_sha256"] = "b"*64
    ledger = d.root/"memory/candidate_lessons.jsonl"
    ledger.write_text(json.dumps(d.record)+"\n")
    import hashlib
    d.catalog["source"]["ledger_file_sha256"] = hashlib.sha256(ledger.read_bytes()).hexdigest()
    d.capture = kr.capture_knowledge(d.root)
    d.meta["knowledge_snapshot_hash"] = d.capture["knowledge_snapshot_hash"]
    d.meta["lesson_references"][0].update(d.capture["reviewed_lesson_versions"][0])
    write_candidate(d)
    path = epoch_start(d, monkeypatch)
    d.epoch = json.loads(path.read_text())
    d.payload = {"factor": {"definition_hash": d.factor.definition_hash}, "research_spec": deepcopy(d.spec)}
    d.target = {"record_id": "campaign-001/epoch-001/lineage_probe"}
    return d


def retained(d):
    return projection.retained_lineage(d.root, d.epoch, d.factor.name, d.payload)


def resolved(d, lineage=None):
    rows = [deepcopy(d.record), deepcopy(d.target)]
    projection.resolve_public_lineage(rows, {d.target["record_id"]: retained(d) if lineage is None else lineage}, safe)
    return rows[-1]["registered_lineage"]


def test_retained_registration_to_public_reference_and_no_private_payload(registered, monkeypatch):
    d = registered
    monkeypatch.setattr(kr, "_authenticated", lambda *_: pytest.fail("Recursive export"))
    before = {str(p):p.read_bytes() for p in d.root.rglob('*') if p.is_file()}
    out = resolved(d)
    assert out["status"] == "RECORDED_AT_REGISTRATION"
    assert out["reference_authentication"] == "CURRENT_PUBLIC_REVIEW_VERSION_AND_PACKET"
    assert out["lesson_references"] == d.meta["lesson_references"]
    assert out["withheld_reference_count"] == 0
    assert not out["follow_up_executed"] and not out["independent_evidence"]
    text = json.dumps(out)
    for private in ("knowledge_text", "never_export_raw_oos", "9.87654321", str(d.root), d.record["review"]["general_lesson"]):
        assert private not in text
    assert resolved(d) == out
    assert before == {str(p):p.read_bytes() for p in d.root.rglob('*') if p.is_file()}


def test_legacy_is_read_free_no_new_fields_or_counts(monkeypatch, tmp_path):
    monkeypatch.setattr(projection, "read_registered_lineage", lambda *_: pytest.fail("Legacy capture read"))
    assert projection.retained_lineage(tmp_path, {}, "old", {"research_spec": {}}) is None
    # Other members in a mixed epoch opting in must not change this old candidate.
    assert projection.retained_lineage(tmp_path, {"knowledge_lineage": {"candidate_bindings": {"other": {}}}}, "old", {}) is None
    rows = [{"record_id": "old", "definition": {"research_spec": {"thesis": "old"}}}]
    before = json.dumps(rows)
    projection.resolve_public_lineage(rows, {}, lambda *_: pytest.fail("Unneeded sanitation"))
    assert json.dumps(rows) == before


def test_public_spec_copy_does_not_change_frozen_payload(registered):
    d = registered
    before = deepcopy(d.payload)
    cleaned = projection.public_spec(d.payload["research_spec"])
    assert "knowledge_lineage" not in cleaned
    assert d.payload == before
    assert cleaned["strategy_sha256"] == d.spec["strategy_sha256"]


@pytest.mark.parametrize("change", ["raw_only", "epoch_only", "null_block", "list_block", "list_bindings", "capture_missing", "capture_tampered", "changed_declaration", "changed_strategy", "changed_definition"])
def test_invalid_optional_binding_withholds_only_lineage(registered, change):
    d = registered
    if change == "raw_only": d.epoch.pop("knowledge_lineage")
    elif change == "epoch_only": d.payload["research_spec"].pop("knowledge_lineage")
    elif change == "null_block": d.epoch["knowledge_lineage"] = None
    elif change == "list_block": d.epoch["knowledge_lineage"] = []
    elif change == "list_bindings": d.epoch["knowledge_lineage"]["candidate_bindings"] = []
    elif change == "capture_missing": __import__('pathlib').Path(d.capture["path"]).unlink()
    elif change == "capture_tampered": __import__('pathlib').Path(d.capture["path"]).write_text('{"private_path":"/do/not/export"}')
    elif change == "changed_declaration": d.payload["research_spec"]["knowledge_lineage"]["declared_at"] = "2099-01-01T00:00:00Z"
    elif change == "changed_strategy": d.payload["research_spec"]["strategy_sha256"] = "f"*64
    elif change == "changed_definition": d.payload["factor"]["definition_hash"] = "f"*64
    result = retained(d)
    assert result["status"] == "WITHHELD"
    assert set(result) == {"schema_version", "status", "reason"}
    out = resolved(d, result)
    assert out == result
    assert d.target == {"record_id": "campaign-001/epoch-001/lineage_probe"}


@pytest.mark.parametrize("change,reason", [("missing", "SOURCE_NOT_PUBLIC"), ("pending", "SOURCE_NOT_CURRENT_REVIEWED"), ("stale", "SOURCE_NOT_CURRENT_REVIEWED"), ("review", "SOURCE_REVIEW_VERSION_CHANGED"), ("packet", "SOURCE_PACKET_VERSION_CHANGED"), ("relation", "UNSUPPORTED_RELATION")])
def test_source_no_longer_current_does_not_leak_identity(registered, change, reason):
    d = registered
    lineage = retained(d)
    if change == "missing": d.record["record_id"] = "different"
    elif change == "pending": d.record["visibility"] = "PENDING"
    elif change == "stale": d.record["review_status"] = "STALE_OR_INVALID_REVIEW_WITHHELD"
    elif change == "review": d.record["review"]["general_lesson"] = "New review"
    elif change == "packet": d.record["provenance"]["packet_sha256"] = "c"*64
    elif change == "relation": lineage["lesson_references"][0]["relation"] = "SUPPORTS"
    out = resolved(d, lineage)
    assert out["lesson_references"] == []
    assert out["withheld_reference_reasons"] == {reason: 1}
    assert d.meta["referenced_lesson_record_ids"][0] not in json.dumps(out)


def test_reference_hash_uses_same_sanitized_view_as_capture(registered):
    d = registered
    lineage = retained(d)
    d.record["review"]["context"] = "postgres://private.example/db"
    lineage["lesson_references"][0]["review_hash"] = canonical_hash(safe(d.record["review"]))
    assert canonical_hash(d.record["review"]) != lineage["lesson_references"][0]["review_hash"]
    assert len(resolved(d, lineage)["lesson_references"]) == 1


def test_explicit_empty_references_distinguished_from_unrecorded(registered):
    d = registered
    lineage = retained(d)
    lineage["lesson_references"] = []
    out = resolved(d, lineage)
    assert out["status"] == "RECORDED_AT_REGISTRATION" and out["lesson_references"] == []
    assert out["withheld_reference_count"] == 0


def test_comparison_keeps_its_relation(registered):
    lineage = retained(registered)
    lineage["lesson_references"][0]["relation"] = "DECLARED_COMPARISON_REFERENCE"
    assert resolved(registered, lineage)["lesson_references"][0]["relation"] == "DECLARED_COMPARISON_REFERENCE"


def test_pending_release_never_reads_optional_capture_or_frozen_packet(tmp_path, monkeypatch):
    from scripts.dashboard_exports import export_research_catalog as exporter
    (tmp_path/'memory').mkdir()
    (tmp_path/'memory/candidate_lessons.jsonl').write_text(json.dumps({
        "record_id": "sealed/e/private", "visibility": "PENDING", "evidence": {"campaign": "sealed"}})+'\n')
    monkeypatch.setattr(exporter, "retained_lineage", lambda *_: pytest.fail("Sealed capture read"))
    monkeypatch.setattr(exporter.epochs, "load_epoch", lambda *_: pytest.fail("Sealed epoch read"))
    out = exporter.export(tmp_path, "2030-01-01")
    assert out["records"] == [] and out["counts"]["withheld_records"] == 1
    assert "registered_lineage" not in json.dumps(out)
