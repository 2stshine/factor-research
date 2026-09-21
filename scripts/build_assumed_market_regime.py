"""Build explicitly PIT-assumed monthly KRX index context; no DB or campaign I/O.

The latest observed raw month is always excluded: a later local trading date
must demonstrate that a candidate month has ended. The union of local KRX
index/stock partition dates is an assumed trading calendar, not independently
certified exchange holiday evidence. It detects missing selected-index days
relative to that union, but cannot detect a date missing from every source.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from engine.regime_inputs import VERSION, digest, make_assumption_acceptance, read_context
from engine.regimes import RULES, RULES_HASH, classify_monthly_market


INDEX_NAMES = {"KOSPI": "코스피", "KOSDAQ": "코스닥"}
ASSUMPTIONS = [
    "Historical KRX index closes are accepted as usable month-end observations under the explicit user policy; first-publication vintages and later corrections are not independently certified.",
    "known_at is the observation-month end at 23:59:59 Asia/Seoul, serialized without timezone for the existing decision-calendar contract; it is an assumed diagnostic availability bound, not an observed publication or receipt timestamp.",
    "The union of local KRX index and stock date partitions is assumed to cover the trading calendar. Missing selected-index dates relative to that union are blocked; dates absent from all local sources cannot be detected.",
    "A month is accepted only when a following-month local trading date exists, the selected index covers every local-calendar day in that month, and the local last trading day is within seven calendar days of month-end. The latest raw month is excluded even if it might be complete.",
    "Only one primary official market index is used. KOSPI is the fixed default, chosen without factor-performance inspection; the optional KOSDAQ output must not be combined as another primary index.",
    "Rules remain monthly-trend-vol-v2. Missing observations are not filled and warm-up or state thresholds are not shortened. Month-t regimes describe conditions for month-t+1 diagnostics, not contemporaneous return prediction.",
]


def encode(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode()


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _partition_day(path: Path) -> date:
    return date.fromisoformat(path.parent.name.removeprefix("date="))


def collect_local(data_dir: Path, index: str, as_of: str) -> tuple[list[dict], list[dict], dict]:
    if index not in INDEX_NAMES:
        raise ValueError("Only KOSPI or KOSDAQ is supported")
    cutoff = date.fromisoformat(as_of)
    calendar_paths = []
    for relative in ("index/krxapi", "stock/marcap", "stock/krxapi"):
        calendar_paths.extend(p for p in sorted((data_dir / relative).glob("date=*/*.parquet"))
                              if _partition_day(p) <= cutoff)
    if not calendar_paths:
        raise ValueError("No local KRX trading calendar partitions")
    days = sorted({_partition_day(p).isoformat() for p in calendar_paths})
    paths = [p for p in sorted((data_dir / "index/krxapi").glob(f"date=*/{index.lower()}.parquet"))
             if _partition_day(p) <= cutoff]
    if not paths:
        raise ValueError("No selected index source files")
    daily, files = [], []
    for path in paths:
        body = path.read_bytes()
        table = pq.ParquetFile(path).read(columns=["BAS_DD", "IDX_NM", "CLSPRC_IDX"])
        records = table.to_pylist()
        selected = [(i, row) for i, row in enumerate(records) if row["IDX_NM"] == INDEX_NAMES[index]]
        if len(selected) != 1:
            raise ValueError(f"Expected exactly one selected index row: {path}")
        i, row = selected[0]
        trade_date = datetime.strptime(str(row["BAS_DD"]), "%Y%m%d").date()
        if trade_date != _partition_day(path):
            raise ValueError(f"Source trade date differs from partition: {path}")
        close = float(str(row["CLSPRC_IDX"]).replace(",", ""))
        if not math.isfinite(close) or close <= 0:
            raise ValueError(f"Nonfinite or nonpositive index close: {path}")
        proof = {"path": str(path.resolve()), "sha256": sha(body),
                 "trade_date": trade_date.isoformat(), "source_row_index": i,
                 "row_count": len(records)}
        files.append(proof)
        daily.append({"trade_date": trade_date.isoformat(), "close": close,
                      "source_file": proof["path"], "source_sha256": proof["sha256"],
                      "source_row_index": i, "raw_close": row["CLSPRC_IDX"]})
    calendar = {"dates": days, "date_count": len(days),
                "partition_count": len(calendar_paths),
                "partition_paths_sha256": digest([str(p.resolve()) for p in calendar_paths]),
                "date_set_sha256": digest(days),
                "semantics": "ASSUMED_LOCAL_TRADING_DATE_UNION_NOT_VERIFIED_HOLIDAY_CALENDAR"}
    return daily, files, calendar


def monthly_rows(daily: list[dict], calendar_dates: list[str], *, as_of: str) -> tuple[list[dict], dict]:
    """Fail closed on source conflicts/calendar gaps; do not fill missing data."""
    cutoff = pd.Timestamp(date.fromisoformat(as_of))
    if not daily or not calendar_dates:
        raise ValueError("Daily observations and local calendar are required")
    by_date = {}
    for row in daily:
        day = date.fromisoformat(row["trade_date"])
        if day.isoformat() in by_date:
            raise ValueError("Duplicate index trade date; explicit resolution required")
        if day > cutoff.date():
            continue
        if not math.isfinite(row["close"]) or row["close"] <= 0:
            raise ValueError("Index close must be finite and positive")
        by_date[day.isoformat()] = row
    if not by_date:
        raise ValueError("No observations on or before as_of")
    calendar = sorted({date.fromisoformat(d).isoformat() for d in calendar_dates
                       if date.fromisoformat(d) <= cutoff.date()})
    if not calendar or not set(by_date).issubset(calendar):
        raise ValueError("Selected-index date absent from local trading calendar")
    first = pd.Period(min(by_date), freq="M")
    last_raw = pd.Period(max(by_date), freq="M")
    # Conservative even at calendar month-end: never infer that the last
    # observed month is complete merely from today's wall clock.
    last = min(last_raw - 1, pd.Period(max(calendar), freq="M") - 1,
               cutoff.to_period("M") - 1)
    if first > last:
        raise ValueError("No month has subsequent trading-date completeness evidence")
    rows, checks = [], []
    for month in pd.period_range(first, last, freq="M"):
        expected = [d for d in calendar if d[:7] == str(month)]
        if not expected:
            raise ValueError(f"Missing full calendar month: {month}")
        missing = sorted(set(expected) - set(by_date))
        if missing:
            raise ValueError(f"Selected-index daily gap in {month}: {missing[:5]}")
        end_gap = (month.end_time.date() - date.fromisoformat(expected[-1])).days
        if end_gap > 7:
            raise ValueError(f"Local calendar does not establish near-month-end coverage: {month}")
        selected = by_date[expected[-1]]
        known_at = month.end_time.floor("s").isoformat()
        rows.append({"month": str(month), "close": selected["close"], "known_at": known_at,
                     "source_trade_date": selected["trade_date"],
                     "source_file": selected.get("source_file"),
                     "source_sha256": selected.get("source_sha256"),
                     "source_row_index": selected.get("source_row_index")})
        checks.append({"month": str(month), "local_calendar_dates": len(expected),
                       "last_trade_date": expected[-1], "calendar_month_end_gap_days": end_gap})
    return rows, {"method": "SUBSEQUENT_MONTH_PLUS_COMPLETE_ASSUMED_LOCAL_CALENDAR",
                  "first_month": str(first), "last_complete_month": str(last),
                  "last_raw_trade_date": max(by_date), "excluded_latest_raw_month": str(last_raw),
                  "missing_daily_rows": 0, "duplicate_dates": 0, "month_checks": checks,
                  "actual_publication_times_verified": False,
                  "calendar_holidays_independently_verified": False}


def build(data_dir: Path, output: Path, policy_path: Path, *, as_of: str,
          index: str = "KOSPI") -> dict:
    if output.exists():
        raise FileExistsError("Output must be a new directory; existing artifacts are immutable")
    policy_body = policy_path.read_bytes()
    policy = json.loads(policy_body)
    daily, raw_files, calendar = collect_local(data_dir, index, as_of)
    rows, completeness = monthly_rows(daily, calendar["dates"], as_of=as_of)
    accepted_at = datetime.now(timezone.utc).isoformat()
    provenance = {"schema_version": "assumed-krx-market-provenance-v1", "index": index,
                  "data_dir": str(data_dir.resolve()), "as_of": as_of,
                  "compiled_at": accepted_at, "actual_historical_receipt_times": None,
                  "raw_files": raw_files, "raw_daily_rows": daily,
                  "local_calendar": calendar, "completeness": completeness,
                  "compiler_sha256": sha(Path(__file__).read_bytes()),
                  "raw_modified": False, "db_accessed": False,
                  "factor_results_read": False, "pit_status": "PIT_ASSUMED"}
    provenance_body = encode(provenance)
    first, last = rows[0]["month"], rows[-1]["month"]
    source = {"context_id": f"KRX_{index}_MONTH_END_ASSUMED",
              "source_id": f"krx-{index.lower()}-monthend-assumed-{first}-{last}-v1",
              "kind": "market_index", "market_id": index, "official_market_index": True,
              "frequency": "MONTH_END", "purpose": "DIAGNOSTIC_ONLY",
              "pit_status": "PIT_ASSUMED",
              "known_at_semantics": "ASSUMED_HISTORICAL_AVAILABILITY",
              "assumptions": ASSUMPTIONS,
              "scope": {"start_month": first, "end_month": last,
                        "intraday_allowed": False, "factor_feature_allowed": False},
              "provenance_file": "provenance.json", "provenance_sha256": sha(provenance_body),
              "raw_source_fingerprint": digest(raw_files),
              "classification_rules": RULES, "classification_rules_sha256": RULES_HASH,
              "rows": rows}
    evidence = [{"uri": str((output / "provenance.json").resolve()), "sha256": sha(provenance_body)},
                {"uri": str(policy_path.resolve()), "sha256": sha(policy_body)}]
    acceptance = make_assumption_acceptance(source, policy, evidence, accepted_at=accepted_at)
    acceptance_body = encode(acceptance)
    context = {"schema_version": VERSION, "contexts": [{"source": source,
               "approval_file": "approval.json", "approval_sha256": sha(acceptance_body)}]}
    timeline = classify_monthly_market(pd.DataFrame(rows), as_of=as_of,
        market_id=index, source_id=source["source_id"], rules_version="monthly-trend-vol-v2")
    timeline_rows = json.loads(timeline.to_json(orient="records", double_precision=15))
    ready = [r for r in timeline_rows if r["detail_status"] == "READY"]
    summary = {"pit_status": "PIT_ASSUMED", "historical_pit_verified": False,
        "index": index, "as_of": as_of, "raw_daily_rows": len(daily),
        "source_months": len(rows), "source_start_month": first, "source_end_month": last,
        "last_raw_trade_date": completeness["last_raw_trade_date"],
        "excluded_latest_raw_month": completeness["excluded_latest_raw_month"],
        "timeline_months": len(timeline_rows), "all_four_axes_ready_months": len(ready),
        "first_all_four_axes_ready_month": ready[0]["month"] if ready else None,
        "regime_counts": dict(Counter(r["regime"] for r in timeline_rows)),
        "detail_status_counts": dict(Counter(r["detail_status"] for r in timeline_rows)),
        "source_sha256": digest(source), "context_sha256": sha(encode(context)),
        "rules_version": "monthly-trend-vol-v2", "rules_sha256": RULES_HASH,
        "factor_returns_evaluated": False, "campaign_modified": False, "registry_modified": False}
    readme = (f"# {index} 월말 레짐 — PIT_ASSUMED\n\n"
        "사용자의 명시적 가정 기반 진단 사용 정책으로 연결한 파생 입력이다. 역사적 PIT 검증 완료나 최초 발표본 인증이 아니다.\n\n"
        f"- 원시 마지막 거래일: {completeness['last_raw_trade_date']}. 최신 원시월 {completeness['excluded_latest_raw_month']}은 보수적으로 제외.\n"
        f"- 사용 입력: {first}~{last}, {len(rows)}개월. 룰 monthly-trend-vol-v2 그대로.\n"
        f"- 네 축 최초 READY: {summary['first_all_four_axes_ready_month']}; 전체 READY {len(ready)}개월. 초기 warm-up은 UNKNOWN/PARTIAL이며 기준을 완화하지 않았다.\n"
        "- known_at 월말23:59:59는 KST 의사결정용 가정 bound이며 실제 수신·발표 시각이 아니다. 원시 거래일은 별도 보존한다.\n"
        "- 지수별 원시일이 로컬 KRX 달력 합집합과 일치하는지 확인한다. 모든 로컬 소스에서 함께 사라진 거래일은 확인할 수 없어 달력 완전성 가정을 명시했다.\n"
        "- provenance.json에 원시 파일 SHA·거래일·원문 행, 정책 및 승인 바인딩은 approval.json/context.json에 보존.\n"
        "- timeline.json은 시장 상태만 분류한다. 팩터 성과, OOS, DB, 기존 캠페인, Gold는 읽거나 변경하지 않았다.\n")
    artifacts = {"provenance.json": provenance_body, "approval.json": acceptance_body,
                 "context.json": encode(context), "summary.json": encode(summary),
                 "timeline.json": encode({"pit_status": "PIT_ASSUMED", "assumptions": ASSUMPTIONS,
                    "source_sha256": digest(source), "rules": RULES, "as_of": as_of,
                    "rows": timeline_rows}), "README.md": readme.encode()}
    output.mkdir(parents=True, exist_ok=False)
    for name, body in artifacts.items():
        with (output / name).open("xb") as f:
            f.write(body)
    read_context(output / "context.json")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--data-dir", type=Path,
        default=Path("/Users/mac/Documents/GitHub/TeamAlpha-data/data"))
    parser.add_argument("--index", choices=sorted(INDEX_NAMES), default="KOSPI")
    args = parser.parse_args()
    print(json.dumps(build(args.data_dir, args.output, args.policy,
                           as_of=args.as_of, index=args.index), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
