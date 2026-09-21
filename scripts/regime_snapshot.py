"""Render registered monthly regime inputs, not factor results or promotion decisions."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import pandas as pd

from engine.regime_inputs import load_campaign_context
from engine.regimes import classify_monthly_market


def snapshot(registry: Path, *, as_of: str) -> dict:
    registry = Path(registry).resolve()
    if not registry.is_file():
        raise ValueError("Explicit regime registry is missing")
    cutoff = pd.Timestamp(as_of)
    if pd.isna(cutoff) or cutoff.tzinfo is not None or cutoff != cutoff.normalize():
        raise ValueError("as_of must be a KST calendar date")
    last = cutoff.to_period("M")
    if last.end_time.date() > cutoff.date():
        last -= 1
    bundle = load_campaign_context(registry_path=registry)
    if not bundle or not bundle["contexts"]:
        raise ValueError("No registered regime context")
    ids, output = set(), []
    market_count = 0
    for item in bundle["contexts"]:
        source, acceptance = item["source"], item["approval"]
        identity = source["context_id"]
        if identity in ids:
            raise ValueError("Duplicate registered context")
        ids.add(identity)
        assumed = acceptance.get("schema_version") == "pit-regime-assumption-v1"
        kind = source["kind"]
        market_count += kind == "market_index"
        if market_count > 1:
            raise ValueError("Only one primary official market index is supported")
        frame = pd.DataFrame(source["rows"])
        required = {"month", "known_at", "close" if kind == "market_index" else "state"}
        if frame.empty or not required.issubset(frame):
            raise ValueError("Incomplete registered regime rows")
        months = pd.PeriodIndex(frame["month"], freq="M")
        # Standalone source-state inspection, not a campaign or OOS evaluation.
        frame = frame.loc[months <= last].copy()
        if frame.empty:
            output.append({"context_id": identity, "status": "NO_COMPLETED_ROWS",
                           "pit_status": "PIT_ASSUMED" if assumed else "PIT_VERIFIED",
                           "usable_months": 0, "rows": []})
            continue
        frame["month"] = pd.PeriodIndex(frame["month"], freq="M")
        if frame["month"].duplicated().any():
            raise ValueError("Unresolved monthly revisions")
        known = pd.to_datetime(frame["known_at"], errors="raise")
        if known.isna().any() or known.dt.tz is not None:
            raise ValueError("Expected nonmissing KST-naive availability")
        if (known.dt.to_period("M") < frame["month"]).any():
            raise ValueError("Availability precedes decision month")
        frame["known_at"] = known
        scope = source.get("scope")
        if scope:
            first_scope = pd.Period(scope["start_month"], freq="M")
            last_scope = pd.Period(scope["end_month"], freq="M")
            if first_scope > last_scope or (frame["month"] > last_scope).any():
                raise ValueError("Rows exceed declared source scope")
        if acceptance.get("schema_version") == "pit-regime-approval-v2":
            if not known.eq(frame["month"].dt.end_time.dt.floor("s")).all():
                raise ValueError("Policy day-bound rows require month-end availability")
        frame = frame.sort_values("month")
        if kind == "market_index":
            if source.get("official_market_index") is not True:
                raise ValueError("A market-index context cannot be an ETF proxy")
            if frame["close"].map(lambda x: isinstance(x, bool)).any():
                raise ValueError("Boolean market close")
            if not (known <= last.end_time).any():
                timeline = [{"month": str(m), "effective_month": str(m + 1),
                             "state": "UNKNOWN", "status": "MISSING_OR_LATE_MONTH"}
                            for m in pd.period_range(frame["month"].min(), last, freq="M")]
            else:
                values = frame.copy()
                values["month"] = values["month"].astype(str)
                classified = classify_monthly_market(values, as_of=str(last.end_time.date()),
                    market_id=source["market_id"], source_id=source["source_id"])
                timeline = [{"month": r["month"], "effective_month": r["effective_month"],
                             "state": r["regime_detail"], "coarse_state": r["regime"],
                             "status": r["detail_status"], "reason": r["detail_reason"]}
                            for r in classified.to_dict(orient="records")]
        elif kind == "macro_state":
            states = source.get("states", [])
            if len(states) < 2 or len(set(states)) != len(states) or "UNKNOWN" in states:
                raise ValueError("Invalid macro states")
            if not set(frame["state"]).issubset(set(states) | {"UNKNOWN"}):
                raise ValueError("Undeclared macro state")
            if not source.get("classification_rules", {}).get("version"):
                raise ValueError("Missing classification rules")
            lookup = frame.set_index("month").to_dict(orient="index")
            timeline = []
            for month in pd.period_range(frame["month"].min(), last, freq="M"):
                row = lookup.get(month)
                state = (row["state"] if row and row["known_at"] <= month.end_time else "UNKNOWN")
                timeline.append({"month": str(month), "effective_month": str(month + 1),
                                 "state": state, "status": "READY" if state != "UNKNOWN" else "UNKNOWN"})
        else:
            raise ValueError("Unsupported regime kind")
        # Pre-scope prices may support causal market warmup, but are not
        # themselves covered by the source's accepted diagnostic scope.
        if scope:
            timeline = [r for r in timeline if pd.Period(r["month"], freq="M") >= first_scope]
        if not timeline:
            output.append({"context_id": identity, "status": "NO_COMPLETED_ROWS",
                           "pit_status": "PIT_ASSUMED" if assumed else "PIT_VERIFIED",
                           "usable_months": 0, "rows": []})
            continue
        usable = [r for r in timeline if r["status"] == "READY"]
        output.append({"context_id": identity, "source_id": source["source_id"], "kind": kind,
                       "pit_status": "PIT_ASSUMED" if assumed else "PIT_VERIFIED",
                       "approval_sha256": item["approval_sha256"],
                       "assumption_policy_sha256": acceptance.get("assumption_policy_sha256"),
                       "assumptions": source.get("assumptions", []),
                       "data_first_month": str(frame["month"].min()),
                       "data_latest_month": str(frame["month"].max()),
                       "first_usable_month": usable[0]["month"] if usable else None,
                       "latest_usable_month": usable[-1]["month"] if usable else None,
                       "usable_months": len(usable), "total_months": len(timeline),
                       "state_counts": dict(Counter(r["state"] for r in timeline)),
                       "latest_state": timeline[-1]["state"], "latest_status": timeline[-1]["status"],
                       "status": "AVAILABLE" if len(usable) == len(timeline) else "PARTIAL" if usable else "UNKNOWN",
                       "rows": timeline})
    assumed_ids = [x["context_id"] for x in output if x["pit_status"] == "PIT_ASSUMED"]
    return {"schema_version": "registered-regime-snapshot-v1",
            "mode": "SOURCE_STATE_PREVIEW_NOT_FACTOR_EVALUATION", "as_of": as_of,
            "last_completed_month": str(last), "registry_path": str(registry),
            "registry_sha256": hashlib.sha256(registry.read_bytes()).hexdigest(),
            "context_count": len(output), "assumed_context_ids": assumed_ids,
            "verified_context_ids": [x["context_id"] for x in output if x["pit_status"] == "PIT_VERIFIED"],
            "contexts_with_usable_history": sum(x["usable_months"] > 0 for x in output),
            "configured_and_usable": all(x["usable_months"] > 0 for x in output),
            "historical_pit_verified_for_all_inputs": not assumed_ids,
            "factor_evaluation_executed": False, "campaign_created_or_modified": False,
            "promotion_gates_changed": False, "contexts": output}


def render(report: dict) -> str:
    lines = ["# 레짐 연결·판독 결과", "",
             "원시 입력으로 월별 상태를 계산한 결과다. 팩터 성과 평가·승격 실행·PIT 재검증은 아니다.", "",
             f"기준일: {report['as_of']}; 마지막 완료월: {report['last_completed_month']}",
             f"연결 {report['context_count']}축: 검증 범위 내 {len(report['verified_context_ids'])}, "
             f"PIT 가정 {len(report['assumed_context_ids'])}. 사용 가능한 과거 구간 보유 {report['contexts_with_usable_history']}축.", "",
             "| Context | PIT basis | Source last month | First usable | Usable months | Latest state |",
             "|---|---|---|---|---:|---|"]
    for row in report["contexts"]:
        lines.append(f"| {row['context_id']} | {row['pit_status']} | {row.get('data_latest_month', '-')} | "
                     f"{row.get('first_usable_month', '-')} | {row['usable_months']} | {row.get('latest_state', 'UNKNOWN')} |")
    lines += ["", "`UNKNOWN`에는 워밍업·원본 부재·노후화·가용시각 제약이 포함된다. 누락 월은 채우지 않는다.",
              "가정 입력은 검증된 최초 발표본이 아니다. 가정·규칙·출처는 새 캠페인 생성 때 동결된다.",
              "기존 캠페인이나 승격 기준을 변경하지 않는다. 레짐별 팩터 성과는 새 연구 실행 이후에만 생성된다.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("research/regime_sources.json"))
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, required=True, help="A new output directory")
    args = parser.parse_args()
    report = snapshot(args.registry, as_of=args.as_of)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "snapshot.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    (args.output / "README.md").write_text(render(report))
    print(json.dumps({k: report[k] for k in ("context_count", "contexts_with_usable_history", "configured_and_usable", "last_completed_month")}))


if __name__ == "__main__":
    main()
