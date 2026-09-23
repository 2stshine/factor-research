"""Date alignment of frozen KOSPI context to retained next-session index opens.

This intentionally cannot certify trades: the calendar is an accepted local
date union, index levels are not investable asset prices, and actual exchange
open timestamps/holdings/costs were not provided. No factor/OOS results read.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from engine.monthly_execution_timing import CONTRACT
from engine.regime_inputs import read_context
from scripts.build_assumed_fmp_regimes import save


def audit(context_path, output):
    context_path, output = Path(context_path).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError("Use a new report directory")
    contexts = read_context(context_path)["contexts"]
    markets = [c["source"] for c in contexts if c["source"]["kind"] == "market_index"]
    if len(markets) != 1 or markets[0].get("market_id") != "KOSPI":
        raise ValueError("Exactly one KOSPI source required")
    source = markets[0]
    path = context_path.parent / source["provenance_file"]
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != source["provenance_sha256"]:
        raise ValueError("Source provenance hash mismatch")
    proof = json.loads(body)
    days = proof["local_calendar"]["dates"]
    if days != sorted(set(days)):
        raise ValueError("Calendar must be ordered and unique")
    daily = {r["trade_date"]: r for r in proof["raw_daily_rows"]}
    results = []
    for row in source["rows"]:
        month = pd.Period(row["month"], freq="M")
        cutoff = month.end_time.floor("s")
        if pd.Timestamp(row["known_at"]) != cutoff:
            raise ValueError("Unexpected source cutoff")
        if pd.Period(row["source_trade_date"], freq="M") != month:
            raise ValueError("Source close date outside decision month")
        next_day = next((d for d in days if pd.Timestamp(d) > cutoff), None)
        next_source = daily.get(next_day)
        opened, error = None, None
        if next_source:
            raw = Path(next_source["source_file"])
            if hashlib.sha256(raw.read_bytes()).hexdigest() != next_source["source_sha256"]:
                raise ValueError("Next-session raw file hash mismatch")
            values = pq.ParquetFile(raw).read(columns=["BAS_DD", "IDX_NM", "OPNPRC_IDX"]).to_pylist()
            item = values[next_source["source_row_index"]]
            if item["IDX_NM"] != "코스피" or str(item["BAS_DD"]) != next_day.replace("-", ""):
                raise ValueError("Next-session row identity mismatch")
            try:
                opened = float(str(item["OPNPRC_IDX"]).replace(",", ""))
            except (TypeError, ValueError):
                error = "MISSING_INDEX_OPEN"
            if opened is not None and (not math.isfinite(opened) or opened <= 0):
                opened, error = None, "INVALID_INDEX_OPEN"
        else:
            error = "NEXT_CALENDAR_DATE_HAS_NO_INDEX_ROW"
        if next_day and next_day[:7] != str(month + 1):
            error = "NO_NEXT_MONTH_SESSION"
        results.append({"signal_month": str(month), "effective_month": str(month + 1),
            "decision_at_kst": cutoff.tz_localize("Asia/Seoul").isoformat(),
            "source_close_date": row["source_trade_date"], "same_month_close_execution_allowed": False,
            "next_observed_session_date": next_day, "next_index_open_level": opened,
            "exact_execution_at": None, "exact_execution_at_status": "NOT_PROVIDED; special open times not guessed",
            "next_source_sha256": next_source["source_sha256"] if next_source else None,
            "date_alignment_passed": error is None,
            "status": error or "DATE_ALIGNMENT_ONLY_NOT_EXECUTION"})
    report = {"schema_version": CONTRACT["version"], "context_file_sha256": hashlib.sha256(context_path.read_bytes()).hexdigest(),
        "source_provenance_sha256": source["provenance_sha256"], "contract": CONTRACT,
        "signal_months": len(results), "date_aligned_months": sum(r["date_alignment_passed"] for r in results),
        "status_counts": dict(Counter(r["status"] for r in results)),
        "first_signal_month": results[0]["signal_month"], "last_signal_month": results[-1]["signal_month"],
        "execution_certified": False, "factor_research_rerun": False, "orders_submitted": False,
        "limitations": ["Calendar is the already accepted local KRX date union, not independently verified exchange sessions.",
            "KOSPI index open is an alignment reference, not an executable stock or ETF fill price.",
            "No exact special-day open times, asset-level executable prices, holdings, cost/slippage or broker fills were supplied.",
            "Existing month-end return diagnostics and frozen factor gates/results are unchanged.",
            "Temporal contract passing alone cannot approve a regime-based trading strategy."], "rows": results}
    output.mkdir(parents=True)
    save(output / "alignment.json", report)
    save(output / "README.md", ("# 월말 판독 → 다음 관측 거래일 정렬\n\n"
        f"날짜·지수 시가 연결 {report['date_aligned_months']}/{len(results)}개월. 실제 매매 인증 아님.\n\n"
        + "\n".join("- " + x for x in report["limitations"]) + "\n").encode())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.context, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
