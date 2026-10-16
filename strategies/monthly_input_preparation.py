"""Pure draft input preparation, not an execution or certification authority.

Existing Silver canonical-event evidence is an input to this layer. Raw DART
receipts, inferred adjustment scales and gate terminal-loss scenarios are not.
No DB/network/writer is imported. Existing frozen execution code is unchanged.
"""
from __future__ import annotations

import math
from collections import defaultdict

import pandas as pd

VERSION = "monthly-input-preparation-v1"
SUPPORTED_ACTIONS = {"CASH_DIVIDEND", "SPLIT", "REVERSE_SPLIT", "BONUS_SHARES"}


class PreparationBlocked(ValueError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(f"{code}: {detail}")


def require(condition, code, detail):
    if not condition:
        raise PreparationBlocked(code, detail)


def stamp(value):
    try:
        result = pd.Timestamp(value)
    except (ValueError, TypeError):
        raise PreparationBlocked("TIMESTAMP_REQUIRED", "Invalid timestamp") from None
    require(not pd.isna(result) and result.tzinfo is not None,
            "TIMESTAMP_REQUIRED", "Explicit timezone-aware timestamp required")
    return result.tz_convert("Asia/Seoul")


def day(value):
    try:
        result = pd.Timestamp(value)
    except (ValueError, TypeError):
        raise PreparationBlocked("DATE_REQUIRED", "Invalid date") from None
    require(not pd.isna(result) and result.tzinfo is None and result == result.normalize(),
            "DATE_REQUIRED", "Explicit local session date required")
    return result.date().isoformat()


def positive(value, label):
    require(not isinstance(value, bool), "POSITIVE_VALUE_REQUIRED", label)
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise PreparationBlocked("POSITIVE_VALUE_REQUIRED", label) from None
    require(math.isfinite(number) and number > 0, "POSITIVE_VALUE_REQUIRED", label)
    return number


def availability(refs, sources):
    """Maximum of actual, version-specific input availability; never loaded_at."""
    require(isinstance(refs, list) and bool(refs) and len(set(refs)) == len(refs),
            "INPUT_LINEAGE_REQUIRED", "Nonempty unique source references required")
    times = []
    for ref in refs:
        source = sources.get(ref, {})
        require(source.get("status") == "VERIFIED_SOURCE_AVAILABILITY"
                and source.get("evidence_ref")
                and source.get("availability_basis") in {
                    "OFFICIAL_PUBLICATION", "VERIFIED_VENDOR_RELEASE", "EXCHANGE_OBSERVATION",
                    "CANONICAL_ANNOUNCEMENT_PLUS_ONE_DAY"},
                "INPUT_LINEAGE_REQUIRED", f"Missing reviewed source availability: {ref}")
        times.append(stamp(source.get("available_at")))
    return max(times)


def prepare_pit_scores(candidates, universe, sources, factor_bindings):
    """Select latest observable dated score for each declared factor/month/asset.

    Universe membership is supplied with complete reviewed lineage. Missing
    scores remain null; eligibility is never inferred from their existence.
    Production source extraction/dependency completeness must be reviewed
    upstream. Gold as_of_date/insert time alone cannot satisfy this interface.
    """
    bindings = {b["factor_id"]: b["definition_hash"] for b in factor_bindings}
    require(len(bindings) == len(factor_bindings) and bool(bindings),
            "FACTOR_BINDING", "Unique nonempty frozen factor set required")
    indexed = defaultdict(list)
    seen = set()
    for row in candidates:
        factor, asset = row["factor_id"], row["asset_id"]
        require(factor in bindings and row.get("definition_hash") == bindings[factor],
                "FACTOR_BINDING", "Score differs from frozen definition")
        require(row.get("dependency_coverage") == "COMPLETE_REVIEWED",
                "INPUT_LINEAGE_REQUIRED", "All formula dependencies must be accounted for")
        date = day(row["as_of_date"])
        key = factor, asset, date
        require(key not in seen, "DUPLICATE_SCORE", "Resolve score vintages before selection")
        seen.add(key)
        known = availability(row.get("input_refs"), sources)
        value = row.get("signed_score")
        require(value is None or (not isinstance(value, bool) and math.isfinite(float(value))),
                "INVALID_SCORE", "Only explicit null or finite already-signed score allowed")
        indexed[(factor, asset)].append((date, known, row))
    output, audit, seen_universe = [], [], set()
    require(bool(universe), "UNIVERSE_REQUIRED", "Explicit month/asset universe required")
    for item in universe:
        month, asset = item["signal_month"], item["asset_id"]
        cutoff = pd.Period(month, "M").end_time.floor("s").tz_localize("Asia/Seoul")
        key = month, asset
        require(key not in seen_universe, "DUPLICATE_UNIVERSE", str(key))
        seen_universe.add(key)
        require(isinstance(item.get("eligible"), bool), "UNIVERSE_REQUIRED", "Explicit eligibility required")
        require(item.get("dependency_coverage") == "COMPLETE_REVIEWED",
                "INPUT_LINEAGE_REQUIRED", "Universe and cap lineage must be complete")
        universe_known = availability(item.get("universe_refs"), sources)
        cap_known = availability(item.get("cap_refs"), sources)
        require(max(universe_known, cap_known) <= cutoff,
                "PIT_AFTER_CUTOFF", "Universe/cap were not available at decision time")
        cap = positive(item.get("market_cap"), "market_cap") if item["eligible"] else item.get("market_cap")
        for factor in bindings:
            choices = [(d, known, r) for d, known, r in indexed[(factor, asset)]
                       if d <= cutoff.date().isoformat() and known <= cutoff]
            selected = max(choices, key=lambda value: value[0]) if choices else None
            value = selected[2].get("signed_score") if selected else None
            known = max(universe_known, cap_known, selected[1] if selected else universe_known)
            output.append(dict(factor_id=factor, signal_month=month, asset_id=asset,
                               signed_score=None if value is None else float(value), eligible=item["eligible"],
                               market_cap=cap, available_at=known.isoformat()))
            audit.append(dict(factor_id=factor, signal_month=month, asset_id=asset,
                              selected_as_of_date=selected[0] if selected else None,
                              score_input_refs=selected[2]["input_refs"] if selected else [],
                              universe_refs=item["universe_refs"], cap_refs=item["cap_refs"],
                              status="OBSERVABLE_SCORE_SELECTED" if selected else "MISSING_SCORE_RETAINED"))
    return {"scores": output, "audit": audit, "execution_certified": False}


def compute_open_window(prices, events, coverage):
    """Raw-share wealth path, with gross ex-date cash reinvested at that close.

    Purchase at entry open has no entitlement to entry-date distributions.
    Exit-date distributions belong to the existing holder and are valued as
    cash receivables at exit open, without using that day's future close.
    Only continuous trading and one listing episode are supported in v1.
    Unsupported/terminal actions and missing/zero quotes block the WHOLE window.
    No close-TR-to-adjusted-open shortcut or terminal-loss imputation is used.
    """
    require(coverage.get("status") == "REVIEWED_COMPLETE" and coverage.get("evidence_refs"),
            "EVENT_COVERAGE_REQUIRED", "Empty events are not proof of no events")
    require(coverage.get("raw_share_basis") == "RAW_UNADJUSTED"
            and coverage.get("event_cash_basis") == "PRE_EVENT_RAW_SHARE",
            "SHARE_BASIS_REQUIRED", "Reviewed raw-price/share/cash basis required")
    expected = list(map(day, coverage.get("session_dates", [])))
    require(len(expected) >= 2 and expected == sorted(set(expected)),
            "SESSION_COVERAGE_REQUIRED", "Ordered complete daily session dates required")
    require([day(p["date"]) for p in prices] == expected,
            "MISSING_PRICE_SESSION", "Do not bridge missing/suspended sessions")
    asset = coverage["asset_id"]
    episode = coverage["listing_episode_id"]
    for row in prices:
        require(row.get("asset_id") == asset and row.get("listing_episode_id") == episode,
                "ASSET_EPISODE_MISMATCH", "Cannot bridge security/listing episodes")
        require(row.get("source_ref") and row.get("open_status") == "VERIFIED_TRADABLE",
                "TRADABILITY_UNVERIFIED", "Raw positive quotes alone do not prove tradability")
        positive(row.get("open"), "raw open")
    by_day, ids = defaultdict(list), set()
    for event in events:
        event_id = event.get("economic_event_id")
        require(event_id and event_id not in ids, "DUPLICATE_EVENT", "One canonical decision per event")
        ids.add(event_id)
        require(event.get("asset_id") == asset and event.get("listing_episode_id") == episode,
                "ASSET_EPISODE_MISMATCH", "Event belongs to another security/listing episode")
        require(event.get("canonical") is True and event.get("source_ref")
                and event.get("resolution_status") == "VERIFIED",
                "EVENT_RESOLUTION_REQUIRED", "Use existing canonical/reconciled evidence, not raw receipts")
        require(event.get("type") in SUPPORTED_ACTIONS, "UNSUPPORTED_CORPORATE_ACTION",
                f"Explicit accounting needed for {event.get('type')}; no gate terminal scenario")
        event_day = day(event["ex_date"])
        require(event_day in expected, "EVENT_OUTSIDE_SESSION_PATH", "Do not infer/move an ex-date")
        field = "cash_per_pre_action_share" if event["type"] == "CASH_DIVIDEND" else "new_shares_per_old_share"
        positive(event.get(field), field)
        by_day[event_day].append(event)
    shares, cash, audit = 1., 0., []
    entry = positive(prices[0]["open"], "entry open")
    for i, row in enumerate(prices):
        date = day(row["date"])
        actions = by_day[date]
        before = shares
        splits = [e for e in actions if e["type"] != "CASH_DIVIDEND"]
        require(len(splits) <= 1, "COMBINED_ACTION_REVIEW_REQUIRED", "Combined share transformations need explicit resolution")
        if i:
            cash += before * sum(float(e["cash_per_pre_action_share"]) for e in actions if e["type"] == "CASH_DIVIDEND")
            if splits:
                shares *= float(splits[0]["new_shares_per_old_share"])
        open_wealth = shares * float(row["open"]) + cash
        require(math.isfinite(open_wealth) and open_wealth > 0, "INVALID_WEALTH", "Nonfinite/terminal wealth requires review")
        received = cash
        # Terminal open is the observation boundary; never consume its close.
        if i < len(prices) - 1 and cash:
            require(row.get("close_status") == "VERIFIED_TRADABLE", "REINVESTMENT_QUOTE_REQUIRED", "Ex-date close reinvestment must be supported")
            shares += cash / positive(row.get("close"), "raw reinvestment close")
            cash = 0.
        audit.append(dict(date=date, shares_before=before, shares_after=shares,
                          entitlement_cash=received, cash_after=cash, wealth_at_open=open_wealth,
                          event_ids=[e["economic_event_id"] for e in actions],
                          entry_date_entitlements_excluded=(i == 0)))
    return {"gross_total_return_multiplier": open_wealth / entry,
            "entry_open": entry, "audit": audit, "execution_certified": False,
            "convention": "RAW_SHARES_GROSS_EX_DATE_CLOSE_REINVESTMENT_EXIT_OPEN_RECEIVABLE",
            "limitations": ["Continuous trading and simple share/cash events only",
                            "Receipt selection/source truth/completeness must be verified upstream",
                            "Not actual fills, order-book capacity, delisting proceeds or paid-date cash trading"]}


def external_input_blockers(calendar, market):
    """Missing external inputs remain explicit failures; no inferred clock/TR."""
    blockers = []
    sessions = {}
    if not calendar or calendar.get("status") != "VERIFIED_OFFICIAL_SESSIONS":
        blockers.append("OFFICIAL_SESSION_TIMESTAMPS_REQUIRED")
    elif not calendar.get("source_refs") or not calendar.get("sessions"):
        blockers.append("CALENDAR_SOURCE_COVERAGE_REQUIRED")
    else:
        for row in calendar["sessions"]:
            opened = stamp(row.get("open_at"))
            require(str(opened.tz_localize(None).to_period("M")) == row.get("session_month"),
                    "CALENDAR_MONTH_MISMATCH", "Session does not belong to month")
            require(row['session_month'] not in sessions, "DUPLICATE_SESSION", "One first session per month")
            sessions[row['session_month']] = opened
    if (not market or market.get("market_id") != "KRX300_TR"
            or market.get("return_type") != "gross_total_return"
            or market.get("currency") != "KRW"
            or market.get("interval") != "same_entry_open_to_exit_open"
            or market.get("status") != "VERIFIED_OFFICIAL_TOTAL_RETURN"
            or not market.get("source_refs") or not market.get("windows")):
        blockers.append("KRX300_OPEN_TOTAL_RETURN_REQUIRED")
    else:
        seen = set()
        for row in market['windows']:
            month = pd.Period(row['signal_month'], 'M')
            require(str(month) not in seen, "DUPLICATE_MARKET_WINDOW", str(month))
            seen.add(str(month))
            entry, exit_time, known = map(stamp, [row.get('entry_at'), row.get('exit_at'), row.get('return_available_at')])
            require(exit_time > entry and known >= exit_time, "MARKET_TIME_MISMATCH", "Invalid market interval/availability")
            if sessions:
                require(entry == sessions.get(str(month+1)) and exit_time == sessions.get(str(month+2)),
                        "MARKET_TIME_MISMATCH", "Use the exact official entry/exit opens")
            value = row.get('gross_total_return_multiplier')
            require(isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value) and value >= 0,
                    "INVALID_MARKET_RETURN", "Explicit nonnegative gross TR multiplier required")
    return blockers


def draft_status(calendar=None, market=None):
    """Never emit a runnable monthly-comparison-inputs-v1 or set evidence true."""
    return {"schema_version": VERSION, "status": "DRAFT_COMPONENTS_NOT_EXECUTION_CERTIFIED",
            "execution_certified": False, "real_performance_computed": False,
            "external_blockers": external_input_blockers(calendar, market),
            "required_before_execution": ["Source-file hash and reviewer binding",
                "Complete exact plan factor/month/asset coverage and input bounds",
                "PIT dependency completeness, listing identity and unsupported-action resolution",
                "Independent reconciliation of raw-share wealth convention and market interval"]}
