import json

import pytest

from scripts.freeze_monthly_comparison_catalog import build_catalog
from scripts.dashboard_exports.export_monthly_comparison import export
from strategies import run_monthly_comparison as runner


def row():
    return dict(name="example", version=3, status="APPROVED", frequency="daily",
                definition_hash="b" * 16, implementation_hash="c" * 64,
                predicted_sign="-1", lookback_translation="21_krx_sessions_per_month")


def prior():
    return {"factors": [{"name": "example", "definition_hash": "a" * 16}]}


def test_freeze_keeps_exact_set_and_direction():
    result = build_catalog([row()], as_of="2026-09-30T00:00:00+00:00", prior=prior())
    assert result["approved_count"] == 1
    assert result["factors"][0]["predicted_sign"] == -1
    assert result["is_live"] is False


@pytest.mark.parametrize("field,value", [
    ("name", "different"), ("frequency", "monthly"), ("status", "RETIRED"),
    ("definition_hash", None), ("implementation_hash", ""), ("predicted_sign", "0"), ("version", 0),
])
def test_invalid_identity_refused(field, value):
    changed = row() | {field: value}
    with pytest.raises(ValueError):
        build_catalog([changed], as_of="2026-09-30", prior=prior())


def test_duplicate_approval_refused():
    with pytest.raises(ValueError):
        build_catalog([row(), row() | {"version": 4}], as_of="2026-09-30", prior=prior())


@pytest.fixture
def prepared(tmp_path):
    root = tmp_path / "research"
    (root / "campaigns").mkdir(parents=True)
    old = tmp_path / "prior.json"
    runner.save_new(old, prior())
    catalog = build_catalog([row()], as_of="2026-09-30T11:00:00+00:00", prior=prior())
    catalog["prior_snapshot_sha256"] = runner.hashlib.sha256(old.read_bytes()).hexdigest()
    # Ensure public exporter is an allowlist, not a copy of arbitrary local metadata.
    catalog["private_debug"] = "do-not-publish"
    cp = tmp_path / "catalog.json"
    runner.save_new(cp, catalog)
    plan = tmp_path / "plan.json"
    runner.prepare(cp, decision_start="2025-01", decision_end="2025-02", output=plan, research_root=root)
    runner.run(plan, output=tmp_path / "run", research_root=root)
    audit = tmp_path / "audit.json"
    runner.save_new(audit, {"as_of": catalog["as_of"], "read_only": True, "return_contracts": []})
    return [cp, plan, tmp_path / "run/readiness.json", audit, old, tmp_path / "public.json"]


def test_public_readiness_no_performance_or_internal_paths(prepared):
    result = export(*prepared)
    assert result["published_performance"] is False
    text = prepared[-1].read_text()
    public = json.loads(text)
    assert public["factor_count"] == 1
    assert public["planned_comparisons"] == 4 and public["completed_comparisons"] == 0
    assert public["historical_definition_changed"] == 1
    assert public["factors"][0]["comparison_status"] == "NOT_COMPUTED"
    assert "do-not-publish" not in text and str(prepared[0].parent) not in text
    with pytest.raises(FileExistsError):
        export(*prepared)


@pytest.mark.parametrize("target,field,value", [
    (2, "real_performance_computed", True), (2, "plan_sha256", "0" * 64),
    (2, "factor_count", 100), (3, "as_of", "2020-01-01"), (3, "read_only", False),
])
def test_public_export_refuses_mismatched_evidence(prepared, target, field, value):
    path = prepared[target]
    data = runner.read_json(path)
    data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        export(*prepared)
    assert not prepared[-1].exists()


def test_public_export_refuses_changed_catalog(prepared):
    path = prepared[0]
    data = runner.read_json(path)
    data["factors"][0]["definition_hash"] = "d" * 16
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="catalog changed"):
        export(*prepared)
