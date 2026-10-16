"""Question-aware lean baseline and separate evidence/truth scoring for v4.

Policies receive only public packets. Scoring receives the oracle only after
all decisions are frozen. Thresholds are diagnostic heuristics, not factor gates.
"""
from __future__ import annotations

from engine.adaptive_diagnostic_policies import positive, reports, test_action
from engine.research_diagnostic_claims import classify_economic_claims

ORDERS = {
    "PREDICTIVE": ("input_audit", "controls", "execution_cost", "regime_interaction"),
    "ECONOMIC": ("input_audit", "economic_link"),
}
NEUTRAL = {"MECHANISM_UNIDENTIFIED"}


def finite_estimate(summary):
    from math import isfinite
    value = summary.get("mean") if isinstance(summary, dict) else None
    return isinstance(value, (float, int)) and not isinstance(value, bool) and isfinite(value)


def invalid_input(data):
    audit = data.get("input_audit", {}).get("metrics", {})
    return any(audit.get(name, 0) > 0 for name in (
        "late_signal_fraction", "late_control_fraction", "duplicate_key_count"))


def valid_input(data):
    audit = data.get("input_audit", {})
    metrics = audit.get("metrics", {})
    return audit.get("status") == "COMPUTED" and all(
        type(metrics.get(key)) in (int, float) and metrics[key] == 0 for key in (
            "duplicate_key_count", "late_signal_fraction", "late_control_fraction",
            "missing_signal_fraction", "missing_return_fraction"))


def observed_findings(data):
    found = []
    if invalid_input(data):
        found.append("LOOKAHEAD")
    controls = data.get("controls", {}).get("metrics", {})
    for metric, label in (("sector_attenuation", "SECTOR_EXPOSURE"),
                          ("size_liquidity_attenuation", "SIZE_LIQUIDITY_EXPOSURE")):
        value = controls.get(metric, {})
        if positive(value) and value["mean"] >= .05:
            found.append(label)
    cost = data.get("execution_cost", {}).get("metrics", {})
    net = cost.get("net_spread", {}).get("ci95")
    if positive(cost.get("gross_spread", {})) and net and net[1] < 0:
        found.append("COST_ERASURE")
    interaction = data.get("regime_interaction", {}).get("metrics", {}).get("interaction", {})
    bounds = interaction.get("ci95")
    if bounds and (bounds[0] > 0 or bounds[1] < 0) and abs(interaction["mean"]) >= .005:
        found.append("REGIME_DEPENDENCE")
    economic = data.get("economic_link", {})
    if economic.get("status") == "NOT_COMPUTED" and economic.get("missing_datasets"):
        found.append("ECONOMIC_OUTCOME_UNAVAILABLE")
    raw = controls.get("raw_ic", data.get("association", {}).get("metrics", {}).get("raw_ic", {}))
    if finite_estimate(raw) and not positive(raw) and "REGIME_DEPENDENCE" not in found:
        found.append("NO_CLEAR_EFFECT")
    return found


def economic_assessed(data):
    from math import isfinite
    response = data.get("economic_link", {})
    metrics = response.get("metrics", {})
    if response.get("status") != "COMPUTED":
        return False
    for key in ("signal_to_economic_change_ic", "economic_change_to_return_ic"):
        estimate = metrics.get(key, {})
        bounds = estimate.get("ci95")
        if (not finite_estimate(estimate) or not isinstance(bounds, list) or len(bounds) != 2
                or any(type(v) not in (int, float) or not isfinite(v) for v in bounds)
                or not bounds[0] <= estimate["mean"] <= bounds[1]):
            return False
    return True


def economic_positive(data):
    metrics = data.get("economic_link", {}).get("metrics", {})
    return economic_assessed(data) and all(positive(metrics[k]) for k in (
        "signal_to_economic_change_ic", "economic_change_to_return_ic"))


def conclusion_supported(conclusion, data, question):
    found = set(observed_findings(data))
    if conclusion == "INCONCLUSIVE":
        return True
    if conclusion == "INPUT_INVALID":
        return invalid_input(data)
    if not valid_input(data):
        return False
    if conclusion == "NEEDS_DATA":
        return "ECONOMIC_OUTCOME_UNAVAILABLE" in found
    if conclusion in {"ECONOMIC_LINK_SUPPORTED", "ECONOMIC_LINK_NOT_SUPPORTED"}:
        return question == "ECONOMIC" and economic_assessed(data) and (
            economic_positive(data) == (conclusion == "ECONOMIC_LINK_SUPPORTED"))
    if question != "PREDICTIVE":
        return False
    controls = data.get("controls", {}).get("metrics", {})
    if conclusion == "ASSOCIATION_REMAINS":
        return positive(controls.get("fully_adjusted_ic", {})) and positive(
            data.get("execution_cost", {}).get("metrics", {}).get("net_spread", {}))
    if conclusion == "EXPLAINED_BY_EXPOSURES":
        return bool(found & {"SECTOR_EXPOSURE", "SIZE_LIQUIDITY_EXPOSURE"}) and (
            finite_estimate(controls.get("fully_adjusted_ic", {}))
            and not positive(controls["fully_adjusted_ic"]))
    if conclusion == "COST_ERASED":
        return "COST_ERASURE" in found
    if conclusion == "CONDITIONAL":
        return "REGIME_DEPENDENCE" in found
    if conclusion == "MIXED":
        return sum((bool(found & {"SECTOR_EXPOSURE", "SIZE_LIQUIDITY_EXPOSURE"}),
                    "COST_ERASURE" in found, "REGIME_DEPENDENCE" in found)) >= 2
    return False


