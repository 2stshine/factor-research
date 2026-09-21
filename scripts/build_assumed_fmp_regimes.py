"""Build explicitly assumed diagnostic FMP contexts from preserved local Bronze.

No API/DB call, no historical-PIT certification, no campaign execution, and no
overwrite. Existing fully reviewed Korean policy context is not duplicated.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from engine.assumed_macro_regimes import normalize_observation, monthly_states, source_context
from scripts.fmp_pit_audit import COT_EXCEPTIONS, load_run, encoded
from scripts.verify_fmp_remaining import load_exact_macro

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / "TeamAlpha-data/data/regime"
POLICY_ROOT = ROOT / "output/regime_inputs/kr-policy-pit-20260920"

# Reuse the already retained official special-announcement text. These dates
# are timing assumptions for current values, not claims of first-vintage proof.
COT_KNOWN_RELEASE_DATES = {
    **COT_EXCEPTIONS, "2015-06-30": "2015-07-06", "2025-12-23": "2025-12-29",
    "2023-01-31": "2023-02-24", "2023-02-07": "2023-03-03",
    "2023-02-14": "2023-03-08", "2023-02-21": "2023-03-10",
    "2023-02-28": "2023-03-14", "2023-03-07": "2023-03-16", "2023-03-14": "2023-03-21",
}


def save(path, value):
    body = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(body)
    return hashlib.sha256(body).hexdigest()


def load_sources(data_root=DATA_ROOT, policy_root=POLICY_ROOT):
    # Reuse integrity-aware local readers only; no numerical audit, network
    # source search, or historical-vintage verification is performed here.
    rows, macro_lineage = load_exact_macro(policy_root)
    kinds = {s: "macro" for s in rows}
    lineage = [macro_lineage]
    for version in ("korea-external-v1", "korea-risk-v1"):
        run = data_root / "fmp-external" / version / "snapshot=backfill-20260920/runs/from=2015-01-01/to=2026-09-18/manifest.json"
        extra, proof = load_run(run)
        contract = json.loads(run.read_bytes())["contract"]["scope"]
        for symbol, values in extra.items():
            if symbol in rows:
                raise ValueError("Unexpected duplicate source identity")
            rows[symbol] = values
            kinds[symbol] = contract[symbol]["kind"]
        lineage.append(proof)
    return rows, kinds, lineage


def build(output, policy_path, as_of, *, data_root=DATA_ROOT, policy_root=POLICY_ROOT):
    from engine.regime_inputs import make_assumption_acceptance

    output, policy_path = Path(output).resolve(), Path(policy_path).resolve()
    if output.exists():
        raise FileExistsError("A fresh output directory is required")
    policy = json.loads(policy_path.read_bytes())
    rows, kinds, lineage = load_sources(data_root, policy_root)
    policy_body_hash = hashlib.sha256(policy_path.read_bytes()).hexdigest()
    lineage_payload = {"source_runs": lineage, "raw_policy_rate_excluded": True,
                       "source_counts": {s: len(v) for s, v in sorted(rows.items())},
                       "assumption_policy_file": str(policy_path), "assumption_policy_sha256": policy_body_hash,
                       "cot_exception_release_dates": COT_KNOWN_RELEASE_DATES,
                       "cot_exception_evidence": str(ROOT / "output/pit_audit/fmp-20260920/evidence/cftc_announcements.html")}
    lineage_payload["cot_exception_evidence_sha256"] = hashlib.sha256(Path(lineage_payload["cot_exception_evidence"]).read_bytes()).hexdigest()
    output.mkdir(parents=True)
    lineage_hash = save(output / "provenance.json", lineage_payload)
    contexts, stats = [], []
    acceptance_time = datetime.now(timezone.utc).isoformat()
    for symbol in sorted(rows):
        if symbol == "KR_POLICY_RATE":
            continue
        kind = kinds[symbol]
        normalized = [normalize_observation(symbol, kind, r, cot_release_dates=COT_KNOWN_RELEASE_DATES) for r in rows[symbol]]
        normalized.sort(key=lambda r: (r["provider_date"], r["observation_id"]))
        name = symbol.replace("^", "").replace("-", "_").replace(".", "_")
        normalized_path = output / "normalized" / f"{name}.json"
        normalized_hash = save(normalized_path, normalized)
        monthly = monthly_states(normalized, kind, start_month="2015-01", as_of=as_of)
        source = source_context(symbol, kind, normalized, monthly, normalized_sha256=normalized_hash, lineage_sha256=lineage_hash)
        evidence = [{"uri": str(normalized_path), "sha256": normalized_hash},
                    {"uri": str(output / "provenance.json"), "sha256": lineage_hash},
                    {"uri": str(policy_path), "sha256": policy_body_hash}]
        approval = make_assumption_acceptance(source, policy, evidence, accepted_at=acceptance_time)
        approval_name = f"approvals/{name}.json"
        approval_hash = save(output / approval_name, approval)
        contexts.append({"source": source, "approval_file": approval_name, "approval_sha256": approval_hash})
        stats.append({"series_id": symbol, "kind": kind, "context_id": source["context_id"], "observations": len(normalized),
                      "excluded_observations": dict(Counter(r["excluded_reason"] for r in normalized if r["excluded_reason"])),
                      "months": len(monthly), "states": dict(Counter(r["state"] for r in monthly)),
                      "unknown_reasons": dict(Counter(r["reason"] for r in monthly if r["state"] == "UNKNOWN")),
                      "first_classified_month": next((r["month"] for r in monthly if r["state"] != "UNKNOWN"), None),
                      "last_month_state": monthly[-1]["state"]})
    context_hash = save(output / "context.json", {"schema_version": "diagnostic-regime-input-v1", "contexts": contexts})
    legacy = []
    for manifest_path in sorted((data_root / "fmp").glob("series=*/*/*/*/manifest.json")):
        manifest = json.loads(manifest_path.read_bytes())
        params = manifest["request_params"]
        legacy.append({"series_id": params.get("symbol", "US_TREASURY"), "from": params["from"], "to": params["to"],
                       "reason": "LOCAL_LEGACY_SAMPLE_ONLY_2026_09; no completed requested month or historical warm-up",
                       "manifest_path": str(manifest_path), "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()})
    summary = {"schema_version": "assumed-fmp-regime-build-v1", "as_of": as_of,
               "pit_status": "PIT_ASSUMED", "historical_pit_verified": False,
               "context_file": str(output / "context.json"), "context_sha256": context_hash,
               "context_count": len(contexts), "series": stats,
               "replaced_raw_policy": {"series_id": "KR_POLICY_RATE", "raw_rows": len(rows["KR_POLICY_RATE"]),
                                       "replacement": "Existing separately approved KR_POLICY_DIRECTION_3M context, not copied here"},
               "legacy_sources_skipped": legacy, "fmp_api_calls": 0,
               "originals_modified": False, "database_accessed": False, "campaigns_modified": False,
               "new_verified_pit_approvals": 0}
    save(output / "summary.json", summary)
    lines = ["# 가정 기반 FMP 월말 레짐 입력", "", "**PIT_ASSUMED — 역사적 PIT 검증 완료가 아닌 사용자가 수용한 가정 기반 진단 자료.**", "",
             "원본 actual/close/COT 포지션을 사용하되, 과거 최초값·정정 이력은 복원되지 않았다는 한계를 유지한다.",
             "실제 수집시각은 보존하며 별도 assumed 가용시각을 계산한다. 기존 source/approval/DB/campaign은 수정하지 않는다.", "",
             "- 경제 캘린더: provider UTC→KST, 기준월이 아니라 가용 시점의 최신 actual 사용.",
             "- ETF/FX: provider 날짜 다음 뉴욕 자정 가용 가정, 연속 4개월 월말값의 3개월 변화 부호.",
             "- 매크로/COT/변동성지수: 현재 월을 제외한 과거 유효월말 최소 24개 중앙값 대비 HIGH/LOW.",
             "- COT: 비상업 순포지션/OI; 일반 화요일+3일 15:30 NY 가정, 보존된 지연 예외는 별도 적용.",
             "- 알려진 미복원 COT 지연/비정규 기준일은 제외한다. 주별 자료는 발표 후 경과뿐 아니라 포지션 기준일 이후 14일도 적용한다.",
             "- stale 제한: 월간 60일, COT 14일, 가격/지수 7일. 결측·상충·워밍업은 UNKNOWN으로 보존한다.",
             "- 월 t 판독은 t+1 진단용이다. HIGH/UP이 경기 호조·미래 상승을 뜻하지 않는다.",
             "- 동일 시각 값 충돌은 UNKNOWN; 숫자 1개와 null 중복이면 숫자를 사용하되 양쪽 원본 연결을 보존한다.", "",
             "| Series | Kind | Records | Months | States | First classified |", "|---|---|---:|---:|---|---|"]
    for item in stats:
        lines.append(f"| {item['series_id']} | {item['kind']} | {item['observations']} | {item['months']} | {item['states']} | {item['first_classified_month']} |")
    lines += ["", f"컨텍스트 {len(contexts)}개. raw 정책금리 105행은 기존 검증 정제축으로 대체하여 중복 생성하지 않는다.",
              f"기존 FMP {len(legacy)}계열의 로컬 자료는 2026년 9월 표본뿐이라 이번 완료월 범위에서 제외한다. 추가 수집하지 않았다.",
              "수용서 schema는 pit-regime-assumption-v1이며 검증 PIT 승인과 구별한다. 분류 룰은 팩터 성과 없이 고정했다.", ""]
    save(output / "README.md", "\n".join(lines).encode())
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    result = build(args.output, args.policy, args.as_of)
    print(json.dumps({"context_count": result["context_count"], "pit_status": result["pit_status"], "context_file": result["context_file"]}))


if __name__ == "__main__":
    main()
