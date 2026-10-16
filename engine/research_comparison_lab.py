"""Versioned, question-aware synthetic comparison laboratory.

The original development lab is deliberately unchanged. Public metadata is
identical within each question kind. Only the grader may call ``oracle``; the
researcher receives numerical diagnostic reports, never generating labels.
This is logical separation, not an OS security boundary or a market backtest.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from engine.research_diagnostic_lab import DiagnosticLab, DIAGNOSTIC_CATALOG, _ar


VERSION = "question-aware-synthetic-comparison-lab-v1"
CATALOG = deepcopy(DIAGNOSTIC_CATALOG)
CATALOG["economic_link"]["description"] = (
    "Assess the hypothesized positive signal-to-economic-change and "
    "economic-change-to-return associations, or disclose missing outcome data; not causality."
)
SCENARIOS_BY_QUESTION = {
    "PREDICTIVE": (
        "clean", "lookahead", "sector_confounding", "exposure_confounding",
        "costs", "regime", "mixed", "weak",
    ),
    "ECONOMIC": (
        "economic_supported", "economic_null", "economic_missing", "economic_lookahead",
    ),
}


class ComparisonLab:
    """One anonymous case with frozen signal, horizon, costs and question."""

    def __init__(self, seed: int, scenario: str, question_kind: str):
        if question_kind not in SCENARIOS_BY_QUESTION:
            raise ValueError("unknown question_kind")
        if scenario not in SCENARIOS_BY_QUESTION[question_kind]:
            raise ValueError("scenario does not belong to question_kind")
        self._question_kind, self._scenario = question_kind, scenario
        base_scenario = scenario if question_kind == "PREDICTIVE" else (
            "lookahead" if scenario == "economic_lookahead" else "clean"
        )
        self._lab = DiagnosticLab(seed, base_scenario)
        self._seed = int(seed)
        if scenario == "economic_null":
            # Independent innovation stream; no signal, latent process, return,
            # sector, or control enters this economic outcome. Finite-sample
            # correlations are still possible and are measured, not hard-coded.
            rng = np.random.default_rng(np.random.SeedSequence([int(seed), 271828]))
            self._lab._economic_change = .06 * _ar(
                rng, (self._lab._n_months, self._lab._n_assets), .3
            )
        elif scenario == "economic_missing":
            self._lab._economic_change = None

    def public_case(self) -> dict[str, Any]:
        value = self._lab.public_case()
        value.update({
            "schema_version": VERSION,
            "question_kind": self._question_kind,
            "diagnostics": deepcopy(CATALOG),
            "report_status_contract": "AVAILABLE is explicitly translated to COMPUTED in this version only",
            "causal_identification_allowed": False,
            "shared_diagnostic_rubric": {
                "positive_association": "Descriptive ci95 lower bound > 0; not sequential significance or causal proof",
                "exposure_finding": "Corresponding raw-minus-controlled IC attenuation ci95 lower > 0 and mean >= 0.05",
                "cost_erasure": "Gross spread ci95 lower > 0 and net spread ci95 upper < 0",
                "regime_dependence": "Direct interaction ci95 excludes 0 and absolute mean >= 0.005",
                "no_clear_effect": "Observed raw_ic ci95 lower <= 0; no observed material regime interaction. Unestablished, not proof of zero",
                "economic_path_supported": "Both economic_link IC estimates have ci95 lower > 0",
                "economic_path_not_supported": "Both estimates observed but expected positive path not established; not a causal disproof",
                "primary_conclusions": {
                    "INPUT_INVALID": "Observed late signal/control inputs or duplicate keys",
                    "EXPLAINED_BY_EXPOSURES": "Valid audit; material exposure attenuation and positive fully-adjusted IC not established",
                    "COST_ERASED": "Valid audit and observed cost erasure",
                    "CONDITIONAL": "Valid audit and observed direct regime dependence",
                    "MIXED": "Valid audit; at least two of exposure explanation, cost erasure, regime dependence observed",
                    "INCONCLUSIVE": "Insufficient observations or uncertain association; distinguish unrun from absent",
                },
                "scope": "Shared predeclared synthetic diagnostic heuristics, not factor admission rules",
            },
        })
        if self._question_kind == "ECONOMIC":
            value.update({
                "question": (
                    "After checking formation-time input validity, do observations support "
                    "the specified positive signal -> next-period economic change -> return "
                    "association path, or is outcome data required to assess it?"
                ),
                "mechanism_question": (
                    "Both signal-to-economic-change and economic-change-to-return "
                    "associations are expected positive. This is an observational path "
                    "assessment, never causal identification. Failure of this path does "
                    "not disprove predictive return association."
                ),
                "primary_evidence_required": ["input_audit", "economic_link"],
                "execution_cost_required_for_primary_question": False,
                "economic_outcomes_are_labels_not_formation_features": True,
            })
        else:
            value["primary_evidence_required"] = ["input_audit", "controls", "execution_cost"]
            value["execution_cost_required_for_primary_question"] = True
        return value

    def run(self, diagnostic_id: str) -> dict[str, Any]:
        report = self._lab.run(diagnostic_id)
        if report["status"] == "AVAILABLE":
            report["status"] = "COMPUTED"
        report["report_contract_version"] = VERSION
        return report

    def oracle(self) -> dict[str, Any]:
        """Grader-only generating process; finite-sample detection not assured."""
        value = self._lab.oracle()
        value.update({"scenario": self._scenario, "question_kind": self._question_kind})
        if self._question_kind == "ECONOMIC":
            findings, conclusions, decision = {
                "economic_supported": ([], ["ECONOMIC_LINK_SUPPORTED"], "SUPPORTED"),
                "economic_null": ([], ["ECONOMIC_LINK_NOT_SUPPORTED"], "NOT_SUPPORTED"),
                "economic_missing": (["ECONOMIC_OUTCOME_UNAVAILABLE"], ["NEEDS_DATA"], "NEEDS_DATA"),
                "economic_lookahead": (["LOOKAHEAD"], ["INPUT_INVALID"], "INPUT_INVALID"),
            }[self._scenario]
            value.update({
                "expected_findings": findings, "acceptable_conclusions": conclusions,
                "expected_economic_decision": decision, "multiple_causes": False,
                "optional_data_missing": self._scenario == "economic_missing",
            })
        else:
            value["expected_economic_decision"] = "NOT_PRIMARY"
        return value
