from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

from scripts import retrospective_finalize as finalize


ROOT = Path(__file__).resolve().parents[1]
ACTUAL_RESULT = (
    ROOT
    / "research/audits/retrospective-qualified-oos-20260807-003/result.json"
)


def _actual_statistics() -> dict:
    return json.loads(ACTUAL_RESULT.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _completion_fixture(tmp_path: Path) -> tuple[Path, Path, dict, str]:
    root = tmp_path / "repo"
    audit_dir = root / "research/audits" / finalize.AUDIT_ID
    statistics_path = audit_dir / "result.json"
    _write_json(statistics_path, _actual_statistics())

    validation_manifest = {
        "audit_id": finalize.AUDIT_ID,
        "statistics": {
            "result_path": str(statistics_path.relative_to(root)),
            "result_sha256": finalize._file_digest(statistics_path),
        },
    }
    manifest_digest = finalize._payload_digest(validation_manifest)

    parity = {
        "validation_manifest_digest": manifest_digest,
        "passed": True,
        "results": [
            {
                "factor": name,
                "definition_hash": definition_hash,
                "passed": True,
            }
            for name, definition_hash in finalize.FACTORS.items()
        ],
    }
    _write_json(audit_dir / "implementation-verification.json", parity)

    calibration_frame = pd.DataFrame({"kind": ["random"], "replicate": [0]})
    calibration_path = audit_dir / "null-calibration.parquet"
    calibration_frame.to_parquet(calibration_path, index=False)
    calibration = {
        "validation_manifest_digest": manifest_digest,
        "passed": True,
        "parquet_path": calibration_path.name,
        "parquet_sha256": finalize._file_digest(calibration_path),
    }
    _write_json(audit_dir / "null-calibration.json", calibration)
    return root, audit_dir, validation_manifest, manifest_digest


def test_statistics_pass_authenticates_actual_retrospective_audit() -> None:
    passed, failures = finalize._statistics_pass(_actual_statistics())

    assert passed is True
    assert failures == []


@pytest.mark.parametrize(
    ("mutate", "expected_failure"),
    [
        (
            lambda payload: payload["factors"][0]["retrospective_later_period"].update(
                {"t4_effect_and_by_pass": False}
            ),
            "operating_return_on_capital_employed:retrospective_t4",
        ),
        (
            lambda payload: payload.update({"gold_write": True}),
            "gold_write",
        ),
        (
            lambda payload: payload["factors"][0].update(
                {"definition_hash": "tampered"}
            ),
            "operating_return_on_capital_employed:definition_hash",
        ),
    ],
)
def test_statistics_pass_rejects_t4_failure_and_tampering(
    mutate, expected_failure: str,
) -> None:
    payload = deepcopy(_actual_statistics())
    mutate(payload)

    passed, failures = finalize._statistics_pass(payload)

    assert passed is False
    assert expected_failure in failures


def test_exclusive_json_and_text_writes_never_overwrite(tmp_path: Path) -> None:
    json_path = tmp_path / "artifact.json"
    text_path = tmp_path / "artifact.md"
    finalize._json_exclusive(json_path, {"version": 1})
    finalize._text_exclusive(text_path, "first")

    with pytest.raises(FileExistsError):
        finalize._json_exclusive(json_path, {"version": 2})
    with pytest.raises(FileExistsError):
        finalize._text_exclusive(text_path, "second")

    assert json.loads(json_path.read_text(encoding="utf-8")) == {"version": 1}
    assert text_path.read_text(encoding="utf-8") == "first"
    assert not list(tmp_path.glob(".*.tmp"))


def test_exclusive_parquet_write_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "artifact.parquet"
    first = pd.DataFrame({"value": [1, 2]})
    finalize._parquet_exclusive(path, first)

    with pytest.raises(FileExistsError):
        finalize._parquet_exclusive(path, pd.DataFrame({"value": [9]}))

    pd.testing.assert_frame_equal(pd.read_parquet(path), first)
    assert not list(tmp_path.glob(".*.tmp"))


def test_completion_refuses_failed_null_calibration(tmp_path: Path) -> None:
    root, audit_dir, manifest, digest = _completion_fixture(tmp_path)
    null_path = audit_dir / "null-calibration.json"
    calibration = json.loads(null_path.read_text(encoding="utf-8"))
    calibration["passed"] = False
    _write_json(null_path, calibration)

    result = finalize.write_completion(root, audit_dir, manifest, digest)

    assert result is None
    assert not (audit_dir / "completion.json").exists()
    assert not (audit_dir / "completion.md").exists()


def test_completion_refuses_stale_manifest_digest(tmp_path: Path) -> None:
    root, audit_dir, manifest, digest = _completion_fixture(tmp_path)
    manifest["audit_id"] = "changed-after-digest"

    with pytest.raises(SystemExit, match="manifest digest"):
        finalize.write_completion(root, audit_dir, manifest, digest)

    assert not (audit_dir / "completion.json").exists()


def test_completion_refuses_tampered_statistics_artifact(tmp_path: Path) -> None:
    root, audit_dir, manifest, digest = _completion_fixture(tmp_path)
    statistics_path = root / manifest["statistics"]["result_path"]
    statistics = json.loads(statistics_path.read_text(encoding="utf-8"))
    statistics["unexpected_after_freeze"] = True
    _write_json(statistics_path, statistics)

    with pytest.raises(SystemExit, match="result artifact"):
        finalize.write_completion(root, audit_dir, manifest, digest)

    assert not (audit_dir / "completion.json").exists()


def test_completion_writes_only_after_all_authenticated_inputs_pass(
    tmp_path: Path,
) -> None:
    root, audit_dir, manifest, digest = _completion_fixture(tmp_path)

    result = finalize.write_completion(root, audit_dir, manifest, digest)

    assert result is not None
    assert result["engineering_parity_pass"] is True
    assert result["null_calibration_pass"] is True
    assert result["retrospective_statistics_pass"] is True
    assert result["strict_gold_approval"] == "BLOCKED_CLEAN_OOS"
    assert result["gold_write"] is False
    assert (audit_dir / "completion.json").is_file()
    assert (audit_dir / "completion.md").is_file()


def _validation_manifest_fixture(*, binding_sha: str, created_at: str) -> dict:
    return {
        "schema_version": "retrospective-validation-manifest-v1",
        "audit_id": finalize.AUDIT_ID,
        "created_at": created_at,
        "ruleset_version": "test-ruleset",
        "boundary": {"oos_start": "2023-06", "oos_end": "2026-05"},
        "snapshots": {"confirmation_sha256": "frozen-snapshot"},
        "factors": [{"name": "factor-a", "definition_hash": "factor-hash"}],
        "implementation_bindings": [{
            "factor": "factor-a",
            "implementation_sha256": binding_sha,
        }],
        "gold_write": False,
    }


def test_validation_manifest_reuses_exact_current_scope(
    tmp_path: Path, monkeypatch,
) -> None:
    audit_dir = tmp_path / "audit"
    path = audit_dir / finalize.AUDIT_MANIFEST_NAME
    existing = _validation_manifest_fixture(
        binding_sha="sql-v1", created_at="2026-08-07T00:00:00+00:00",
    )
    candidate = _validation_manifest_fixture(
        binding_sha="sql-v1", created_at="2026-08-08T00:00:00+00:00",
    )
    _write_json(path, existing)
    monkeypatch.setattr(
        finalize, "_build_validation_manifest", lambda *_args: candidate,
    )

    manifest, digest = finalize._ensure_validation_manifest(
        tmp_path, audit_dir, {}, [], object(),
    )

    assert manifest == existing
    assert digest == finalize._payload_digest(existing)
    assert json.loads(path.read_text(encoding="utf-8")) == existing
    assert not (audit_dir / "validation-manifest-002.json").exists()


def test_validation_manifest_appends_revision_for_binding_only_change(
    tmp_path: Path, monkeypatch,
) -> None:
    audit_dir = tmp_path / "audit"
    original_path = audit_dir / finalize.AUDIT_MANIFEST_NAME
    original = _validation_manifest_fixture(
        binding_sha="sql-v1", created_at="2026-08-07T00:00:00+00:00",
    )
    candidate = _validation_manifest_fixture(
        binding_sha="sql-v2", created_at="2026-08-08T00:00:00+00:00",
    )
    _write_json(original_path, original)
    monkeypatch.setattr(
        finalize, "_build_validation_manifest", lambda *_args: candidate,
    )

    manifest, digest = finalize._ensure_validation_manifest(
        tmp_path, audit_dir, {}, [], object(),
    )

    revision_path = audit_dir / "validation-manifest-002.json"
    assert manifest == candidate
    assert digest == finalize._payload_digest(candidate)
    assert json.loads(original_path.read_text(encoding="utf-8")) == original
    assert json.loads(revision_path.read_text(encoding="utf-8")) == candidate


def test_validation_manifest_rejects_any_non_binding_scope_change(
    tmp_path: Path, monkeypatch,
) -> None:
    audit_dir = tmp_path / "audit"
    original_path = audit_dir / finalize.AUDIT_MANIFEST_NAME
    original = _validation_manifest_fixture(
        binding_sha="sql-v1", created_at="2026-08-07T00:00:00+00:00",
    )
    candidate = _validation_manifest_fixture(
        binding_sha="sql-v2", created_at="2026-08-08T00:00:00+00:00",
    )
    candidate["snapshots"] = {"confirmation_sha256": "changed-snapshot"}
    _write_json(original_path, original)
    monkeypatch.setattr(
        finalize, "_build_validation_manifest", lambda *_args: candidate,
    )

    with pytest.raises(SystemExit, match="SQL 구현 이외의 동결 validation scope"):
        finalize._ensure_validation_manifest(
            tmp_path, audit_dir, {}, [], object(),
        )

    assert json.loads(original_path.read_text(encoding="utf-8")) == original
    assert not (audit_dir / "validation-manifest-002.json").exists()


def test_cli_forwards_one_factor_only_to_parity(monkeypatch) -> None:
    selected = "return_kurtosis_24m"
    captured: dict[str, object] = {}
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(sys, "argv", ["retrospective_finalize.py", "--step", "parity", "--factor", selected])
    monkeypatch.setattr(finalize, "_source", lambda _root: {})
    monkeypatch.setattr(finalize, "_targets", lambda _source: [])
    monkeypatch.setattr(finalize.run, "_load", lambda: object())
    monkeypatch.setattr(
        finalize,
        "_ensure_validation_manifest",
        lambda *_args: ({}, "manifest-digest"),
    )

    def fake_verify(*_args, selected_factor=None, **_kwargs):
        captured["selected_factor"] = selected_factor
        return {
            "passed": False,
            "attempts": [{
                "result": {
                    "factor": selected,
                    "status": "PASS",
                    "failure_reasons": [],
                }
            }],
        }

    monkeypatch.setattr(finalize, "verify_parity", fake_verify)
    monkeypatch.setattr(
        finalize,
        "calibrate_null",
        lambda *_args, **_kwargs: pytest.fail("null 단계가 실행되면 안 됩니다"),
    )
    monkeypatch.setattr(finalize, "write_completion", lambda *_args: None)

    finalize.main()

    assert captured == {"selected_factor": selected}
