"""Durable campaign/epoch state for sealed-OOS factor research."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from engine.factors import Factor
from engine.gate import (
    Result,
    RULESET_VERSION,
    TH,
    by_qvalues,
    discovery_evidence_digest,
)


PROTOCOL_VERSION = "epoch-1.2"
_ID = re.compile(r"^[a-z][a-z0-9-]*$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_id(value: str, label: str) -> str:
    if not _ID.fullmatch(value):
        raise ValueError(f"{label}는 소문자·숫자·하이픈만 사용해야 합니다: {value!r}")
    return value


def _campaign_dir(root: str | Path, campaign_id: str) -> Path:
    return Path(root) / "campaigns" / campaign_id


def _campaign_path(root: str | Path, campaign_id: str) -> Path:
    return _campaign_dir(root, campaign_id) / "manifest.json"


def _epoch_path(root: str | Path, campaign_id: str, epoch_id: str) -> Path:
    return _campaign_dir(root, campaign_id) / "epochs" / epoch_id / "manifest.json"


def _read(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f"연구 상태 파일이 없습니다: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _family_digest(definition_hashes: list[str]) -> str:
    canonical = "\n".join(sorted(definition_hashes)).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _payload_digest(payload: dict) -> str:
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_campaign(root: str | Path, campaign_id: str) -> dict:
    return _read(_campaign_path(root, _validate_id(campaign_id, "campaign id")))


def load_epoch(root: str | Path, campaign_id: str, epoch_id: str) -> dict:
    _validate_id(campaign_id, "campaign id")
    _validate_id(epoch_id, "epoch id")
    return _read(_epoch_path(root, campaign_id, epoch_id))


def _assert_current_state(campaign: dict, epoch: dict | None = None) -> None:
    """Refuse to reinterpret frozen research with a newer protocol/ruleset."""
    if campaign.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError(
            "campaign protocol이 현재 엔진과 다릅니다: "
            f"{campaign.get('protocol_version')} != {PROTOCOL_VERSION}"
        )
    if campaign.get("ruleset_version") != RULESET_VERSION:
        raise ValueError(
            "campaign ruleset이 현재 엔진과 다릅니다: "
            f"{campaign.get('ruleset_version')} != {RULESET_VERSION}"
        )
    if epoch is not None:
        if epoch.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError(
                "epoch protocol이 현재 엔진과 다릅니다: "
                f"{epoch.get('protocol_version')} != {PROTOCOL_VERSION}"
            )
        if epoch.get("ruleset_version") != RULESET_VERSION:
            raise ValueError(
                "epoch ruleset이 현재 엔진과 다릅니다: "
                f"{epoch.get('ruleset_version')} != {RULESET_VERSION}"
            )


def start_campaign(
    root: str | Path,
    campaign_id: str,
    *,
    data_cutoff: str,
    oos_start: str | None = None,
    min_oos_months: int = TH["min_oos_months"],
) -> Path:
    """Create a campaign whose final OOS starts after the known snapshot."""
    campaign_id = _validate_id(campaign_id, "campaign id")
    path = _campaign_path(root, campaign_id)
    if path.exists():
        raise ValueError(f"이미 존재하는 campaign입니다: {campaign_id}")
    cutoff = pd.Timestamp(data_cutoff).to_period("M")
    start = pd.Period(oos_start, freq="M") if oos_start else cutoff + 1
    if start <= cutoff:
        raise ValueError(f"봉인 OOS 시작 {start}는 데이터 cutoff {cutoff}보다 뒤여야 합니다")
    if min_oos_months != TH["min_oos_months"]:
        raise ValueError(
            f"min_oos_months는 현재 ruleset 고정값 {TH['min_oos_months']}이어야 합니다"
        )
    end = start + min_oos_months
    conflicts = []
    for candidate in (Path(root) / "campaigns").glob("*/manifest.json"):
        existing = _read(candidate)
        if existing.get("status") not in {"OPEN", "FROZEN"}:
            continue
        existing_start = pd.Period(existing["oos"]["start"], freq="M")
        existing_end = pd.Period(existing["oos"]["earliest_data_month"], freq="M")
        if start < existing_end and existing_start < end:
            conflicts.append(existing.get("campaign_id", candidate.parent.name))
    if conflicts:
        raise ValueError(
            "active campaign과 봉인 OOS 기간이 겹칩니다. 새 OOS 시작을 기존 기간 뒤로 미루세요: "
            f"{conflicts}"
        )
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "campaign_id": campaign_id,
        "status": "OPEN",
        "created_at": _now(),
        "ruleset_version": RULESET_VERSION,
        "data_cutoff": str(pd.Timestamp(data_cutoff).date()),
        "oos": {
            "status": "SEALED",
            "start": str(start),
            "signal_end": str(end - 1),
            "min_months": int(min_oos_months),
            # The last signal month also needs its following realized return.
            "required_data_month": str(end),
            # The following month proves that required_data_month is closed,
            # rather than a partial current-month snapshot.
            "earliest_reveal_month": str(end + 1),
            "earliest_data_month": str(end + 1),
            "revealed_at": None,
        },
        "epochs": [],
        "survivors": [],
    }
    _write(path, payload)
    return path


def start_epoch(
    root: str | Path,
    campaign_id: str,
    epoch_id: str,
    factors: list[Factor],
) -> Path:
    """Freeze every candidate name and definition hash before any result is seen."""
    epoch_id = _validate_id(epoch_id, "epoch id")
    campaign = load_campaign(root, campaign_id)
    _assert_current_state(campaign)
    if campaign["status"] != "OPEN":
        raise ValueError(f"OPEN campaign에서만 epoch을 시작할 수 있습니다: {campaign['status']}")
    if not factors:
        raise ValueError("epoch에는 후보가 하나 이상 필요합니다")
    names = [factor.name for factor in factors]
    hashes = [factor.definition_hash for factor in factors]
    if len(names) != len(set(names)) or len(hashes) != len(set(hashes)):
        raise ValueError("epoch 후보 이름과 definition hash는 고유해야 합니다")
    existing = {
        row["name"]
        for epoch_ref in campaign["epochs"]
        for row in load_epoch(root, campaign_id, epoch_ref["epoch_id"])["candidates"]
    }
    existing_hashes = {
        row["definition_hash"]
        for epoch_ref in campaign["epochs"]
        for row in load_epoch(root, campaign_id, epoch_ref["epoch_id"])["candidates"]
    }
    overlap = sorted(existing & set(names))
    if overlap:
        raise ValueError(f"campaign에서 이미 등록한 후보입니다: {overlap}")
    hash_overlap = sorted(existing_hashes & set(hashes))
    if hash_overlap:
        raise ValueError(f"campaign에서 이미 등록한 definition hash입니다: {hash_overlap}")
    path = _epoch_path(root, campaign_id, epoch_id)
    if path.exists():
        raise ValueError(f"이미 존재하는 epoch입니다: {epoch_id}")
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "campaign_id": campaign_id,
        "epoch_id": epoch_id,
        "status": "OPEN",
        "created_at": _now(),
        "ruleset_version": campaign["ruleset_version"],
        "data_cutoff": campaign["data_cutoff"],
        "oos_status": "SEALED",
        "candidates": [
            {
                "name": factor.name,
                "family": factor.family or factor.name,
                "definition_hash": factor.definition_hash,
                "status": "REGISTERED",
                "cycle_id": None,
                "verdict": None,
                "pre_fdr_verdict": None,
                "report": None,
                "failed_tiers": [],
                "failed_checks": [],
                "novelty": None,
                "ic_p_investable": None,
                "discovery_evidence_digest": None,
                "fdr_status": "PENDING",
                "fdr_qvalue": None,
            }
            for factor in factors
        ],
        "closed_at": None,
        "reflection": None,
    }
    _write(path, payload)
    campaign["epochs"].append({"epoch_id": epoch_id, "status": "OPEN"})
    _write(_campaign_path(root, campaign_id), campaign)
    return path


def assert_candidate_ready(
    root: str | Path,
    campaign_id: str,
    epoch_id: str,
    factor: Factor,
) -> dict:
    campaign = load_campaign(root, campaign_id)
    epoch = load_epoch(root, campaign_id, epoch_id)
    _assert_current_state(campaign, epoch)
    if campaign["status"] != "OPEN" or epoch["status"] != "OPEN":
        raise ValueError("OPEN campaign의 OPEN epoch에서만 discovery 평가할 수 있습니다")
    candidate = next((row for row in epoch["candidates"] if row["name"] == factor.name), None)
    if candidate is None:
        raise ValueError(f"epoch에 사전등록되지 않은 후보입니다: {factor.name}")
    if candidate["definition_hash"] != factor.definition_hash:
        raise ValueError(f"사전등록 후 정의가 변경됐습니다: {factor.name}")
    if candidate["status"] != "REGISTERED":
        raise ValueError(f"이미 평가했거나 평가 중인 후보입니다: {factor.name}")
    return candidate


def mark_evaluated(
    root: str | Path,
    campaign_id: str,
    epoch_id: str,
    factor: Factor,
    result: Result,
    *,
    report: str,
    strongest_relationship: dict | None,
) -> None:
    campaign = load_campaign(root, campaign_id)
    epoch = load_epoch(root, campaign_id, epoch_id)
    _assert_current_state(campaign, epoch)
    if campaign["status"] != "OPEN" or epoch["status"] != "OPEN":
        raise ValueError("OPEN campaign의 OPEN epoch에서만 결과를 기록할 수 있습니다")
    candidate = next(row for row in epoch["candidates"] if row["name"] == factor.name)
    if candidate["definition_hash"] != factor.definition_hash:
        raise ValueError(f"사전등록 정의와 평가 정의가 다릅니다: {factor.name}")
    relation = strongest_relationship or {}
    correlation = relation.get("abs_median_spearman")
    if correlation is None:
        novelty = "UNMEASURED"
    elif correlation > TH["max_corr"]:
        novelty = "DUPLICATE"
    elif correlation >= .60:
        novelty = "RELATED"
    else:
        novelty = "INDEPENDENT"
    candidate.update({
        "status": "EVALUATED",
        "cycle_id": Path(report).parent.name,
        "verdict": result.verdict.value,
        "pre_fdr_verdict": result.verdict.value,
        "report": report,
        "failed_tiers": sorted({check.tier for check in result.failed}),
        "failed_checks": [check.name for check in result.failed],
        "novelty": novelty,
        "strongest_relationship": strongest_relationship,
        "ic_p_investable": result.metrics.get("ic_p_investable"),
        "discovery_evidence_digest": discovery_evidence_digest(result),
        "fdr_status": "PENDING",
        "fdr_qvalue": None,
    })
    _write(_epoch_path(root, campaign_id, epoch_id), epoch)


def _failure_bucket(candidate: dict) -> str:
    tiers = tuple(candidate.get("failed_tiers") or ())
    if any(tier.startswith(("T0", "T1")) for tier in tiers):
        return "DATA_OR_INTEGRITY"
    if any(tier.startswith("T2") for tier in tiers):
        return "NO_PREDICTIVE_EVIDENCE"
    if any(tier.startswith("T3") for tier in tiers):
        return "ROBUSTNESS_OR_DATA_GAP"
    if any(tier.startswith("T4") for tier in tiers):
        return "MULTIPLE_TESTING"
    if any(tier.startswith("T5") for tier in tiers):
        return "GOLD_REDUNDANCY"
    if candidate.get("fdr_status") == "PENDING":
        return "DISCOVERY_FDR_PENDING"
    return "DISCOVERY_SURVIVOR"


def close_epoch(
    root: str | Path,
    campaign_id: str,
    epoch_id: str,
) -> tuple[Path, Path]:
    """Close an epoch; discovery FDR stays pending until campaign freeze."""
    campaign = load_campaign(root, campaign_id)
    epoch = load_epoch(root, campaign_id, epoch_id)
    _assert_current_state(campaign, epoch)
    if campaign["status"] != "OPEN":
        raise ValueError(f"OPEN campaign의 epoch만 닫을 수 있습니다: {campaign['status']}")
    if epoch["status"] != "OPEN":
        raise ValueError(f"OPEN epoch만 닫을 수 있습니다: {epoch['status']}")
    pending = [row["name"] for row in epoch["candidates"] if row["status"] != "EVALUATED"]
    if pending:
        raise ValueError(f"평가하지 않은 사전등록 후보가 있습니다: {pending}")

    epoch_dir = _epoch_path(root, campaign_id, epoch_id).parent
    lessons = []
    for candidate in epoch["candidates"]:
        lessons.append({
            "factor": candidate["name"],
            "family": candidate["family"],
            "outcome": _failure_bucket(candidate),
            "novelty": candidate["novelty"],
            "evidence": candidate["report"],
        })
    duplicates = [row["name"] for row in epoch["candidates"] if row["novelty"] == "DUPLICATE"]
    permitted = [
        "다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.",
        "실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.",
    ]
    if duplicates:
        permitted.append("중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.")
    reflection = {
        "protocol_version": PROTOCOL_VERSION,
        "campaign_id": campaign_id,
        "epoch_id": epoch_id,
        "created_at": _now(),
        "oos_status": "SEALED",
        "discovery_fdr_status": "PENDING_UNTIL_CAMPAIGN_FREEZE",
        "lessons": lessons,
        "duplicates": duplicates,
        "permitted_next_actions": permitted,
        "forbidden_actions": [
            "결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.",
            "게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.",
            "봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.",
        ],
    }
    json_path = epoch_dir / "reflection.json"
    _write(json_path, reflection)
    lines = [
        f"# {campaign_id} / {epoch_id} 성찰", "",
        "- OOS 상태: **SEALED**", "",
        "- Discovery 다중검정: **PENDING** (campaign freeze에서 전체 후보 일괄 판정)", "",
        "## 구조적 교훈", "",
        "| factor | family | outcome | novelty | evidence |",
        "|---|---|---|---|---|",
    ]
    for row in lessons:
        lines.append(
            f"| `{row['factor']}` | `{row['family']}` | {row['outcome']} | "
            f"{row['novelty']} | `{row['evidence']}` |"
        )
    lines += ["", "## 다음 epoch에서 허용되는 학습", ""]
    lines += [f"- {item}" for item in permitted]
    lines += ["", "## 금지되는 사후 적응", ""]
    lines += [f"- {item}" for item in reflection["forbidden_actions"]]
    lines.append("")
    markdown_path = epoch_dir / "reflection.md"
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    epoch["status"] = "CLOSED"
    epoch["closed_at"] = _now()
    epoch["reflection"] = str(markdown_path)
    _write(_epoch_path(root, campaign_id, epoch_id), epoch)
    for reference in campaign["epochs"]:
        if reference["epoch_id"] == epoch_id:
            reference["status"] = "CLOSED"
    _write(_campaign_path(root, campaign_id), campaign)
    return markdown_path, json_path


def freeze_campaign(
    root: str | Path,
    campaign_id: str,
    survivor_names: list[str],
) -> Path:
    campaign = load_campaign(root, campaign_id)
    _assert_current_state(campaign)
    if campaign["status"] != "OPEN":
        raise ValueError(f"OPEN campaign만 동결할 수 있습니다: {campaign['status']}")
    if not campaign["epochs"] or any(row["status"] != "CLOSED" for row in campaign["epochs"]):
        raise ValueError("모든 epoch을 닫은 뒤 campaign을 동결해야 합니다")
    if len(survivor_names) != len(set(survivor_names)):
        raise ValueError("survivor 이름은 중복될 수 없습니다")
    epochs_by_id = {
        reference["epoch_id"]: load_epoch(root, campaign_id, reference["epoch_id"])
        for reference in campaign["epochs"]
    }
    for epoch in epochs_by_id.values():
        _assert_current_state(campaign, epoch)
    candidates = {
        row["name"]: row
        for epoch in epochs_by_id.values()
        for row in epoch["candidates"]
    }
    unknown = sorted(set(survivor_names) - set(candidates))
    if unknown:
        raise ValueError(f"campaign에 없는 survivor입니다: {unknown}")
    # The campaign is the immutable discovery family.  Epoch-close decisions
    # stay pending so later epochs cannot retroactively change an earlier final
    # verdict.  Every registered definition enters exactly once; candidates
    # without a valid IC p-value conservatively enter BY with p=1.
    by_inputs = {
        candidate["definition_hash"]: (
            float(candidate["ic_p_investable"])
            if candidate.get("ic_p_investable") is not None
            and math.isfinite(float(candidate["ic_p_investable"]))
            else 1.0
        )
        for candidate in candidates.values()
    }
    qvalues = by_qvalues(by_inputs)
    family_digest = _family_digest(list(by_inputs))
    fdr_rows = []
    for candidate in candidates.values():
        raw_pvalue = candidate.get("ic_p_investable")
        testable = raw_pvalue is not None and math.isfinite(float(raw_pvalue))
        qvalue = qvalues[candidate["definition_hash"]]
        passed = bool(testable and qvalue <= TH["fdr_q"])
        candidate["fdr_status"] = "PASS" if passed else ("FAIL" if testable else "NOT_TESTABLE")
        candidate["fdr_qvalue"] = qvalue if testable else None
        if candidate.get("pre_fdr_verdict") == "REJECT" or not passed:
            candidate["verdict"] = "REJECT"
        else:
            candidate["verdict"] = candidate.get("pre_fdr_verdict") or "PROVISIONAL"
        if not passed:
            if "T4.3" not in candidate["failed_tiers"]:
                candidate["failed_tiers"].append("T4.3")
            if "다중검정 FDR" not in candidate["failed_checks"]:
                candidate["failed_checks"].append("다중검정 FDR")
        fdr_rows.append({
            "factor": candidate["name"],
            "definition_hash": candidate["definition_hash"],
            "pvalue": float(raw_pvalue) if testable else None,
            "by_input_pvalue": by_inputs[candidate["definition_hash"]],
            "qvalue": qvalue if testable else None,
            "status": candidate["fdr_status"],
            "verdict": candidate["verdict"],
            "discovery_evidence_digest": candidate["discovery_evidence_digest"],
        })
    rejected = [name for name in survivor_names if candidates[name]["verdict"] == "REJECT"]
    if rejected:
        raise ValueError(f"discovery REJECT 후보는 survivor가 될 수 없습니다: {rejected}")
    multiple_testing_path = _campaign_dir(root, campaign_id) / "multiple-testing.json"
    for epoch_id, epoch in epochs_by_id.items():
        epoch["discovery_fdr_status"] = "FINAL"
        epoch["campaign_multiple_testing"] = str(multiple_testing_path)
        _write(_epoch_path(root, campaign_id, epoch_id), epoch)
    multiple_testing = {
        "protocol_version": PROTOCOL_VERSION,
        "ruleset_version": RULESET_VERSION,
        "campaign_id": campaign_id,
        "method": "Benjamini-Yekutieli",
        "threshold": TH["fdr_q"],
        "family": "all preregistered definitions in this campaign",
        "family_digest": family_digest,
        "total_definitions": len(by_inputs),
        "results": fdr_rows,
    }
    _write(multiple_testing_path, multiple_testing)
    campaign["survivors"] = [
        {
            "name": name,
            "family": candidates[name]["family"],
            "definition_hash": candidates[name]["definition_hash"],
            "discovery_report": candidates[name]["report"],
            "discovery_multiple_testing": str(multiple_testing_path),
        }
        for name in survivor_names
    ]
    if survivor_names:
        campaign["status"] = "FROZEN"
        campaign["frozen_at"] = _now()
    else:
        campaign["status"] = "CLOSED_NO_SURVIVOR"
        campaign["closed_at"] = _now()
        campaign["oos"]["status"] = "NOT_USED"
    campaign["discovery_multiple_testing"] = str(multiple_testing_path)
    campaign["discovery_multiple_testing_digest"] = _payload_digest(multiple_testing)
    campaign["discovery_family_size"] = len(by_inputs)
    campaign["discovery_family_digest"] = family_digest
    campaign["oos_family_digest"] = _family_digest([
        candidates[name]["definition_hash"] for name in survivor_names
    ])
    path = _campaign_path(root, campaign_id)
    _write(path, campaign)
    return path


def load_discovery_multiple_testing(root: str | Path, campaign_id: str) -> dict:
    """Load and authenticate the frozen campaign-wide discovery family."""
    campaign = load_campaign(root, campaign_id)
    _assert_current_state(campaign)
    artifact_path = campaign.get("discovery_multiple_testing")
    if not artifact_path:
        raise ValueError("campaign discovery 다중검정 artifact가 없습니다")
    artifact = _read(Path(artifact_path))
    rows = artifact.get("results") or []
    hashes = [row.get("definition_hash") for row in rows]
    expected_hashes = [
        candidate["definition_hash"]
        for reference in campaign["epochs"]
        for candidate in load_epoch(
            root, campaign_id, reference["epoch_id"],
        )["candidates"]
    ]
    valid = (
        artifact.get("protocol_version") == PROTOCOL_VERSION
        and artifact.get("ruleset_version") == RULESET_VERSION
        and artifact.get("campaign_id") == campaign_id
        and artifact.get("method") == "Benjamini-Yekutieli"
        and artifact.get("threshold") == TH["fdr_q"]
        and artifact.get("total_definitions") == len(expected_hashes)
        and len(hashes) == len(set(hashes))
        and set(hashes) == set(expected_hashes)
        and _family_digest(hashes) == campaign.get("discovery_family_digest")
        and artifact.get("family_digest") == campaign.get("discovery_family_digest")
        and _payload_digest(artifact)
        == campaign.get("discovery_multiple_testing_digest")
    )
    if not valid:
        raise ValueError("campaign discovery 다중검정 artifact 무결성 검증에 실패했습니다")
    return artifact


def assert_reveal_ready(root: str | Path, campaign_id: str, panel_month: pd.Period) -> dict:
    campaign = load_campaign(root, campaign_id)
    _assert_current_state(campaign)
    if int(campaign.get("oos", {}).get("min_months", 0)) < TH["min_oos_months"]:
        raise ValueError("campaign OOS 기간이 현재 ruleset 최소기간보다 짧습니다")
    if campaign["status"] != "FROZEN":
        raise ValueError(f"FROZEN campaign만 OOS를 공개할 수 있습니다: {campaign['status']}")
    earliest = pd.Period(campaign["oos"]["earliest_data_month"], freq="M")
    if panel_month < earliest:
        raise ValueError(
            f"봉인 OOS가 아직 {campaign['oos']['min_months']}개월 쌓이지 않았습니다: "
            f"현재 {panel_month}, 최소 {earliest}"
        )
    return campaign


def record_reveal(
    root: str | Path,
    campaign_id: str,
    confirmations: list[dict],
) -> tuple[Path, Path]:
    campaign = load_campaign(root, campaign_id)
    _assert_current_state(campaign)
    if campaign["status"] != "FROZEN":
        raise ValueError("FROZEN campaign만 reveal 결과를 기록할 수 있습니다")
    load_discovery_multiple_testing(root, campaign_id)
    expected = [
        (row["name"], row["definition_hash"])
        for row in campaign["survivors"]
    ]
    observed = [
        (row.get("factor"), row.get("definition_hash"))
        for row in confirmations
    ]
    if len(observed) != len(set(observed)) or set(observed) != set(expected):
        raise ValueError(
            "confirmation은 동결 survivor와 이름·definition hash가 정확히 일치해야 합니다: "
            f"expected={expected}, observed={observed}"
        )
    by_name = {row["factor"]: row for row in confirmations}
    confirmations = [by_name[name] for name, _definition_hash in expected]
    wrong_oos_window = [
        row["factor"]
        for row in confirmations
        if row.get("evaluation", {}).get("metrics", {}).get("oos_start")
        != campaign["oos"]["start"]
        or row.get("evaluation", {}).get("metrics", {}).get("oos_end")
        != campaign["oos"]["signal_end"]
    ]
    if wrong_oos_window:
        raise ValueError(f"동결 OOS 구간과 다른 confirmation입니다: {wrong_oos_window}")
    directory = _campaign_dir(root, campaign_id) / "confirmation"
    json_path = directory / "result.json"
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "campaign_id": campaign_id,
        "revealed_at": _now(),
        "oos_start": campaign["oos"]["start"],
        "oos_end": campaign["oos"]["signal_end"],
        "confirmations": confirmations,
    }
    _write(json_path, payload)
    lines = [
        f"# {campaign_id} 봉인 OOS 확인", "",
        f"- OOS start: `{campaign['oos']['start']}`",
        f"- OOS signal end: `{campaign['oos']['signal_end']}`",
        f"- Ruleset: `{campaign['ruleset_version']}`", "",
        "| factor | verdict | OOS IC | OOS BY q | definition hash |",
        "|---|---|---:|---:|---|",
    ]
    for row in confirmations:
        metrics = row.get("evaluation", {}).get("metrics", {})
        lines.append(
            f"| `{row['factor']}` | {row['verdict']} | "
            f"{metrics.get('oos_ic')} | {metrics.get('oos_fdr_qvalue')} | "
            f"`{row['definition_hash']}` |"
        )
    lines.append("")
    report_path = directory / "report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    campaign["status"] = "REVEALED"
    campaign["oos"]["status"] = "REVEALED"
    campaign["oos"]["revealed_at"] = payload["revealed_at"]
    campaign["confirmation"] = str(report_path)
    _write(_campaign_path(root, campaign_id), campaign)
    return report_path, json_path


def context_rows(root: str | Path) -> list[dict]:
    campaigns_dir = Path(root) / "campaigns"
    if not campaigns_dir.exists():
        return []
    output = []
    for path in sorted(campaigns_dir.glob("*/manifest.json")):
        row = _read(path)
        reflections = [
            load_epoch(root, row["campaign_id"], reference["epoch_id"]).get("reflection")
            for reference in row["epochs"]
            if reference["status"] == "CLOSED"
        ]
        latest_reflection = next((value for value in reversed(reflections) if value), None)
        output.append({
            "campaign_id": row["campaign_id"],
            "status": row["status"],
            "data_cutoff": row["data_cutoff"],
            "oos_status": row["oos"]["status"],
            "oos_start": row["oos"]["start"],
            "epochs": len(row["epochs"]),
            "survivors": len(row["survivors"]),
            "latest_reflection": latest_reflection,
        })
    return output
