#!/usr/bin/env python
"""Complete engineering and null checks for the frozen retrospective family.

This runner deliberately writes only append-only audit artifacts.  It never
changes the superseded campaign, never relabels exposed history as clean OOS,
and never writes Gold values.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

import pandas as pd
import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import gate, implementation, null, panel as P, silver, trials
from engine.boundaries import (
    CampaignWindow, QUALIFICATION_POLICY, validate_manifest,
)
from scripts import run


AUDIT_ID = "retrospective-qualified-oos-20260807-003"
AUDIT_RULESET_VERSION = "fr-3.9.0"
SOURCE_CAMPAIGN = "campaign-20260807-002"
DISCOVERY_CUTOFF = "2023-05-31"
SNAPSHOT_CUTOFF = "2026-06-30"
OOS_START = pd.Period("2023-06", freq="M")
OOS_END = pd.Period("2026-05", freq="M")
FACTORS = {
    "turnover_volatility_12m": "07f156b1d7953440",
    "return_kurtosis_24m": "be70b24e1222fb72",
    "operating_return_on_capital_employed": "aa11ccad9cfd19c6",
}
AUDIT_MANIFEST_NAME = "validation-manifest.json"
PARITY_STATEMENT_TIMEOUT_MS = 30 * 60 * 1000


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def _payload_digest(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_exclusive(path: Path, payload: dict) -> None:
    """Atomically create one immutable JSON artifact; never overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(
                (json.dumps(
                    payload, ensure_ascii=False, indent=2, allow_nan=False,
                ) + "\n").encode("utf-8")
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _parquet_exclusive(path: Path, frame: pd.DataFrame) -> None:
    """Atomically create one immutable parquet artifact; never overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        frame.to_parquet(temporary, index=False)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _text_exclusive(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _next_attempt_path(directory: Path, prefix: str = "attempt") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for number in range(1, 100_000):
        path = directory / f"{prefix}-{number:05d}.json"
        if not path.exists():
            return path
    raise RuntimeError(f"attempt 번호 공간이 소진되었습니다: {directory}")


def _source(root: Path) -> dict:
    return json.loads(
        (root / "research/campaigns" / SOURCE_CAMPAIGN / "manifest.json").read_text(
            encoding="utf-8"
        )
    )


def _targets(source: dict):
    run.load_registry()
    frozen = {
        row["name"]: row["definition_hash"]
        for row in source.get("qualified_factors", [])
    }
    if frozen != FACTORS:
        raise SystemExit("source campaign의 동결 qualified family가 달라졌습니다")
    targets = [run.F.REGISTRY[name] for name in FACTORS]
    if {factor.name: factor.definition_hash for factor in targets} != FACTORS:
        raise SystemExit("현재 Python 후보 정의가 동결 hash와 다릅니다")
    return targets


def _window_and_panels(base):
    window = CampaignWindow.from_completed_snapshot(
        discovery_data_cutoff=DISCOVERY_CUTOFF,
        snapshot_cutoff=SNAPSHOT_CUTOFF,
        oos_months=gate.TH["min_oos_months"],
    )
    if window.oos_signal_start != OOS_START or window.oos_signal_end != OOS_END:
        raise SystemExit("회고 감사 경계 계약이 달라졌습니다")
    snapshot = run._scope_snapshot_panel(base, snapshot_cutoff=SNAPSHOT_CUTOFF)
    discovery = run._scope_discovery_panel(
        base, data_cutoff=DISCOVERY_CUTOFF, oos_start=OOS_START,
    )
    confirmation = run._scope_confirmation_panel(
        base,
        data_cutoff=DISCOVERY_CUTOFF,
        oos_start=OOS_START,
        oos_end=OOS_END,
    )
    return window, snapshot, discovery, confirmation


def _campaign_manifest(source: dict, window, snapshot, discovery) -> dict:
    return {
        "protocol_version": source["protocol_version"],
        "ruleset_version": AUDIT_RULESET_VERSION,
        "campaign_id": f"{AUDIT_ID}-in-memory",
        "snapshot": {
            **window.snapshot_manifest(),
            "source": "RDS public Silver",
            "input_digest": P.snapshot_digest(snapshot),
            "discovery_input_digest": P.snapshot_digest(discovery),
        },
        "discovery": window.discovery_manifest(),
        "oos": window.oos_manifest(),
        "qualification_policy": QUALIFICATION_POLICY,
        "discovery_family_size": int(source["discovery_family_size"]),
        "discovery_family_digest": source["discovery_family_digest"],
        "oos_family_digest": source["oos_family_digest"],
        "qualified_factors": source["qualified_factors"],
    }


def _gold_scope(confirmation) -> tuple[dict[str, pd.Series], pd.DataFrame, dict]:
    with silver.connect(read_only=True) as conn:
        silver.verify_live_total_return_contract(
            conn,
            confirmation.meta.get("return_contract_validation_evidence"),
        )
        run._verify_confirmation_live_identity(conn, confirmation)
        approved = run._approved_signals(conn, confirmation.monthly)
        gold_trials = silver.load_gold_trial_history(conn)
    names = sorted(approved)
    return approved, gold_trials, {
        "approved_factor_names": names,
        "approved_factor_count": len(names),
        "approved_family_digest": run._signal_family_digest(approved),
        "trial_definition_hashes": sorted(
            set(gold_trials.get("definition_hash", pd.Series(dtype=str)).astype(str))
        ),
    }


def _statistics_pass(result: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []
    expected_split = {
        "data_cutoff": DISCOVERY_CUTOFF,
        "is_start": str(gate.RESEARCH_START),
        "is_end": "2023-04",
        "is_months": 62,
        "embargo_month": "2023-05",
        "oos_start": str(OOS_START),
        "oos_end": str(OOS_END),
        "oos_months": 36,
        "last_return_month": "2026-06",
        "closure_month": "2026-07",
    }
    if result.get("audit_id") != AUDIT_ID:
        failures.append("audit_id")
    if result.get("source_campaign") != SOURCE_CAMPAIGN:
        failures.append("source_campaign")
    if result.get("ruleset_version") != AUDIT_RULESET_VERSION:
        failures.append("ruleset_version")
    if result.get("split") != expected_split:
        failures.append("split")
    if result.get("gold_write") is not False:
        failures.append("gold_write")
    if result.get("candidate_count") != len(FACTORS):
        failures.append("candidate_count")
    threshold_keys = (
        "min_ic", "min_rank_icir", "neutral_ic", "neutral_ic_retention",
        "oos_ic", "oos_ic_retention", "min_oos_months", "fdr_q",
    )
    recorded_thresholds = result.get("thresholds", {})
    for key in threshold_keys:
        if recorded_thresholds.get(key) != gate.TH[key]:
            failures.append(f"threshold:{key}")
    rows = result.get("factors", [])
    by_name = {row.get("factor"): row for row in rows}
    if set(by_name) != set(FACTORS):
        failures.append("factor_family")
        return False, failures
    for name, definition_hash in FACTORS.items():
        row = by_name[name]
        historical = row.get("historical_is", {})
        later = row.get("retrospective_later_period", {})
        if row.get("definition_hash") != definition_hash:
            failures.append(f"{name}:definition_hash")
        if not historical.get("auto_qualified") or historical.get("failed_checks"):
            failures.append(f"{name}:historical_is")
        if historical.get("months") != 62 or historical.get("t5_pass") is not True:
            failures.append(f"{name}:historical_coverage_or_t5")
        required_later = (
            later.get("months") == 36,
            later.get("t4_effect_and_by_pass") is True,
            later.get("absolute_effect_threshold_pass") is True,
            later.get("retention_threshold_pass") is True,
            later.get("rank_icir_threshold_pass") is True,
            later.get("neutral_threshold_pass") is True,
        )
        if not all(required_later):
            failures.append(f"{name}:retrospective_t4")
    return not failures, failures


def _build_validation_manifest(
    root: Path, source: dict, targets, base,
) -> dict:
    window, snapshot, discovery, confirmation = _window_and_panels(base)
    approved, gold_trials, gold_scope = _gold_scope(confirmation)
    del approved
    external = [
        (str(row.definition_hash), None, None)
        for row in gold_trials.itertuples(index=False)
    ]
    trial_summary = trials.read_trial_summary(
        run.TRIAL_DB, external=external, ruleset_version=AUDIT_RULESET_VERSION,
    )
    source_path = root / "research/campaigns" / SOURCE_CAMPAIGN / "manifest.json"
    result_path = root / "research/audits" / AUDIT_ID / "result.json"
    report_path = root / "research/audits" / AUDIT_ID / "report.md"
    statistics = json.loads(result_path.read_text(encoding="utf-8"))
    passed, failures = _statistics_pass(statistics)
    if not passed:
        raise SystemExit(f"기존 회고 통계 artifact 인증 실패: {failures}")
    if statistics.get("approved_gold_factors") != gold_scope["approved_factor_names"]:
        raise SystemExit("회고 T5의 Gold family와 현재 RDS Gold family가 다릅니다")
    bindings = [run._implementation_contract(factor)[3] for factor in targets]
    return {
        "schema_version": "retrospective-validation-manifest-v1",
        "audit_id": AUDIT_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label": "RETROSPECTIVE_ONLY_ALREADY_EXPOSED",
        "ruleset_version": AUDIT_RULESET_VERSION,
        "thresholds": gate.TH,
        "qualification_policy": QUALIFICATION_POLICY,
        "source_campaign": {
            "id": SOURCE_CAMPAIGN,
            "path": str(source_path.relative_to(root)),
            "sha256": _file_digest(source_path),
            "discovery_family_size": int(source["discovery_family_size"]),
            "discovery_family_digest": source["discovery_family_digest"],
            "oos_family_digest": source["oos_family_digest"],
        },
        "statistics": {
            "result_path": str(result_path.relative_to(root)),
            "result_sha256": _file_digest(result_path),
            "report_path": str(report_path.relative_to(root)),
            "report_sha256": _file_digest(report_path),
        },
        "boundary": {
            **window.discovery_manifest(),
            "oos": window.oos_manifest(),
            "snapshot_cutoff": SNAPSHOT_CUTOFF,
        },
        "snapshots": {
            "snapshot_sha256": P.snapshot_digest(snapshot),
            "discovery_sha256": P.snapshot_digest(discovery),
            "confirmation_sha256": P.snapshot_digest(confirmation),
        },
        "factors": [
            {"name": factor.name, "definition_hash": factor.definition_hash}
            for factor in targets
        ],
        "implementation_bindings": bindings,
        "gold_scope": gold_scope,
        "trial_scope": {
            "trial_count": int(trial_summary.count),
            "prior_sharpes": list(trial_summary.sharpes),
            "ledger_sha256": (
                _file_digest(run.TRIAL_DB) if run.TRIAL_DB.is_file() else None
            ),
        },
        "gold_write": False,
    }


def _ensure_validation_manifest(
    root: Path, audit_dir: Path, source: dict, targets, base,
) -> tuple[dict, str]:
    audit_dir.mkdir(parents=True, exist_ok=True)
    candidate = _build_validation_manifest(root, source, targets, base)

    def stable(payload: dict, *, without_bindings: bool = False) -> dict:
        value = dict(payload)
        value.pop("created_at", None)
        if without_bindings:
            value.pop("implementation_bindings", None)
        return value

    paths = [audit_dir / AUDIT_MANIFEST_NAME]
    paths.extend(sorted(audit_dir.glob("validation-manifest-[0-9][0-9][0-9].json")))
    existing: list[tuple[Path, dict]] = []
    for path in paths:
        if path.is_file():
            existing.append((path, json.loads(path.read_text(encoding="utf-8"))))
    for _path, manifest in reversed(existing):
        if stable(manifest) == stable(candidate):
            return manifest, _payload_digest(manifest)
    if existing:
        _latest_path, latest = existing[-1]
        if stable(latest, without_bindings=True) != stable(
            candidate, without_bindings=True,
        ):
            raise SystemExit(
                "SQL 구현 이외의 동결 validation scope가 변경됐습니다. "
                "기존 회고 감사와 합칠 수 없습니다"
            )
        next_number = len(existing) + 1
        path = audit_dir / f"validation-manifest-{next_number:03d}.json"
    else:
        path = audit_dir / AUDIT_MANIFEST_NAME
    _json_exclusive(path, candidate)
    return candidate, _payload_digest(candidate)


def _verify_one_implementation(manifest: dict, factor):
    """Run one production-equivalent parity check on an isolated DB session."""
    window = validate_manifest(
        manifest, expected_oos_months=gate.TH["min_oos_months"],
    )
    base = run._load()
    discovery = run._scope_discovery_panel(
        base,
        data_cutoff=window.discovery_data_cutoff,
        oos_start=window.oos_signal_start,
    )
    digest = P.snapshot_digest(discovery)
    if digest != manifest["snapshot"]["discovery_input_digest"]:
        raise ValueError("회고 discovery Silver snapshot digest가 달라졌습니다")
    start = gate.RESEARCH_START
    end = window.discovery_signal_end
    from factors.candidate_loader import RESEARCH_SPECS

    strategy_sha256 = RESEARCH_SPECS[factor.name]["strategy_sha256"]
    binding = None
    interrupted = False
    try:
        _ref, spec, sql_path, binding = run._implementation_contract(factor)
        with silver.connect(read_only=True) as conn:
            conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            silver.verify_live_total_return_contract(
                conn,
                discovery.meta.get("return_contract_validation_evidence"),
            )
            P.verify_live_asset_identity(
                conn, discovery, cutoff=window.discovery_data_cutoff,
            )
            research_frame = run._research_input_panel(discovery)
            frame = research_frame.monthly
            in_scope = (
                research_frame.universe
                & frame["ym"].ge(start)
                & frame["ym"].le(end)
            )
            raw = run.research_policy.compute_factor(factor, frame)
            if not isinstance(raw, pd.Series) or not raw.index.equals(frame.index):
                raise ValueError(
                    "Python factor가 입력 index의 Series를 반환하지 않습니다: "
                    f"{factor.name}"
                )
            raw = pd.to_numeric(raw, errors="coerce")
            finite = raw.notna() & raw.abs().ne(float("inf"))
            valid = in_scope & finite
            python_frame = frame.loc[valid, ["asset_id", "trade_date"]].rename(
                columns={"trade_date": "as_of_date"},
            )
            python_frame["value"] = raw.loc[valid].astype(float).to_numpy()
            print(f"  [parity SQL] {factor.name} {start}~{end}", flush=True)
            frames: list[pd.DataFrame] = []
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SET LOCAL statement_timeout = {PARITY_STATEMENT_TIMEOUT_MS}"
                )
                cursor.execute(sql_path.read_text(encoding="utf-8"), {
                    "start_month": f"{start}-01",
                    "end_month": f"{end}-01",
                })
                columns = [column.name for column in cursor.description]
                while rows := cursor.fetchmany(20_000):
                    frames.append(pd.DataFrame.from_records(rows, columns=columns))
        sql_frame = (
            pd.concat(frames, ignore_index=True)
            if frames else pd.DataFrame(columns=("asset_id", "as_of_date", "value", "rank"))
        )
        evidence = implementation.compare_parity(
            factor,
            python_frame,
            sql_frame,
            implementation_uri=binding["implementation_uri"],
            implementation_sha256=binding["implementation_sha256"],
            manifest_spec=spec,
            discovery_signal_start=start,
            discovery_signal_end=end,
            discovery_snapshot_digest=digest,
            strategy_sha256=strategy_sha256,
            atol=float(spec.get("parity_atol", implementation.DEFAULT_ATOL)),
            rtol=float(spec.get("parity_rtol", implementation.DEFAULT_RTOL)),
            allow_tolerance_equivalent_ranks=bool(spec.get(
                "allow_tolerance_equivalent_ranks", False,
            )),
        )
    except KeyboardInterrupt as exc:
        interrupted = True
        evidence = implementation.failure_evidence(
            factor,
            discovery_signal_start=start,
            discovery_signal_end=end,
            discovery_snapshot_digest=digest,
            strategy_sha256=strategy_sha256,
            stage="interrupted",
            error=exc,
            binding=binding,
        )
    except Exception as exc:
        evidence = implementation.failure_evidence(
            factor,
            discovery_signal_start=start,
            discovery_signal_end=end,
            discovery_snapshot_digest=digest,
            strategy_sha256=strategy_sha256,
            stage="sql_execute_or_parity",
            error=exc,
            binding=binding,
        )
    return evidence, interrupted


def _write_parity_attempt(
    audit_dir: Path, manifest_digest: str, evidence: dict,
) -> dict:
    payload = {
        "schema_version": "retrospective-engineering-parity-attempt-v2",
        "audit_id": AUDIT_ID,
        "validation_manifest_digest": manifest_digest,
        "label": "RETROSPECTIVE_ENGINEERING_PARITY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "factor": evidence["factor"],
        "result": evidence,
        "passed": bool(evidence["passed"]),
        "gold_write": False,
    }
    directory = audit_dir / "implementation-attempts" / evidence["factor"]
    while True:
        path = _next_attempt_path(directory)
        try:
            _json_exclusive(path, payload)
            return payload
        except FileExistsError:
            continue


def _passed_parity_attempts(
    audit_dir: Path, manifest_digest: str,
) -> dict[str, dict]:
    passed: dict[str, dict] = {}
    for name in FACTORS:
        directory = audit_dir / "implementation-attempts" / name
        for path in sorted(directory.glob("attempt-*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            result = payload.get("result", {})
            if (
                payload.get("validation_manifest_digest") == manifest_digest
                and payload.get("factor") == name
                and payload.get("passed") is True
                and result.get("passed") is True
                and result.get("definition_hash") == FACTORS[name]
            ):
                passed[name] = result
                break
    return passed


def _finalize_parity(audit_dir: Path, manifest_digest: str) -> dict | None:
    passed = _passed_parity_attempts(audit_dir, manifest_digest)
    if set(passed) != set(FACTORS):
        return None
    payload = {
        "schema_version": "retrospective-engineering-parity-v2",
        "audit_id": AUDIT_ID,
        "validation_manifest_digest": manifest_digest,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "results": [passed[name] for name in FACTORS],
        "passed": True,
        "gold_write": False,
    }
    path = audit_dir / "implementation-verification.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if (
            existing.get("validation_manifest_digest") != manifest_digest
            or existing.get("passed") is not True
            or {row.get("factor") for row in existing.get("results", [])} != set(FACTORS)
        ):
            raise SystemExit("기존 parity final artifact가 현재 validation manifest와 다릅니다")
        return existing
    _json_exclusive(path, payload)
    return payload


def verify_parity(
    root: Path, audit_dir: Path, source: dict, targets, base,
    *, selected_factor: str | None = None,
) -> dict:
    validation_manifest, manifest_digest = _ensure_validation_manifest(
        root, audit_dir, source, targets, base,
    )
    window, snapshot, discovery, _confirmation = _window_and_panels(base)
    campaign_manifest = _campaign_manifest(source, window, snapshot, discovery)
    chosen = [factor for factor in targets if selected_factor in (None, factor.name)]
    if not chosen:
        raise SystemExit(f"동결 family에 없는 factor입니다: {selected_factor}")
    existing_passes = _passed_parity_attempts(audit_dir, manifest_digest)
    attempts: list[dict] = []
    for factor in chosen:
        if factor.name in existing_passes:
            attempts.append({
                "factor": factor.name, "passed": True,
                "result": existing_passes[factor.name], "reused": True,
            })
            continue
        evidence, interrupted = _verify_one_implementation(campaign_manifest, factor)
        attempts.append(_write_parity_attempt(audit_dir, manifest_digest, evidence))
        if interrupted:
            raise KeyboardInterrupt
    final = _finalize_parity(audit_dir, manifest_digest)
    return {
        "schema_version": "retrospective-engineering-parity-run-v2",
        "validation_manifest_digest": _payload_digest(validation_manifest),
        "attempts": attempts,
        "passed": final is not None,
        "final": final,
    }


def calibrate_null(
    root: Path, audit_dir: Path, source: dict, targets, base, *, n: int,
) -> dict:
    if n != 25:
        raise SystemExit("정식 T4.4는 generator 종류별 정확히 25개 family로 실행하세요: --n 25")
    validation_manifest, manifest_digest = _ensure_validation_manifest(
        root, audit_dir, source, targets, base,
    )
    _window, _snapshot, _discovery, confirmation = _window_and_panels(base)
    output_path = audit_dir / "null-calibration.parquet"
    summary_path = audit_dir / "null-calibration.json"
    if summary_path.exists():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        recorded = audit_dir / payload.get("parquet_path", "")
        if (
            payload.get("validation_manifest_digest") != manifest_digest
            or not recorded.is_file()
            or _file_digest(recorded) != payload.get("parquet_sha256")
        ):
            raise SystemExit("기존 null calibration artifact가 현재 manifest와 다릅니다")
        return payload
    with silver.connect(read_only=True) as conn:
        silver.verify_live_total_return_contract(
            conn,
            confirmation.meta.get("return_contract_validation_evidence"),
        )
        run._verify_confirmation_live_identity(conn, confirmation)
        approved = run._approved_signals(conn, confirmation.monthly)
    gold_digest = run._signal_family_digest(approved)
    confirmation_digest = P.snapshot_digest(confirmation)
    frozen_source = validation_manifest["source_campaign"]
    scope = {
        "data_cutoff": str(confirmation.monthly["trade_date"].max().date()),
        "oos_start": OOS_START,
        "discovery_family_size": int(frozen_source["discovery_family_size"]),
        "oos_family_size": len(FACTORS),
        "discovery_family_digest": frozen_source["discovery_family_digest"],
        "oos_family_digest": frozen_source["oos_family_digest"],
        "gold_family_digest": gold_digest,
        "confirmation_snapshot_digest": confirmation_digest,
        "research_data_cutoff": DISCOVERY_CUTOFF,
        "oos_end": OOS_END,
        "qualification_policy": QUALIFICATION_POLICY,
    }
    if output_path.exists():
        calibration = pd.read_parquet(output_path)
    else:
        calibration = null.measure(
            confirmation,
            n=n,
            trial_count=int(validation_manifest["trial_scope"]["trial_count"]),
            prior_sharpes=tuple(validation_manifest["trial_scope"]["prior_sharpes"]),
            oos_start=OOS_START,
            oos_end=OOS_END,
            research_data_cutoff=DISCOVERY_CUTOFF,
            discovery_family_size=int(frozen_source["discovery_family_size"]),
            oos_family_size=len(FACTORS),
            discovery_family_digest=frozen_source["discovery_family_digest"],
            oos_family_digest=frozen_source["oos_family_digest"],
            gold_family_digest=gold_digest,
            confirmation_snapshot_digest=confirmation_digest,
            qualification_policy=QUALIFICATION_POLICY,
            existing=approved,
            checkpoint_path=(
                audit_dir / "null-checkpoints" / f"{manifest_digest}.json"
            ),
        )
        _parquet_exclusive(output_path, calibration)
    expected_kinds = {"random", "ar1_095", "ar1_0999", "frozen"}
    kind_counts = calibration.groupby("kind").size().to_dict()
    if (
        len(calibration) != 100
        or set(kind_counts) != expected_kinds
        or any(int(kind_counts[kind]) != 25 for kind in expected_kinds)
        or calibration.duplicated(["kind", "replicate"]).any()
    ):
        raise SystemExit("null calibration은 4종류 x 25개의 고유 family여야 합니다")
    passed = True
    error = None
    try:
        metrics = gate.assert_null_calibration(calibration, **scope)
    except ValueError as exc:
        passed = False
        error = str(exc)
        probe = gate.Result(
            factor="__retrospective_null__",
            definition_hash="__retrospective_null__",
            checks=[gate.Check("T4.4", "게이트 귀무 보정", None)],
        )
        gate.apply_null_calibration([probe], calibration, **scope)
        metrics = probe.metrics
    payload = {
        "schema_version": "retrospective-null-calibration-v2",
        "audit_id": AUDIT_ID,
        "validation_manifest_digest": manifest_digest,
        "label": "RETROSPECTIVE_NULL_CALIBRATION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "null_families": int(len(calibration)),
        "families_per_generator": {
            kind: int(kind_counts[kind]) for kind in sorted(expected_kinds)
        },
        "scope": {
            key: str(value) if isinstance(value, pd.Period) else value
            for key, value in scope.items()
        },
        "parquet_path": output_path.name,
        "parquet_sha256": _file_digest(output_path),
        "metrics": metrics,
        "passed": passed,
        "error": error,
        "gold_write": False,
    }
    _json_exclusive(summary_path, payload)
    return payload


def write_completion(
    root: Path, audit_dir: Path, validation_manifest: dict,
    manifest_digest: str,
) -> dict | None:
    if _payload_digest(validation_manifest) != manifest_digest:
        raise SystemExit("validation manifest digest가 현재 payload와 다릅니다")
    statistics_path = root / validation_manifest["statistics"]["result_path"]
    if (
        not statistics_path.is_file()
        or _file_digest(statistics_path)
        != validation_manifest["statistics"].get("result_sha256")
    ):
        raise SystemExit("동결 회고 result artifact가 validation manifest와 다릅니다")
    parity_path = audit_dir / "implementation-verification.json"
    null_path = audit_dir / "null-calibration.json"
    if not parity_path.exists() or not null_path.exists():
        return None
    parity = json.loads(parity_path.read_text(encoding="utf-8"))
    calibration = json.loads(null_path.read_text(encoding="utf-8"))
    statistics = json.loads(statistics_path.read_text(encoding="utf-8"))
    statistics_passed, statistics_failures = _statistics_pass(statistics)
    parity_results = parity.get("results", [])
    parity_passed = (
        parity.get("validation_manifest_digest") == manifest_digest
        and parity.get("passed") is True
        and len(parity_results) == len(FACTORS)
        and {
            (row.get("factor"), row.get("definition_hash"), row.get("passed"))
            for row in parity_results
        } == {(name, definition_hash, True) for name, definition_hash in FACTORS.items()}
    )
    parquet_path = audit_dir / calibration.get("parquet_path", "")
    null_passed = (
        calibration.get("validation_manifest_digest") == manifest_digest
        and calibration.get("passed") is True
        and parquet_path.is_file()
        and _file_digest(parquet_path) == calibration.get("parquet_sha256")
    )
    if not (statistics_passed and parity_passed and null_passed):
        return None
    strict = "BLOCKED_CLEAN_OOS"
    payload = {
        "schema_version": "retrospective-validation-completion-v2",
        "audit_id": AUDIT_ID,
        "validation_manifest_digest": manifest_digest,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "engineering_parity_pass": parity_passed,
        "null_calibration_pass": null_passed,
        "retrospective_statistics_pass": statistics_passed,
        "retrospective_statistics_failures": statistics_failures,
        "strict_gold_approval": strict,
        "validation_status": "RETROSPECTIVE_VALIDATION_COMPLETE",
        "blocking_reason": (
            "세 정의가 2023-06~2026-05 결과에 이미 노출되어 clean hidden OOS를 "
            "소급 복원할 수 없음"
        ),
        "gold_write": False,
    }
    completion_path = audit_dir / "completion.json"
    if completion_path.exists():
        existing = json.loads(completion_path.read_text(encoding="utf-8"))
        if (
            existing.get("validation_manifest_digest") != manifest_digest
            or existing.get("validation_status") != payload["validation_status"]
        ):
            raise SystemExit("기존 completion artifact가 현재 validation manifest와 다릅니다")
        return existing
    _json_exclusive(completion_path, payload)
    lines = [
        f"# {AUDIT_ID} 완료 상태", "",
        "- Engineering Python/Gold SQL parity: **PASS**",
        "- T4.4 null calibration: **PASS**",
        "- Retrospective T0~T5 statistics: **PASS** (이미 노출된 과거자료)",
        f"- Strict Gold approval: **{strict}**", "",
        "이미 공개된 과거 결과를 미관측 상태로 되돌릴 수 없으므로, 구현과 통계 검증을 "
        "완료해도 이 세 정의는 현재 규칙에서 정식 clean-OOS 승격으로 바뀌지 않는다.", "",
        "Gold 값 적재: 없음", "",
    ]
    _text_exclusive(audit_dir / "completion.md", "\n".join(lines))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", choices=("parity", "null", "all"), default="all")
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument(
        "--factor", choices=tuple(FACTORS),
        help="parity를 한 팩터만 실행; 통과 artifact는 다음 실행에서 재사용",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if Path.cwd().resolve() != root:
        raise SystemExit(f"레포 루트에서 실행하세요: {root}")
    source = _source(root)
    targets = _targets(source)
    base = run._load()
    audit_dir = root / "research/audits" / AUDIT_ID
    validation_manifest, manifest_digest = _ensure_validation_manifest(
        root, audit_dir, source, targets, base,
    )
    if args.step in {"parity", "all"}:
        result = verify_parity(
            root, audit_dir, source, targets, base,
            selected_factor=args.factor,
        )
        print(f"Gold SQL parity family: {'PASS' if result['passed'] else 'INCOMPLETE'}")
        for attempt in result["attempts"]:
            row = attempt["result"]
            reused = " (기존 PASS 재사용)" if attempt.get("reused") else ""
            print(
                f"  {row['factor']}: {row['status']} {row['failure_reasons']}{reused}"
            )
    if args.step in {"null", "all"}:
        if args.factor is not None:
            raise SystemExit("--factor는 parity 단계에서만 사용할 수 있습니다")
        result = calibrate_null(root, audit_dir, source, targets, base, n=args.n)
        print(f"T4.4 null calibration: {'PASS' if result['passed'] else 'FAIL'}")
    completion = write_completion(
        root, audit_dir, validation_manifest, manifest_digest,
    )
    if completion is not None:
        print(f"Validation completion: {completion['validation_status']}")
    print("Gold write: 없음")


if __name__ == "__main__":
    main()
