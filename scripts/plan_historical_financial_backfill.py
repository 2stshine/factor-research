"""Input-only symbolic upper bound for restoring original 2015 quarters.

This does not populate financial values or execute a factor return experiment.
Unknown standalone amounts remain symbolic. Original-report availability,
normalization and fiscal-calendar evidence are prerequisites, never assumed
certified merely because an input-coverage upper bound is promising.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pickle

import numpy as np
import pandas as pd

from engine import fundamentals
from engine.research_memory_transfer import write_artifact
from factors.candidates import sales_growth_acceleration_12m as candidate

ROOT = Path(__file__).resolve().parents[1]
START, END = "2018-03", "2023-06"
RAW_END = "2023-07-31"
EXPECTED_SOURCE_SHA = "136da8ad847ec3510549c881109dacff4cbb406359c4ec8d9c5a7347cff8f1ed"
EXPECTED_CANDIDATE_SHA = "5fa3c73652c11f14e15ac7a2bf7ae1c209cee238cd4afd3def9a07d175ca19eb"
INPUT_COLUMNS = ["asset_id", "ym", "trade_date", "in_universe", "market_cap", "adj_close", "revenue_ttm"]
RAW_COLUMNS = ["asset_id", "period_end", "fiscal_period", "fs_type", "available_date", "metric", "value", "revision_key"]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Amount:
    constant: float
    terms: tuple = ()
    required: frozenset = frozenset()

    def plus(self, other, sign=1):
        terms = Counter(dict(self.terms))
        for name, coefficient in other.terms:
            terms[name] += sign * coefficient
        return Amount(self.constant + sign * other.constant,
                      tuple(sorted((key, value) for key, value in terms.items() if value)),
                      self.required | other.required)


def known(value):
    return Amount(float(value)) if pd.notna(value) and np.isfinite(float(value)) else None


def contiguous(points):
    """Use the frozen calendar/label validator, not invented financial numbers."""
    if not 2 <= len(points) <= 5 or any(point[2] is None for point in points):
        return False
    labels = tuple({"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}.get(point[1]) for point in points)
    if any(label is None for label in labels):
        return False
    return fundamentals._quarter_structure_is_contiguous(tuple(point[0] for point in points), labels)


def original_quarter_requirements(state):
    """Calendar-schedule upper bound inferred ONLY from already-known FY rows.

    Only Q1/Q2/Q3 endpoints in calendar 2015 may be added; existing rows,
    explicit nulls and revisions are not replaced. A non-month-end FY is left
    outside this upper bound: weekly/fiscal calendars require original evidence.
    """
    requirements = {}
    for (fy_end, label), row in state.items():
        if label != "FY" or not fy_end.is_month_end:
            continue
        for quarter in (1, 2, 3):
            date = fy_end - pd.offsets.MonthEnd(3 * (4 - quarter))
            fiscal_period = f"Q{quarter}"
            if date.year != 2015 or (date, fiscal_period) in state:
                continue
            key = (date, fiscal_period)
            requirements[key] = {
                "period_end": date.date().isoformat(), "fiscal_period": fiscal_period,
                "fy_end": fy_end.date().isoformat(),
                "known_fy_available_date": pd.Timestamp(row["available_date"]).date().isoformat(),
                "known_fy_fs_type": row["fs_type"],
                "requires_original_standalone_amount": True,
                "requires_historical_known_at_proof": True,
                "fiscal_calendar_inferred_not_certified": True,
            }
    return requirements


def symbolic_ttm(state):
    requirements = original_quarter_requirements(state)
    by_period = {}
    for (date, label), row in sorted(state.items()):
        if label == "FY":
            continue
        if date in by_period or label not in {"Q1", "Q2", "Q3", "Q4"}:
            by_period[date] = ("INVALID", None)
        else:
            by_period[date] = (label, known(row["value"]))
    for (date, label), _ in sorted(requirements.items()):
        if date in by_period:
            # Missing a competing label is not permission to replace or merge
            # an observed endpoint. Preserve ambiguity as a barrier.
            by_period[date] = ("INVALID", None)
        else:
            symbol = (date.date().isoformat(), label)
            by_period[date] = (label, Amount(0.0, ((symbol, 1),), frozenset({symbol})))
    previous_fy = None
    for (fy_end, label), row in sorted(state.items()):
        if label != "FY":
            continue
        explicit = by_period.get(fy_end)
        if explicit is not None and explicit[0] == "Q4":
            previous_fy = fy_end
            continue
        prior = [(date, fp, amount) for date, (fp, amount) in sorted(by_period.items()) if date < fy_end][-3:]
        chain = [*prior, (fy_end, "Q4", known(row["value"]))]
        valid = explicit is None and [point[1] for point in prior] == ["Q1", "Q2", "Q3"] and contiguous(chain)
        if valid and previous_fy is not None:
            valid = contiguous([(previous_fy, "Q4", Amount(0.0)), *chain])
        if valid:
            amount = chain[-1][2]
            for point in prior:
                amount = amount.plus(point[2], -1)
            by_period[fy_end] = ("Q4", amount)
        else:
            by_period[fy_end] = ("INVALID", None)
        previous_fy = fy_end
    series = [(date, fp, amount) for date, (fp, amount) in sorted(by_period.items())]
    recent = series[-4:]
    if len(recent) != 4 or not contiguous(recent):
        return {"repairable_structure": False, "reason": "FOUR_CONTIGUOUS_QUARTERS_STILL_UNAVAILABLE",
                "latest_quarter_structure": [{"period_end": date.date().isoformat(), "fiscal_period": label,
                    "amount_available_or_symbolic": amount is not None} for date, label, amount in recent]}
    result = Amount(0.0)
    for _, _, amount in recent:
        result = result.plus(amount)
    required = [requirements[(pd.Timestamp(date), label)] for date, label in sorted(result.required)]
    return {
        "repairable_structure": bool(required),
        "reason": "ORIGINAL_2015_QUARTER_EVIDENCE_REQUIRED" if required else "NO_2015_QUARTER_DEPENDENCY",
        "ttm_amount_is_algebraically_known": not bool(result.terms),
        "known_ttm_positive": bool(result.constant > 0) if not result.terms else None,
        "positive_denominator_still_unverified": bool(result.terms),
        "required_original_quarters": required,
        "latest_quarter_structure": [{"period_end": date.date().isoformat(), "fiscal_period": label,
                                      "amount_available_or_symbolic": amount is not None}
                                     for date, label, amount in recent],
    }


def normalize_raw(rows):
    rows = rows.loc[rows.metric.eq("revenue"), RAW_COLUMNS].copy()
    for field in ("period_end", "available_date"):
        rows[field] = pd.to_datetime(rows[field], errors="raise")
    rows = rows.loc[rows.available_date.le(pd.Timestamp(RAW_END))].copy()
    rows["value"] = pd.to_numeric(rows.value, errors="raise")
    if np.isinf(rows.value.to_numpy(float)).any():
        raise ValueError("Nonfinite non-null raw amount")
    keys = ["asset_id", "period_end", "fiscal_period", "available_date", "revision_key"]
    duplicate = rows.assign(cfs=rows.fs_type.eq("CFS")).duplicated([*keys, "cfs"], keep=False)
    if duplicate.any():
        raise ValueError("Ambiguous equal-priority raw revisions; no silent deduplication")
    return rows.sort_values(["asset_id", "available_date", "revision_key", "period_end", "fiscal_period"])


def slot_audits(frame, rows, keys):
    """Inspect only required missing input slots, using their own trade date."""
    missing = frame.set_index(["asset_id", "ym"]).loc[list(keys)].reset_index()
    raw_by_asset = {int(asset): group.to_dict("records") for asset, group in rows.groupby("asset_id")}
    result = {}
    for asset, months in missing.groupby("asset_id", sort=True):
        records = raw_by_asset.get(int(asset), [])
        state, position, prior_signature, cached = {}, 0, None, None
        for month in months.sort_values("trade_date").itertuples(index=False):
            as_of = pd.Timestamp(month.trade_date)
            while position < len(records) and records[position]["available_date"] <= as_of:
                row = records[position]
                key = (pd.Timestamp(row["period_end"]), str(row["fiscal_period"]))
                if key not in state or fundamentals._priority(row) > fundamentals._priority(state[key]):
                    state[key] = row
                position += 1
            if position != prior_signature:
                cached = symbolic_ttm(state)
                prior_signature = position
            if cached is None:
                cached = symbolic_ttm(state)
            result[(int(asset), month.ym)] = {"asset_id": int(asset), "input_month": str(month.ym),
                "as_of_date": as_of.date().isoformat(), **cached}
    return result


def analyze(frame, raw_rows):
    frame = frame.loc[frame.ym.between(pd.Period("2015-01"), pd.Period(RAW_END[:7])), INPUT_COLUMNS].copy()
    if frame.duplicated(["asset_id", "ym"]).any():
        raise ValueError("Duplicate asset-month input key")
    frame = frame.sort_values(["asset_id", "ym"])
    rows = normalize_raw(raw_rows)
    scores = candidate.compute(frame)
    groups = frame.groupby("asset_id", sort=False)
    calendar_ok = frame.ym.eq(groups.ym.shift(12) + 12) & frame.ym.eq(groups.ym.shift(24) + 24)
    universe = frame.in_universe & frame.market_cap.notna() & frame.market_cap.gt(0) & frame.adj_close.notna() & frame.adj_close.gt(0)
    target = frame.loc[universe & frame.ym.between(pd.Period(START), pd.Period(END))].copy()
    indexed = frame.set_index(["asset_id", "ym"])
    values = indexed.revenue_ttm.to_dict()
    missing_keys = set()
    for row in target.itertuples():
        if not calendar_ok.loc[row.Index]:
            continue
        for lag in (0, 12, 24):
            key = (int(row.asset_id), row.ym - lag)
            if key in values and not np.isfinite(values[key]):
                missing_keys.add(key)
    audits = slot_audits(frame, rows, missing_keys) if missing_keys else {}
    monthly = []
    for month, group in target.groupby("ym", sort=True):
        base, possible, unknown_positive, repaired_ids = 0, 0, 0, []
        missing_patterns, blockers = Counter(), Counter()
        for row in group.itertuples():
            baseline = bool(np.isfinite(scores.loc[row.Index]))
            base += baseline
            can, conditional, pattern = bool(calendar_ok.loc[row.Index]), False, []
            if not can:
                blockers["EXACT_12_24_MONTH_CALENDAR_ALIGNMENT_MISSING"] += 1
            for lag in (0, 12, 24):
                key = (int(row.asset_id), row.ym - lag)
                value = values.get(key, np.nan)
                if np.isfinite(value):
                    if lag and value <= 0:
                        can = False
                        blockers[f"KNOWN_NONPOSITIVE_{lag}M_DENOMINATOR"] += 1
                    continue
                pattern.append(str(lag))
                slot = audits.get(key)
                if slot is None or not slot["repairable_structure"]:
                    can = False
                    blockers[f"UNREPAIRABLE_MISSING_{lag}M_INPUT"] += 1
                elif lag and slot.get("known_ttm_positive") is False:
                    can = False
                    blockers[f"KNOWN_NONPOSITIVE_RECONSTRUCTIBLE_{lag}M_DENOMINATOR"] += 1
                elif lag and slot.get("positive_denominator_still_unverified"):
                    conditional = True
            missing_patterns["+".join(pattern) or "NONE"] += 1
            possible += baseline or can
            if can and not baseline:
                repaired_ids.append(int(row.asset_id))
                unknown_positive += conditional
        monthly.append({"month": str(month), "universe_rows": len(group), "current_finite_signals": base,
            "current_coverage": base / len(group), "structural_upper_bound_signals": possible,
            "structural_upper_bound_coverage": possible / len(group),
            "newly_structurally_repairable_asset_ids": repaired_ids,
            "additional_signals_with_unverified_positive_denominator": unknown_positive,
            "missing_slot_pattern_counts_lags_months": dict(missing_patterns),
            "blocking_reason_counts_nonexclusive": dict(blockers)})
    source_2015 = rows.loc[rows.period_end.dt.year.eq(2015)]
    available_counts = source_2015.groupby(["fiscal_period", source_2015.available_date.dt.to_period("M")]).size()
    first = target.loc[target.ym.eq(pd.Period(START))]
    march_group = []
    for row in first.itertuples():
        key = (int(row.asset_id), pd.Period("2016-03"))
        slot = audits.get(key)
        if slot is not None:
            march_group.append(slot)
    return {
        "monthly": monthly,
        "summary": {
            "current_overall_coverage": sum(row["current_finite_signals"] for row in monthly) / len(target),
            "current_monthly_p10": float(np.quantile([row["current_coverage"] for row in monthly], .1)),
            "structural_upper_bound_overall_coverage": sum(row["structural_upper_bound_signals"] for row in monthly) / len(target),
            "structural_upper_bound_monthly_p10": float(np.quantile([row["structural_upper_bound_coverage"] for row in monthly], .1)),
            "minimum_monthly_coverage_p10": .3, "minimum_overall_coverage": .5,
            "structural_upper_bound_meets_both_thresholds": bool(
                sum(row["structural_upper_bound_signals"] for row in monthly) / len(target) >= .5
                and np.quantile([row["structural_upper_bound_coverage"] for row in monthly], .1) >= .3),
            "actual_backfill_verified": False, "candidate_input_gate_passed": False,
            "missing_input_slot_count": len(audits),
            "structurally_repairable_missing_input_slots": sum(slot["repairable_structure"] for slot in audits.values()),
            "first_structurally_possible_signal_month": next((row["month"] for row in monthly if row["structural_upper_bound_signals"]), None),
        },
        "march_2018_requires_march_2016_ttm": {
            "universe_rows": len(first),
            "missing_24m_slot_audits": march_group,
            "explanation": "Each 2016-03 cutoff is that asset's observed trade_date, not automatically March 31; FY evidence must already be available. Original quarter amounts/known-at must still be obtained.",
        },
        "repairable_input_slots": [audits[key] for key in sorted(audits) if audits[key]["repairable_structure"]],
        "unrepairable_slot_reasons": dict(Counter(slot["reason"] for slot in audits.values() if not slot["repairable_structure"])),
        "source_2015_available_date_distribution": [
            {"fiscal_period": label, "available_month": str(month), "revision_rows": int(count)}
            for (label, month), count in available_counts.items()],
        "source_2015_first_available_distribution": [
            {"first_available_month": str(month), "assets": int(count)}
            for month, count in source_2015.groupby("asset_id").available_date.min().dt.to_period("M").value_counts().sort_index().items()],
        "source_2015_period_end_counts": [
            {"period_end": date.date().isoformat(), "fiscal_period": label, "revision_rows": int(count)}
            for (date, label), count in source_2015.groupby(["period_end", "fiscal_period"]).size().items()],
    }


def run(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / "research" / "v2"):
        raise ValueError("Use a new output under research/v2")
    panel_path, raw_path = source / "panel.pkl", source / "certified-financial-rows.parquet"
    candidate_path = ROOT / "factors/candidates/sales_growth_acceleration_12m.py"
    if fundamentals.source_sha256() != EXPECTED_SOURCE_SHA or sha(candidate_path) != EXPECTED_CANDIDATE_SHA:
        raise ValueError("Frozen materializer or candidate definition changed")
    hashes = {str(path.relative_to(ROOT)): sha(path) for path in (panel_path, raw_path, candidate_path)}
    with panel_path.open("rb") as stream:
        panel = pickle.load(stream)
    frame = panel.monthly[INPUT_COLUMNS].copy()
    del panel
    rows = pd.read_parquet(raw_path, columns=RAW_COLUMNS, filters=[
        ("metric", "==", "revenue"), ("available_date", "<=", pd.Timestamp(RAW_END))])
    result = analyze(frame, rows)
    for path, digest in hashes.items():
        if sha(ROOT / path) != digest:
            raise ValueError("Frozen input changed during audit")
    artifact = {
        "schema_version": "original-2015-quarter-symbolic-input-upper-bound-v1",
        "completed_at": datetime.now(timezone.utc).isoformat(), "signal_start": START, "signal_end": END,
        "source_available_date_cutoff": RAW_END, "protected_input_hashes": hashes,
        "materializer_source_sha256": fundamentals.source_sha256(), "script_sha256": sha(__file__),
        "candidate": candidate.FACTOR.name, "input_columns": INPUT_COLUMNS,
        "full_panel_bytes_loaded_input_columns_only_inspected": True,
        "return_evaluations": 0, "oos_performance_inspections": 0, "database_queries": 0,
        "source_data_modified": False, "frozen_artifacts_modified": False, "imputed_financial_amounts": 0,
        "limitations": [
            "This is an optimistic structural upper bound, not a passed input gate or executed research.",
            "Every symbolic quarter requires original standalone value, compatible statement basis and historical availability proof by the target cutoff.",
            "Unknown rolling TTM denominators may be nonpositive; their positivity is not established.",
            "Quarter endpoints are inferred from then-known month-end fiscal years. Non-month-end schedules are not modeled; this is not universal fiscal-calendar certification.",
            "No 2014 or earlier quarters, missing annual reports, existing nulls, or later missing quarters are repaired.",
            "Only certified local ledger coverage is measured; no assertion of provider-wide historical absence.",
            "Potential financial overflow of hypothetical ratios is not evaluated because unknown amounts are never filled.",
        ], **result,
    }
    write_artifact(output, artifact)
    print(json.dumps(artifact["summary"], sort_keys=True), flush=True)
    return artifact


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run(args.source, args.output)


if __name__ == "__main__":
    main()
