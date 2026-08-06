"""Durable campaign/epoch state for sealed-OOS factor research."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from engine.factors import Factor
from engine.gate import Result, RULESET_VERSION, TH


PROTOCOL_VERSION = "epoch-1.0"
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


def load_campaign(root: str | Path, campaign_id: str) -> dict:
    return _read(_campaign_path(root, _validate_id(campaign_id, "campaign id")))


def load_epoch(root: str | Path, campaign_id: str, epoch_id: str) -> dict:
    _validate_id(campaign_id, "campaign id")
    _validate_id(epoch_id, "epoch id")
    return _read(_epoch_path(root, campaign_id, epoch_id))


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
    if min_oos_months < 1:
        raise ValueError("min_oos_months는 1 이상이어야 합니다")
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
            "min_months": int(min_oos_months),
            # The last signal month also needs its following realized return.
            "earliest_data_month": str(start + min_oos_months),
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
    overlap = sorted(existing & set(names))
    if overlap:
        raise ValueError(f"campaign에서 이미 등록한 후보입니다: {overlap}")
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
                "report": None,
                "failed_tiers": [],
                "failed_checks": [],
                "novelty": None,
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
    if campaign["ruleset_version"] != RULESET_VERSION:
        raise ValueError(
            "campaign ruleset이 현재 엔진과 다릅니다: "
            f"{campaign['ruleset_version']} != {RULESET_VERSION}"
        )
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
    epoch = load_epoch(root, campaign_id, epoch_id)
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
        "report": report,
        "failed_tiers": sorted({check.tier for check in result.failed}),
        "failed_checks": [check.name for check in result.failed],
        "novelty": novelty,
        "strongest_relationship": strongest_relationship,
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
    return "DISCOVERY_SURVIVOR"


def close_epoch(root: str | Path, campaign_id: str, epoch_id: str) -> tuple[Path, Path]:
    """Close an epoch and generate non-numeric structural reflection artifacts."""
    epoch = load_epoch(root, campaign_id, epoch_id)
    if epoch["status"] != "OPEN":
        raise ValueError(f"OPEN epoch만 닫을 수 있습니다: {epoch['status']}")
    pending = [row["name"] for row in epoch["candidates"] if row["status"] != "EVALUATED"]
    if pending:
        raise ValueError(f"평가하지 않은 사전등록 후보가 있습니다: {pending}")
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
        "lessons": lessons,
        "duplicates": duplicates,
        "permitted_next_actions": permitted,
        "forbidden_actions": [
            "결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.",
            "게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.",
            "봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.",
        ],
    }
    epoch_dir = _epoch_path(root, campaign_id, epoch_id).parent
    json_path = epoch_dir / "reflection.json"
    _write(json_path, reflection)
    lines = [
        f"# {campaign_id} / {epoch_id} 성찰", "",
        "- OOS 상태: **SEALED**", "",
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
    campaign = load_campaign(root, campaign_id)
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
    if campaign["status"] != "OPEN":
        raise ValueError(f"OPEN campaign만 동결할 수 있습니다: {campaign['status']}")
    if not campaign["epochs"] or any(row["status"] != "CLOSED" for row in campaign["epochs"]):
        raise ValueError("모든 epoch을 닫은 뒤 campaign을 동결해야 합니다")
    candidates = {
        row["name"]: row
        for reference in campaign["epochs"]
        for row in load_epoch(root, campaign_id, reference["epoch_id"])["candidates"]
    }
    unknown = sorted(set(survivor_names) - set(candidates))
    if unknown:
        raise ValueError(f"campaign에 없는 survivor입니다: {unknown}")
    if not survivor_names:
        raise ValueError("봉인 OOS에서 확인할 survivor가 하나 이상 필요합니다")
    rejected = [name for name in survivor_names if candidates[name]["verdict"] == "REJECT"]
    if rejected:
        raise ValueError(f"discovery REJECT 후보는 survivor가 될 수 없습니다: {rejected}")
    campaign["survivors"] = [
        {
            "name": name,
            "family": candidates[name]["family"],
            "definition_hash": candidates[name]["definition_hash"],
            "discovery_report": candidates[name]["report"],
        }
        for name in survivor_names
    ]
    campaign["status"] = "FROZEN"
    campaign["frozen_at"] = _now()
    path = _campaign_path(root, campaign_id)
    _write(path, campaign)
    return path


def assert_reveal_ready(root: str | Path, campaign_id: str, panel_month: pd.Period) -> dict:
    campaign = load_campaign(root, campaign_id)
    if campaign["ruleset_version"] != RULESET_VERSION:
        raise ValueError(
            "campaign ruleset이 현재 엔진과 다릅니다: "
            f"{campaign['ruleset_version']} != {RULESET_VERSION}"
        )
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
    if campaign["status"] != "FROZEN":
        raise ValueError("FROZEN campaign만 reveal 결과를 기록할 수 있습니다")
    directory = _campaign_dir(root, campaign_id) / "confirmation"
    json_path = directory / "result.json"
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "campaign_id": campaign_id,
        "revealed_at": _now(),
        "oos_start": campaign["oos"]["start"],
        "confirmations": confirmations,
    }
    _write(json_path, payload)
    lines = [
        f"# {campaign_id} 봉인 OOS 확인", "",
        f"- OOS start: `{campaign['oos']['start']}`",
        f"- Ruleset: `{campaign['ruleset_version']}`", "",
        "| factor | verdict | definition hash |",
        "|---|---|---|",
    ]
    for row in confirmations:
        lines.append(f"| `{row['factor']}` | {row['verdict']} | `{row['definition_hash']}` |")
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
