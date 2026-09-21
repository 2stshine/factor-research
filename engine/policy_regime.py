"""Official dated policy targets reconciled to FMP; no returns or tuning."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import math

import pandas as pd

RULES = {
    "version": "announced-policy-target-direction-3m-v1",
    "definition": "At each completed Korean calendar month end, compare the latest publicly announced policy target with that at t-3 month end.",
    "lookback_months": 3,
    "threshold_percentage_points": 0,
    "states": {"TIGHTENING": "delta > 0", "UNCHANGED": "delta == 0", "EASING": "delta < 0"},
    "timing": "Official dated decision available conservatively by end of its publication day (Asia/Seoul); apply t state only to t+1 outcomes.",
    "carry_policy": "An announced policy target persists until superseded by another official decision; not generic missing-value filling.",
    "purpose": "DIAGNOSTIC_ONLY",
}


def reconcile(decisions, fmp_rows, *, start="2015-01-01", through="2026-08-31"):
    official = {}
    for row in decisions:
        day = row["decision_date"]
        value = row["target_rate_pct"]
        if (day in official or row.get("document_date_verified") is not True
                or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not 0 <= value <= 100):
            raise ValueError("Invalid/duplicate official dated decision")
        official[day] = row
    matched = defaultdict(list)
    for row in fmp_rows:
        payload = row["payload"]
        day = date.fromisoformat(payload["date"][:10])
        if not start <= str(day) <= through:
            raise ValueError("FMP policy observation outside review scope")
        if (payload.get("country") != "KR" or payload.get("unit") != "%"
                or row["series_id"] != "KR_POLICY_RATE"):
            raise ValueError("Wrong FMP policy identity/unit")
        # Match calendar identity first, not by value: a bad value must not pick
        # a different decision. No timezone is inferred from the FMP clock.
        candidates = [str(day + timedelta(days=i)) for i in (-1, 0, 1)
                      if str(day + timedelta(days=i)) in official]
        if len(candidates) != 1:
            raise ValueError("Ambiguous/unmatched FMP decision date")
        key = candidates[0]
        if payload.get("actual") != official[key]["target_rate_pct"]:
            raise ValueError("FMP target conflicts with official dated decision")
        matched[key].append(row)
    expected = {d for d in official if start <= d <= through}
    if set(matched) != expected:
        raise ValueError("Official/FMP policy decision coverage mismatch")
    resolved = []
    for day in sorted(expected):
        row = official[day]
        group = matched[day]
        resolved.append({"publication_date": day, "available_at_upper_bound": day + "T23:59:59+09:00",
            "announced_target_rate_pct": row["target_rate_pct"], "official_url": row["url"],
            "official_sha256": row["pdf_sha256"], "raw_fmp_rows": group,
            "duplicate_excess": len(group) - 1,
            "provider_calendar_dates_corrected": sum(x["payload"]["date"][:10] != day for x in group),
            "system_known_at": max(x["received_at"] for x in group),
            "availability_precision": "day_upper_bound_not_exact_publication_time"})
    return resolved


def monthly_states(decisions, *, start="2015-01", end="2026-08"):
    """Only use a release whose own publication day is on/before the cutoff."""
    rates = sorted(decisions, key=lambda x: x["decision_date"])
    if len({x["decision_date"] for x in rates}) != len(rates):
        raise ValueError("Duplicate policy decision")
    def at(month):
        eligible = [r for r in rates if pd.Timestamp(r["decision_date"]) <= month.end_time]
        if not eligible:
            raise ValueError("Insufficient official policy warm-up")
        return eligible[-1]
    rows = []
    for month in pd.period_range(start, end, freq="M"):
        current, lag = at(month), at(month - RULES["lookback_months"])
        delta = current["target_rate_pct"] - lag["target_rate_pct"]
        rows.append({"month": str(month), "known_at": month.end_time.floor("s").isoformat(),
            "state": "TIGHTENING" if delta > 0 else "EASING" if delta < 0 else "UNCHANGED",
            "announced_target_rate_pct": current["target_rate_pct"], "lag3m_rate_pct": lag["target_rate_pct"],
            "change_3m_percentage_points": delta, "latest_publication_date": current["decision_date"],
            "latest_publication_upper_bound_kst": current["decision_date"] + "T23:59:59+09:00",
            "official_decision_sha256": current["pdf_sha256"], "official_url": current["url"],
            "lag_official_decision_sha256": lag["pdf_sha256"]})
    return rows
