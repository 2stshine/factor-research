"""Experimental, input-only market diagnostics. Never an active regime policy.

The twelve-month reference window is a predeclared engineering prototype, not
an optimized or approved replacement for ``engine.regimes``. No factor returns,
campaigns, promotion gates, or database interfaces are used here.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence

import numpy as np
import pandas as pd


VERSION = "experimental-market-shadow-rv63-reference12-v1"
RULES = {
    "version": VERSION,
    "status": "EXPERIMENTAL_SHADOW_NOT_APPROVED",
    "trend_months": 10,
    "risk_return_sessions": 63,
    "short_risk_return_sessions": 21,
    "return_type": "DAILY_LOG_RETURN",
    "standard_deviation_ddof": 1,
    "annualization": 252,
    "reference_months": 12,
    "reference": "PREVIOUS_12_CONSECUTIVE_MONTH_END_RV63_SNAPSHOTS",
    "reference_excludes_current_month": True,
    "threshold": "MEDIAN",
    "percentile": "MIDRANK_IN_THE_SAME_12_PRIOR_SNAPSHOTS",
    "ties": "close_equal_sma_UP;rv_equal_median_LOW",
    "decision_clock": "KST_CALENDAR_MONTH_END",
    "effective_month": "NEXT_CALENDAR_MONTH",
    "missing": "NO_IMPUTATION;UNKNOWN",
    "purpose": "INPUT_DIAGNOSTICS_ONLY",
    "interpretation": "HIGH/LOW is relative to the past year, not absolute safety or forecast return",
    "selected_using_factor_performance": False,
    "selected_for_balanced_state_counts": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(",", ":")).encode()).hexdigest()


def _day(value: str) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is not None or stamp != stamp.normalize():
        raise ValueError("Calendar dates must be timezone-naive complete dates")
    return stamp


def _finite(value: object) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def classify_daily_market(
    observations: pd.DataFrame,
    *,
    calendar_dates: Sequence[str],
    calendar_complete_through: str,
    as_of: str,
    market_id: str,
    source_id: str,
    start_month: str,
    calendar_verified: bool = False,
    known_at_semantics: str = "UNVERIFIED",
) -> dict:
    """Calculate month-end snapshots using only that decision's available rows.

    ``calendar_complete_through`` is the caller's explicit coverage assertion,
    not something inferred from the last price. ``calendar_verified`` records
    its provenance, never grants approval. All outputs remain PIT_UNKNOWN and
    NOT_APPROVED. A price requires an aware ``known_at`` not earlier than its
    KST observation date; the exact session/publication time is not certified.
    Late rows may enter later decisions but never repair previous snapshots.
    A missing daily session breaks daily windows rather than creating a
    multi-day return that is mislabeled daily. Extra input fields are ignored.
    """
    if not isinstance(market_id, str) or not market_id.strip():
        raise ValueError("market_id required")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id required")
    if not isinstance(known_at_semantics, str) or not known_at_semantics.strip():
        raise ValueError("known_at_semantics required")
    if not isinstance(calendar_verified, bool):
        raise ValueError("calendar_verified must be Boolean")
    cutoff = _day(as_of)
    coverage_day = _day(calendar_complete_through)
    last_month = cutoff.to_period("M")
    if cutoff.date() < last_month.end_time.date():
        last_month -= 1
    first_month = pd.Period(start_month, freq="M")
    if str(first_month) != start_month:
        raise ValueError("start_month must be YYYY-MM")
    if first_month > last_month:
        raise ValueError("No completed month in scope")
    # Future calendar and price rows do not contribute to snapshots/hashes.
    calendar = [_day(day) for day in calendar_dates]
    calendar = [day for day in calendar if day <= cutoff]
    if len(calendar) != len(set(calendar)):
        raise ValueError("Duplicate calendar session")
    calendar = sorted(calendar)
    expected_set = set(calendar)
    required = {"trade_date", "close", "known_at"}
    if not required.issubset(observations.columns):
        raise ValueError(f"Required input columns: {sorted(required)}")
    points = {}
    for raw in observations[list(sorted(required))].to_dict("records"):
        day = _day(raw["trade_date"])
        if day > cutoff:
            continue
        known = pd.Timestamp(raw["known_at"])
        if pd.isna(known) or known.tzinfo is None:
            raise ValueError("known_at must have an explicit timezone")
        known = known.tz_convert("Asia/Seoul")
        if known.date() < day.date():
            raise ValueError("known_at precedes the observation date")
        if known > (cutoff + pd.Timedelta(days=1)).tz_localize("Asia/Seoul") - pd.Timedelta(nanoseconds=1):
            continue
        if day not in expected_set:
            raise ValueError("Price observation is absent from supplied calendar")
        if day in points:
            raise ValueError("Duplicate observation; revisions require explicit resolution")
        try:
            close = float(raw["close"])
        except (ValueError, TypeError) as exc:
            raise ValueError("close must be finite and positive") from exc
        if not math.isfinite(close) or close <= 0:
            raise ValueError("close must be finite and positive")
        points[day] = (close, known)

    rows, month_closes, monthly_risks = [], {}, {}
    for month in pd.period_range(first_month, last_month, freq="M"):
        decision = month.end_time.tz_localize("Asia/Seoul")
        sessions = [day for day in calendar if day.to_period("M") <= month]
        current_sessions = [day for day in sessions if day.to_period("M") == month]
        covered = month.end_time.normalize() <= coverage_day
        available = {day: value for day, (value, known) in points.items()
                     if day.to_period("M") <= month and known <= decision}
        missing = [day for day in current_sessions if day not in available]
        month_complete = covered and bool(current_sessions) and not missing
        close = available[current_sessions[-1]] if month_complete else None
        month_closes[month] = close

        def risk(n: int) -> float | None:
            window = sessions[-(n + 1):]
            if not month_complete or len(window) != n + 1 or any(day not in available for day in window):
                return None
            values = np.array([available[day] for day in window], dtype=float)
            return float(np.diff(np.log(values)).std(ddof=1) * np.sqrt(RULES["annualization"]))

        rv63, rv21 = risk(63), risk(21)
        monthly_risks[month] = rv63
        trend_window = [month_closes.get(month - i) for i in range(9, -1, -1)]
        sma = math.fsum(trend_window) / 10 if all(_finite(v) for v in trend_window) else None
        prior_months = [month - i for i in range(12, 0, -1)]
        prior = [monthly_risks.get(m) for m in prior_months]
        has_reference = all(_finite(value) for value in prior)
        threshold = float(np.median(prior)) if has_reference else None
        percentile = (100 * (sum(value < rv63 for value in prior)
                             + .5 * sum(value == rv63 for value in prior)) / 12
                      if has_reference and rv63 is not None else None)
        trend = "UNKNOWN" if sma is None else ("UP" if close >= sma else "DOWN")
        relative_risk = "UNKNOWN" if rv63 is None or threshold is None else (
            "HIGH" if rv63 > threshold else "LOW")
        reasons = []
        if not covered:
            reasons.append("CALENDAR_COVERAGE_NOT_ESTABLISHED")
        if not current_sessions:
            reasons.append("NO_CALENDAR_SESSIONS")
        if missing:
            reasons.append("MISSING_OR_LATE_DAILY_OBSERVATION")
        if sma is None:
            reasons.append("INSUFFICIENT_10_CONTIGUOUS_MONTH_CLOSES")
        if rv63 is None:
            reasons.append("INSUFFICIENT_64_CONTIGUOUS_SESSION_CLOSES")
        if not has_reference:
            reasons.append("INSUFFICIENT_12_CONTIGUOUS_PRIOR_RV63_SNAPSHOTS")
        ready = not reasons
        fingerprint = {
            "market_id": market_id, "source_id": source_id,
            "calendar_sessions": [str(day.date()) for day in sessions],
            "calendar_covered": covered,
            "available_observations": [
                [str(day.date()), points[day][0], points[day][1].isoformat()]
                for day in sorted(available)],
        }
        rows.append({
            "month": str(month), "effective_month": str(month + 1),
            "decision_at": decision.isoformat(), "market_id": market_id,
            "source_id": source_id, "status": "READY_SHADOW" if ready else "UNKNOWN",
            "approval_status": "NOT_APPROVED", "pit_status": "PIT_UNKNOWN",
            "regime": f"{trend}_{relative_risk}" if ready else "UNKNOWN",
            "trend": trend, "relative_risk": relative_risk,
            "close": close, "sma_10m": sma,
            "trend_distance": close / sma - 1 if sma is not None else None,
            "rv63_annualized": rv63, "rv21_annualized": rv21,
            "risk_change_21_over_63": rv21 / rv63 - 1 if rv63 and rv21 is not None else None,
            "risk_change_status": "AVAILABLE" if rv63 and rv21 is not None else "UNDEFINED_OR_MISSING",
            "prior_12m_rv63_median": threshold, "rv63_prior_12m_percentile": percentile,
            "prior_reference_months": [str(m) for m in prior_months],
            "prior_reference_valid_months": sum(_finite(value) for value in prior),
            "reference_values": prior,
            "expected_sessions_this_month": len(current_sessions),
            "missing_or_late_sessions": [str(day.date()) for day in missing],
            "calendar_verified": calendar_verified, "known_at_semantics": known_at_semantics,
            "reason": ";".join(reasons), "input_sha256": _digest(fingerprint),
            "rules_version": VERSION, "rules_sha256": _digest(RULES),
        })
    return {
        "schema_version": "market-regime-shadow-v1", "rules": dict(RULES),
        "rules_sha256": _digest(RULES), "as_of": as_of,
        "market_id": market_id, "source_id": source_id,
        "approval_status": "NOT_APPROVED", "pit_status": "PIT_UNKNOWN",
        "calendar_verified": calendar_verified,
        "calendar_complete_through": calendar_complete_through,
        "known_at_semantics": known_at_semantics,
        "factor_returns_accessed": False, "active_registry_changed": False,
        "factor_feature_allowed": False, "trading_allowed": False,
        "limitations": [
            "Experimental method only; not a PIT approval or active regime replacement.",
            "Calendar completeness is a supplied assertion, not certified by this calculation.",
            "HIGH/LOW is relative to twelve prior monthly snapshots, not absolute risk or safety.",
            "A sustained risky environment can become relatively normal; always inspect absolute RV63.",
            "Historical values/publication times may be unverified; do not relabel as PIT_VERIFIED.",
            "No factor returns, balancing objective, or strategy performance selected these parameters.",
        ],
        "rows": rows,
    }
