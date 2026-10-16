"""Frozen reference policies and a grader for the synthetic smoke benchmark.

These are deliberately labelled scripted references, never LLM experiments.
The grader is separate from all planner inputs and handles abstention explicitly.
Thresholds are diagnostic heuristics for this development lab, not admissions.
"""
from __future__ import annotations

from engine.adaptive_research import FINDINGS

FIXED_ORDER = ("input_audit", "association", "controls", "execution_cost", "regime_interaction", "economic_link")


def reports(packet):
    return {e["diagnostic_id"]: e["response"] for e in packet["state"]["evidence"]}


def mean(summary):
    return summary.get("mean") if isinstance(summary, dict) else None


def positive(summary):
    bounds = summary.get("ci95") if isinstance(summary, dict) else None
    return bool(bounds and bounds[0] > 0)


def observed_findings(data):
    found = []
    audit = data.get("input_audit", {}).get("metrics", {})
    if audit.get("late_signal_fraction", 0) > 0:
        found.append("LOOKAHEAD")
    controls = data.get("controls", {}).get("metrics", {})
    for metric, label in (("sector_attenuation", "SECTOR_EXPOSURE"),
                          ("size_liquidity_attenuation", "SIZE_LIQUIDITY_EXPOSURE")):
        if positive(controls.get(metric, {})) and mean(controls[metric]) >= .05:
            found.append(label)
    cost = data.get("execution_cost", {}).get("metrics", {})
    net_bounds = cost.get("net_spread", {}).get("ci95")
    if positive(cost.get("gross_spread", {})) and net_bounds and net_bounds[1] < 0:
        found.append("COST_ERASURE")
    interaction = data.get("regime_interaction", {}).get("metrics", {}).get("interaction", {})
    bounds = interaction.get("ci95")
    if bounds and (bounds[0] > 0 or bounds[1] < 0) and abs(mean(interaction)) >= .005:
        found.append("REGIME_DEPENDENCE")
    if data.get("economic_link", {}).get("status") == "NOT_COMPUTED":
        found.append("MECHANISM_UNIDENTIFIED")
    association = data.get("association", {}).get("metrics", {})
    if association and not positive(association.get("raw_ic", {})) and "REGIME_DEPENDENCE" not in found:
        found.append("NO_CLEAR_EFFECT")
    return found


def stop_action(packet):
    data = reports(packet)
    found = observed_findings(data)
    controls = data.get("controls", {}).get("metrics", {})
    if "LOOKAHEAD" in found:
        conclusion = "INPUT_INVALID"
    elif "COST_ERASURE" in found:
        conclusion = "COST_ERASED"
    elif "REGIME_DEPENDENCE" in found:
        conclusion = "CONDITIONAL"
    elif any(f in found for f in ("SECTOR_EXPOSURE", "SIZE_LIQUIDITY_EXPOSURE")) and not positive(
            controls.get("fully_adjusted_ic", {})):
        conclusion = "EXPLAINED_BY_EXPOSURES"
    elif positive(controls.get("fully_adjusted_ic", {})) and positive(
            data.get("execution_cost", {}).get("metrics", {}).get("net_spread", {})):
        conclusion = "ASSOCIATION_REMAINS"
    else:
        conclusion = "INCONCLUSIVE"
    return {"kind": "STOP", "reason": "Summarize the observations within the fixed diagnostic budget.",
            "evidence_ids": [e["evidence_id"] for e in packet["state"]["evidence"]],
            "payload": {"conclusion": conclusion, "findings": found, "mechanism_identified": False,
                        "limitations": "Exploratory synthetic association only. Unrun diagnostics remain unknown; no causal proof or real-market approval."}}


def test_action(packet, test):
    contrasts = {
        "input_audit": ("properly timed measurement", "late or invalid input", "All inputs precede formation", "Some inputs follow formation"),
        "association": ("predictive association", "weak or no association", "A positive monthly relationship", "Uncertain or near-zero relationship"),
        "controls": ("incremental signal", "observed exposure explanation", "Relationship remains on the same controlled sample", "Relationship attenuates after controls"),
        "execution_cost": ("implementable spread", "cost-erased spread", "Positive net spread", "Gross spread is consumed by cost"),
        "regime_interaction": ("stable association", "state-dependent association", "Small direct interaction", "Material direct interaction with uncertainty"),
        "economic_link": ("economic path consistent", "unmeasured economic path", "Measurable outcome association", "Missing or inconclusive economic observations"),
    }
    first, second, a, b = contrasts[test]
    return {"kind": "TEST", "reason": f"Distinguish {first} from {second}.",
            "evidence_ids": [e["evidence_id"] for e in packet["state"]["evidence"]],
            "payload": {"diagnostic_id": test,
                        "rivals": [{"explanation": first, "expected_if_true": a},
                                   {"explanation": second, "expected_if_true": b}],
                        "changes_mind_if": b + "; interpret uncertainty and do not infer causality."}}


