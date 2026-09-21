"""Candidate lesson records and conservative, qualitative grouped memory.

No model calls and no numeric performance values are exported. Economic causes
are not inferred from a failed statistical test.
"""
from __future__ import annotations

import json
import hashlib
import re
from collections import defaultdict
from pathlib import Path

from engine import epochs
from engine.lesson_evidence import (
    LEGACY_VERSION, SUPPORTED_VERSIONS, build_packet, digest, portable_provenance,
    validate_review,
)
from scripts.lessons import _atomic_write_text, read_jsonl


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _checks(evaluation):
    return [
        {"check": str(c.get("tier", "")), "name": str(c.get("name", "")),
         "status": "PASS" if c.get("passed") is True else
                   "FAIL" if c.get("passed") is False else "UNVERIFIED"}
        for c in evaluation.get("checks", [])
    ]


def _regime_rules(packet):
    """Copy classification identity only; regime results stay reviewer-only."""
    section = packet.get("diagnostics", {}).get("regime_comparison", {})
    if section.get("status") not in {"AVAILABLE", "PARTIAL"}:
        return []
    rules = section.get("data", {}).get("classification_rules", [])
    if not isinstance(rules, list):
        raise ValueError("Invalid regime classification identities")
    identities = set()
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("version"), str) or not isinstance(rule.get("sha256"), str):
            raise ValueError("Invalid regime classification identity")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{0,79}", rule["version"]) or not re.fullmatch(r"[0-9a-f]{64}", rule["sha256"]):
            raise ValueError("Invalid regime classification identity")
        identities.add((rule["version"], rule["sha256"]))
    return [{"version": version, "sha256": sha} for version, sha in sorted(identities)]


