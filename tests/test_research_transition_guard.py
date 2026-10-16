import json

import pytest

from engine import research_transition_guard as guard


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    pointer = tmp_path / "research" / "active-generation.json"
    pointer.parent.mkdir()
    monkeypatch.setattr(guard, "ACTIVE_POLICY", pointer)
    return pointer


def test_uninitialized_legacy_checkout_remains_reproducible(workspace):
    assert guard.new_generation_active() is False
    guard.require_legacy_cli("evaluate")


@pytest.mark.parametrize('generation_id',['reference-factor-v3','phenomenon-research-v1'])
def test_new_empty_library_never_falls_back_to_legacy(workspace,generation_id):
    workspace.write_text(json.dumps({"generation_id": generation_id}))
    with pytest.raises(ValueError, match="archived"):
        guard.require_legacy_read("explicit legacy factor list")
    with pytest.raises(ValueError, match="archived"):
        guard.require_legacy_cli("evaluate")
    guard.require_legacy_cli("evaluate", explicit=True)


@pytest.mark.parametrize('generation_id',['reference-factor-v3','phenomenon-research-v1'])
def test_explicit_legacy_flag_cannot_enable_gold_writes(workspace,generation_id):
    workspace.write_text(json.dumps({"generation_id": generation_id}))
    with pytest.raises(ValueError, match="read-only"):
        guard.require_legacy_cli("campaign-publish", explicit=True, writes_gold=True)


def test_corrupt_pointer_fails_closed(workspace):
    workspace.write_text("[]")
    with pytest.raises(ValueError, match="Invalid"):
        guard.require_legacy_read("cache")
    workspace.write_text("broken")
    with pytest.raises(ValueError):
        guard.require_legacy_gold_write("publish")


def test_deleted_pointer_does_not_restore_old_gold(workspace):
    (workspace.parent / "generations" / "reference-factor-v3").mkdir(parents=True)
    with pytest.raises(ValueError, match="missing"):
        guard.require_legacy_read("cache")
