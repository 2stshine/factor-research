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
                payload = _read(result_path)
                factor = payload.get("factor", {})
                if (payload.get("campaign_id"), payload.get("epoch_id"), factor.get("name"), factor.get("definition_hash")) != (
                    cid, eid, name, candidate.get("definition_hash")):
                    raise ValueError("candidate lesson source binding mismatch")
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
                    "visibility": "RELEASED_QUALITATIVE" if published else "PENDING",
                    "release_note": release_note,
                    "hypothesis_and_calculation": {
                        "hypothesis": spec.get("thesis", ""), "mechanism": spec.get("mechanism", ""),
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
                    "evidence": {"campaign": cid, "epoch": eid, "cycle": cycle,
                        "definition_hash": factor.get("definition_hash"), "result": str(result_path)},
                }
                # Human/agent interpretation survives regenerated factual fields.
                if "review" in saved.get(rid, {}):
                    record["review"] = saved[rid]["review"]
                record["review_basis"] = hashlib.sha256(json.dumps(
                    {"validation": record["validation"], "evidence": record["evidence"]},
                    sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                saved[rid] = record
                current.append(record)
    _atomic_write_text(target, "".join(json.dumps(saved[k], ensure_ascii=False, sort_keys=True) + "\n" for k in sorted(saved)))
    return current


def reviewed_text(record):
    """Only explicitly reviewed qualitative text bound to current evidence."""
    review = record.get("review", {})
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
    groups = defaultdict(list)
    for record in records:
        if record["visibility"] != "RELEASED_QUALITATIVE":
            continue
        v = record["validation"]
        # Same failure is not sufficient: keep mechanism family, ruleset and
        # evaluation phase separate. No automatic semantic/causal merging.
        key = (record["family"], record["ruleset"], v["phase"],
               tuple(sorted((c["check"], c["name"], c["status"]) for c in v["checks"])),
               reviewed_text(record))
        groups[key].append(record)
    lines = ["## 누적 검증 교훈", "", "같은 계열·검사·규칙·단계의 관측을 묶었다. 독립적인 증거 개수가 아니다.", ""]
    for key, rows in sorted(groups.items(), key=lambda x: str(x[0])):
        row = rows[0]
        review = reviewed_text(row)
        lines += [f"### {key[0]} / {key[2]}", "",
                  "- 확인된 검사: " + "; ".join(f"{c['check']} {c['name']}: {c['status']}" for c in row["validation"]["checks"]),
                  "- 해석(추정): " + (review[0] if review else row["economic_interpretation"]),
                  "- 교훈: " + (review[1] if review else row["general_lesson"]),
                  "- 적용 한계: " + (review[2] if review else "해당 계열과 검증 데이터에 한정. 경제적 해석 검토 대기."),
                  "- 근거: " + ", ".join(r["record_id"] for r in rows), ""]
    if not groups:
        lines += ["공개 가능한 종료 캠페인의 교훈 없음. 후보별 기록은 공개 대기 상태로 보존한다.", ""]
    return "\n".join(lines)
