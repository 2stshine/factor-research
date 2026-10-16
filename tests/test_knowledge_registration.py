"""Synthetic opt-in lifecycle. All writes are confined to pytest tmp_path."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine import epochs, knowledge_registration as kr
from engine.factors import Factor
from engine.knowledge_lineage import VERSION, canonical_hash, AUTHENTICATION


def _compute(frame):
    return frame["market_cap"]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path / "research"
    (root / "memory").mkdir(parents=True)
    review = {"status": "REVIEWED", "basis": "basis", "economic_interpretation": "Proxy and mechanism differ.",
              "general_lesson": "Check the construct before causal interpretation.", "scope": "Descriptive only."}
    rid = "campaign-source/epoch-source/source_factor"
    record = {"record_id": rid, "visibility": "RELEASED_QUALITATIVE", "review_status": "REVIEWED_CURRENT",
              "review": review, "review_basis": "basis", "family": "source", "ruleset": "synthetic",
              "validation": {"phase": "discovery", "checks": []},
              "provenance": {"authentication": AUTHENTICATION, "packet_sha256": "b"*64},
              "performance": {"never_export_raw_oos": 9.87654321}}
    ledger = root / "memory/candidate_lessons.jsonl"
    ledger.write_text(json.dumps(record)+"\n")
    catalog = {"records": [record], "source": {"ledger_file_sha256": hashlib.sha256(ledger.read_bytes()).hexdigest()}}
    monkeypatch.setattr(kr, "_authenticated", lambda *_: deepcopy(catalog))
    monkeypatch.setattr(kr, "_now", lambda: "2030-01-01T00:00:00+00:00")
    factor = Factor(name="lineage_probe", category="other", hypothesis="Synthetic new candidate only",
                    predicted_sign=1, compute=_compute)
    source = tmp_path / "factors/candidates/lineage_probe.py"
    source.parent.mkdir(parents=True)
    data = SimpleNamespace(root=root, catalog=catalog, meta={}, factor=factor,
                           source=source, cutoff="2030-01-01T00:02:00+00:00", record=record)
    write_candidate(data)
    from scripts.knowledge import _knowledge_parts, _render_knowledge
    base = "## Frozen research state\n\n- Synthetic inputs only.\n\n## Available strategy inputs\n\nmarket_cap\n"
    text = _render_knowledge(_knowledge_parts(root, base), [record])
    (root / "KNOWLEDGE.md").write_text(text)
    capture = kr.capture_knowledge(root)
    meta = {"schema_version": VERSION, "knowledge_snapshot_hash": capture["knowledge_snapshot_hash"],
            "snapshot_captured_at": capture["captured_at"], "declared_at": "2030-01-01T00:01:00+00:00",
            "referenced_lesson_record_ids": [rid], "lesson_references": [{
                **capture["reviewed_lesson_versions"][0], "relation": "DECLARED_QUALITATIVE_LESSON_USE"}]}
    data.capture, data.meta = capture, meta
    write_candidate(data)
    return data


def write_candidate(data, prefix=""):
    from factors.candidate_loader import _load_module, _validate_spec
    literal = {key: "Synthetic fixture" for key in (
        "thesis", "mechanism", "falsification", "expected_relationship", "data_notes")}
    literal["knowledge_lineage"] = data.meta
    data.source.write_text(
        'from engine.factors import Factor\n\n'
        'def compute(frame):\n    return frame["market_cap"]\n\n'
        'FACTOR = Factor(name="lineage_probe", category="other", '
        'hypothesis="Synthetic new candidate only", predicted_sign=1, compute=compute)\n'
        + prefix + "RESEARCH_SPEC = " + repr(literal) + "\n")
    module, sha, _ = _load_module(data.source)
    data.factor = module.FACTOR
    data.spec = _validate_spec(data.source, data.factor, module.RESEARCH_SPEC, source_digest=sha)
    data.digests = {data.factor.name: sha}


def prepare(data):
    return kr.prepare_registration(data.root, data.capture["capture_id"], [data.factor],
                                   {data.factor.name: data.spec}, data.digests, cutoff=data.cutoff)


def test_capture_archives_exact_existing_bytes_but_never_exports_reviewer_payload(setup):
    data = setup
    assert "knowledge_text" not in data.capture
    assert "never_export_raw_oos" not in json.dumps(data.capture)
    payload = kr.load_capture(data.root, data.capture["capture_id"])
    assert payload["knowledge_text"].encode() == (data.root/"KNOWLEDGE.md").read_bytes()
    assert "never_export_raw_oos" not in json.dumps(payload)
    assert "9.87654321" not in json.dumps(payload)
    assert payload["snapshot_content_safety_audited"] is False
    before = {str(p): p.read_bytes() for p in data.root.rglob('*') if p.is_file()}
    repeated = kr.capture_knowledge(data.root)
    assert repeated == data.capture
    assert before == {str(p): p.read_bytes() for p in data.root.rglob('*') if p.is_file()}


def test_capture_does_not_claim_full_input_context_safety(setup):
    # Existing renderer carries context text through; the lineage tool must not
    # turn identity capture into a content-safety certificate or a new prompt.
    data = setup
    path = data.root/"KNOWLEDGE.md"
    path.write_text(path.read_text().replace("- Synthetic inputs only.", "- Unreviewed synthetic context marker."))
    captured = kr.capture_knowledge(data.root)
    assert captured["snapshot_content_safety_audited"] is False
    assert "knowledge_text" not in captured and captured["candidate_registered"] is False


def test_stale_knowledge_and_concurrent_ledger_fail_before_new_capture(setup, monkeypatch):
    data = setup
    directory = data.root/"memory/knowledge_snapshots"
    before = sorted(directory.iterdir())
    original = (data.root/"KNOWLEDGE.md").read_bytes()
    (data.root/"KNOWLEDGE.md").write_bytes(original+b"\nUnreviewed lesson added\n")
    with pytest.raises(ValueError, match="current authenticated qualitative view"):
        kr.capture_knowledge(data.root)
    (data.root/"KNOWLEDGE.md").write_bytes(original)
    def race(*_):
        path = data.root/"memory/candidate_lessons.jsonl"
        path.write_bytes(path.read_bytes()+b"\n")
        return data.catalog
    monkeypatch.setattr(kr, "_authenticated", race)
    with pytest.raises(ValueError, match="changed during capture"):
        kr.capture_knowledge(data.root)
    assert sorted(directory.iterdir()) == before


def test_stale_saved_review_cannot_be_rendered_as_current_capture(setup):
    # Stored review text may still render from its old saved flag, but current
    # authentication is authoritative. No stale prompt is certified by copying it.
    setup.catalog["records"][0]["review_status"] = "STALE_OR_INVALID_REVIEW_WITHHELD"
    setup.catalog["records"][0]["review"] = None
    before = sorted((setup.root/"memory/knowledge_snapshots").iterdir())
    with pytest.raises(ValueError, match="current authenticated qualitative view"):
        kr.capture_knowledge(setup.root)
    assert sorted((setup.root/"memory/knowledge_snapshots").iterdir()) == before


def test_valid_preparation_binds_candidate_source_and_no_raw_values(setup):
    before = setup.factor.definition_hash
    out = prepare(setup)
    assert out["status"] == "VALIDATED_BEFORE_REGISTRATION"
    binding = out["candidate_bindings"][setup.factor.name]
    assert binding["strategy_sha256"] == setup.digests[setup.factor.name]
    assert binding["declaration_hash"] == canonical_hash(setup.meta)
    assert out["follow_up_executed"] is False and out["independent_evidence"] is False
    assert "knowledge_text" not in json.dumps(out) and "never_export_raw_oos" not in json.dumps(out)
    assert setup.factor.definition_hash == before


def test_core_rejects_same_named_factor_from_another_source(setup):
    from dataclasses import replace
    setup.factor = replace(setup.factor, compute=_compute)
    with pytest.raises(ValueError, match="not loaded from the declared"):
        prepare(setup)


def test_core_rejects_reconstructed_factor_even_with_copied_function(setup):
    from dataclasses import replace
    setup.factor = replace(setup.factor, params={"different": 6})
    with pytest.raises(ValueError, match="not loaded from the declared"):
        prepare(setup)


@pytest.mark.parametrize("change,match", [
    ("after_registration", "after registration cutoff"),
    ("late_declaration", "later than registration"),
    ("capture_time", "capture time differs"),
    ("snapshot", "snapshot differs"),
    ("not_in_capture", "not captured as public and reviewed"),
    ("different_captured_review", "version differs from capture"),
    ("pending_now", "Pending"), ("unreviewed_now", "Pending"),
    ("absent_now", "absent"), ("review_changed_now", "Review hash"),
    ("packet_changed_now", "packet hash"),
    ("duplicate_ref", "Unique"), ("execution_claim", "causality"),
])
def test_snapshot_time_release_and_version_negative_cases(setup, change, match):
    data = setup
    if change == "after_registration": data.cutoff = "2029-12-31T23:59:59+00:00"
    elif change == "late_declaration": data.meta["declared_at"] = "2030-01-02T00:00:00+00:00"
    elif change == "capture_time": data.meta["snapshot_captured_at"] = "2029-12-31T23:59:59+00:00"
    elif change == "snapshot": data.meta["knowledge_snapshot_hash"] = "c"*64
    elif change == "not_in_capture":
        new = deepcopy(data.record);new["record_id"] += "_only_released_after_capture"
        data.catalog["records"].append(new)
        data.meta["referenced_lesson_record_ids"] = [new["record_id"]]
        data.meta["lesson_references"][0]["record_id"] = new["record_id"]
    elif change == "different_captured_review": data.meta["lesson_references"][0]["review_hash"] = "c"*64
    elif change == "pending_now": data.catalog["records"][0]["visibility"] = "PENDING"
    elif change == "unreviewed_now": data.catalog["records"][0]["review_status"] = "UNREVIEWED"
    elif change == "absent_now": data.catalog["records"] = []
    elif change == "review_changed_now": data.catalog["records"][0]["review"]["scope"] = "Changed after capture."
    elif change == "packet_changed_now": data.catalog["records"][0]["provenance"]["packet_sha256"] = "c"*64
    elif change == "duplicate_ref":
        data.meta["referenced_lesson_record_ids"] *= 2;data.meta["lesson_references"] *= 2
    elif change == "execution_claim": data.meta["lesson_references"][0]["relation"] = "FOLLOW_UP_EXECUTED"
    write_candidate(data)
    with pytest.raises(ValueError, match=match): prepare(data)


@pytest.mark.parametrize("change,match", [
    ("edited_source", "source changed"), ("loaded_metadata", "Loaded declaration differs"),
    ("two_assignments", "one top-level"), ("nonliteral", "literal mapping"),
    ("capture_tamper", "content hash"), ("path_escape", "SHA-256"),
])
def test_source_and_capture_integrity_negative_cases(setup, change, match):
    data = setup
    if change == "edited_source": data.source.write_text(data.source.read_text()+"# changed\n")
    elif change == "loaded_metadata":
        data.spec = deepcopy(data.spec);data.spec["knowledge_lineage"]["declared_at"] = data.cutoff
    elif change == "two_assignments": write_candidate(data, "RESEARCH_SPEC = {}\n")
    elif change == "nonliteral":
        data.source.write_text("RESEARCH_SPEC = dict()\n")
        data.spec["strategy_sha256"] = data.digests[data.factor.name] = hashlib.sha256(data.source.read_bytes()).hexdigest()
    elif change == "capture_tamper":
        path = Path(data.capture["path"]);p=json.loads(path.read_text());p["knowledge_text"] += "tampered";path.write_text(json.dumps(p))
    elif change == "path_escape": data.capture["capture_id"] = "../../elsewhere"
    with pytest.raises(ValueError, match=match): prepare(data)


def test_legacy_noop_reads_nothing_and_optin_requires_flag(setup, monkeypatch):
    monkeypatch.setattr(kr, "_authenticated", lambda *_: pytest.fail("Legacy path read catalog"))
    assert kr.prepare_registration(None, None, [], None, None, cutoff=None) is None
    assert kr.prepare_registration(None, None, [setup.factor], {setup.factor.name:{}}, None, cutoff=None) is None
    with pytest.raises(ValueError, match="explicit --knowledge-capture"):
        kr.prepare_registration(setup.root, None, [setup.factor], {setup.factor.name:setup.spec}, setup.digests, cutoff=setup.cutoff)
    assert kr.read_registered_lineage(None, {}, "old") == {"status":"NOT_RECORDED", "historical_backfill":False}


def epoch_start(data, monkeypatch, *, optin=True):
    from test_invariants import _start_campaign, _input_feasibility, _gold_preflight
    monkeypatch.setattr(epochs, "_now", lambda: data.cutoff)
    if not (data.root/'campaigns/campaign-001/manifest.json').exists(): _start_campaign(data.root)
    kwargs = {"knowledge_capture_id": data.capture["capture_id"], "knowledge_specs": {data.factor.name:data.spec}} if optin else {}
    return epochs.start_epoch(data.root, "campaign-001", "epoch-001", [data.factor], strategy_digests=data.digests,
                              input_feasibility=_input_feasibility([data.factor]), gold_signal_preflight=_gold_preflight([data.factor]), **kwargs)


def test_real_registration_hook_and_reexecution_preserve_old_artifacts(setup, monkeypatch):
    data = setup
    before_capture = Path(data.capture["path"]).read_bytes()
    path = epoch_start(data, monkeypatch)
    epoch = json.loads(path.read_text())
    assert epoch["knowledge_lineage"]["registered_at"] == epoch["created_at"] == data.cutoff
    assert epoch["knowledge_lineage"]["status"] == "RECORDED_AT_REGISTRATION"
    audit = kr.read_registered_lineage(data.root, epoch, data.factor.name)
    assert audit["status"] == "RECORDED_AT_REGISTRATION"
    assert kr.read_registered_lineage(data.root, epoch, "unrecorded")["status"] == "NOT_RECORDED"
    before = {str(p):p.read_bytes() for p in data.root.rglob('*') if p.is_file()}
    with pytest.raises(ValueError): epoch_start(data, monkeypatch)
    assert before == {str(p):p.read_bytes() for p in data.root.rglob('*') if p.is_file()}
    assert Path(data.capture["path"]).read_bytes() == before_capture
    # An audit of a frozen registration never substitutes today's source/review.
    data.source.write_text('Current candidate has changed completely\n')
    monkeypatch.setattr(kr, "_authenticated", lambda *_: pytest.fail("Historical audit read current evidence"))
    assert kr.read_registered_lineage(data.root, epoch, data.factor.name) == audit


def test_invalid_core_optin_creates_no_epoch_and_leaves_campaign_unchanged(setup, monkeypatch):
    from test_invariants import _start_campaign
    data = setup
    path = _start_campaign(data.root);before = path.read_bytes()
    data.catalog["records"] = []
    with pytest.raises(ValueError, match="absent"): epoch_start(data, monkeypatch)
    assert path.read_bytes() == before
    assert not (data.root/'campaigns/campaign-001/epochs/epoch-001/manifest.json').exists()


def test_legacy_core_writes_no_new_fields_or_reads(setup, monkeypatch):
    monkeypatch.setattr(kr, "_authenticated", lambda *_: pytest.fail("Legacy core read evidence"))
    path = epoch_start(setup, monkeypatch, optin=False)
    epoch = json.loads(path.read_text())
    assert "knowledge_lineage" not in epoch and "knowledge_lineage" not in epoch["candidates"][0]


def test_invalid_cli_optin_stops_before_trial_db_and_gold(setup, monkeypatch):
    from scripts import research as cli
    data = setup
    monkeypatch.chdir(data.root.parent)
    monkeypatch.setattr(cli.run, "load_registry", lambda: None)
    monkeypatch.setattr(cli.F, "REGISTRY", {data.factor.name:data.factor})
    monkeypatch.setattr(cli, "RESEARCH_SPECS", {data.factor.name:data.spec})
    monkeypatch.setattr(cli.epochs, "_now", lambda: data.cutoff)
    def forbidden(*_, **__): pytest.fail("Invalid lineage accessed trial DB or live preflight")
    monkeypatch.setattr(cli.run.trials, "TrialLedger", forbidden)
    monkeypatch.setattr(cli.run, "preflight_candidate_registration", forbidden)
    data.catalog["records"] = []
    with pytest.raises(SystemExit, match="계보 사전검사 실패"):
        cli.cmd_epoch_start(SimpleNamespace(factors=[data.factor.name], campaign="campaign-new", epoch="epoch-new", knowledge_capture=data.capture["capture_id"]))


def test_pending_and_unreviewed_do_not_enter_capture_versions(setup):
    rows = [deepcopy(setup.record) for _ in range(3)]
    rows[1]['record_id'] += '_pending';rows[1]['visibility'] = 'PENDING'
    rows[2]['record_id'] += '_unreviewed';rows[2]['review_status'] = 'UNREVIEWED'
    assert [r['record_id'] for r in kr._versions(rows)] == [setup.record['record_id']]


@pytest.mark.parametrize('invalidate_after_preflight', [False, True])
def test_cli_forwards_optin_and_core_reauthenticates_after_preflight(setup, monkeypatch, invalidate_after_preflight):
    from scripts import research as cli
    from engine.factors import Registry
    from test_invariants import _start_campaign, _input_feasibility, _gold_preflight
    data = setup
    monkeypatch.chdir(data.root.parent)
    monkeypatch.setattr(epochs, '_now', lambda: data.cutoff)
    _start_campaign(data.root)
    registry = Registry()
    registry.add(data.factor)
    monkeypatch.setattr(cli.F, 'REGISTRY', registry)
    monkeypatch.setattr(cli.run, 'load_registry', lambda: None)
    monkeypatch.setattr(cli, 'RESEARCH_SPECS', {data.factor.name: data.spec})
    monkeypatch.setattr(cli.run.trials, 'TrialLedger', lambda *_: SimpleNamespace(definition_hashes=lambda: set()))
    monkeypatch.setattr(cli.run, '_load', lambda: object())
    calls = []
    def preflight(_campaign, _panel, factors):
        calls.append('input_and_gold_preflight')
        if invalidate_after_preflight:
            data.catalog['records'] = []
        return _input_feasibility(factors), _gold_preflight(factors)
    monkeypatch.setattr(cli.run, 'preflight_candidate_registration', preflight)
    monkeypatch.setattr(cli.run.silver, 'connect', lambda *_a, **_k: pytest.fail('Real DB reached'))
    args = SimpleNamespace(factors=[data.factor.name], campaign='campaign-001', epoch='epoch-001',
                           knowledge_capture=data.capture['capture_id'])
    path = data.root/'campaigns/campaign-001/epochs/epoch-001/manifest.json'
    if invalidate_after_preflight:
        with pytest.raises(SystemExit, match='absent'):
            cli.cmd_epoch_start(args)
        assert not path.exists()
    else:
        cli.cmd_epoch_start(args)
        assert kr.read_registered_lineage(data.root, json.loads(path.read_text()), data.factor.name)['status'] == 'RECORDED_AT_REGISTRATION'
    assert calls == ['input_and_gold_preflight']
