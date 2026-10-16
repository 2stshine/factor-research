"""Conditional official index-component arithmetic; never execution certification.

No collection, credential, DB, or file access. Price-only data, stock close TR,
interpolated openings, and unmarked later dividend vintages are never substitutes.
Official prelaunch backcasts retain their later release date and are not PIT features.
"""
from __future__ import annotations

import math
import re
import pandas as pd
from strategies.monthly_input_preparation import PreparationBlocked, positive, require, stamp

VERSION = "monthly-benchmark-preparation-v1"


def required_opening_months(signal_months):
    months = [pd.Period(x, "M") for x in signal_months]
    require(bool(months) and len(months) == len(set(months)), "SIGNAL_MONTHS_REQUIRED", "Nonempty unique signal months")
    return sorted({str(m + offset) for m in months for offset in (1, 2)})


def _contract(contract):
    require(isinstance(contract, dict), "OFFICIAL_INDEX_CONTRACT_REQUIRED", "No default benchmark assumptions")
    require(contract.get("index_id") == "KRX300_TR" and contract.get("price_index_id") == "KRX300"
            and contract.get("currency") == "KRW" and contract.get("return_type") == "gross_total_return",
            "INDEX_IDENTITY_MISMATCH", "Exact KRX300 gross KRW total-return identity is required")
    require(contract.get("data_kind") in {"SYNTHETIC_TEST", "HISTORICAL_MARKET"},
            "DATA_KIND_REQUIRED", "Synthetic inputs must remain labeled")
    require(contract.get("component_status") == "REVIEWED_OFFICIAL_INDEX_COMPONENTS"
            and contract.get("dividend_basis") == "OFFICIAL_INDEX_DIVIDEND_POINTS",
            "OFFICIAL_COMPONENTS_REQUIRED", "Individual-stock close adjustment ratios are not index components")
    require(contract.get("revision_basis") == "AS_PUBLISHED_AT_INDEX_OPEN",
            "INDEX_VINTAGE_REQUIRED", "Do not substitute later corrected dividend points")
    require(contract.get("opening_basis") == "REVIEWED_SCHEDULED_OPEN_INDEX_MARK",
            "OPENING_SEMANTICS_REQUIRED", "Daily OHLC alone does not prove the scheduled-open mark")
    require(bool(contract.get("methodology_ref")) and bool(contract.get("review_ref")),
            "SOURCE_REVIEW_REQUIRED", "Retain methodology and source-contract review references")
    require(isinstance(contract.get("series_revision_id"), str) and bool(contract["series_revision_id"]),
            "SERIES_REVISION_REQUIRED", "Bind one reviewed coherent series/revision basis")
    sources = contract.get("source_hashes")
    require(isinstance(sources, dict) and bool(sources) and
            all(isinstance(k, str) and isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) for k,v in sources.items()),
            "SOURCE_HASH_REQUIRED", "Every source requires an immutable byte hash")
    return sources


