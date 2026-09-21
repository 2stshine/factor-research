"""Reuse already evaluated Discovery inputs for a diagnostic-only study.

No factor execution, DB access, OOS data access, or promotion decisions here.
Follow-ups are changes in *public PIT snapshots*, not latent firm fundamentals
or analyst surprises. Their missingness is part of the evidence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.gate import RESEARCH_START


def capture_discovery(panel, frame, factor, result, campaign, spec):
    from engine.mechanism_diagnostics import build_diagnostics
    from engine.regime_inputs import campaign_context, attach_macro_context

    if any(c.tier.startswith("T0") and c.passed is False for c in result.checks):
        return {"status": "NOT_COLLECTED", "reason": "SIGNAL_INTEGRITY_FAILED"}
    cutoff = pd.Timestamp(campaign["discovery"]["data_cutoff"]).normalize()
    oos_start = pd.Period(campaign["oos"]["start"], freq="M")
    if not frame.index.equals(panel.monthly.index):
        raise ValueError("Diagnostic frame and evaluated panel index differ")
    col = f"f_{factor.name}"
    if col not in frame or "fwd_mid" not in frame:
        return {"status": "NOT_COLLECTED", "reason": "EVALUATED_SIGNAL_OR_RETURN_UNAVAILABLE"}
    eligible = panel.investable.reindex(frame.index).fillna(False)
    months = pd.PeriodIndex(frame["ym"], freq="M")
    scope = (months >= RESEARCH_START) & (months < cutoff.to_period("M")) & (months < oos_start - 1)
    if "trade_date" in frame:
        scope &= pd.to_datetime(frame["trade_date"]).le(cutoff).to_numpy()
    # First scope the entire data source, BEFORE any forward joining.
    selected = list(dict.fromkeys([
        "asset_id", "ym", col, "fwd_mid", *factor.needs,
        "market", "market_cap", "adv20", "available_date",
        "net_income_ttm", "total_assets", "revenue_ttm",
    ]))
    base = frame.loc[scope, [c for c in selected if c in frame]].copy()
    base["ym"] = pd.PeriodIndex(base["ym"], freq="M")
    if base.duplicated(["asset_id", "ym"]).any():
        raise ValueError("Duplicate diagnostic asset-month")
    data = base.loc[eligible.reindex(base.index)].copy()
    # Existing certified forward labels are known by the frozen Discovery data
    # cutoff; use that conservative observation date, never invent a filing date.
    data["fwd_mid__known_at"] = cutoff
    controls = [c for c in ("market",) if c in data]
    for source, target in (("market_cap", "log_market_cap"), ("adv20", "log_adv20")):
        if source in data:
            data[target] = np.log(pd.to_numeric(data[source], errors="coerce").where(data[source] > 0))
            controls.append(target)
    outcomes = []
    economic_notes = []
    if {"available_date", "total_assets", "net_income_ttm"}.issubset(base.columns):
        base["public_roa"] = base["net_income_ttm"] / base["total_assets"].where(base["total_assets"] > 0)
        future = base[["asset_id", "ym", "public_roa", "available_date"]].copy()
        future["outcome_month"] = future["ym"].astype(str)
        future["ym"] -= 12
        future = future.rename(columns={"public_roa": "future_public_roa", "available_date": "future_filing_date"})
        current = base.set_index(["asset_id", "ym"])["public_roa"]
        data["current_public_roa"] = pd.MultiIndex.from_frame(data[["asset_id", "ym"]]).map(current)
        data = data.merge(future, on=["asset_id", "ym"], how="left", validate="one_to_one")
        formation = data["ym"].dt.end_time
        future_filing = pd.to_datetime(data["future_filing_date"], errors="coerce")
        horizon_end = (data["ym"] + 12).dt.end_time
        fresh = future_filing.gt(formation) & future_filing.le(horizon_end) & horizon_end.le(cutoff)
        name = "public_roa_change_12m"
        data[name] = (data["future_public_roa"] - data["current_public_roa"]).where(fresh)
        data[f"{name}__known_at"] = horizon_end.where(fresh)
        outcomes.append(name)
        economic_notes.append("Public PIT ROA change at a fixed twelve-month horizon, not future fiscal-year earnings or expectations. Missing exits are not imputed.")
    # These inputs were fixed before any candidate evaluation. No latest-file
    # fallback, Bronze bypass, or reconstruction from candidate returns.
    regimes, macro_regimes, regime_input_status = campaign_context(campaign)
    diagnostics = build_diagnostics(
        data, signal=col, forward_return="fwd_mid", controls=controls,
        outcomes=outcomes, as_of=str(cutoff.date()), regimes=regimes,
    )
    regime_section = diagnostics["regime_comparison"]
    regime_section["data"]["input_status"] = regime_input_status
    if regime_input_status.get("pit_status") == "PIT_ASSUMED":
        regime_section["limitations"].append(
            "Historical regime inputs include explicitly accepted PIT assumptions, not verified "
            "first-release vintages. This diagnostic does not change factor promotion criteria.")
    attach_macro_context(regime_section, macro_regimes,
                         diagnostics["monthly_performance"]["data"]["monthly"])
    if "input_contract_sha256" in regime_input_status:
        regime_section["data"]["classification_rules"].append({
            "version": "regime-input-contract-v1",
            "sha256": regime_input_status["input_contract_sha256"],
        })
    raw_inputs = []
    for column in factor.needs:
        if column not in data:
            raw_inputs.append({"name": column, "status": "NOT_COLLECTED"})
            continue
        numeric = pd.to_numeric(data[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        raw_inputs.append({"name": column, "n_present": int(numeric.notna().sum()),
                           "n_missing_or_nonnumeric": int(numeric.isna().sum()),
                           "n_zero": int(numeric.eq(0).sum()),
                           "quantiles": {str(q): float(numeric.quantile(q)) if numeric.notna().any() else None
                                         for q in (.01, .5, .99)}})
    quality = diagnostics["input_quality"]
    quality["data"]["raw_input_profile"] = raw_inputs
    if "available_date" in data:
        age = (data["ym"].dt.end_time - pd.to_datetime(data["available_date"], errors="coerce")).dt.days
        quality["data"]["filing_age_days"] = {
            "n_known": int(age.notna().sum()), "n_future_input_dates": int(age.lt(0).sum()),
            "median": float(age.median()) if age.notna().any() else None,
        }
        if age.lt(0).any():
            raise ValueError("Diagnostic financial input published after formation")
    quality["limitations"].append("Raw input distributions cover factor-declared columns only; filing age is snapshot-level, not per-account audit.")
    return {
        "status": "COLLECTED", "schema_version": "mechanism-study-v1",
        "campaign_id": campaign["campaign_id"],
        "phase": "discovery", "analysis_origin": "FIXED_DESCRIPTIVE_PROTOCOL",
        "definition_hash": factor.definition_hash,
        "strategy_sha256": spec.get("strategy_sha256"),
        "data_cutoff": str(cutoff.date()),
        "snapshot_digest": campaign.get("snapshot", {}).get("discovery_input_digest"),
        "asset_identity_digest": campaign.get("snapshot", {}).get("discovery_asset_identity_digest"),
        "oos_start": str(oos_start),
        "sample": "frozen_discovery_investable; no OOS/embargo",
        "signal_orientation": "already_signed_by_predicted_sign",
        "return_contract": "existing fwd_mid, including configured terminal scenario",
        "controls": controls, "outcomes": outcomes,
        "economic_outcome_notes": economic_notes,
        "sections": diagnostics,
        "limitations": [
            "All comparisons are observational, not causal identification.",
            "Financial follow-ups can be selection-biased when firms disappear; report missingness.",
            "No point-in-time industry classification, consensus surprises, event returns or costs are fabricated.",
            "Monthly reformed group returns are diagnostics, not the candidate's implemented holding strategy.",
        ],
    }