def fixed_reference(packet):
    """Competent frozen measurement -> association -> exposure -> cost checklist."""
    data = reports(packet)
    # A compulsory validity stop is shared; no baseline deliberately wastes
    # a full budget analyzing a signal already known to use future values.
    if "LOOKAHEAD" in observed_findings(data):
        return stop_action(packet)
    for test in FIXED_ORDER:
        if test not in data and packet["catalog"][test]["cost"] <= packet["state"]["cost_units_remaining"]:
            return test_action(packet, test)
    return stop_action(packet)


def adaptive_reference(packet):
    """Scripted reference, not autonomous LLM reasoning or learned policy."""
    data = reports(packet)
    found = observed_findings(data)
    if "LOOKAHEAD" in found:
        return stop_action(packet)
    candidates = []
    for required in ("input_audit", "association"):
        if required not in data:
            candidates = [required]
            break
    if not candidates:
        raw = data["association"]["metrics"]["raw_ic"]
        if not positive(raw) or abs(mean(raw)) < .10:
            candidates = ["regime_interaction", "controls", "execution_cost", "economic_link"]
        else:
            candidates = ["controls", "execution_cost", "regime_interaction", "economic_link"]
        controls = data.get("controls", {}).get("metrics", {})
        if (any(f in found for f in ("SECTOR_EXPOSURE", "SIZE_LIQUIDITY_EXPOSURE"))
                and controls and not positive(controls.get("fully_adjusted_ic", {}))):
            return stop_action(packet)
    for test in candidates:
        if test not in data and packet["catalog"][test]["cost"] <= packet["state"]["cost_units_remaining"]:
            return test_action(packet, test)
    return stop_action(packet)


def score_episode(export, oracle):
    """Score observed decisions against generating truth, not text eloquence.

    Primary conclusion correctness differs from optional mechanism diagnostic
    coverage. In finite samples a justified inconclusive answer may still miss
    the generating class, so report both, never just a single aggregate reward.
    """
    state = export["state"]
    terminal = state["terminal"] or {}
    action = terminal.get("decision", {})
    payload = action.get("payload", {})
    requested = action.get("kind") == "REQUEST_DATA"
    conclusion = payload.get("conclusion", "NEEDS_DATA" if requested else "INCONCLUSIVE")
    found = set(payload.get("findings", [])) & FINDINGS
    truth = set(oracle["expected_findings"])
    supported = found & truth
    false = found - truth
    complete = terminal.get("status") in {"STOPPED", "DATA_REQUESTED_NOT_ACQUIRED"}
    data = {e["diagnostic_id"]: e["response"] for e in state["evidence"]}
    valid_measurement = "input_audit" in data and "LOOKAHEAD" not in observed_findings(data)
    incremental = positive(data.get("controls", {}).get("metrics", {}).get("fully_adjusted_ic", {}))
    net_positive = positive(data.get("execution_cost", {}).get("metrics", {}).get("net_spread", {}))
    unsupported_normal = conclusion == "ASSOCIATION_REMAINS" and not (
        valid_measurement and incremental and net_positive)
    errors = [e for e in export["events"] if e.get("type") == "RESULT" and e["status"] in {
        "REJECTED", "EXECUTION_FAILED"}]
    useful_request = requested and oracle.get("optional_data_missing") and "economic" in payload.get("dataset", "").lower()
    return {"complete": complete, "conclusion": conclusion,
            "primary_conclusion_correct": complete and conclusion in oracle["acceptable_conclusions"],
            "true_findings": sorted(supported), "false_findings": sorted(false),
            "missed_findings": sorted(truth - found),
            "normal_effect_preserved": conclusion == "ASSOCIATION_REMAINS" if oracle["scenario"] in {"clean", "mechanism_missing"} else None,
            "correct_abstention": conclusion == "INCONCLUSIVE" if oracle["scenario"] == "weak" else None,
            "useful_data_request": bool(useful_request),
            "unsupported_normal_conclusion": unsupported_normal,
            "mechanism_overclaim": payload.get("mechanism_identified", False) is not False,
            "tool_cost_units": state["cost_units_used"], "actions": state["actions_used"],
            "invalid_or_failed_actions": len(errors),
            "planner_tokens": None, "planner_monetary_cost": None,
            "scope": "SYNTHETIC_SMOKE_NOT_GENERALIZATION_PROOF"}