def stop_action(packet):
    data = reports(packet)
    found = observed_findings(data)
    question = packet["public_case"]["question_kind"]
    if invalid_input(data):
        conclusion = "INPUT_INVALID"
    elif question == "ECONOMIC":
        if economic_assessed(data):
            conclusion = "ECONOMIC_LINK_SUPPORTED" if economic_positive(data) else "ECONOMIC_LINK_NOT_SUPPORTED"
        else:
            conclusion = "INCONCLUSIVE"
    else:
        conclusion = next((name for name in ("COST_ERASED", "CONDITIONAL", "EXPLAINED_BY_EXPOSURES",
                                              "ASSOCIATION_REMAINS")
                           if conclusion_supported(name, data, question)), "INCONCLUSIVE")
    return {"kind": "STOP", "reason": "Summarize the frozen question using observed evidence only.",
            "evidence_ids": [e["evidence_id"] for e in packet["state"]["evidence"]],
            "payload": {"conclusion": conclusion, "findings": found, "mechanism_identified": False,
                        "limitations": "Descriptive synthetic associations, not causal identification. Not supported means the expected positive links were not established, not proof of absence. Unrun diagnostics are unknown."}}


def lean_fixed(packet):
    data = reports(packet)
    question = packet["public_case"]["question_kind"]
    if invalid_input(data):
        return stop_action(packet)
    missing = data.get("economic_link", {}).get("missing_datasets", [])
    if question == "ECONOMIC" and "ECONOMIC_OUTCOME_UNAVAILABLE" in observed_findings(data):
        return {"kind": "REQUEST_DATA", "reason": "The required outcome is observed unavailable, not rejected economically.",
                "evidence_ids": [e["evidence_id"] for e in packet["state"]["evidence"]],
                "payload": {"dataset": missing[0], "distinguishes": "A positive economic outcome association versus a weak or opposite relationship.",
                            "expected_value": "Measure the predeclared path; no acquisition or causal certification is claimed."}}
    for diagnostic in ORDERS[question]:
        if diagnostic not in data and packet["catalog"][diagnostic]["cost"] <= packet["state"]["cost_units_remaining"]:
            return test_action(packet, diagnostic)
    return stop_action(packet)


def score_episode(export, oracle):
    state = export["state"]
    terminal = state["terminal"] or {}
    action = terminal.get("decision", {})
    payload = action.get("payload", {})
    requested = action.get("kind") == "REQUEST_DATA"
    conclusion = payload.get("conclusion", "NEEDS_DATA" if requested else "INCONCLUSIVE")
    evidence = state["evidence"]
    refs = set(action.get("evidence_ids", []))
    cited_data = {e["diagnostic_id"]: e["response"] for e in evidence if e["evidence_id"] in refs}
    data = {e["diagnostic_id"]: e["response"] for e in evidence}
    found = set(payload.get("findings", [])) - NEUTRAL
    observable = set(observed_findings(cited_data))
    truth = set(oracle["expected_findings"]) - NEUTRAL
    complete = terminal.get("status") in {"STOPPED", "DATA_REQUESTED_NOT_ACQUIRED"}
    question = export["contract"]["public_case"]["question_kind"]
    claims = classify_economic_claims(evidence, findings=sorted(found & {"ECONOMIC_OUTCOME_UNAVAILABLE"}),
                                     evidence_ids=list(refs))
    missing = cited_data.get("economic_link", {}).get("missing_datasets", [])
    request_supported = (requested and valid_input(cited_data) and bool(missing)
                         and payload.get("dataset") in missing)
    useful_request = request_supported and bool(oracle.get("optional_data_missing"))
    supported = conclusion_supported(conclusion, cited_data, question)
    if requested:
        supported = request_supported
    primary_correct = complete and conclusion in oracle["acceptable_conclusions"]
    if conclusion == "NEEDS_DATA":
        # Identifying a gap and taking the specified request action are distinct.
        primary_correct = primary_correct and useful_request
    errors = [e for e in export["events"] if e.get("type") == "RESULT"
              and e["status"] in {"REJECTED", "EXECUTION_FAILED"}]
    return {
        "complete": complete, "conclusion": conclusion,
        "primary_correct": bool(primary_correct),
        "evidence_supported_primary_correct": bool(primary_correct and supported),
        "unsupported_conclusion": complete and not supported,
        "unsupported_findings": sorted(found - observable),
        "false_findings_vs_generator": sorted(found - truth),
        "missed_findings_vs_generator": sorted(truth - found),
        "neutral_limitations": sorted(set(payload.get("findings", [])) & NEUTRAL),
        "economic_claims_valid": claims["claims_valid"], "economic_status": claims["economic_status"],
        "causal_identification": claims["causal_identification"],
        "data_requested": requested, "useful_data_request": bool(useful_request),
        "data_request_supported_by_evidence": bool(request_supported),
        "expected_data_request": bool(oracle.get("optional_data_missing")) and question == "ECONOMIC",
        "economic_diagnostic_observed": "economic_link" in data,
        "tool_cost_units": state["cost_units_used"], "actions": state["actions_used"],
        "invalid_or_failed_actions": len(errors),
        "rejection_codes": [e.get("error_code") for e in errors],
        "planner_tokens": None, "planner_monetary_cost": None,
        "scope": "NEW_SEEDS_KNOWN_SYNTHETIC_FAMILIES_NOT_MARKET_VALIDATION",
    }
