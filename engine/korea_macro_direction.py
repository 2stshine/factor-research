"""Causal production/inflation directions from frozen monthly as-of snapshots.

No factor outcomes, estimated reference periods, first-vintage certification,
or re-estimation of earlier decision snapshots. Parent HIGH/LOW classifications
are deliberately NOT inputs to this independent diagnostic.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math

import pandas as pd

from engine.assumed_macro_regimes import completed_end_month

VERSION = "kr-production-inflation-direction-v1"
CONTEXT_ID = "KR_PRODUCTION_INFLATION_DIRECTION"
PARENTS = {"production": "FMP_ASSUMED_KR_INDUSTRIAL_PRODUCTION_YOY",
           "inflation": "FMP_ASSUMED_KR_CPI_YOY"}
STATES = ["PRODUCTION_UP_INFLATION_DOWN", "PRODUCTION_UP_INFLATION_UP",
          "PRODUCTION_DOWN_INFLATION_UP", "PRODUCTION_DOWN_INFLATION_DOWN", "NEUTRAL"]
RULES = {"version": VERSION, "purpose": "DIAGNOSTIC_ONLY",
         "formula": "mean(latest 3 decision-month snapshots) - mean(previous 3 snapshots)",
         "window_months": 6, "require_contiguous_snapshots": True, "max_age_days": 60,
         "ties": "either exact zero => NEUTRAL", "missing": "UNKNOWN; no imputation",
         "month_alignment": "KST month t state describes t+1 outcomes",
         "interpretation": "production YoY momentum proxy and CPI YoY direction, not GDP or recession",
         "parent_level_states_used": False, "threshold_optimized_on_returns": False}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _snapshot(row, month):
    if row is None:
        return {"month": str(month), "valid": False, "reason": "MISSING_DECISION_MONTH"}
    cutoff = month.end_time.floor("s").tz_localize("Asia/Seoul")
    known = pd.Timestamp(row.get("known_at"))
    available = pd.Timestamp(row.get("selected_available_at_assumed"))
    ids = row.get("selected_observation_ids")
    valid_clock = (not pd.isna(known) and known.tzinfo is None
                   and known.to_period("M") == month and known <= month.end_time)
    valid_available = (not pd.isna(available) and available.tzinfo is not None
                       and available <= cutoff)
    age = (cutoff - available).total_seconds() / 86400 if valid_available else None
    valid = (valid_clock and valid_available and age <= 60 and _number(row.get("value"))
             and isinstance(ids, list) and bool(ids) and all(isinstance(x, str) and x for x in ids)
             and len(ids) == len(set(ids)))
    return {"month": str(month), "valid": bool(valid),
            "reason": "AVAILABLE_SNAPSHOT" if valid else "MISSING_STALE_OR_UNAVAILABLE_SNAPSHOT",
            "value": row.get("value") if valid else None,
            "snapshot_known_at_kst": row.get("known_at"),
            "available_at_assumed": row.get("selected_available_at_assumed"),
            "observation_ids": deepcopy(ids or []), "age_days": age,
            "provider_event_dates": deepcopy(row.get("latest_provider_dates", [])),
            "statistical_reference_period": None,
            "reference_period_status": "NOT_PROVIDED_BY_PARENT; event date is not reference period"}


def classify(production, inflation, *, start_month, as_of):
    """Accept authenticated parent rows; independently enforce causal row clocks."""
    maps = {}
    for name, rows in (("production", production), ("inflation", inflation)):
        index = {pd.Period(r["month"], freq="M"): r for r in rows}
        if len(index) != len(rows):
            raise ValueError("Duplicate decision month; revisions must not replace snapshots")
        maps[name] = index
    start, end = pd.Period(start_month, freq="M"), completed_end_month(as_of)
    if start > end:
        raise ValueError("No completed month")
    output = []
    for month in pd.period_range(start, end, freq="M"):
        row = {"month": str(month), "effective_month": str(month + 1),
               "known_at": month.end_time.floor("s").isoformat(),
               "state": "UNKNOWN", "reason": "INSUFFICIENT_SIX_CONTIGUOUS_SNAPSHOTS",
               "pit_status": "PIT_ASSUMED", "directions": {}, "inputs": {}}
        for name, index in maps.items():
            snapshots = [_snapshot(index.get(month - i) if month - i >= start else None, month - i)
                         for i in range(5, -1, -1)]
            # Reuse of an unchanged release is explicit, not fabricated new data.
            identities = [tuple(s.get("observation_ids", [])) for s in snapshots if s["valid"]]
            repeated = sum(count - 1 for count in Counter(identities).values())
            row["inputs"][name] = {"snapshots": snapshots, "reused_snapshot_count": repeated}
            row["directions"][name] = (math.fsum(s["value"] for s in snapshots[3:]) / 3
                                        - math.fsum(s["value"] for s in snapshots[:3]) / 3
                                        if all(s["valid"] for s in snapshots) else None)
        g, i = row["directions"]["production"], row["directions"]["inflation"]
        if g is not None and i is not None:
            state = ("NEUTRAL" if g == 0 or i == 0 else
                     f"PRODUCTION_{'UP' if g > 0 else 'DOWN'}_INFLATION_{'UP' if i > 0 else 'DOWN'}")
            row.update(state=state, reason="CLASSIFIED_UNDER_ASSUMPTIONS")
        output.append(row)
    return output
