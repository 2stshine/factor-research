"""Fixed causal diagnostic rules over explicitly assumption-based observations.

This module does not certify historical vintages, access databases, inspect
factor performance, or turn assumptions into verified publication timestamps.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from statistics import median
from zoneinfo import ZoneInfo

import pandas as pd

KST = ZoneInfo("Asia/Seoul")
NEW_YORK = ZoneInfo("America/New_York")
RULE_VERSION = "assumed-fmp-monthly-diagnostics-v1"
MAX_AGE_DAYS = {"macro": 60, "cot": 14, "fx": 7, "etf": 7, "index": 7}
MIN_PRIOR_MONTHS = 24
# Already identified outage interval. Exclusion is deliberately broader than a
# reconstructed publication calendar; no release dates are invented here.
COT_UNRESOLVED_POSITION_RANGES = (("2018-12-24", "2019-03-05"),)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def normalize_observation(series_id, kind, row, *, cot_release_dates):
    """Retain receipt and raw lineage; add a separate assumed public clock."""
    payload = row["payload"]
    provider_date = payload["date"]
    day = provider_date[:10]
    receipt = row.get("audit_received_at", row.get("system_known_at", row.get("observed_at")))
    if not receipt or datetime.fromisoformat(receipt).tzinfo is None:
        raise ValueError("Actual timezone-aware receipt is required")
    record = {"series_id": series_id, "kind": kind, "provider_date": provider_date,
              "system_known_at": receipt, "raw_uri": row["audit_source_uri"],
              "source_row_index": row["source_row_index"], "payload_sha256": sha(payload),
              "pit_status": "PIT_ASSUMED", "available_at_assumed": None,
              "available_at_verified": None, "value": None, "excluded_reason": None}
    record["observation_id"] = sha({k: record[k] for k in ("series_id", "raw_uri", "source_row_index", "payload_sha256", "system_known_at")})
    if kind == "macro":
        dt = datetime.fromisoformat(provider_date)
        if dt.tzinfo is not None:
            raise ValueError("Expected provider UTC-naive economic-calendar timestamp")
        available = dt.replace(tzinfo=timezone.utc).astimezone(KST)
        value = payload.get("actual")
        record.update(value_field="actual", availability_assumption="PROVIDER_EVENT_TIMESTAMP_AS_UTC",
                      provider_unit=payload.get("unit"), provider_currency=payload.get("currency"))
    elif kind in {"fx", "etf", "index"}:
        # Conservative, explicit assumption: provider day D has finished by the
        # following New York calendar midnight. This is not a verified close.
        next_day = datetime.fromisoformat(day) + timedelta(days=1)
        available = next_day.replace(tzinfo=NEW_YORK).astimezone(KST)
        value = payload.get("close")
        record.update(value_field="close", availability_assumption="FOLLOWING_NEW_YORK_MIDNIGHT")
        if finite(value) and value <= 0:
            value = None
            record["excluded_reason"] = "NONPOSITIVE_PRICE"
    elif kind == "cot":
        value = None
        long, short, oi = (payload.get(k) for k in ("noncommPositionsLongAll", "noncommPositionsShortAll", "openInterestAll"))
        if all(finite(v) for v in (long, short, oi)) and min(long, short) >= 0 and oi > 0:
            value = (long - short) / oi
        record.update(value_field="(noncommPositionsLongAll-noncommPositionsShortAll)/openInterestAll",
                      contract_code=payload.get("cftcContractMarketCode"))
        if day in cot_release_dates:
            release = datetime.fromisoformat(cot_release_dates[day])
            record["availability_assumption"] = "PRESERVED_OFFICIAL_EXCEPTION_DATE_PLUS_ASSUMED_1530_NEW_YORK"
        elif any(start <= day <= end for start, end in COT_UNRESOLVED_POSITION_RANGES):
            record["excluded_reason"] = "KNOWN_COT_OUTAGE_RELEASE_DATE_UNRESOLVED"
            return record
        elif "2023-01-31" <= day <= "2023-03-21":
            record["excluded_reason"] = "KNOWN_ION_OUTAGE_RELEASE_DATE_UNRESOLVED"
            return record
        else:
            reference = datetime.fromisoformat(day)
            if reference.weekday() != 1:
                record["excluded_reason"] = "NON_TUESDAY_COT_RELEASE_DATE_UNRESOLVED"
                return record
            release = reference + timedelta(days=3)
            record["availability_assumption"] = "REGULAR_TUESDAY_POSITION_PLUS_3_DAYS_1530_NEW_YORK"
        available = release.replace(hour=15, minute=30, tzinfo=NEW_YORK).astimezone(KST)
        # For known position corrections in these contracts, do not expose the
        # retained current value before the dated correction notice.
        if day == "2019-03-26" and series_id in {"ZN", "VX", "GC"}:
            available = datetime(2019, 4, 3, 23, 59, 59, tzinfo=NEW_YORK).astimezone(KST)
            record["availability_assumption"] = "KNOWN_CORRECTION_DAY_END_NEW_YORK"
    else:
        raise ValueError(f"Unsupported assumed source kind: {kind}")
    record["available_at_assumed"] = available.isoformat()
    if finite(value):
        record["value"] = float(value)
    elif record["excluded_reason"] is None:
        record["excluded_reason"] = "MISSING_OR_NONFINITE_VALUE"
    return record


def completed_end_month(as_of):
    stamp = pd.Timestamp(as_of)
    if stamp.tzinfo is not None or stamp != stamp.normalize():
        raise ValueError("as_of must be a timezone-naive date")
    month = stamp.to_period("M")
    if stamp.date() < month.end_time.date():
        month -= 1
    return month


def classification_rules(kind):
    momentum = kind in {"fx", "etf"}
    return {"version": RULE_VERSION, "method": "TRAILING_3_MONTH_CHANGE_SIGN" if momentum else "EXPANDING_PRIOR_MONTH_MEDIAN",
            "min_prior_months": None if momentum else MIN_PRIOR_MONTHS,
            "require_four_consecutive_month_end_values": momentum,
            "threshold_excludes_current_month": True, "max_age_days": MAX_AGE_DAYS[kind],
            "staleness_clock": "position_date_and_assumed_publication" if kind == "cot" else "assumed_publication",
            "ties": "UP if change >= 0" if momentum else "LOW if level <= prior median",
            "classification_input": "monthly latest available non-conflicting actual/close/net-share observation",
            "purpose": "DIAGNOSTIC_ONLY", "economic_good_bad_interpretation": False,
            "pit_status": "PIT_ASSUMED", "month_alignment": "KST month t state describes t+1 outcomes"}


def monthly_states(records, kind, *, start_month, as_of):
    """Latest *available* snapshot; never backdate a future observation."""
    groups = defaultdict(list)
    for record in records:
        if record["available_at_assumed"] is not None:
            groups[record["available_at_assumed"]].append(record)
    points = sorted((datetime.fromisoformat(at), rows) for at, rows in groups.items())
    end = completed_end_month(as_of)
    start = pd.Period(start_month, freq="M")
    if start > end:
        raise ValueError("No completed months in requested scope")
    result, values, prior = [], {}, []
    cursor, latest = 0, None
    for month in pd.period_range(start, end, freq="M"):
        cutoff = month.end_time.floor("s").to_pydatetime().replace(tzinfo=KST)
        while cursor < len(points) and points[cursor][0] <= cutoff:
            latest = points[cursor]
            cursor += 1
        row = {"month": str(month), "known_at": cutoff.replace(tzinfo=None).isoformat(),
               "effective_month": str(month + 1), "state": "UNKNOWN", "value": None,
               "reason": "NO_AVAILABLE_OBSERVATION", "pit_status": "PIT_ASSUMED",
               "selected_observation_ids": [], "selected_available_at_assumed": None,
               "threshold": None, "prior_valid_months": len(prior)}
        value = None
        if latest:
            at, candidates = latest
            valid_values = {r["value"] for r in candidates if r["value"] is not None}
            # A null sibling is retained in lineage but cannot erase an otherwise
            # unambiguous numeric observation at the exact same event time.
            age = (cutoff - at).total_seconds() / 86400
            reference_age = max((cutoff.date() - datetime.fromisoformat(r["provider_date"][:10]).date()).days for r in candidates)
            row.update(selected_observation_ids=sorted(r["observation_id"] for r in candidates),
                       selected_available_at_assumed=at.isoformat(), age_days=age,
                       latest_provider_dates=sorted({r["provider_date"] for r in candidates}))
            if len(valid_values) > 1:
                row["reason"] = "CONFLICTING_SAME_TIME_VALUES"
            elif not valid_values:
                row["reason"] = "LATEST_OBSERVATION_HAS_NO_VALID_VALUE"
            elif age > MAX_AGE_DAYS[kind] or (kind == "cot" and reference_age > MAX_AGE_DAYS[kind]):
                row["reason"] = "STALE_OBSERVATION"
            else:
                value = next(iter(valid_values))
                row["value"] = value
                if kind in {"etf", "fx"}:
                    window = [values.get(month - i) for i in (3, 2, 1)] + [value]
                    if any(v is None or v <= 0 for v in window):
                        row["reason"] = "INSUFFICIENT_CONTIGUOUS_3M_HISTORY"
                    else:
                        change = value / window[0] - 1
                        row.update(state="UP" if change >= 0 else "DOWN", reason="CLASSIFIED_UNDER_ASSUMPTIONS", change_3m=change)
                elif len(prior) < MIN_PRIOR_MONTHS:
                    row["reason"] = "INSUFFICIENT_24_PRIOR_VALID_MONTHS"
                else:
                    threshold = median(prior)
                    row.update(state="HIGH" if value > threshold else "LOW", threshold=threshold,
                               reason="CLASSIFIED_UNDER_ASSUMPTIONS")
        values[month] = value
        if value is not None:
            prior.append(value)
        result.append(row)
    return result


def source_context(series_id, kind, normalized, rows, *, normalized_sha256, lineage_sha256):
    rules = classification_rules(kind)
    return {"context_id": "FMP_ASSUMED_" + series_id.replace("^", "").replace("-", "_").replace(".", "_"),
            "source_id": f"fmp-assumed-{series_id}-{normalized_sha256[:16]}-{RULE_VERSION}",
            "kind": "macro_state", "macro_type": "assumed_" + kind,
            "frequency": "MONTH_END", "storage_layer": "DERIVED_RESEARCH_CONTEXT",
            "pit_status": "PIT_ASSUMED", "known_at_semantics": "ASSUMED_HISTORICAL_AVAILABILITY",
            "scope": {"start_month": rows[0]["month"], "end_month": rows[-1]["month"],
                      "intraday_allowed": False, "factor_feature_allowed": False},
            "states": ["UP", "DOWN"] if kind in {"fx", "etf"} else ["HIGH", "LOW"],
            "classification_rules": rules,
            "assumptions": ["Current preserved FMP values are used as a historical-vintage approximation; initial values and later revisions are not reconstructed.",
                "Assumed public availability is distinct from the preserved actual 2026 receipt timestamp.",
                "FMP macro provider timestamps are treated as UTC; US/FX daily bars are available at following New York midnight.",
                "COT regular Tuesday positions are assumed available Friday 15:30 New York; recorded exceptions override, unresolved known outages are excluded.",
                "Historical market price adjustments/corrections remain accepted uncertainties; no total-return interpretation.",
                "Fixed diagnostic classification only; HIGH/UP does not assert a good economy or positive future returns."],
            "normalized_observation_count": len(normalized), "normalized_sha256": normalized_sha256,
            "lineage_sha256": lineage_sha256, "rows": rows}
