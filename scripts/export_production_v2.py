"""Publish new-campaign v2 process metadata, never research/OOS result values.

This is deliberately not a lesson exporter.  The old six-case pilot snapshot is
untouched. Session scalars are read through SQLite JSON projections in read-only
mode: no raw frames, evidence payloads, action prose or result.json are loaded.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from engine.adaptive_research import digest

SCHEMA = "public-production-v2-v1"
VERSION = "production-research-v2-v1"
ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = {"input_audit", "association", "controls", "regime_interaction", "economic_link", "execution_cost"}
CAMPAIGN_STATES = {"OPEN", "AWAITING_IMPLEMENTATION", "READY_FOR_CONFIRMATION", "REVEALED",
                   "CLOSED_NO_QUALIFIED", "CLOSED_ABORTED", "CLOSED_INVALIDATED_INPUT_IDENTITY",
                   "CLOSED_RETROSPECTIVE_ONLY", "SUPERSEDED_BOUNDARY_POLICY"}


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("Invalid public research identifier")
    return value


def _bound(payload, label):
    if not isinstance(payload, dict) or payload.get("version") != VERSION:
        raise ValueError(f"Unsupported {label} metadata")
    body = {key: value for key, value in payload.items() if key != "sha256"}
    if payload.get("sha256") != digest(body):
        raise ValueError(f"Changed {label} metadata")


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing metadata timestamp")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Metadata timestamp requires timezone")
    return stamp.isoformat()


def _session_metadata(path, manifest):
    if not path.is_file():
        return {"status": "NOT_INITIALIZED", "diagnostics_observed": 0, "explicit_stop": False}
    # No SELECT body, response, metrics, evidence array or investigator narrative.
    query = """SELECT revision, sha, json_extract(body,'$.previous_sha256'),
        json_extract(body,'$.type'), json_extract(body,'$.status'),
        json_extract(body,'$.request_id'), json_extract(body,'$.evidence.diagnostic_id'),
        json_extract(body,'$.contract.data_contract_sha256'),
        json_extract(body,'$.contract.planner_kind'),
        json_extract(body,'$.contract.max_actions') FROM events ORDER BY revision"""
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        rows = db.execute(query).fetchall()
    if (not rows or rows[0][3] != "CREATED" or rows[0][7] != manifest["data_contract_sha256"]
            or rows[0][8] != "HOST_LLM" or type(rows[0][9]) is not int or rows[0][9] < 1):
        raise ValueError("Session metadata is not bound to this host handoff")
    previous, actions, results, observed, terminal = "", set(), set(), set(), None
    for index, (revision, sha, prev, kind, status, request, diagnostic, _contract, _planner, _budget) in enumerate(rows):
        if (revision != index or prev != previous or not isinstance(sha, str)
                or re.fullmatch(r"[a-f0-9]{64}", sha) is None):
            raise ValueError("Session metadata chain discontinuity")
        previous = sha
        if kind == "ACTION":
            actions.add(request)
        elif kind == "RESULT":
            results.add(request)
            if diagnostic in DIAGNOSTICS:
                observed.add(diagnostic)
            if status in {"STOPPED", "DATA_REQUESTED_NOT_ACQUIRED", "NEW_TEST_PENDING_REVIEW"}:
                terminal = status
    status = "PENDING_RECONCILIATION" if actions - results else terminal or "ACTIVE"
    if status == "ACTIVE" and len(actions) >= rows[0][9]:
        status = "ACTION_BUDGET_EXHAUSTED"
    return {"status": status, "diagnostics_observed": len(observed),
            "explicit_stop": status == "STOPPED", "revision": rows[-1][0],
            "authentication": "CONTRACT_AND_STATUS_CHAIN_HEADERS_ONLY_NOT_EVIDENCE_OR_CRITIC_REVIEW"}


def _campaign_metadata(directory):
    manifest = _read(directory / "manifest.json")
    config = manifest.get("research_v2")
    if config is None:
        return None
    _bound(config, "campaign v2")
    cid = _identifier(manifest["campaign_id"])
    if cid != directory.name:
        raise ValueError("Campaign directory identity mismatch")
    status = manifest.get("status")
    if status not in CAMPAIGN_STATES:
        raise ValueError("Unknown campaign status; do not publish arbitrary text")
    registered = set()
    for entry in manifest.get("epochs", []):
        eid = _identifier(entry["epoch_id"])
        epoch = _read(directory / "epochs" / eid / "manifest.json")
        plans = epoch.get("research_v2_plans", {})
        if (epoch.get("research_v2_sha256") != config["sha256"]
                or epoch.get("research_v2_plans_sha256") != digest(plans)):
            raise ValueError("Epoch v2 registration metadata changed")
        registered.update((eid, _identifier(name)) for name in plans)
    handoffs = []
    for path in sorted((directory / "v2").glob("*/*/manifest.json")):
        if any(part.startswith(".") for part in path.relative_to(directory).parts):
            continue
        handoff = _read(path)
        _bound(handoff, "handoff")
        eid, factor = _identifier(handoff["epoch_id"]), _identifier(handoff["factor"])
        if (handoff["campaign_id"] != cid or handoff["campaign_sha256"] != config["sha256"]
                or (eid, factor) not in registered or path.parent.name != factor
                or path.parent.parent.name != eid):
            raise ValueError("Handoff is outside registered campaign scope")
        handoffs.append({"epoch_id": eid, "factor": factor,
                         "markets": sorted(name for name in handoff.get("regime_labs", {}) if name in {"KOSPI", "KOSDAQ"}),
                         "macro_axes_count": len(handoff.get("macro_labs", {})),
                         "session": _session_metadata(path.parent / "session.sqlite", handoff),
                         "review_status": "NOT_EXPORTED_BY_PROCESS_STATUS_VIEW"})
    if status == "CLOSED_ABORTED" and not registered:
        process_stage = "ABORTED_BEFORE_REGISTRATION"
    elif not registered:
        process_stage = "CAMPAIGN_FROZEN_NO_REGISTERED_CANDIDATE"
    elif not handoffs:
        process_stage = "CANDIDATES_REGISTERED_NO_HANDOFF"
    elif len(handoffs) < len(registered):
        process_stage = "PARTIAL_HANDOFF"
    elif all(item["session"]["explicit_stop"] for item in handoffs):
        process_stage = "HOST_STOPPED_REVIEW_SEPARATE"
    else:
        process_stage = "HANDOFF_READY_HOST_PENDING_OR_ACTIVE"
    return {"campaign_id": cid, "status": status, "created_at": _timestamp(manifest["created_at"]),
            "process_stage": process_stage, "registered_epochs": len(manifest.get("epochs", [])),
            "registered_candidates": len(registered), "handoffs": handoffs,
            "config_sha256": config["sha256"], "campaign_manifest_sha256": _sha(directory / "manifest.json")}


def build_summary(*, repo_root=ROOT, generated_at=None):
    root = Path(repo_root).resolve()
    policy_path = root / "research/v2/production-policy.json"
    policy = _read(policy_path)
    if (policy.get("version") != VERSION or type(policy.get("enabled")) is not bool
            or policy.get("graph_retrieval") is not False or policy.get("utility_ranking_weight") != 0
            or policy.get("automatic_gold_publication") is not False
            or policy.get("legacy_campaign_migration") is not False
            or not set(policy.get("mandatory_diagnostics", [])) <= DIAGNOSTICS):
        raise ValueError("Unsupported production dashboard policy")
    campaigns = []
    for path in sorted((root / "research/campaigns").glob("*/manifest.json")):
        if path.parent.name.startswith("."):
            continue
        value = _campaign_metadata(path.parent)
        if value:
            campaigns.append(value)
    campaigns.sort(key=lambda value: (value["created_at"], value["campaign_id"]), reverse=True)
    sessions = [handoff["session"] for campaign in campaigns for handoff in campaign["handoffs"]]
    sources = ["engine/research_production.py", "engine/research_production_evidence.py",
               "engine/research_regime_production.py", "engine/research_memory_transfer.py",
               "scripts/research.py", "engine/epochs.py"]
    # Fail closed if a displayed implementation module is absent.
    module_hashes = {name: _sha(root / name) for name in sources}
    value = {
        "schema_version": SCHEMA, "generated_at": _timestamp(generated_at or datetime.now(timezone.utc).isoformat()),
        "snapshot_kind": "STATIC_PROCESS_METADATA_NOT_LIVE_RESULTS", "policy_enabled": policy["enabled"],
        "oos_results_included": False, "performance_metrics_included": False,
        "production_lessons_included": False, "automatic_gold_publication": False,
        "legacy_campaigns_changed": False, "counts": {
            "new_campaigns": len(campaigns), "aborted_campaigns": sum(c["status"] == "CLOSED_ABORTED" for c in campaigns),
            "campaigns_with_registered_candidates": sum(c["registered_candidates"] > 0 for c in campaigns),
            "registered_candidates": sum(c["registered_candidates"] for c in campaigns),
            "prepared_handoffs": len(sessions), "explicitly_stopped_sessions": sum(s["explicit_stop"] for s in sessions),
            "pending_host_sessions": sum(not s["explicit_stop"] for s in sessions)},
        "architecture": [
            {"name": "신규 캠페인·후보", "status": "연결됨", "note": "생성 시 진단 정책·자료·코드·기억 사용을 동결하고 기존 Discovery에서 만든 자료를 전달합니다. 기존 캠페인은 소급 변경하지 않습니다."},
            {"name": "진단 → 교훈 → 다음 연구", "status": "호스트·독립 검토 필요", "note": "필수 검사는 유지합니다. 호스트가 추가 검사와 해석을 수행하고 별도 비평이 승인한 교훈만 활성화합니다. 새 범위로 옮길 때도 검토·사용 기록이 필요합니다."},
            {"name": "시장별 레짐·매크로", "status": "연결됨", "note": "KOSPI·KOSDAQ을 각각 매핑하고 별도 표본으로 진단합니다. 매크로는 가설에 사전 지정한 최대 두 축만 비교하며 모든 조합을 탐색하지 않습니다. PIT_ASSUMED와 UNKNOWN은 유지합니다."},
            {"name": "체결·비용", "status": "동일 실행 모의 비용 연결", "note": "기존 월말 수익·보유규칙의 비용 자료입니다. 월말 판단 뒤 다음 거래일 시가에 실제 체결한 수익은 아니며 그 검증은 별도입니다."},
            {"name": "그래프·효용 학습", "status": "의도적으로 꺼짐", "note": "효용 가중치는 영입니다. 단순 사용 횟수나 승인 수를 교훈의 진실성·효용으로 학습하지 않습니다."},
        ],
        "campaigns": campaigns,
        "review_boundary": "이 현황은 실행 상태만 확인합니다. 해석 종료는 독립 비평·교훈 승인과 다릅니다. 새 교훈 본문과 검토 완료 건수는 별도 인증된 공개 요약이 마련되기 전까지 여기서 주장하지 않습니다.",
        "source_boundary": "원시 패널·진단 수치·OOS 결과·연구자의 해석 문장은 읽거나 내보내지 않습니다. 세션 상태 연결 확인은 근거 전체의 무결성 검증이나 독립 비평을 대신하지 않습니다.",
        "provenance": {"policy_file_sha256": _sha(policy_path), "implementation_sha256": module_hashes},
    }
    body = json.dumps(value, ensure_ascii=False, allow_nan=False)
    if re.search(r"postgres(?:ql)?://|/Users/|\b(?:AKIA|ASIA)[A-Z0-9]{16}|secret_access_key|access_token|password", body, re.I):
        raise ValueError("Private content in public process export")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    value = build_summary(repo_root=args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Fresh immutable export; publish/copy is a separate caller operation.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "EXPORTED_PROCESS_METADATA_ONLY", "counts": value["counts"], "sha256": _sha(args.output)}))


if __name__ == "__main__":
    main()
