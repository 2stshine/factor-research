"""Outcome-free v2 planning; does not change the active 36-month policy.

This module plans calendar warm-up from caller-verified metadata, not price or
return observations. It neither verifies that metadata nor authorizes a run.
First-available months must already incorporate source warm-up and publication
availability. Source history is reported separately, not added a second time.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


SCHEMA_VERSION = "research-horizon-plan-v1"


def _month(value: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise ValueError("month must be YYYY-MM")
    year, month = map(int, value.split("-"))
    if year < 1:
        raise ValueError("year must be positive")
    return year * 12 + month - 1


def _format_month(value: int) -> str:
    year, month = divmod(value, 12)
    return f"{year:04d}-{month + 1:02d}"


def _nonnegative_int(value: int, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


@dataclass(frozen=True)
class InputHistory:
    """One input's verified first usable month and actual dependency bounds.

    formula_lag_months is the oldest monthly offset used by the formula, not
    a count of observations (lag 12 can require 13 monthly price points).
    source_history_months includes a materialized field's own raw lookback;
    latest TTM is not a zero-history raw economic measurement.
    This is a caller-declared dependency bound, not a measured age bound for
    stale filings. Publication delays and stale-age rules require separate
    validation. A calendar span is not a count of valid evaluation months.
    """

    input_id: str
    first_available_signal_month: str
    formula_lag_months: int
    source_history_months: int
    source_ref: str
    availability_scope_checked: bool


@dataclass(frozen=True)
class HypothesisHorizon:
    hypothesis_id: str
    inputs: tuple[InputHistory, ...]
    return_label_horizon_months: int = 1
    economic_label_horizon_months: int | None = None


def plan_horizons(
    hypotheses: Iterable[HypothesisHorizon],
    *,
    signal_end: str,
    minimum_primary_start: str | None = None,
    short_history_months: int = 12,
) -> dict:
    """Plan one common comparison start without inspecting any outcomes.

    Longer hypotheses are flagged, not silently shortened or rejected. The
    caller should split short/long cohorts before using a common start. Actual
    candidate coverage, gaps and matched assets remain separate prerequisites.
    Label horizons affect maturity requirements, never feature warm-up.
    """
    end = _month(signal_end)
    threshold = _nonnegative_int(short_history_months, "short_history_months")
    floor = _month(minimum_primary_start) if minimum_primary_start else None
    items = list(hypotheses)
    if not items or len({item.hypothesis_id for item in items}) != len(items):
        raise ValueError("provide nonempty hypotheses with unique IDs")
    rows = []
    for item in items:
        if not item.hypothesis_id or not item.inputs:
            raise ValueError("each hypothesis needs an ID and explicit inputs")
        if len({entry.input_id for entry in item.inputs}) != len(item.inputs):
            raise ValueError("input IDs must be unique within each hypothesis")
        return_horizon = _nonnegative_int(item.return_label_horizon_months, "return horizon")
        if return_horizon == 0:
            raise ValueError("return label horizon must be positive")
        economic_horizon = item.economic_label_horizon_months
        if economic_horizon is not None:
            _nonnegative_int(economic_horizon, "economic horizon")
            if economic_horizon == 0:
                raise ValueError("economic label horizon must be positive")
        inputs = []
        for entry in item.inputs:
            if not entry.input_id or not entry.source_ref or entry.availability_scope_checked is not True:
                raise ValueError("input availability requires checked scope and source provenance")
            first = _month(entry.first_available_signal_month)
            lag = _nonnegative_int(entry.formula_lag_months, "formula lag")
            source = _nonnegative_int(entry.source_history_months, "source history")
            inputs.append({
                "input_id": entry.input_id,
                "first_available_signal_month": entry.first_available_signal_month,
                "formula_lag_months": lag,
                "source_history_months": source,
                "raw_history_upper_bound_months": source + lag,
                "first_formula_ready_month": _format_month(first + lag),
                "source_ref": entry.source_ref,
            })
        first_ready = max(_month(entry["first_formula_ready_month"]) for entry in inputs)
        raw_history = max(entry["raw_history_upper_bound_months"] for entry in inputs)
        rows.append({
            "hypothesis_id": item.hypothesis_id,
            "inputs": inputs,
            "first_formula_ready_month": _format_month(first_ready),
            "formula_max_lag_months": max(entry["formula_lag_months"] for entry in inputs),
            "raw_history_upper_bound_months": raw_history,
            "extended_history_rationale_required": raw_history > threshold,
            "return_label_horizon_months": return_horizon,
            "economic_label_horizon_months": economic_horizon,
        })
    start = max(_month(row["first_formula_ready_month"]) for row in rows)
    if floor is not None:
        start = max(start, floor)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "METADATA_ONLY_NOT_EXECUTION_AUTHORIZATION",
        "active_policy_modified": False,
        "source_metadata_verified_by_this_planner": False,
        "status": "PLANNED" if start <= end else "NO_COMMON_CALENDAR",
        "common_primary_start": _format_month(start),
        "signal_end": signal_end,
        "common_calendar_months": max(0, end - start + 1),
        "short_history_months": threshold,
        "hypotheses": rows,
        "remaining_checks": [
            "actual_defined_candidate_and_source_lineage",
            "calendar_gaps_and_formula_coverage",
            "common_eligible_asset_sample",
            "label_maturity_within_permitted_evaluation_scope",
            "campaign_registration_and_exposure_policy",
        ],
    }
