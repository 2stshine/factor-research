"""Create an unapproved input-only shadow from existing local KRX files.

No network, factor returns, campaigns, database access, or registry edits.
The local partition union is only an assumed calendar, not an official calendar
certificate. Existing artifacts are never overwritten.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from engine.regime_shadow import classify_daily_market
from scripts.build_assumed_market_regime import collect_local, monthly_rows


def _completed_month(contract_path: Path | None, *, market: str, daily: list[dict],
                     calendar_dates: list[str], conservative_month: str, as_of: str):
    """Optionally establish one final month against a bound expected-session list.

    This is a caller-supplied, source-backed calendar assertion for an experimental
    diagnostic. It neither certifies historical calendars nor changes PIT flags.
    A source month cannot establish its own expected sessions from its price rows.
    """
    if contract_path is None:
        return conservative_month, None
    body = contract_path.read_bytes()
    contract = json.loads(body)
    if contract.get("schema_version") != "regime-shadow-month-completion-v1":
        raise ValueError("Unsupported month-completion contract")
    if sorted(contract.get("market_ids", [])) != ["KOSDAQ", "KOSPI"] or market not in contract["market_ids"]:
        raise ValueError("Completion contract must bind both requested markets")
    month = pd.Period(contract.get("month"), freq="M")
    if str(month) != contract.get("month") or month != pd.Period(conservative_month, freq="M") + 1:
        raise ValueError("Completion contract may establish only the next excluded month")
    cutoff = pd.Timestamp(as_of)
    if month.end_time.normalize() > cutoff or contract.get("complete_through") != str(month.end_time.date()):
        raise ValueError("Completion contract cannot establish a partial or future month")
    evidence_name = contract.get("calendar_evidence_file")
    evidence_sha = contract.get("calendar_evidence_sha256", "")
    if not isinstance(evidence_name, str) or not re.fullmatch(r"[a-f0-9]{64}", evidence_sha):
        raise ValueError("Bound calendar evidence is required")
    evidence_path = (contract_path.parent / evidence_name).resolve()
    if not evidence_path.is_relative_to(contract_path.parent.resolve()):
        raise ValueError("Calendar evidence must be inside the contract directory")
    evidence_body = evidence_path.read_bytes()
    if hashlib.sha256(evidence_body).hexdigest() != evidence_sha:
        raise ValueError("Calendar evidence hash mismatch")
    evidence = json.loads(evidence_body)
    if (evidence.get("schema_version") != "versioned-expected-market-sessions-v1"
            or evidence.get("month") != str(month)
            or evidence.get("calendar_name") != "XKRX"
            or evidence.get("source_kind") != "VERSIONED_CALENDAR_LIBRARY"
            or not evidence.get("package_version")
            or not re.fullmatch(r"[a-f0-9]{64}", evidence.get("calendar_implementation_sha256", ""))):
        raise ValueError("Independent versioned calendar source metadata required")
    expected = evidence.get("expected_sessions")
    if not isinstance(expected, list) or not expected or expected != sorted(set(expected)):
        raise ValueError("Expected sessions must be nonempty, sorted and unique")
    for day in expected:
        stamp = pd.Timestamp(day)
        if (stamp.tzinfo is not None or str(stamp.date()) != day
                or stamp.to_period("M") != month or stamp.dayofweek >= 5):
            raise ValueError("Invalid expected session date")
    observed = sorted(row["trade_date"] for row in daily if row["trade_date"][:7] == str(month))
    local = sorted(day for day in calendar_dates if day[:7] == str(month))
    if observed != expected or local != expected:
        raise ValueError("Observed market and local calendar must exactly match expected sessions")
    return str(month), {
        "contract_file": str(contract_path.resolve()),
        "contract_sha256": hashlib.sha256(body).hexdigest(),
        "calendar_evidence_file": str(evidence_path),
        "calendar_evidence_sha256": evidence_sha,
        "complete_through": contract["complete_through"],
        "expected_sessions": expected,
        "source_kind": evidence["source_kind"],
        "package_version": evidence["package_version"],
        "calendar_verified": False,
        "historical_calendar_before_month_recertified": False,
        "historical_known_at_verified": False,
    }


def build(*, data_dir: Path, output: Path, as_of: str,
          completion_contract: Path | None = None) -> dict:
    if output.exists():
        raise FileExistsError("Refusing to overwrite existing shadow artifact")
    markets = {}
    for market in ("KOSPI", "KOSDAQ"):
        daily, files, calendar = collect_local(data_dir, market, as_of)
        monthly, completeness = monthly_rows(daily, calendar["dates"], as_of=as_of)
        complete_month, completion = _completed_month(
            completion_contract, market=market, daily=daily,
            calendar_dates=calendar["dates"],
            conservative_month=completeness["last_complete_month"], as_of=as_of)
        complete_through = str(pd.Period(complete_month, freq="M").end_time.date())
        # An explicit modeled clock, not a fabricated observed receipt.
        observations = pd.DataFrame([{
            "trade_date": row["trade_date"], "close": row["close"],
            "known_at": row["trade_date"] + "T23:59:59+09:00",
        } for row in daily if row["trade_date"][:7] <= complete_month])
        result = classify_daily_market(observations,
            calendar_dates=calendar["dates"], calendar_complete_through=complete_through,
            as_of=as_of, market_id=market,
            source_id=f"local-krx-{market.lower()}-daily-unverified",
            start_month=monthly[0]["month"], calendar_verified=False,
            known_at_semantics="ASSUMED_OBSERVATION_DAY_END_KST_NOT_RECEIPT")
        result["source_provenance"] = {
            "data_dir": str(data_dir.resolve()), "raw_daily_rows": len(daily),
            "last_raw_trade_date": completeness["last_raw_trade_date"],
            "last_complete_input_month": complete_month,
            "raw_files": files, "local_calendar": calendar,
            "completeness": completeness,
            "explicit_month_completion": completion,
            "historical_receipts_available": False,
            "daily_available_at_assumed": True,
            "parent_assumption_policy_does_not_approve_this_new_method": True,
        }
        result["summary"] = {
            "months": len(result["rows"]),
            "status_counts": dict(Counter(row["status"] for row in result["rows"])),
            "regime_counts": dict(Counter(row["regime"] for row in result["rows"])),
            "first_ready_month": next((row["month"] for row in result["rows"]
                                       if row["status"] == "READY_SHADOW"), None),
            "latest_requested_month": result["rows"][-1]["month"],
            "latest_status": result["rows"][-1]["status"],
            "latest_reason": result["rows"][-1]["reason"],
            "input_stale_for_latest_month": complete_month < result["rows"][-1]["month"],
        }
        markets[market] = result
    payload = {
        "schema_version": "local-krx-regime-shadow-bundle-v1",
        "created_at": datetime.now(timezone.utc).isoformat(), "as_of": as_of,
        "status": "EXPERIMENTAL_SHADOW_NOT_APPROVED", "pit_status": "PIT_UNKNOWN",
        "factor_returns_accessed": False, "active_registry_changed": False,
        "db_accessed": False, "network_accessed": False,
        "compiler_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "engine_sha256": hashlib.sha256(Path(__file__).resolve().parents[1].joinpath(
            "engine/regime_shadow.py").read_bytes()).hexdigest(),
        "markets": markets,
    }
    body = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as target:
        target.write(body)
    return {market: result["summary"] for market, result in markets.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--completion-contract", type=Path,
                        help="Optional expected-calendar contract for the final excluded month")
    args = parser.parse_args()
    print(json.dumps(build(data_dir=args.data_dir, output=args.output, as_of=args.as_of,
                           completion_contract=args.completion_contract),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
