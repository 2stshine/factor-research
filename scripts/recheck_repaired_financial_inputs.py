"""Same-candidate, label-free input check on an inactive repaired panel.

The old closed campaign supplies calendar boundaries, not an execution identity.
This creates no campaign, registration, return result, or publication authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine import factors, gate, panel, fundamental_contract, research_policy
from engine.research_memory_transfer import write_artifact
from scripts import run
from scripts.repair_fundamental_panel import file_sha

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "research/campaigns/v2-e2e-20261002-sales-acceleration"
SOURCE = ROOT / "factors/candidates/sales_growth_acceleration_12m.py"
_FIXED_CALENDAR = {"data_cutoff": "2023-07-31", "signal_end": "2023-06", "oos_start": "2023-08"}


def _validate_reference(manifest, prior):
    """Freeze the old calendar and T1.1 thresholds, never its new data digest."""
    current = {"data_cutoff": manifest["discovery"]["data_cutoff"],
               "signal_end": manifest["discovery"]["signal_end"], "oos_start": manifest["oos"]["start"]}
    evidence = prior["input_feasibility"]
    if (current != _FIXED_CALENDAR
            or prior["campaign_id"] != manifest["campaign_id"]
            or evidence["snapshot_digest"] != manifest["snapshot"]["discovery_input_digest"]
            or evidence["signal_start"] != str(gate.RESEARCH_START)
            or evidence["signal_end"] != current["signal_end"]
            or evidence["minimum_coverage"] != gate.TH["coverage"]
            or evidence["minimum_monthly_coverage_p10"] != gate.TH["monthly_coverage_p10"]
            or str(research_policy.RESEARCH_INPUT_START) != "2015-01"):
        raise ValueError("Reference calendar, input boundary, or coverage policy changed")


def _label_free_panel(repaired, manifest):
    """Select only input and unchanged universe fields; never compute labels."""
    columns = ["asset_id", "Code", "ym", "trade_date", "instrument_type", "market",
               "in_universe", "market_cap", "adj_close", "available_date", "revenue_ttm"]
    frame = repaired.monthly[columns]
    cutoff = pd.Timestamp(manifest["discovery"]["data_cutoff"]).normalize()
    oos_start = pd.Period(manifest["oos"]["start"], freq="M")
    scope = (pd.to_datetime(frame.trade_date).dt.normalize().le(cutoff) & frame.ym.lt(oos_start))
    bounded = frame.loc[scope].copy()
    if bounded.empty or pd.Timestamp(bounded.trade_date.max()).normalize() != cutoff:
        raise ValueError("Repaired input does not reproduce the fixed Discovery cutoff")
    frame = research_policy.research_input_frame(bounded)
    if frame.duplicated(["asset_id", "ym"]).any():
        raise ValueError("Repaired input contains duplicate asset/month keys")
    frame = frame.sort_values(["asset_id", "ym"], kind="mergesort").reset_index(drop=True)
    frame.attrs.clear()
    contract_key = (fundamental_contract.OVERLAY_META_KEY
                    if fundamental_contract.OVERLAY_META_KEY in repaired.meta else fundamental_contract.META_KEY)
    meta = {"schema_version": "label-free-repaired-candidate-input-v1",
            "financial_contract_sha256": repaired.meta[contract_key]["sha256"],
            "research_input_start": str(research_policy.RESEARCH_INPUT_START),
            "discovery_data_cutoff": str(cutoff.date()), "oos_start": str(oos_start)}
    # Dead membership and terminal-return labels are deliberately absent: this
    # diagnostic needs the exact existing Panel.universe rule, not return logic.
    return panel.Panel(frame, pd.Series(dtype="datetime64[ns]"), meta)


def check(panel_path, output):
    panel_path, output = Path(panel_path).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Refusing to overwrite a diagnostic receipt")
    manifest_path = CAMPAIGN / "manifest.json"
    prior_path = CAMPAIGN / "candidate-input-check-sales-growth-acceleration.json"
    protected = {str(path): file_sha(path) for path in (manifest_path, prior_path, SOURCE, panel_path)}
    manifest = json.loads(manifest_path.read_text())
    prior = json.loads(prior_path.read_text())
    if manifest["status"] != "CLOSED_ABORTED" or manifest["oos"]["status"] != "NOT_USED":
        raise ValueError("The fixed reference campaign must remain closed without OOS use")
    _validate_reference(manifest, prior)
    if file_sha(SOURCE) != prior["candidate_source_sha256"]:
        raise ValueError("Candidate source changed from the pre-repair input check")
    run.load_registry()
    candidate = factors.REGISTRY["sales_growth_acceleration_12m"]
    if candidate.definition_hash != prior["input_feasibility"]["factors"][0]["definition_hash"]:
        raise ValueError("Candidate definition changed")
    original_path = run.PANEL_CACHE
    try:
        run.PANEL_CACHE = panel_path
        repaired = run._load()
    finally:
        run.PANEL_CACHE = original_path
    financial_binding = fundamental_contract.verify(repaired, require_financial=True)
    # Exact prior dates, NEW input-only digest. The normal scoped-panel builder
    # calculates forward labels, so do not call it for this diagnostic.
    research = _label_free_panel(repaired, manifest)
    digest = panel.snapshot_digest(research)
    frame = research.monthly
    frame[f"f_{candidate.name}"] = research_policy.compute_factor(candidate, frame) * candidate.predicted_sign
    signal_end = pd.Period(manifest["discovery"]["signal_end"], freq="M")
    scope = (research.universe.reindex(frame.index).fillna(False)
             & frame.ym.ge(gate.RESEARCH_START) & frame.ym.le(signal_end))
    feasibility = run._candidate_input_feasibility([candidate], frame=frame, scope=scope,
        snapshot_digest=digest, signal_end=signal_end)
    monthly = []
    for month, group in frame.loc[scope, ["ym", "f_sales_growth_acceleration_12m"]].groupby("ym"):
        valid = np.isfinite(pd.to_numeric(group.iloc[:, 1], errors="coerce"))
        monthly.append({"month": str(month), "universe_rows": len(group),
                        "finite_signals": int(valid.sum()), "finite_coverage": float(valid.mean())})
    inputs = frame.loc[frame.ym.le(signal_end), ["ym", "revenue_ttm"]].copy()
    inputs["year"] = inputs.ym.dt.year
    yearly = [{"year": int(year), "panel_rows": len(group),
               "finite_revenue_ttm_rows": int(np.isfinite(pd.to_numeric(group.revenue_ttm, errors="coerce")).sum())}
              for year, group in inputs.groupby("year")]
    if protected != {name: file_sha(name) for name in protected}:
        raise ValueError("A protected input changed during the diagnostic")
    receipt = {
        "schema_version": "repaired-financial-input-recheck-v1",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "semantics": "New financial data version; same candidate and calendar; NOT an old-campaign replay or registration",
        "reference_campaign": manifest["campaign_id"], "protected_inputs_sha256": protected,
        "financial_contract": financial_binding,
        "reference_full_discovery_digest": manifest["snapshot"]["discovery_input_digest"],
        "new_label_free_input_digest": digest,
        "digest_comparison": "Different scopes: original full Discovery panel vs new input-only panel; not equality or a direct financial-change measure",
        "label_free_input_columns": [column for column in frame if not column.startswith("f_")],
        "universe_rule": "Unchanged Panel.universe: in_universe and positive nonmissing market_cap and adj_close; no extra liquidity restriction",
        "discovery_data_cutoff": manifest["discovery"]["data_cutoff"],
        "input_feasibility": feasibility, "monthly_input_coverage": monthly,
        "yearly_revenue_input_counts": yearly,
        "prior_input_feasibility": prior["input_feasibility"],
        "live_identity_checked_by_this_check": False,
        "registration_attempted": False, "registration_authorized": False,
        "default_cache_changed": False,
        "historical_backfill_applied": fundamental_contract.OVERLAY_META_KEY in repaired.meta,
        "full_panel_bytes_loaded_for_integrity_verification": True,
        "candidate_exposed_to_oos_rows": False,
        "forward_labels_recomputed": False,
        "return_evaluations": 0, "oos_performance_evaluations": 0,
        "oos_performance_inspections": 0, "gold_writes": 0,
        "disposition": ("INPUT_GATE_PASS_OTHER_GATES_NOT_RUN" if feasibility["status"] == "PASS"
                        else "INPUT_HISTORY_INSUFFICIENT_ECONOMIC_HYPOTHESIS_UNTESTED"),
    }
    write_artifact(output, receipt)
    print(json.dumps({"input_feasibility": feasibility, "disposition": receipt["disposition"],
                      "zero_signal_months": [row["month"] for row in monthly if not row["finite_signals"]]}, indent=2))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    check(args.panel, args.output)