def conditional_open_level(point, contract):
    """T(open)=T(previous close)*(P(open)+DI(as-of open))/P(previous close).

    This is conditional arithmetic, not independent validation of a provider's
    values or rounding precision. The full prior TR level must already include
    intervening distributions and official corrections. Source-level basis and
    opening-time claims must be reviewed outside this function.
    """
    sources = _contract(contract)
    require(isinstance(point, dict), "OPEN_POINT_REQUIRED", "Explicit official components required")
    require(point.get("series_revision_id") == contract["series_revision_id"],
            "SERIES_REVISION_MISMATCH", "Cannot combine opening levels from unrelated revision bases")
    refs = point.get("source_refs")
    require(isinstance(refs, list) and refs and len(set(refs)) == len(refs) and all(ref in sources for ref in refs),
            "SOURCE_REFERENCE_REQUIRED", "Point must cite bound source files")
    opened, observed, previous, vintage = map(stamp, [point.get("scheduled_open_at"),
        point.get("index_observed_at"), point.get("previous_close_at"), point.get("component_vintage_as_of")])
    require(opened == observed and previous < opened and previous.date() < opened.date(),
            "INDEX_TIME_MISMATCH", "Scheduled open, index observation, previous close and vintage must reconcile")
    require(point.get("session_month") == str(opened.tz_localize(None).to_period("M")),
            "INDEX_MONTH_MISMATCH", "Opening month does not match timestamp")
    require(point.get("calendar_relation") == "VERIFIED_FIRST_AND_PREVIOUS_SESSIONS",
            "OFFICIAL_CALENDAR_REQUIRED", "First and prior sessions require official calendar reconciliation")
    history = point.get("history_kind")
    require(history in {"LIVE_DISSEMINATED", "OFFICIAL_BACKCALCULATED"},
            "INDEX_HISTORY_REQUIRED", "Prelaunch history must be identified explicitly")
    if str(opened.date()) < "2018-12-24":
        require(history == "OFFICIAL_BACKCALCULATED", "PRELAUNCH_HISTORY_MISMATCH", "KRX300 TR was not live before 2018-12-24")
    if history == "OFFICIAL_BACKCALCULATED":
        require(contract.get("backcalculated_history") == "EXPLICITLY_REVIEWED"
                and contract.get("backcast_revision_basis") == "OFFICIAL_RELEASE_VERSION_BOUND",
                "BACKCALCULATED_HISTORY_REVIEW_REQUIRED", "Do not label a backcast as a live publication")
        release = stamp(point.get("backcast_release_at"))
        require(release == vintage == stamp(contract.get("backcast_series_release_at"))
                and str(release.date()) >= "2018-12-24" and release > opened,
                "BACKCAST_VINTAGE_MISMATCH", "Backcalculation is published later, never as known at the historical open")
        require(release <= stamp(contract.get("allowed_data_time")), "OUTSIDE_DATA_BOUNDARY", "Backcast version exceeds allowed plan data boundary")
    else:
        require(vintage <= opened, "INDEX_TIME_MISMATCH", "Live opening components cannot use later corrections")
    pprev = positive(point.get("price_previous_close"), "official previous price-index close")
    tprev = positive(point.get("tr_previous_close"), "official previous gross TR close")
    popen = positive(point.get("price_open"), "official price-index scheduled-open mark")
    dividend = point.get("dividend_points_at_open")
    # Corrections/cancellations can be negative. None is not a zero dividend.
    require(isinstance(dividend, (int,float)) and not isinstance(dividend,bool) and math.isfinite(dividend),
            "INDEX_DIVIDEND_POINTS_REQUIRED", "Official same-vintage index dividend points, including explicit zero")
    value = tprev * (popen + dividend) / pprev
    require(math.isfinite(value) and value > 0, "INVALID_TR_LEVEL", "Total-return index level must be finite and positive")
    return {"session_month":point["session_month"], "scheduled_open_at":opened.isoformat(),
            "conditional_tr_open":value, "history_kind":history, "source_refs":list(refs),
            "component_vintage_as_of":vintage.isoformat(), "historically_live_observation":history=="LIVE_DISSEMINATED",
            "status":"CONDITIONAL_COMPONENT_ARITHMETIC", "execution_certified":False,
            "actual_fill_verified":False, "provider_rounding_reconciled":False}


def build_benchmark_draft(signal_months, points, contract=None):
    """Retain all requested months and blockers; never create runnable inputs."""
    expected = required_opening_months(signal_months)
    result = {"schema_version":VERSION,"status":"DRAFT_NOT_EXECUTION_CERTIFIED",
              "execution_certified":False,"actual_fill_verified":False,"real_performance_computed":False,
              "data_kind":contract.get("data_kind") if isinstance(contract,dict) else None,
              "signal_months":list(signal_months),"required_opening_months":expected,
              "points":[],"windows":[],"blockers":[]}
    seen=set()
    for point in points:
        month=point.get("session_month")
        require(month in expected and month not in seen, "EXTRA_OR_DUPLICATE_OPEN_POINT", "One point for each required opening month")
        seen.add(month)
        try: result["points"].append(conditional_open_level(point,contract))
        except PreparationBlocked as exc: result["blockers"].append({"session_month":month,"code":exc.code})
    result["missing_opening_months"]=sorted(set(expected)-seen)
    if result["missing_opening_months"]:
        result["blockers"].append({"code":"OFFICIAL_OPEN_COMPONENTS_REQUIRED","months":result["missing_opening_months"]})
    if contract is None: result["blockers"].append({"code":"OFFICIAL_INDEX_CONTRACT_REQUIRED"})
    by_month={p["session_month"]:p for p in result["points"]}
    for signal in signal_months:
        month=pd.Period(signal,"M");a,b=by_month.get(str(month+1)),by_month.get(str(month+2))
        if a is None or b is None:continue
        result["windows"].append({"signal_month":str(month),"entry_at":a["scheduled_open_at"],
            "exit_at":b["scheduled_open_at"],"conditional_gross_multiplier":b["conditional_tr_open"]/a["conditional_tr_open"],
            "history_kinds":sorted({a["history_kind"],b["history_kind"]}),"status":"CONDITIONAL_COMPONENT_ARITHMETIC"})
    result["missing_windows"]=[x for x in signal_months if x not in {r["signal_month"] for r in result["windows"]}]
    result["remaining_review"]=["Exact official source identity, entitlement and coverage", "Official calendar exceptions and scheduled-opening mark semantics",
        "Provider precision/revision reconciliation, including prelaunch backcasts", "Stock total-return/PIT inputs and full frozen-plan bundle review remain separate"]
    return result