def evidence_packet_path(root: Path, packet_sha256: str) -> Path:
    """Resolve content-addressed evidence in this checkout, not a saved path."""
    if not isinstance(packet_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", packet_sha256):
        raise ValueError("Invalid evidence packet SHA-256")
    return Path(root) / "memory/lesson_evidence" / f"{packet_sha256}.json"


def _compatible_legacy_packet(root, previous, record, payload, final):
    """Retain an unchanged v1 packet/review without trusting its old locator.

    A legacy hash is reusable only after rebuilding the entire packet from
    the freshly release-authenticated source with its original provenance.
    Merely matching a record id or source hash cannot authorize reuse.
    """
    descriptor = previous.get("evidence_packet", {})
    packet_hash = descriptor.get("sha256")
    if not packet_hash:
        return None
    path = evidence_packet_path(root, packet_hash)
    if not path.is_file():
        return None
    packet = _read(path)
    if digest(packet) != packet_hash:
        raise ValueError("Archived evidence packet hash mismatch")
    if packet.get("schema_version") != LEGACY_VERSION:
        return None
    provenance = packet.get("provenance")
    if not isinstance(provenance, dict) or portable_provenance(provenance) != record["evidence"]:
        return None
    legacy_record = {**record, "evidence": provenance}
    rebuilt = build_packet(legacy_record, payload, final, schema_version=LEGACY_VERSION)
    if digest(rebuilt) != packet_hash:
        return None
    record["evidence"] = dict(provenance)
    return packet


def _write_packet_once(path, packet):
    if path.exists():
        if digest(_read(path)) != digest(packet):
            raise ValueError("Content-addressed evidence packet collision")
        return  # Preserve the exact bytes of every existing evidence artifact.
    _atomic_write_text(path, json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def refresh_candidate_lessons(root: Path | str):
    root = Path(root)
    target = root / "memory/candidate_lessons.jsonl"
    # Preserve records whose source is temporarily unavailable; do not publish
    # them unless freshly authenticated in this refresh.
    saved = {r["record_id"]: r for r in read_jsonl(target)}
    current = []
    for manifest in sorted((root / "campaigns").glob("*/manifest.json")):
        campaign = _read(manifest)
        cid = campaign["campaign_id"]
        released = campaign.get("status") == "REVEALED" and campaign.get("oos", {}).get("status") == "REVEALED"
        no_qualified = campaign.get("status") == "CLOSED_NO_QUALIFIED"
        confirmation = {}
        release_note = ""
        if released:
            # Validates the terminal confirmation bindings before any export.
            try:
                confirmation = {r["factor"]: r for r in epochs.load_confirmation(root, cid)["confirmations"]}
            except (ValueError, OSError, KeyError):
                released = False
                release_note = "기존 확인 결과의 현재 계약 인증 불가: 정체성만 보존, 결과 공개 보류"
        for reference in campaign.get("epochs", []):
            eid = reference["epoch_id"]
            epoch = epochs.load_epoch(root, cid, eid)
            if epoch.get("status") != "CLOSED":
                continue
            for candidate in epoch.get("candidates", []):
                name = candidate["name"]
                cycle = candidate.get("cycle_id")
                if not cycle or Path(cycle).name != cycle:
                    continue
                result_path = root / "runs" / cycle / "result.json"
                if not result_path.exists():
                    continue
                result_bytes = result_path.read_bytes()
                payload = json.loads(result_bytes)
                factor = payload.get("factor", {})
                if (payload.get("campaign_id"), payload.get("epoch_id"), factor.get("name"), factor.get("definition_hash")) != (
                    cid, eid, name, candidate.get("definition_hash")):
                    raise ValueError("candidate lesson source binding mismatch")
                expected_hash = candidate.get("discovery_result_artifact_sha256")
                if expected_hash or "mechanism_study" in payload:
                    # Branch on the trusted epoch binding, not a removable
                    # payload key. Legacy is only allowed if originally unbound.
                    if not expected_hash or hashlib.sha256(result_bytes).hexdigest() != expected_hash:
                        raise ValueError("mechanism study frozen discovery artifact mismatch")
                rid = f"{cid}/{eid}/{name}"
                spec = payload.get("research_spec", {})
                published = released or no_qualified
                checks = _checks(payload.get("evaluation", {})) if published else []
                final = confirmation.get(name)
                if final:
                    checks += _checks(final.get("evaluation", {}))
                failures = [c for c in checks if c["status"] == "FAIL"]
                passed = [c for c in checks if c["status"] == "PASS"]
                record = {
                    "record_id": rid, "version": 1, "family": factor.get("family", name),
                    "ruleset": payload.get("ruleset_version"),
                    "regime_rules": [],
                    "visibility": "RELEASED_QUALITATIVE" if published else "PENDING",
                    "release_note": release_note,
                    "hypothesis_and_calculation": {
                        "hypothesis": spec.get("thesis", ""), "mechanism": spec.get("mechanism", ""),
                        "falsification": spec.get("falsification", ""),
                        "expected_relationship": spec.get("expected_relationship", ""),
                        "data_notes": spec.get("data_notes", ""),
                        "source": factor.get("source", ""), "inputs": factor.get("needs", []),
                        "params": factor.get("params", {}),
                    },
                    "validation": {"checks": checks, "phase": "confirmation" if final else "discovery",
                        "verdict": final.get("verdict") if final else candidate.get("verdict") if published else None},
                    "observations": {
                        "strengths": [c["name"] for c in passed], "weaknesses": [c["name"] for c in failures],
                        "limit": "통과는 해당 검사의 관측이며 경제적 원인의 증명이 아님. 미실행 단계는 미검증.",
                    },
                    "economic_interpretation": "원인 미확인. 사전 가설은 인과관계의 검증 결과가 아님.",
                    "general_lesson": "실패 검사와 경제적 원인을 구분해야 한다." if failures else
                        "검사 통과를 미래 수익 보장으로 해석하지 않는다." if published else "평가 공개 대기",
                    "evidence": portable_provenance({"campaign": cid, "epoch": eid, "cycle": cycle,
                        "definition_hash": factor.get("definition_hash"), "result": f"runs/{cycle}/result.json"}),
                }
                packet = None
                if published:
                    packet = build_packet(record, payload, final)
                    legacy = _compatible_legacy_packet(root, saved.get(rid, {}), record, payload, final)
                    if legacy is not None:
                        packet = legacy
                    record["regime_rules"] = _regime_rules(packet)
                    packet_hash = digest(packet)
                    # Content-addressed evidence; never copy numeric metrics to
                    # candidate memory or KNOWLEDGE. Old versions remain auditable.
                    packet_path = evidence_packet_path(root, packet_hash)
                    _write_packet_once(packet_path, packet)
                    record["evidence_packet"] = {
                        "path": str(packet_path), "sha256": packet_hash,
                        "missing": [key for key, section in packet["diagnostics"].items()
                                    if section.get("status") != "AVAILABLE"],
                    }
                # Human/agent interpretation survives regenerated factual fields.
                if "review" in saved.get(rid, {}):
                    record["review"] = saved[rid]["review"]
                record["review_basis"] = hashlib.sha256(json.dumps(
                    {"validation": record["validation"], "evidence": record["evidence"],
                     "packet_sha256": record.get("evidence_packet", {}).get("sha256")},
                    sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                if record.get("review", {}).get("schema_version") in SUPPORTED_VERSIONS:
                    try:
                        if packet is None:
                            raise ValueError("Unreleased evidence")
                        validate_review(record["review"], record, packet)
                        record["review_validation"] = "CURRENT"
                    except (ValueError, TypeError, KeyError):
                        record["review_validation"] = "STALE_OR_INVALID"
                saved[rid] = record
                current.append(record)
    _atomic_write_text(target, "".join(json.dumps(saved[k], ensure_ascii=False, sort_keys=True) + "\n" for k in sorted(saved)))
    return current


def reviewed_text(record):
    """Only explicitly reviewed qualitative text bound to current evidence."""
    review = record.get("review", {})
    if review.get("schema_version") not in {None, *SUPPORTED_VERSIONS}:
        return None
    if review.get("schema_version") in SUPPORTED_VERSIONS and record.get("review_validation") != "CURRENT":
        return None
    if review.get("basis") != record.get("review_basis") or review.get("status") != "REVIEWED":
        return None
    fields = ("economic_interpretation", "general_lesson", "scope")
    if not all(isinstance(review.get(k), str) and 0 < len(review[k]) <= 600 for k in fields):
        return None
    # A conservative format guard, not a substitute for evidence review.
    if any(re.search(r"\d|%|IC|p값|수익률.*[=<>]", review[k]) for k in fields):
        return None
    return tuple(review[k] for k in fields)


def render_grouped_lessons(records):
    # A repeated input row is not another observation. Conflicting versions of
    # the same identity are withheld instead of picking whichever came first.
    unique_records = {}
    conflicting_ids = set()
    for record in records:
        rid = record["record_id"]
        if rid in unique_records and unique_records[rid] != record:
            conflicting_ids.add(rid)
        else:
            unique_records[rid] = record
    groups = defaultdict(list)
    pending_review = 0
    structured = defaultdict(list)

    def regime_key(record):
        return tuple(sorted({(rule["version"], rule["sha256"])
                             for rule in record.get("regime_rules", [])}))

    for rid, record in sorted(unique_records.items()):
        if rid in conflicting_ids:
            continue
        if record["visibility"] != "RELEASED_QUALITATIVE":
            continue
        v = record["validation"]
        review = reviewed_text(record)
        if review is None:
            pending_review += 1
            continue
        if record.get("review", {}).get("schema_version") in SUPPORTED_VERSIONS:
            # Same key is not enough: scope, ruleset and exact principle text
            # must agree. Contradicting cases retain their own interpretation.
            key = (record["review"]["lesson_key"], record["ruleset"],
                   review[1], review[2], regime_key(record))
            structured[key].append(record)
            continue
        # Same failure is not sufficient: keep mechanism family, ruleset and
        # evaluation phase separate. No automatic semantic/causal merging.
        key = (record["family"], record["ruleset"], v["phase"],
               tuple(sorted((c["check"], c["name"], c["status"]) for c in v["checks"])),
               reviewed_text(record), regime_key(record))
        groups[key].append(record)
    lines = ["## 누적 검증 교훈", "", "검토된 일반 교훈만 축약한다. 같은 표본의 반복은 독립 증거가 아니다.",
             f"경제적 해석 검토 대기: {pending_review}건. 상세 검사 기록은 candidate_lessons.jsonl에 보존한다.", ""]
    if conflicting_ids:
        lines += [f"동일 시행의 상충 버전 {len(conflicting_ids)}건은 확인 전 요약에서 제외한다.", ""]

    def references(rows):
        ids = sorted({row["record_id"] for row in rows})
        return ("- 근거: " + ", ".join(ids[:5])
                + (f" 외 {len(ids) - 5}건 (전체 근거는 candidate_lessons.jsonl)" if len(ids) > 5 else ""))

    def regime_identity(row):
        return "- 레짐 기준: " + (", ".join(
            f"{version} ({sha[:12]})" for version, sha in regime_key(row)
        ) or "미연결/기준 미상")

    for key, rows in sorted(structured.items(), key=lambda item: str(item[0])):
        stances = {r["review"]["stance"] for r in rows}
        label = "반례 있음" if "CONTRADICTS" in stances else "잠정 관찰 (독립 재현 미확인)"
        lines += [f"### {key[0]}", "", f"- 검사 규칙: {key[1] or '미상'}", f"- 교훈: {key[2]}",
                  f"- 적용 한계: {key[3]}", regime_identity(rows[0]), f"- 근거 수준: {label}"]
        for stance in ("SUPPORTS", "CONTRADICTS", "UNCERTAIN"):
            subset = [r for r in rows if r["review"]["stance"] == stance]
            if not subset:
                continue
            interpretations = sorted({r["review"]["economic_interpretation"] for r in subset})
            lines.append(f"- {stance} 관측 {len(subset)}건: " + " / ".join(interpretations[:2])
                         + (f" (다른 해석 {len(interpretations) - 2}개는 후보 원장에 보존)"
                            if len(interpretations) > 2 else ""))
        lines.append(references(rows))
        lines.append("")
    for key, rows in sorted(groups.items(), key=lambda x: str(x[0])):
        row = rows[0]
        review = reviewed_text(row)
        lines += [f"### {key[0]} / {key[2]}", "",
                  f"- 검사 규칙: {key[1] or '미상'}",
                  regime_identity(row),
                  "- 확인된 검사: " + "; ".join(f"{c['check']} {c['name']}: {c['status']}" for c in row["validation"]["checks"]),
                  "- 해석(추정): " + (review[0] if review else row["economic_interpretation"]),
                  "- 교훈: " + (review[1] if review else row["general_lesson"]),
                  "- 적용 한계: " + (review[2] if review else "해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기."),
                  references(rows), ""]
    if not groups and not structured:
        lines += ["검토가 완료된 공개 교훈 없음. 검사 실패에서 경제적 원인을 자동 추론하지 않는다.", ""]
    return "\n".join(lines)
