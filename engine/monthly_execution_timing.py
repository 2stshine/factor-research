"""Validate a proposed monthly execution timeline, without orders or returns.

Supplied attestations are not created by this module. Passing temporal checks
alone never upgrades diagnostic input permission or certifies actual fills.
"""
from __future__ import annotations

import math
import pandas as pd

VERSION = "month-end-next-session-timing-v1"
CONTRACT = {"version": VERSION, "decision_timezone": "Asia/Seoul",
            "decision_cutoff": "calendar month end 23:59:59",
            "execution_rule": "first supplied verified session open strictly after decision",
            "same_close_execution_allowed": False, "intramonth_reclassification": False,
            "existing_return_label": "UNCHANGED_DIAGNOSTIC_NOT_EXECUTABLE_PNL",
            "execution_certified": False}


def _stamp(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required; no guessed timezone")
    return stamp.tz_convert("Asia/Seoul")


def check_timing(*, month, decision_at, input_available_at, session_opens,
                 execution_at, price, attestations=None):
    """Check exact caller-supplied times; no weekday or 09:00 assumptions."""
    decision, execution = _stamp(decision_at), _stamp(execution_at)
    period = pd.Period(month, freq="M")
    cutoff = period.end_time.floor("s").tz_localize("Asia/Seoul")
    sessions = sorted(_stamp(t) for t in session_opens)
    if len(set(sessions)) != len(sessions):
        raise ValueError("Duplicate session open")
    clocks = [_stamp(t) for t in input_available_at]
    following = next((s for s in sessions if s > decision), None)
    errors = []
    if decision != cutoff:
        errors.append("DECISION_NOT_DECLARED_MONTH_END_CUTOFF")
    if not clocks:
        errors.append("NO_INPUT_AVAILABILITY_EVIDENCE")
    if any(t > decision for t in clocks):
        errors.append("INPUT_AVAILABLE_AFTER_DECISION")
    if execution <= decision:
        errors.append("EXECUTION_NOT_AFTER_DECISION")
    if following is None or execution != following:
        errors.append("NOT_FIRST_SUPPLIED_NEXT_SESSION_OPEN")
    if execution.tz_localize(None).to_period("M") != period + 1:
        errors.append("EXECUTION_NOT_NEXT_MONTH")
    if not isinstance(price, (int, float)) or isinstance(price, bool) or not math.isfinite(price) or price <= 0:
        errors.append("INVALID_EXECUTION_PRICE")
    required = ("calendar_verified", "tradeable_asset_price_verified", "execution_scope_approved",
                "holding_and_cost_contract_verified")
    missing = [k for k in required if (attestations or {}).get(k) is not True]
    return {"version": VERSION, "timing_passed": not errors, "violations": errors,
            "missing_attestations": missing, "provided_contract_passed": not errors and not missing,
            "actual_fill_verified": False, "orders_submitted": False,
            "status": "TIMING_VIOLATION" if errors else "INCOMPLETE_EXECUTION_CONTRACT" if missing else "PROVIDED_CONTRACT_CHECK_ONLY"}
