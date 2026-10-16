"""Prepare local draft components. Never certify or run market performance."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from strategies.monthly_input_preparation import (
    PreparationBlocked, compute_open_window, draft_status,
    prepare_pit_scores, require, stamp, external_input_blockers,
)
from strategies.run_monthly_comparison import load_plan, save_new

ROOT = Path(__file__).resolve().parents[1]


def _require_signal_window(path, calendar):
    """Bind each draft return to its t+1/t+2 window; no invented session."""
    signal = pd.Period(path["signal_month"], freq="M")
    dates = path["coverage"].get("session_dates", [])
    require(bool(dates), "SESSION_COVERAGE_REQUIRED", "Asset path needs dates")
    endpoints = [pd.Timestamp(dates[0]), pd.Timestamp(dates[-1])]
    require([str(date.to_period("M")) for date in endpoints] == [str(signal+1), str(signal+2)],
            "ASSET_SIGNAL_WINDOW_MISMATCH", "Use the signal month's t+1 entry and t+2 valuation months")
    if calendar and calendar.get("status") == "VERIFIED_OFFICIAL_SESSIONS":
        blockers = external_input_blockers(calendar, None)
        require("CALENDAR_SOURCE_COVERAGE_REQUIRED" not in blockers,
                "CALENDAR_SOURCE_COVERAGE_REQUIRED", "Official calendar sources/sessions required")
        sessions = {row["session_month"]: stamp(row["open_at"]) for row in calendar["sessions"]}
        expected = [sessions.get(str(signal+1)), sessions.get(str(signal+2))]
        require(all(value is not None for value in expected), "ASSET_CALENDAR_WINDOW_MISSING",
                "Official calendar must cover both entry and valuation")
        require([value.date() for value in endpoints] == [value.date() for value in expected],
                "ASSET_OFFICIAL_OPEN_DATE_MISMATCH", "Raw path must use the exact official first-open dates")


def prepare(plan_path, source_path, output, *, research_root=ROOT / "research"):
    # Reuse frozen implementation/plan binding and sealed/shadow metadata guard
    # before reading a source manifest or any files it references.
    plan, registered = load_plan(plan_path, research_root)
    require(not Path(output).exists(), "OUTPUT_EXISTS", "Use a new immutable draft path")
    result = draft_status()
    result.update(plan_sha256=registered["plan_sha256"], component_errors=[],
                  factor_count=len(plan["factor_bindings"]), source_files=[])
    if source_path is None:
        result["component_errors"] = [dict(component=key, code="SOURCE_REQUIRED")
                                      for key in ["pit_scores", "asset_paths"]]
        save_new(output, result)
        return result
    source_path = Path(source_path)
    package = json.loads(source_path.read_text(encoding="utf-8"))
    require(package.get("schema_version") == "monthly-preparation-source-v1",
            "SOURCE_SCHEMA", "Unsupported source manifest")
    require(package.get("data_kind") in {"HISTORICAL_MARKET", "SYNTHETIC_TEST"},
            "SOURCE_SCHEMA", "Separate synthetic fixtures from market inputs")
    require(bool(package.get("source_files")), "SOURCE_HASH_REQUIRED", "Source files are mandatory")
    for item in package["source_files"]:
        path = Path(item["path"])
        if not path.is_absolute():
            path = source_path.parent / path
        require(hashlib.sha256(path.read_bytes()).hexdigest() == item.get("sha256"),
                "SOURCE_HASH_MISMATCH", str(item["path"]))
    result.update(data_kind=package["data_kind"], source_files=package["source_files"],
                  source_manifest_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest())
    expected = set(map(str, pd.period_range(plan["bounds"]["decision_start"],
                                           plan["bounds"]["decision_end"], freq="M")))
    for row in package.get("universe", []):
        require(row["signal_month"] in expected, "OUTSIDE_PLAN", "Universe signal month")
    for row in package.get("score_candidates", []):
        date = pd.Timestamp(row["as_of_date"]).tz_localize("Asia/Seoul")
        require(stamp(plan["bounds"]["input_start"]) <= date <= stamp(plan["bounds"]["input_end"]),
                "OUTSIDE_PLAN", "Score date")
    for source in package.get("availability_sources", {}).values():
        if source.get("available_at"):
            require(stamp(source["available_at"]) <= stamp(plan["bounds"]["allowed_data_time"]),
                    "OUTSIDE_PLAN", "Source availability after allowed data boundary")
    try:
        result["pit_components"] = prepare_pit_scores(package.get("score_candidates", []),
            package.get("universe", []), package.get("availability_sources", {}), plan["factor_bindings"])
    except PreparationBlocked as e:
        result["component_errors"].append(dict(component="pit_scores", code=e.code, detail=str(e)))
    result["asset_components"] = []
    for path in package.get("asset_paths", []):
        require(path["signal_month"] in expected, "OUTSIDE_PLAN", "Asset signal month")
        _require_signal_window(path, package.get("calendar"))
        dates = path["coverage"].get("session_dates", [])
        require(bool(dates), "SESSION_COVERAGE_REQUIRED", "Asset path needs dates")
        require(stamp(plan["bounds"]["trade_start"]) <= pd.Timestamp(dates[0]).tz_localize("Asia/Seoul")
                and pd.Timestamp(dates[-1]).tz_localize("Asia/Seoul") <= stamp(plan["bounds"]["return_support_end"]),
                "OUTSIDE_PLAN", "Asset return path")
        key = {"signal_month": path["signal_month"], "asset_id": path["coverage"]["asset_id"]}
        try:
            result["asset_components"].append({**key, **compute_open_window(
                path["prices"], path["events"], path["coverage"])})
        except PreparationBlocked as e:
            result["component_errors"].append(dict(component="asset_path", **key, code=e.code, detail=str(e)))
    if not package.get("asset_paths"):
        result["component_errors"].append(dict(component="asset_paths", code="SOURCE_REQUIRED"))
    try:
        result.update(draft_status(package.get("calendar"), package.get("market")))
    except PreparationBlocked as e:
        result["component_errors"].append(dict(component="external_inputs", code=e.code, detail=str(e)))
    result["observed_signal_months"] = sorted({r["signal_month"] for r in package.get("universe", [])})
    result["missing_signal_months"] = sorted(expected - set(result["observed_signal_months"]))
    # This schema cannot be accepted by run_monthly_comparison.load_inputs.
    # A later source reconciliation/bundle review is intentionally required.
    save_new(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.plan, args.sources, args.output)
    print(json.dumps({k: result[k] for k in ["status", "execution_certified", "external_blockers", "component_errors"]}, ensure_ascii=False))
    return 2  # Draft preparation is never an execution-ready success.


if __name__ == "__main__":
    raise SystemExit(main())
