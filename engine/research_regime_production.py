"""New-campaign daily-risk context; never upgrades or mutates legacy regimes.

This module only freezes and projects input context.  KOSPI and KOSDAQ must be
analysed in separate cross-sections: their same-month labels may differ.  The
historical clock is assumed, not a certified first-release or execution clock.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from engine.regime_inputs import campaign_context, digest as macro_digest
from engine.regime_shadow import RULES
from engine.research_regime_adoption import (
    ASSUMPTIONS, MARKETS, _policy, _row, validate_adoption,
)

VERSION = "production-daily-risk-context-v1"
LABELS = ["UP_LOW", "UP_HIGH", "DOWN_LOW", "DOWN_HIGH"]
ASSIGNMENT = "ASSET_FORMATION_MARKET_SEPARATE_KOSPI_KOSDAQ_NO_POOLED_FALLBACK"
CONTRAST = ["UP_LOW", "DOWN_HIGH"]


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(",", ":")).encode()).hexdigest()


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _month(value):
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value) is None:
        raise ValueError("Expected canonical YYYY-MM")
    return pd.Period(value, freq="M")


def _aware(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError("Expected aware research-time timestamp")
    return stamp


def _boundary(data_cutoff, oos_start):
    if not isinstance(data_cutoff, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", data_cutoff) is None:
        raise ValueError("Expected date-only data cutoff")
    cutoff, sealed = pd.Timestamp(data_cutoff), _month(oos_start)
    if cutoff >= sealed.start_time:
        raise ValueError("Discovery data cutoff crosses sealed scope")
    return min(cutoff.to_period("M") - 1, sealed - 2)


def load_adoption_contract(path, *, expected_sha256):
    """Load explicitly hash-bound input artifact; never discover a latest file."""
    body = Path(path).read_bytes()
    if not _sha(expected_sha256) or hashlib.sha256(body).hexdigest() != expected_sha256:
        raise ValueError("Daily-risk adoption file hash mismatch")
    payload = json.loads(body)
    validate_adoption(payload)
    return payload


def _macro_context(frozen, *, data_cutoff, oos_start):
    if frozen is None:
        return {}, None
    campaign = {"discovery": {"data_cutoff": data_cutoff},
                "oos": {"start": oos_start}, "diagnostic_regimes": frozen}
    _legacy_market, macro, _metadata = campaign_context(campaign)
    # All axes may be frozen at creation, but none is automatically searched.
    return macro, frozen["sha256"]


def freeze_regime_context(adoption_contract, *, signal_start, data_cutoff,
                          oos_start, frozen_at, macro_context=None):
    """Freeze input-only source, policy and boundary for a NEW campaign.

    ``macro_context`` is an already-frozen ``campaign['diagnostic_regimes']``.
    Its macro axes are retained separately; the old monthly market rule is not
    copied.  Requested months absent from the adoption stay UNKNOWN, including
    future campaigns whose end exceeds this particular source artifact.
    """
    validate_adoption(adoption_contract)
    start, last = _month(signal_start), _boundary(data_cutoff, oos_start)
    stamp = _aware(frozen_at)
    if start > last or stamp < _aware(adoption_contract["adopted_at"]):
        raise ValueError("Invalid freeze scope or research-time ordering")
    if pd.Timestamp(data_cutoff).date() > stamp.tz_convert("Asia/Seoul").date():
        raise ValueError("Cannot freeze a future data cutoff")
    macro, macro_sha = _macro_context(macro_context, data_cutoff=data_cutoff, oos_start=oos_start)
    result = {
        "schema_version": VERSION, "purpose": "DIAGNOSTIC_ONLY", "new_campaigns_only": True,
        "pit_status": "PIT_ASSUMED", "historical_pit_verified": False,
        "calendar_verified": False, "factor_feature_allowed": False,
        "trading_allowed": False, "promotion_gates_unchanged": True,
        "automatic_gold_publication_allowed": False,
        "frozen_at": frozen_at, "signal_start": str(start), "signal_end": str(last),
        "data_cutoff": data_cutoff, "oos_start": oos_start,
        "outcome_mapping": "SIGNAL_MONTH_T_TO_OUTCOME_MONTH_T_PLUS_1",
        "market_assignment": ASSIGNMENT, "separate_market_diagnostics_required": True,
        "rules": deepcopy(RULES), "rules_sha256": _digest(RULES),
        "definition_sha256": _digest({"rules": RULES, "assignment": ASSIGNMENT,
                                      "contrast": CONTRAST}),
        "labels": list(LABELS), "contrast": list(CONTRAST),
        "assumptions": deepcopy(ASSUMPTIONS),
        "adoption": {key: deepcopy(adoption_contract[key]) for key in
                     ("contract_id", "contract_sha256", "authorization_ref", "adopted_at",
                      "source", "policy", "scope")},
        "markets": {}, "macro_context_sha256": macro_sha, "macro_axes": {},
        "macro_selection_policy": "EXPLICIT_HYPOTHESIS_PLAN_MAX_TWO_AXES_NO_COMBINATIONS",
    }
    for market in MARKETS:
        entry = adoption_contract["markets"][market]
        result["markets"][market] = {
            key: deepcopy(entry[key]) for key in
            ("source_id", "source_provenance_sha256", "raw_file_manifest_sha256", "raw_file_count",
             "calendar_dates_sha256", "calendar_session_count", "calendar_semantics",
             "last_complete_input_month", "historical_receipts_available")}
        # Retain proof identity, not its out-of-scope future calendar rows.
        completion = entry.get("completion_evidence")
        result["markets"][market]["completion_evidence_sha256"] = _digest(completion) if completion else None
        result["markets"][market]["rows"] = [
            deepcopy(row) for row in entry["rows"] if start <= _month(row["month"]) <= last]
    for name, context in macro.items():
        entry = deepcopy(context)
        entry["rows"] = [row for row in entry["rows"] if start <= _month(row["month"]) <= last]
        result["macro_axes"][name] = entry
    result["sha256"] = _digest(result)
    validate_frozen_context(result)
    return result


def validate_frozen_context(frozen, *, data_cutoff=None, oos_start=None):
    """Recheck a self-contained campaign copy; no mutable upstream file reads."""
    if not isinstance(frozen, dict) or frozen.get("schema_version") != VERSION:
        raise ValueError("Unsupported daily-risk frozen context")
    body = {key: value for key, value in frozen.items() if key != "sha256"}
    if frozen.get("sha256") != _digest(body):
        raise ValueError("Daily-risk context hash mismatch")
    exact = {
        "purpose": "DIAGNOSTIC_ONLY", "new_campaigns_only": True, "pit_status": "PIT_ASSUMED",
        "historical_pit_verified": False, "calendar_verified": False,
        "factor_feature_allowed": False, "trading_allowed": False,
        "promotion_gates_unchanged": True, "automatic_gold_publication_allowed": False,
        "market_assignment": ASSIGNMENT, "separate_market_diagnostics_required": True,
        "outcome_mapping": "SIGNAL_MONTH_T_TO_OUTCOME_MONTH_T_PLUS_1",
        "macro_selection_policy": "EXPLICIT_HYPOTHESIS_PLAN_MAX_TWO_AXES_NO_COMBINATIONS",
    }
    if any(type(frozen.get(k)) is not type(v) or frozen.get(k) != v for k, v in exact.items()):
        raise ValueError("Daily-risk authority or interpretation boundary changed")
    last = _boundary(frozen["data_cutoff"], frozen["oos_start"])
    start = _month(frozen["signal_start"])
    if (start > last or frozen["signal_end"] != str(last)
            or data_cutoff is not None and data_cutoff != frozen["data_cutoff"]
            or oos_start is not None and oos_start != frozen["oos_start"]):
        raise ValueError("Daily-risk campaign boundary mismatch")
    if (frozen["rules"] != RULES or frozen["rules_sha256"] != _digest(RULES)
            or frozen["labels"] != LABELS or frozen["contrast"] != CONTRAST
            or frozen["assumptions"] != ASSUMPTIONS
            or frozen["definition_sha256"] != _digest({"rules": RULES, "assignment": ASSIGNMENT,
                                                       "contrast": CONTRAST})):
        raise ValueError("Daily-risk classification rule changed")
    adopted = frozen["adoption"]
    _policy(adopted["policy"]["snapshot"])
    if (any(not isinstance(adopted.get(key), str) or not adopted[key].strip()
            for key in ("contract_id", "authorization_ref"))
            or not _sha(adopted["contract_sha256"]) or not _sha(adopted["source"]["sha256"])
            or not _sha(adopted["policy"]["sha256"])
            or adopted["policy"]["policy_id"] != adopted["policy"]["snapshot"]["policy_id"]
            or _aware(frozen["frozen_at"]) < _aware(adopted["adopted_at"])
            or _aware(adopted["adopted_at"]) < _aware(adopted["source"]["created_at"])):
        raise ValueError("Daily-risk source/policy/freeze binding mismatch")
    source_day = pd.Timestamp(adopted["source"]["as_of"])
    if (source_day.tzinfo is not None or source_day != source_day.normalize()
            or source_day.date() > _aware(adopted["adopted_at"]).tz_convert("Asia/Seoul").date()
            or pd.Timestamp(frozen["data_cutoff"]).date() > _aware(frozen["frozen_at"]).tz_convert("Asia/Seoul").date()):
        raise ValueError("Daily-risk as-of ordering mismatch")
    source_start, source_end = (_month(adopted["scope"][k]) for k in ("start_month", "end_month"))
    if (source_start > source_end or source_end.end_time.normalize() > source_day
            or adopted["scope"]["market_ids"] != list(MARKETS)
            or adopted["scope"]["clock"] != "KST_CALENDAR_MONTH_END"
            or adopted["scope"]["outcome_mapping"] != "SIGNAL_MONTH_T_TO_OUTCOME_MONTH_T_PLUS_1"
            or set(frozen["markets"]) != set(MARKETS)):
        raise ValueError("Daily-risk source market/scope mismatch")
    expected = [str(m) for m in pd.period_range(max(start, source_start), min(last, source_end), freq="M")]
    for market, context in frozen["markets"].items():
        if [row["month"] for row in context["rows"]] != expected:
            raise ValueError("Daily-risk source intersection is incomplete or duplicated")
        for key in ("source_provenance_sha256", "raw_file_manifest_sha256", "calendar_dates_sha256"):
            if not _sha(context.get(key)):
                raise ValueError("Daily-risk source provenance hash missing")
        for row in context["rows"]:
            _row(row, market=market, assumed=True)
            if (row["diagnostic_contract_id"] != adopted["contract_id"]
                    or row["assumption_policy_sha256"] != adopted["policy"]["sha256"]
                    or row["assumption_policy_id"] != adopted["policy"]["policy_id"]
                    or row["source_id"] != context["source_id"]):
                raise ValueError("Daily-risk row source/policy binding mismatch")
    if frozen["macro_axes"] and not _sha(frozen["macro_context_sha256"]):
        raise ValueError("Macro axes require their frozen parent context hash")
    for name, context in frozen["macro_axes"].items():
        states = context["states"]
        if (not isinstance(name, str) or not name or len(states) < 2
                or len(set(states)) != len(states) or "UNKNOWN" in states
                or context["rules_sha256"] != macro_digest(context["classification_rules"])
                or not _sha(context["approval_sha256"])):
            raise ValueError("Invalid frozen macro axis")
        months = [row["month"] for row in context["rows"]]
        if months != sorted(set(months)):
            raise ValueError("Duplicate macro observation month")
        for row in context["rows"]:
            month = _month(row["month"])
            known = pd.Timestamp(row["known_at"])
            if (not start <= month <= last or row["effective_month"] != str(month + 1)
                    or pd.isna(known) or known.tzinfo is not None
                    or known < month.start_time or row["state"] not in states + ["UNKNOWN"]
                    or known > month.end_time and row["state"] != "UNKNOWN"):
                raise ValueError("Macro scope, availability or state mismatch")


def macro_catalog(frozen):
    """Input-only catalog for predeclaring at most two hypothesis-relevant axes."""
    validate_frozen_context(frozen)
    return {name: {key: deepcopy(context[key]) for key in
                   ("source_id", "states", "classification_rules", "rules_sha256")}
            for name, context in frozen["macro_axes"].items()}


def project_regime_context(frame, frozen, *, month_column="month", market_column="market", macro_axes=()):
    """Return a copy and metadata; never combine markets in a regression.

    ``metadata['market_views']`` contains positional indices for separate labs.
    The primary pooled lab MUST NOT use ``metadata['regime']`` because it assumes
    one state per month.  Macro axes need predeclared plans, never result ranking.
    """
    validate_frozen_context(frozen)
    if (not isinstance(frame, pd.DataFrame) or not frame.columns.is_unique
            or month_column not in frame or market_column not in frame):
        raise ValueError("Need an exact month and formation-market projection")
    if (not isinstance(macro_axes, (list, tuple)) or len(macro_axes) > 2
            or len(set(macro_axes)) != len(macro_axes)
            or not set(macro_axes).issubset(frozen["macro_axes"])):
        raise ValueError("Select at most two explicitly frozen macro axes")
    months = pd.PeriodIndex(frame[month_column], freq="M")
    if months.isna().any() or not ((months >= _month(frozen["signal_start"]))
                                 & (months <= _month(frozen["signal_end"]))).all():
        raise ValueError("Project Discovery scope before regime handoff")
    generated = {"market_regime", "regime_known_at", "regime_input_status"}
    for name in macro_axes:
        generated.update({_macro_column(name), _macro_column(name) + "_known_at"})
    if generated & set(frame.columns):
        raise ValueError("Refusing to overwrite existing regime columns")
    output = frame.copy(deep=True)
    lookup = {(market, row["month"]): row for market, entry in frozen["markets"].items()
              for row in entry["rows"]}
    mapped, clocks, statuses = [], [], []
    markets = frame[market_column].tolist()
    for market, month in zip(markets, months.astype(str)):
        key = market if isinstance(market, str) else "UNKNOWN"
        row = lookup.get((key, month))
        mapped.append(row["regime"] if row else "UNKNOWN")
        clocks.append(pd.Timestamp(row["decision_at"]).tz_convert("Asia/Seoul").tz_localize(None)
                      if row else pd.NaT)
        statuses.append(("AVAILABLE" if row["status"] == "READY_SHADOW" else row["reason"])
                        if row else "UNSUPPORTED_MARKET" if key not in MARKETS else "OUTSIDE_FROZEN_SOURCE_SCOPE")
    output["market_regime"], output["regime_known_at"] = mapped, pd.to_datetime(clocks)
    output["regime_input_status"] = statuses
    spec = {"column": "market_regime", "known_at": "regime_known_at", "labels": list(LABELS),
            "contrast": list(CONTRAST), "definition_sha256": frozen["definition_sha256"],
            "pit_status": "PIT_ASSUMED"}
    metadata = {"input_status": "FROZEN_ASSUMED_MARKET_SPECIFIC", "sha256": frozen["sha256"],
                "source_contract_sha256": frozen["adoption"]["contract_sha256"],
                "source_as_of": frozen["adoption"]["source"]["as_of"],
                "source_scope": deepcopy(frozen["adoption"]["scope"]),
                "market_assignment": ASSIGNMENT, "pooled_regime_analysis_allowed": False,
                "regime": spec, "market_views": {}, "macro_specs": {},
                "unrecognized_market_rows": sum(not isinstance(m, str) or m not in MARKETS for m in markets),
                "limitations": deepcopy(ASSUMPTIONS)}
    for market in MARKETS:
        positions = [i for i, value in enumerate(markets) if isinstance(value, str) and value == market]
        metadata["market_views"][market] = {
            "row_indices": positions, "regime": deepcopy(spec),
            "rows": len(positions), "unknown_rows": sum(mapped[i] == "UNKNOWN" for i in positions),
            "unknown_months": sorted({str(months[i]) for i in positions if mapped[i] == "UNKNOWN"}),
            "source_id": frozen["markets"][market]["source_id"],
        }
    for name in macro_axes:
        context, column = frozen["macro_axes"][name], _macro_column(name)
        rows = {row["month"]: row for row in context["rows"]}
        output[column] = [rows.get(month, {}).get("state", "UNKNOWN") for month in months.astype(str)]
        output[column + "_known_at"] = pd.to_datetime([
            rows.get(month, {}).get("known_at", pd.NaT) for month in months.astype(str)])
        metadata["macro_specs"][name] = {
            "column": column, "known_at": column + "_known_at", "labels": deepcopy(context["states"]),
            # Source-order first two is not an economic hypothesis.  The caller
            # must supply its predeclared contrast to the evidence contract.
            "contrast": None, "definition_sha256": context["rules_sha256"],
            "pit_status": context.get("pit_status", "VERIFIED"),
        }
    return output, metadata


def _macro_column(name):
    return "macro__" + hashlib.sha256(name.encode()).hexdigest()[:16]
