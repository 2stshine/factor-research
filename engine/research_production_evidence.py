"""Project an already evaluated Discovery into general v2 evidence capabilities.

This is a trusted-host, no-I/O adapter. It never executes a factor, changes the
gate sample, reconstructs a portfolio, reads another result, or enters OOS.
Additional outcomes must be part of the preregistered diagnostic plan. Missing
connections are not proof that the organisation does not own the source data.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
import re

import numpy as np
import pandas as pd

from engine import research_policy
from engine.fundamentals import PIT_FEATURES
from engine.input_profiles import COMMON_MARKET_FIELDS, build_input_profiles
from engine.research_real_diagnostics import make_real_contract


VERSION = "production-discovery-evidence-v1"
PLAN_VERSION = "production-diagnostic-plan-v1"
MANDATORY = ("input_audit", "association", "controls", "regime_interaction")
_FIELD = re.compile(r"^[a-z][a-z0-9_]*$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _field(value):
    if (not isinstance(value, str) or not _FIELD.fullmatch(value)
            or value.startswith(("f_", "fwd_"))
            or value in research_policy.CANDIDATE_LABEL_COLUMNS
            or value in research_policy.UNCERTIFIED_PIT_FEATURE_COLUMNS):
        raise ValueError("Diagnostic source must be an explicit non-label field")
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing {name}")
    return value


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"Invalid {name}")
    return value


def validate_diagnostic_plan(plan=None):
    """Normalize a plan BEFORE registration; do not derive it from performance.

    Economic measurements are future LEVEL or CHANGE of one certified Silver
    financial field, optionally divided by a positive second field. This narrow
    grammar avoids arbitrary code and an automatic ROA proxy for every thesis.
    Other data can be requested, but are reported unconnected until a certified
    adapter exists. Industry requires an explicit historical availability and
    source-evidence contract; merely finding a current industry column is not it.
    """
    raw = {} if plan is None else deepcopy(plan)
    if not isinstance(raw, dict):
        raise ValueError("diagnostic_plan must be a mapping")
    allowed = {"schema_version", "question", "question_kind", "economic_outcome",
               "industry_control", "input_history", "execution_cost", "macro_axes", "macro_contrasts", "ratio_controls"}
    if set(raw) - allowed:
        raise ValueError(f"Unknown diagnostic plan fields: {sorted(set(raw) - allowed)}")
    if raw.get("schema_version", PLAN_VERSION) != PLAN_VERSION:
        raise ValueError("Unsupported diagnostic plan version")
    normalized = {"schema_version": PLAN_VERSION,
        "question_kind": raw.get("question_kind", "EXPLANATORY"),
        "question": raw.get("question", "Distinguish competing explanations for the fixed factor; preserve unsupported claims and missing evidence."),
        "economic_outcome": raw.get("economic_outcome"),
        "industry_control": raw.get("industry_control"),
        "input_history": raw.get("input_history", {}),
        "execution_cost": raw.get("execution_cost", False),
        "macro_axes": raw.get("macro_axes", []), "macro_contrasts": raw.get("macro_contrasts", {}),
        "ratio_controls": raw.get("ratio_controls", [])}
    if normalized["question_kind"] not in {"PREDICTIVE", "ECONOMIC", "EXPLANATORY"}:
        raise ValueError("Invalid diagnostic question kind")
    _text(normalized["question"], "diagnostic question")
    if type(normalized["execution_cost"]) is not bool:
        raise ValueError("execution_cost must be an explicit boolean")
    axes = normalized["macro_axes"]
    if (not isinstance(axes, list) or len(axes) > 2
            or not all(isinstance(x, str) and x for x in axes) or len(axes) != len(set(axes))):
        raise ValueError("At most two unique macro axes may be preregistered")
    contrasts = normalized["macro_contrasts"]
    if not isinstance(contrasts, dict) or set(contrasts) != set(axes):
        raise ValueError("Every declared macro axis requires a preregistered contrast")
    for contrast in contrasts.values():
        if (not isinstance(contrast, list) or len(contrast) != 2
                or not all(isinstance(x, str) and x and x != "UNKNOWN" for x in contrast)
                or contrast[0] == contrast[1]):
            raise ValueError("Macro contrast must contain two distinct known states")
    ratios = normalized["ratio_controls"]
    if not isinstance(ratios, list) or len(ratios) > 2:
        raise ValueError("At most two hypothesis-specific ratio controls may be preregistered")
    control_names = {"market", "size", "liquidity", "industry"}
    for control in ratios:
        if not isinstance(control, dict) or set(control) != {"name", "numerator", "denominator", "available_at"}:
            raise ValueError("Ratio controls need name, numerator, denominator and available_at")
        for value in control.values():
            _field(value)
        if control["name"] in control_names:
            raise ValueError("Duplicate or reserved control name")
        control_names.add(control["name"])
    economic = normalized["economic_outcome"]
    if economic is not None:
        required = {"numerator", "denominator", "available_at", "measurement_kind",
                    "horizon_months", "rationale", "dataset_id"}
        if not isinstance(economic, dict) or set(economic) != required:
            raise ValueError("Economic outcome needs the exact preregistered measurement contract")
        _field(economic["numerator"])
        if economic["denominator"] is not None:
            _field(economic["denominator"])
        _field(economic["available_at"])
        _integer(economic["horizon_months"], "economic horizon", 1)
        if economic["measurement_kind"] not in {"LEVEL", "CHANGE"}:
            raise ValueError("Economic measurement must be LEVEL or CHANGE")
        _text(economic["rationale"], "hypothesis-aligned outcome rationale")
        _text(economic["dataset_id"], "economic dataset identity")
    industry = normalized["industry_control"]
    if industry is not None:
        required = {"column", "known_at", "source_ref", "evidence_sha256", "pit_status"}
        if not isinstance(industry, dict) or set(industry) != required:
            raise ValueError("Industry requires an explicit source and PIT availability contract")
        _field(industry["column"])
        _field(industry["known_at"])
        _text(industry["source_ref"], "industry source")
        if (industry["pit_status"] != "VERIFIED" or not isinstance(industry["evidence_sha256"], str)
                or not _SHA.fullmatch(industry["evidence_sha256"])):
            raise ValueError("A verified historical industry evidence binding is required")
    histories = normalized["input_history"]
    if not isinstance(histories, dict):
        raise ValueError("input_history must be a mapping")
    for field, history in histories.items():
        _field(field)
        if not isinstance(history, dict) or set(history) != {"source_history_months", "source_ref"}:
            raise ValueError("Source history must declare months and provenance")
        _integer(history["source_history_months"], "source history")
        _text(history["source_ref"], "source history provenance")
    # Forbid NaN, callables and other opaque objects in the frozen plan.
    return json.loads(json.dumps(normalized, ensure_ascii=False, allow_nan=False))


def _numeric(series):
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def _dates(series):
    series = series.map(lambda x: None if isinstance(x, (int, float, np.number)) else x)
    value = pd.to_datetime(series, errors="coerce", format="mixed")
    if not pd.api.types.is_datetime64_dtype(value.dtype):
        raise ValueError("Use timezone-naive local calendar input timestamps")
    return value


def _definition(factor, spec):
    body = {"name": factor.name, "definition_hash": factor.definition_hash,
        "source": factor.source, "hypothesis": factor.hypothesis,
        "predicted_sign": factor.predicted_sign, "params": factor.params,
        "needs": list(factor.needs), "rebalance_months": factor.rebalance_months,
        "strategy_sha256": spec.get("strategy_sha256")}
    return {**body, "definition_sha256": _digest(body)}


def _history(source, formation, factor, plan):
    """Describe actual existing signal support, never select a better window."""
    lag = research_policy.assert_allowed_lookback(
        name=factor.name, source=factor.source, params=factor.params)
    fields = list(dict.fromkeys(factor.needs))
    # Price candidates can use common fields without listing them in needs.
    # Static mentions are evidence of a possible dependency, not runtime tracing.
    try:
        literals = {node.value for node in ast.walk(ast.parse(factor.source))
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    except SyntaxError:
        literals = set()
    fields.extend(sorted((literals & set(COMMON_MARKET_FIELDS)) - set(fields)))
    rows = []
    for name in fields:
        valid = _numeric(source[name]).notna() if name in source else pd.Series(False, index=source.index)
        availability = "EXISTING_FEATURE_POLICY_BOUND"
        if name in PIT_FEATURES:
            if "available_date" not in source:
                valid &= False
                availability = "NOT_CONNECTED_FINANCIAL_AVAILABILITY"
            else:
                known = _dates(source.available_date)
                valid &= known.notna() & known.le(source.ym.dt.end_time)
                availability = "SNAPSHOT_TIMESTAMP_CHECKED_NOT_PER_ACCOUNT_AUDIT"
        first = str(source.loc[valid, "ym"].min()) if valid.any() else None
        metadata = plan["input_history"].get(name)
        rows.append({"input_id": name, "column_present": name in source,
            "dependency_basis": "DECLARED_NEEDS" if name in factor.needs else "STATIC_COMMON_FIELD_REFERENCE",
            "first_finite_available_month": first, "availability": availability,
            "n_finite_available_rows": int(valid.sum()),
            "formula_max_lag_bound_months": lag,
            "source_history_months": metadata["source_history_months"] if metadata else None,
            "source_history_provenance": metadata["source_ref"] if metadata else None,
            "nominal_source_window_months": 12 if name.endswith("_ttm") and name in PIT_FEATURES else None,
            "first_formula_ready_calendar_estimate": str(pd.Period(first, freq="M") + lag) if first else None})
    signal = _numeric(formation[f"f_{factor.name}"])
    if set(factor.needs) & PIT_FEATURES:
        if "available_date" in formation:
            known = _dates(formation.available_date)
            signal = signal.where(known.notna() & known.le(formation.ym.dt.end_time))
        else:
            signal = signal.where(pd.Series(False, index=signal.index))
    return {"schema_version": "production-hypothesis-input-history-v1",
        "formula_max_lag_bound_months": lag,
        "policy_maximum_months": research_policy.MAX_FACTOR_LOOKBACK_MONTHS,
        "policy_maximum_is_not_required_warmup": True,
        "first_observed_usable_signal_month": str(formation.loc[signal.notna(), "ym"].min()) if signal.notna().any() else None,
        "n_observed_signal_months": int(formation.loc[signal.notna(), "ym"].nunique()),
        "baseline_evaluation_start": str(research_policy.COMMON_EVALUATION_START),
        "evaluation_start_modified": False, "candidate_recomputed": False,
        "runtime_dependencies_traced": False, "inputs": rows,
        "limitations": ["Global formula dependency bound is not an exact per-input offset or a count of valid observations.",
            "First-ready estimates do not check all calendar gaps, positive denominators, or surviving assets.",
            "Materialized TTM nominal coverage is not source-age or stale-filing certification; undeclared source history remains unknown."]}


def _economic(source, base, out, plan, cutoff):
    request = plan["economic_outcome"]
    if request is None:
        return None, {"status": "NOT_PREREGISTERED", "reason": "No hypothesis-specific outcome was declared; no automatic ROA proxy."}
    needed = {request["numerator"], request["available_at"]}
    if request["denominator"]:
        needed.add(request["denominator"])
    fields = needed - {request["available_at"]}
    if not fields <= PIT_FEATURES or request["available_at"] != "available_date":
        return None, {"status": "NOT_CONNECTED", "reason": "CERTIFIED_ECONOMIC_SOURCE_ADAPTER_REQUIRED",
                      "requested_fields": sorted(needed), "source_absence_established": False}
    missing = sorted(needed - set(source.columns))
    if missing:
        return None, {"status": "NOT_CONNECTED", "reason": "REQUESTED_FIELDS_NOT_IN_THIS_DISCOVERY_FRAME",
                      "missing_fields": missing, "source_absence_established": False}
    value = _numeric(source[request["numerator"]])
    if request["denominator"]:
        denominator = _numeric(source[request["denominator"]])
        value = value / denominator.where(denominator > 0)
    known = _dates(source[request["available_at"]])
    value = value.where(known.notna() & known.le(source.ym.dt.end_time))
    index = pd.MultiIndex.from_frame(source[["asset_id", "ym"]])
    values, knowns = pd.Series(value.to_numpy(), index=index), pd.Series(known.to_numpy(), index=index)
    current_keys = pd.MultiIndex.from_frame(base[["asset_id", "ym"]])
    future_keys = pd.MultiIndex.from_arrays([base.asset_id, base.ym + request["horizon_months"]])
    current = pd.Series(values.reindex(current_keys).to_numpy(), index=out.index)
    future = pd.Series(values.reindex(future_keys).to_numpy(), index=out.index)
    future_known = pd.Series(knowns.reindex(future_keys).to_numpy(), index=out.index)
    formation = pd.Series(pd.PeriodIndex(out.month, freq="M").end_time, index=out.index)
    horizon_end = pd.Series((pd.PeriodIndex(out.month, freq="M") + request["horizon_months"]).end_time, index=out.index)
    fresh = future_known.notna() & future_known.gt(formation) & future_known.le(horizon_end) & horizon_end.le(cutoff)
    measured = future if request["measurement_kind"] == "LEVEL" else future - current
    out["economic_outcome"] = measured.where(fresh)
    # The measurement observes the future public snapshot at the horizon, not
    # the filing instant alone. That snapshot cannot be known before its month.
    out["economic_known_at"] = horizon_end.where(fresh)
    contract = {"column": "economic_outcome", "known_at": "economic_known_at",
        "horizon_months": request["horizon_months"], "dataset_id": request["dataset_id"],
        "measurement_kind": request["measurement_kind"]}
    return contract, {"status": "CONNECTED", "n_usable_rows": int(out.economic_outcome.notna().sum()),
        "measurement": deepcopy(request), "source_absence_established": False,
        "limitations": ["Future public PIT snapshot measurement, not latent fundamentals, fiscal-year outcomes or expectations.",
            "Missing exits, stale filings, unsupported target months and nonpositive denominators are not imputed.",
            "Economic and one-month return horizons may differ; these associations do not establish mediation."]}


def _execution(out, artifact, *, definition, campaign, snapshot, start, end):
    if artifact is None:
        return None, {"status": "NOT_CONNECTED", "reason": "NO_SAME_WINDOW_HOLDINGS_RETURN_COST_ARTIFACT",
                      "source_absence_established": False,
                      "aggregate_gate_metrics_used_as_execution_evidence": False}
    binding = artifact.get("binding", {})
    expected = {"campaign_id": campaign["campaign_id"], "factor_definition_hash": definition["definition_sha256"],
                "snapshot_sha256": snapshot, "signal_start": start, "signal_end": end, "phase": "DISCOVERY"}
    if binding != expected:
        raise ValueError("Execution artifact is not bound to this exact Discovery definition and window")
    contract = deepcopy(artifact.get("contract", {}))
    for key, body_key in (("holdings_sha256", "holdings"), ("return_contract_sha256", "return_contract"),
                          ("cost_model_sha256", "cost_model")):
        if not artifact.get(body_key) or contract.get(key) != _digest(artifact[body_key]):
            raise ValueError("Execution artifact lacks hash-bound holdings/return/cost source evidence")
    rows = pd.DataFrame(artifact.get("monthly", []))
    metric_names = ("gross", "net", "cost", "turnover", "known_at")
    columns = [contract.get(name) for name in metric_names]
    if (rows.empty or "month" not in rows or any(not isinstance(x, str) or x not in rows for x in columns)
            or rows.month.duplicated().any()):
        raise ValueError("Execution artifact must contain unique explicitly measured monthly values")
    if not set(rows.month) <= set(out.month):
        raise ValueError("Execution measurements outside the Discovery signal window")
    holdings = pd.DataFrame(artifact["holdings"])
    if (not {"month", "asset_id", "weight"} <= set(holdings)
            or holdings.duplicated(["month", "asset_id"]).any()
            or set(holdings.month) != set(rows.month)):
        raise ValueError("Execution holdings keys do not match measurement months")
    weights = _numeric(holdings.weight)
    if weights.isna().any() or weights.lt(0).any() or not np.allclose(weights.groupby(holdings.month).sum(), 1):
        raise ValueError("Execution holdings must contain finite long-only fully-invested weights")
    source = rows.set_index("month")
    for name in metric_names:
        target = f"execution_{name}"
        out[target] = out.month.map(source[contract[name]])
        contract[name] = target
    return contract, {"status": "CONNECTED", "n_months": len(rows),
        "evidence_status": "CALLER_SUPPLIED_SAME_RUN_IDENTITIES_VALIDATED_NOT_REEXECUTED",
        "holdings_recomputed": False, "actual_fills_verified": False,
        "limitations": ["Identity/arithmetic binding is not independent portfolio execution or source authentication."]}


def _bind_captured_execution(raw, definition, campaign, snapshot, start, end):
    """Bind a gate-produced same-run measurement; never reconstruct it here."""
    expected = {"factor": definition["name"], "definition_hash": definition["definition_hash"],
        "phase": "DISCOVERY", "signal_start": start, "signal_end": end,
        "data_cutoff": campaign["discovery"]["data_cutoff"], "oos_start": campaign["oos"]["start"]}
    if (raw.get("schema_version") != "same-run-gate-portfolio-v1"
            or raw.get("source_binding") != expected
            or raw.get("timing_contract") != "ORIGINAL_MONTH_END_GATE_SIMULATION_NOT_NEXT_OPEN"):
        raise ValueError("Captured execution does not match same-run Discovery definition/boundaries")
    contract = {"gross": "gross", "net": "net", "cost": "cost", "turnover": "turnover", "known_at": "known_at",
        "holdings_sha256": _digest(raw["holdings"]), "return_contract_sha256": _digest(raw["return_contract"]),
        "cost_model_sha256": _digest(raw["cost_model"]), "timing_contract": raw["timing_contract"], "horizon_months": 1}
    body = {key: deepcopy(raw[key]) for key in ("holdings", "return_contract", "cost_model", "monthly")}
    return {**body, "binding": {"campaign_id": campaign["campaign_id"],
        "factor_definition_hash": definition["definition_sha256"], "snapshot_sha256": snapshot,
        "signal_start": start, "signal_end": end, "phase": "DISCOVERY"}, "contract": contract}


def prepare_discovery_evidence(panel, frame, factor, result, campaign, spec, *,
                               regime_projection=None, execution_artifact=None):
    """Return projected frames/contracts for an arbitrary already evaluated factor.

    ``regime_projection`` is a trusted callable(scoped_frame)->(frame, metadata).
    It may add frozen regime fields but cannot change primary data/row identity.
    Market and macro contracts are separate child labs; a KOSPI label is never
    silently used as a KOSDAQ classification. The caller persists these artifacts
    immutably and supplies the lab to the bounded agent session.
    """
    if any(check.tier.startswith("T0") and check.passed is False for check in result.checks):
        return {"status": "NOT_COLLECTED", "reason": "SIGNAL_INTEGRITY_FAILED"}
    if getattr(result, "factor", factor.name) != factor.name or getattr(result, "definition_hash", factor.definition_hash) != factor.definition_hash:
        raise ValueError("Result definition does not match the evaluated factor")
    if not frame.index.equals(panel.monthly.index):
        raise ValueError("Discovery frame and evaluated panel index differ")
    if not frame.index.is_unique or not frame.columns.is_unique:
        raise ValueError("Discovery frame requires unique row and column indices")
    required = {"asset_id", "ym", f"f_{factor.name}", "fwd_mid"}
    if not required <= set(frame):
        return {"status": "NOT_COLLECTED", "reason": "EVALUATED_SIGNAL_OR_RETURN_UNAVAILABLE"}
    plan = validate_diagnostic_plan(spec.get("diagnostic_plan"))
    definition = _definition(factor, spec)
    snapshot = campaign.get("snapshot", {}).get("discovery_input_digest")
    if not isinstance(snapshot, str) or not _SHA.fullmatch(snapshot):
        raise ValueError("A frozen Discovery snapshot identity is required")
    cutoff_date = pd.Timestamp(campaign["discovery"]["data_cutoff"])
    if cutoff_date.tz is not None or pd.isna(cutoff_date):
        raise ValueError("Discovery cutoff must be a local calendar date")
    cutoff = cutoff_date.normalize() + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    sealed = pd.Period(campaign["oos"]["start"], freq="M")
    end = pd.Period(campaign["discovery"].get("signal_end", cutoff_date.to_period("M") - 1), freq="M")
    if end >= cutoff_date.to_period("M") or cutoff >= sealed.start_time or end >= sealed - 1:
        raise ValueError("Invalid Discovery signal/return-support/sealed boundaries")
    months = pd.PeriodIndex(frame.ym, freq="M")
    scoped = (months >= research_policy.RESEARCH_INPUT_START) & (months <= end)
    if "trade_date" in frame:
        scoped &= _dates(frame.trade_date).le(cutoff).to_numpy()
    # Scope BEFORE any numeric conversion, financial forward join or projection.
    source = frame.loc[scoped].copy()
    source["ym"] = pd.PeriodIndex(source.ym, freq="M")
    if source.duplicated(["asset_id", "ym"]).any() or source.asset_id.isna().any():
        raise ValueError("Duplicate or missing Discovery asset-month identity")
    eligible = panel.investable.reindex(source.index).fillna(False).astype(bool)
    base = source.loc[eligible & source.ym.ge(research_policy.COMMON_EVALUATION_START)].copy()
    if base.empty:
        return {"status": "NOT_COLLECTED", "reason": "NO_ELIGIBLE_DISCOVERY_FORMATION_ROWS"}
    start = str(research_policy.COMMON_EVALUATION_START)
    out = pd.DataFrame({"month": base.ym.astype(str), "asset_id": base.asset_id,
        "signal": _numeric(base[f"f_{factor.name}"]), "forward_return": _numeric(base.fwd_mid),
        "return_known_at": cutoff}).reset_index(drop=True)
    controls, readiness = [], {}
    if "market" in base:
        out["market"] = base.market.to_numpy()
        controls.append({"name": "market", "column": "market", "kind": "categorical", "known_at": None})
    for raw, name, target in (("market_cap", "size", "log_market_cap"), ("adv20", "liquidity", "log_adv20")):
        if raw in base:
            values = _numeric(base[raw])
            out[target] = np.log(values.where(values > 0)).to_numpy()
            controls.append({"name": name, "column": target, "kind": "numeric", "known_at": None})
    readiness["controls"] = {"status": "CONNECTED" if controls else "NOT_CONNECTED",
        "connected": [c["name"] for c in controls], "source_absence_established": False}
    readiness["ratio_controls"] = {}
    for item in plan["ratio_controls"]:
        name = item["name"]
        fields = {item["numerator"], item["denominator"]}
        if not fields <= PIT_FEATURES or item["available_at"] != "available_date" or not (fields | {item["available_at"]}) <= set(base):
            readiness["ratio_controls"][name] = {"status": "NOT_CONNECTED",
                "reason": "CERTIFIED_SAME_FORMATION_FINANCIAL_INPUTS_NOT_CONNECTED", "source_absence_established": False}
            continue
        column, known_at = f"ratio_control_{name}", f"ratio_control_{name}_known_at"
        denominator = _numeric(base[item["denominator"]])
        out[column] = (_numeric(base[item["numerator"]]) / denominator.where(denominator > 0)).to_numpy()
        out[known_at] = _dates(base[item["available_at"]]).to_numpy()
        controls.append({"name": name, "column": column, "kind": "numeric", "known_at": known_at})
        readiness["ratio_controls"][name] = {"status": "CONNECTED", "measurement": item,
            "interpretation": "Observational rival-explanation control, not causal identification or factor construction."}
    signal_known_at = None
    if set(factor.needs) & PIT_FEATURES and "available_date" in base:
        signal_known_at = "signal_known_at"
        out[signal_known_at] = _dates(base.available_date).to_numpy()
    readiness["signal_availability"] = {"status": "TIMESTAMP_CONNECTED" if signal_known_at else "EXISTING_FEATURE_POLICY_BOUND",
        "financial_timestamp_connected": signal_known_at is not None,
        "per_account_or_first_release_certification": False}
    industry = plan["industry_control"]
    if industry and {industry["column"], industry["known_at"]} <= set(base):
        out["industry"] = base[industry["column"]].to_numpy()
        out["industry_known_at"] = _dates(base[industry["known_at"]]).to_numpy()
        controls.append({"name": "industry", "column": "industry", "kind": "categorical", "known_at": "industry_known_at"})
        readiness["industry"] = {"status": "CONNECTED", "contract": industry,
            "source_independently_reverified": False}
    else:
        readiness["industry"] = {"status": "NOT_CONNECTED" if industry else "NOT_PREREGISTERED",
            "reason": "No contracted historical industry data connected to this Discovery", "source_absence_established": False}
    economic, readiness["economic"] = _economic(source, base, out, plan, cutoff)
    captured_execution = getattr(result, "diagnostic_execution_artifact", None)
    used_same_run_capture = execution_artifact is None and captured_execution is not None
    if used_same_run_capture:
        execution_artifact = _bind_captured_execution(captured_execution, definition, campaign, snapshot, start, str(end))
    execution, readiness["execution"] = _execution(out, execution_artifact, definition=definition,
        campaign=campaign, snapshot=snapshot, start=start, end=str(end))
    if used_same_run_capture and execution is not None:
        readiness["execution"]["evidence_status"] = "SAME_RUN_GATE_SIMULATION_CAPTURE_NOT_NEXT_OPEN_FILLS"
    readiness["controls"]["connected"] = [c["name"] for c in controls]
    readiness["controls"]["status"] = "CONNECTED" if controls else "NOT_CONNECTED"
    required_diagnostics = list(MANDATORY)
    if plan["economic_outcome"] or plan["question_kind"] == "ECONOMIC":
        required_diagnostics.append("economic_link")
    if plan["execution_cost"]:
        required_diagnostics.append("execution_cost")
    evidence_binding = _digest({"snapshot": snapshot, "definition": definition, "diagnostic_plan": plan,
                              "discovery": campaign["discovery"], "sealed_start": str(sealed)})
    kwargs = dict(capability_id=f"{campaign['campaign_id']}:{factor.name}:discovery-v2",
        dataset_id=f"{campaign['campaign_id']}:authenticated-discovery",
        snapshot_sha256=snapshot, factor_definition_hash=definition["definition_sha256"],
        signal_start=start, signal_end=str(end), maturity_cutoff=str(cutoff_date.date()), sealed_start=str(sealed),
        columns={"month": "month", "asset_id": "asset_id", "signal": "signal", "signal_known_at": signal_known_at,
                 "forward_return": "forward_return", "return_known_at": "return_known_at"},
        controls=controls, feature_availability={"policy_id": "EXISTING_SILVER_FEATURE_LABEL_ROLE_CONTRACT",
            "status": "POLICY_BOUND", "evidence_sha256": evidence_binding},
        economic=economic, execution=execution, question_kind=plan["question_kind"], question=plan["question"])
    contract = make_real_contract(out, **kwargs)
    regime_labs, macro_labs = {}, {}
    if regime_projection is not None:
        projected, metadata = regime_projection(out.copy(deep=True))
        if len(projected) != len(out) or not projected[list(out.columns)].equals(out):
            raise ValueError("Regime projection modified primary Discovery evidence")
        for market, view in metadata.get("market_views", {}).items():
            positions = view["row_indices"]
            if not positions:
                continue
            regime = view["regime"]
            child = projected.iloc[positions][list(out.columns) + [regime["column"], regime["known_at"]]].reset_index(drop=True)
            if "market" not in child or not child.market.eq(market).all():
                raise ValueError("Market regime view crosses asset market boundaries")
            child_kwargs = {**kwargs, "capability_id": kwargs["capability_id"] + ":market:" + market}
            regime_labs[market] = {"frame": child, "contract": make_real_contract(child, regime=regime, **child_kwargs)}
        for axis, regime in metadata.get("macro_specs", {}).items():
            if axis not in plan["macro_axes"]:
                raise ValueError("Macro diagnostics were not preregistered")
            regime = {**regime, "contrast": plan["macro_contrasts"][axis]}
            child = projected[list(out.columns) + [regime["column"], regime["known_at"]]].copy()
            child_kwargs = {**kwargs, "capability_id": kwargs["capability_id"] + ":macro:" + axis}
            macro_labs[axis] = {"frame": child, "contract": make_real_contract(child, regime=regime, **child_kwargs)}
        readiness["regime"] = {"status": "CONNECTED" if regime_labs else "NOT_CONNECTED",
            "markets": list(regime_labs), "macro_axes": list(macro_labs),
            "missing_preregistered_macro_axes": sorted(set(plan["macro_axes"]) - set(macro_labs)),
            "metadata": {k: v for k, v in metadata.items() if k not in {"market_views", "macro_specs"}}}
    else:
        readiness["regime"] = {"status": "NOT_CONNECTED", "source_absence_established": False,
            "missing_preregistered_macro_axes": plan["macro_axes"]}
    return {"status": "PREPARED", "schema_version": VERSION, "frame": out, "contract": contract,
        "definition": definition, "diagnostic_plan": plan, "required_diagnostics": required_diagnostics,
        "regime_labs": regime_labs, "macro_labs": macro_labs, "readiness": readiness,
        "input_history": _history(source, base, factor, plan),
        "input_profiles": build_input_profiles(base, factor.needs,
            {c: t for c, t in (("market", "market"), ("market_cap", "log_market_cap"), ("adv20", "log_adv20")) if c in base}),
        "candidate_recomputed": False, "gate_decision_modified": False,
        "limitations": ["Discovery-only observational diagnostics, not new independent validation or factor approval.",
            "Financial source joins exclude return-support and sealed rows before calculation.",
            "Source availability, source ownership, historical vintage verification and adapter connection are distinct."]}
