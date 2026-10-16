"""Synthetic software-contract checks; these are NOT financial findings."""
from __future__ import annotations

import copy
import json

import pytest

from engine.phenomenon_research import GraphStore, digest


NOW = "2026-10-02T12:00:00+09:00"
LATER = "2026-10-02T12:01:00+09:00"
ACTORS = {"researcher": ["researcher", "reviewer"], "executor": ["executor"],
          "reviewer": ["reviewer"], "strategist": ["strategist"], "curator": ["curator"]}
SCOPE = {"universe": "SYNTHETIC_FOUR_ROWS_NOT_KRX", "start": "2020-01-01T00:00:00+09:00", "end": "2020-01-31T23:59:59+09:00"}


def add(g, kind, payload, *, actor="researcher", role="researcher", **kw):
    return g.append_node(kind, payload, actor=actor, role=role, known_at=NOW, **kw)


def rows_fixture():
    return [{"row_id": str(i), "observation_at": "2020-01-30T15:30:00+09:00",
             "decision_at": "2020-01-31T16:00:00+09:00", "feature_known_at": "2020-01-31T15:30:00+09:00",
             "outcome_known_at": "2020-02-28T16:00:00+09:00", "x": i, "group": "A" if i < 2 else "B", "y": y}
            for i, y in enumerate([4.0, 6.0, 1.0, 3.0])]


def source_payload(rows, *, origin="SYNTHETIC", stage="EXPLORATORY", root="synthetic-root-one"):
    return {"source_ref": "fixture://explicitly-synthetic-not-market-data", "data_version": "synthetic-v1",
            "rows_sha256": digest(rows), "data_root_ids": [root], "columns": sorted(rows[0]),
            "field_roles": {"x": "FEATURE", "group": "FEATURE", "y": "OUTCOME"},
            "scope": SCOPE, "stage": stage, "origin": origin, "pit_policy": "VERIFIED", "readiness": "READY"}


def world(tmp_path, *, max_runs=2, origin="SYNTHETIC", row_changes=None):
    g = GraphStore(tmp_path / "graph", actors=ACTORS)
    question = add(g, "question", {"title": "Synthetic group contrast", "question": "Can the contract distinguish a group contrast from no contrast?"})
    hypotheses = [add(g, "hypothesis", {"question_id": question["id"], "statement": statement,
                                        "alternatives": ["The fixture has no group contrast", "The source contract is incorrect"]})
                  for statement in ["Synthetic A mean exceeds B", "Synthetic groups have equal means"]]
    prediction = add(g, "prediction", {"hypothesis_id": hypotheses[0]["id"], "statement": "A-B > 0", "observable": "Group mean difference",
                                        "assumptions": ["The fixture groups have the declared interpretation"]})
    rows = rows_fixture()
    if row_changes:
        row_changes(rows)
    source = add(g, "source", source_payload(rows, origin=origin), actor="curator", role="curator")
    study_payload = {"question_id": question["id"], "hypothesis_ids": [x["id"] for x in hypotheses],
                     "stage": "EXPLORATORY", "scope": SCOPE, "max_runs": max_runs, "max_rows": 12,
                     "allowed_pit_policies": ["VERIFIED"]}
    study = g.register_study(study_payload, actor="researcher", known_at=NOW)
    plan_payload = {"study_id": study["id"], "prediction_id": prediction["id"], "source_id": source["id"],
                    "operator": "mean_difference", "stage": "EXPLORATORY", "row_budget": 4, "priority": 3,
                    "discriminates": [x["id"] for x in hypotheses], "selection_reason": "Contrast separates two declared synthetic explanations",
                    "if_consistent": "Review scoped observation", "if_inconsistent": "Keep alternative explanation unresolved",
                    "parameters": {"value_field": "y", "group_field": "group", "groups": ["A", "B"],
                                   "threshold": 0.0, "direction": "ABOVE", "min_rows": 4}}
    plan = add(g, "test_plan", plan_payload)
    return dict(g=g, question=question, hypotheses=hypotheses, prediction=prediction, source=source, study=study,
                plan=plan, rows=rows, study_payload=study_payload, plan_payload=plan_payload)


def execute(w, plan=None, *, candidate_ids=None):
    g, plan = w["g"], plan or w["plan"]
    decision = g.choose_next_test(w["study"]["id"], candidate_ids or [plan["id"]], actor="researcher", known_at=NOW)
    assert decision["payload"]["chosen_plan_id"] == plan["id"]
    return g.execute_test(plan["id"], w["rows"], actor="executor", known_at=NOW)


def claim_payload(w, evidence):
    return {"statement": "In this synthetic fixture only, A has a higher mean than B", "conclusion_type": "ASSOCIATION", "hypothesis_id": w["hypotheses"][0]["id"],
            "scope": SCOPE, "limitations": ["Synthetic software check, not a market finding", "Group association is not causation"],
            "judgment": "SUPPORTED", "stage": "EXPLORATORY", "epistemic_status": "INDEPENDENT_REVIEWED",
            "empirical_use": "SOFTWARE_TEST_ONLY", "evidence_relations": [
                {"evidence_id": evidence["id"], "stance": "SUPPORTS", "reason": "Descriptive group contrast is positive"}]}


def reviewed(w):
    result = execute(w)
    claim = w["g"].review_claim(claim_payload(w, result["evidence"]), actor="reviewer", known_at=NOW)
    return result, claim


def strategy_payload():
    return {"name": "Synthetic monthly contract only", "purpose": "SOFTWARE_TEST_ONLY",
            "execution": {"rebalance": "MONTHLY", "signal_cutoff": "MONTH_END_AFTER_CLOSE", "fill": "NEXT_MONTH_FIRST_TRADABLE_OPEN",
                          "unavailable_price_rule": "Skip unavailable instruments", "corporate_action_policy": "Use certified adjusted execution label"},
            "costs": {"commission_bps": 5, "slippage_bps": 10, "tax_model": "Explicit dated tax schedule required by execution adapter"},
            "benchmarks": ["MARKET_TR", "UNIVERSE_EQUAL_WEIGHT"], "entry_rule": "Illustrative group A condition",
            "exit_rule": "Next monthly rebalance", "sizing_rule": "Illustrative equal weight", "risk_limits": "No leverage; fixture only",
            "validation_plan": "Software validation only; no market returns or publishing"}


def test_end_to_end_synthetic_is_executable_but_never_empirical_or_published(tmp_path):
    w = world(tmp_path)
    result, claim = reviewed(w)
    assert result["evidence"]["payload"]["result"]["effect"] == 3.0
    assert result["evidence"]["payload"]["result"]["statistical_confirmation"] is False
    snapshot = w["g"].snapshot([claim["id"]], as_of=NOW)
    strategy = w["g"].create_strategy(strategy_payload(), snapshot, actor="strategist", known_at=NOW)
    assert strategy["payload"]["publication_authorized"] is False
    assert strategy["payload"]["purpose"] == "SOFTWARE_TEST_ONLY"
    assert w["g"].validate()["statuses"][strategy["id"]] == "ACTIVE"
    reopened = GraphStore(tmp_path / "graph")
    assert reopened.get(claim["id"]) == claim
    assert reopened.validate_snapshot(snapshot, require_current=False) == snapshot


def test_hash_tampering_is_rejected(tmp_path):
    w = world(tmp_path)
    target = next((tmp_path / "graph/records").glob(f"*-{w['question']['id']}.json"))
    data = json.loads(target.read_bytes())
    data["payload"]["question"] = "Tampered question"
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="tampering"):
        w["g"].validate()


def test_actor_policy_cannot_be_replaced_and_role_is_checked(tmp_path):
    w = world(tmp_path)
    with pytest.raises(ValueError, match="policy differs"):
        GraphStore(tmp_path / "graph", actors={"attacker": ["curator"]})
    with pytest.raises(ValueError, match="authorized"):
        add(w["g"], "question", {"title": "x", "question": "x"}, actor="stranger")
    with pytest.raises(ValueError, match="Invalid role"):
        add(w["g"], "question", {"title": "x", "question": "x"}, actor="curator", role="curator")


def test_review_is_independent_and_cannot_use_only_arguments(tmp_path):
    w = world(tmp_path)
    result = execute(w)
    payload = claim_payload(w, result["evidence"])
    with pytest.raises(ValueError, match="independent"):
        w["g"].review_claim(payload, actor="researcher", known_at=NOW)
    payload["evidence_relations"] = []
    with pytest.raises(ValueError, match="observed evidence"):
        w["g"].review_claim(payload, actor="reviewer", known_at=NOW)


def test_proposed_argument_requires_all_premises_and_cannot_be_observed(tmp_path):
    w = world(tmp_path)
    payload = {"premise_ids": [w["hypotheses"][0]["id"]], "premise_mode": "all", "inference_type": "DEDUCTION",
               "conclusion": "Synthetic implication", "assumptions": ["Fixture semantics"], "warrant": "Conditional implication, not proof",
               "epistemic_status": "PROPOSED"}
    argument = add(w["g"], "argument", payload)
    assert argument["payload"]["epistemic_status"] == "PROPOSED"
    for update in ({"premise_mode": "any"}, {"epistemic_status": "OBSERVED"}, {"premise_ids": ["0" * 64]}):
        with pytest.raises(ValueError):
            add(w["g"], "argument", {**payload, **update})


def test_append_cannot_bypass_checked_evidence_or_claim_helpers(tmp_path):
    w = world(tmp_path)
    for kind in ["evidence", "test_run", "claim", "strategy"]:
        with pytest.raises(ValueError, match="checked helper"):
            add(w["g"], kind, {})


def test_exploratory_observation_cannot_become_confirmation_or_causal(tmp_path):
    w = world(tmp_path)
    result = execute(w)
    payload = claim_payload(w, result["evidence"])
    for update in ({"stage": "CONFIRMATION"}, {"conclusion_type": "CAUSAL"}, {"empirical_use": "DESCRIPTIVE_RESEARCH"}):
        with pytest.raises(ValueError):
            w["g"].review_claim({**payload, **update}, actor="reviewer", known_at=NOW)


def test_claim_cannot_generalize_beyond_observed_scope(tmp_path):
    w = world(tmp_path)
    result = execute(w)
    payload = claim_payload(w, result["evidence"])
    payload["scope"] = {**SCOPE, "universe": "ALL_KOREAN_STOCKS"}
    with pytest.raises(ValueError, match="scope"):
        w["g"].review_claim(payload, actor="reviewer", known_at=NOW)


def test_input_hash_context_and_market_known_at_are_checked(tmp_path):
    w = world(tmp_path)
    w["g"].choose_next_test(w["study"]["id"], [w["plan"]["id"]], actor="researcher", known_at=NOW)
    modified = copy.deepcopy(w["rows"])
    modified[0]["y"] = 999
    with pytest.raises(ValueError, match="SHA256"):
        w["g"].execute_test(w["plan"]["id"], modified, actor="executor", known_at=NOW)
    assert w["g"].validate()["node_count"] == 7


@pytest.mark.parametrize("field,value,match", [
    ("feature_known_at", "2020-02-02T00:00:00+09:00", "market-known"),
    ("outcome_known_at", "2030-02-01T00:00:00+09:00", "known_at ordering"),
    ("observation_at", "2019-01-01T00:00:00+09:00", "scope"),
])
def test_source_hash_does_not_override_pit_checks(tmp_path, field, value, match):
    w = world(tmp_path, row_changes=lambda rows: rows[0].update({field: value}))
    with pytest.raises(ValueError, match=match):
        execute(w)


def test_run_must_be_selected_once_and_budget_is_bounded(tmp_path):
    w = world(tmp_path, max_runs=1)
    with pytest.raises(ValueError, match="selected"):
        w["g"].execute_test(w["plan"]["id"], w["rows"], actor="executor", known_at=NOW)
    result = execute(w)
    assert result["remaining_runs"] == 0
    with pytest.raises(ValueError, match="budget exhausted"):
        w["g"].choose_next_test(w["study"]["id"], [], actor="researcher", known_at=NOW)
    with pytest.raises(ValueError, match="already run"):
        w["g"].execute_test(w["plan"]["id"], w["rows"], actor="executor", known_at=NOW)


def test_adaptive_priority_considers_all_candidates_and_prior_observations(tmp_path):
    w = world(tmp_path)
    payload = {**w["plan_payload"], "operator": "coverage", "priority": 5,
               "parameters": {"value_field": "x", "threshold": 0.9, "direction": "ABOVE", "min_rows": 4}}
    coverage = add(w["g"], "test_plan", payload)
    with pytest.raises(ValueError, match="All eligible"):
        w["g"].choose_next_test(w["study"]["id"], [w["plan"]["id"]], actor="researcher", known_at=NOW)
    result = execute(w, coverage, candidate_ids=[w["plan"]["id"], coverage["id"]])
    choice = w["g"].choose_next_test(w["study"]["id"], [w["plan"]["id"]], actor="researcher", known_at=NOW)
    assert choice["payload"]["prior_evidence_ids"] == [result["evidence"]["id"]]
    assert result["evidence"]["payload"]["result"]["effect"] == 1.0


def test_correlation_operator_uses_actual_input_rows(tmp_path):
    w = world(tmp_path)
    payload = {**w["plan_payload"], "operator": "correlation", "priority": 5,
               "parameters": {"x_field": "x", "y_field": "y", "threshold": 0, "direction": "BELOW", "min_rows": 4}}
    plan = add(w["g"], "test_plan", payload)
    result = execute(w, plan, candidate_ids=[w["plan"]["id"], plan["id"]])
    assert result["evidence"]["payload"]["result"]["effect"] == pytest.approx(-4 / 65 ** 0.5)
    payload["parameters"] = {**payload["parameters"], "x_field": "y", "y_field": "x"}
    with pytest.raises(ValueError, match="direction mismatch"):
        add(w["g"], "test_plan", payload)


def test_unknown_fields_or_arbitrary_code_operators_rejected(tmp_path):
    w = world(tmp_path)
    for change in ({"operator": "eval"}, {"parameters": {**w["plan_payload"]["parameters"], "value_field": "secret"}}):
        with pytest.raises(ValueError):
            add(w["g"], "test_plan", {**w["plan_payload"], **change})


def test_snapshot_includes_uncited_sibling_and_challenging_evidence(tmp_path):
    w = world(tmp_path)
    first, claim = reviewed(w)
    second_plan = add(w["g"], "test_plan", {**w["plan_payload"], "parameters": {**w["plan_payload"]["parameters"], "groups": ["B", "A"]}})
    second = execute(w, second_plan)
    snapshot = w["g"].snapshot([claim["id"]], as_of=NOW)
    assert second["evidence"]["id"] in snapshot["node_ids"]
    assert second["evidence"]["payload"]["result"]["directionally_consistent"] is False
    edge = w["g"].append_edge("challenges", second["evidence"]["id"], claim["id"], actor="reviewer", role="reviewer", known_at=NOW,
                             rationale="Opposite fixture ordering illustrates contradictory evidence retrieval")
    snapshot = w["g"].snapshot([claim["id"]], as_of=NOW)
    assert edge["id"] in snapshot["edge_ids"]
    assert snapshot["statuses"][claim["id"]] == "REVIEW_REQUIRED"
    with pytest.raises(ValueError, match="review-required"):
        w["g"].create_strategy(strategy_payload(), snapshot, actor="strategist", known_at=NOW)


def test_invalidation_propagates_source_to_run_claim_and_strategy(tmp_path):
    w = world(tmp_path)
    result, claim = reviewed(w)
    snapshot = w["g"].snapshot([claim["id"]], as_of=NOW)
    strategy = w["g"].create_strategy(strategy_payload(), snapshot, actor="strategist", known_at=NOW)
    before = w["g"].get(result["evidence"]["id"])
    w["g"].invalidate(w["source"]["id"], actor="curator", known_at=LATER, reason="Synthetic source deliberately invalidated")
    status = w["g"].validate()["statuses"]
    assert status[w["source"]["id"]] == "INVALIDATED"
    assert all(status[x] == "DEPENDENCY_BLOCKED" for x in [w["plan"]["id"], result["run"]["id"], result["evidence"]["id"], claim["id"], strategy["id"]])
    assert w["g"].get(before["id"]) == before


def test_supersession_retains_original_and_invalidates_dependents(tmp_path):
    w = world(tmp_path)
    result, claim = reviewed(w)
    replacement = add(w["g"], "source", {**source_payload(w["rows"]), "data_version": "corrected-v2"}, actor="curator", role="curator")
    w["g"].supersede(w["source"]["id"], replacement["id"], actor="curator", known_at=NOW, reason="Corrected source metadata")
    statuses = w["g"].validate()["statuses"]
    assert statuses[w["source"]["id"]] == "SUPERSEDED"
    assert statuses[claim["id"]] == "DEPENDENCY_BLOCKED"
    assert statuses[replacement["id"]] == "ACTIVE"


def test_stale_tampered_and_truncated_snapshots_rejected(tmp_path):
    w = world(tmp_path)
    _, claim = reviewed(w)
    snapshot = w["g"].snapshot([claim["id"]], as_of=NOW)
    tampered = copy.deepcopy(snapshot)
    tampered["statuses"][claim["id"]] = "MAGIC_APPROVED"
    with pytest.raises(ValueError, match="hash"):
        w["g"].validate_snapshot(tampered)
    add(w["g"], "question", {"title": "New context", "question": "A new question"})
    with pytest.raises(ValueError, match="Stale"):
        w["g"].validate_snapshot(snapshot)
    assert w["g"].validate_snapshot(snapshot, require_current=False) == snapshot
    # Kept snapshot detects removal of the anchored last record as well.
    graph_files = sorted((tmp_path / "graph/records").glob("*.json"))
    graph_files[-1].unlink()
    graph_files[-2].unlink()
    with pytest.raises(ValueError, match="anchor"):
        w["g"].validate_snapshot(snapshot, require_current=False)


def test_dependency_cycle_and_unsupported_evidence_inference_rejected(tmp_path):
    w = world(tmp_path)
    with pytest.raises(ValueError, match="cycle"):
        w["g"].append_edge("depends_on", w["question"]["id"], w["hypotheses"][0]["id"], actor="researcher", role="researcher", known_at=NOW, rationale="Invalid cycle")
    with pytest.raises(ValueError, match="Unsupported"):
        w["g"].append_edge("proves", w["hypotheses"][0]["id"], w["hypotheses"][1]["id"], actor="researcher", role="researcher", known_at=NOW, rationale="Language-only proof is not evidence")


def test_strategy_requires_monthly_fill_costs_benchmarks_and_not_synthetic_market_use(tmp_path):
    w = world(tmp_path)
    _, claim = reviewed(w)
    snapshot = w["g"].snapshot([claim["id"]], as_of=NOW)
    for change in ({"purpose": "PRODUCTION"}, {"purpose": "RESEARCH_ONLY"}, {"costs": {}}, {"benchmarks": ["KOSPI"]},
                   {"execution": {**strategy_payload()["execution"], "fill": "SAME_MONTH_END_CLOSE"}}):
        with pytest.raises(ValueError):
            w["g"].create_strategy({**strategy_payload(), **change}, snapshot, actor="strategist", known_at=NOW)


def test_missing_requirement_blocks_test_and_is_not_implicitly_satisfied(tmp_path):
    w = world(tmp_path)
    missing = add(w["g"], "data_requirement", {"question": "Need independent attention data", "discriminates": "Attention versus liquidity", "status": "OPEN"})
    plan = add(w["g"], "test_plan", {**w["plan_payload"], "requirement_ids": [missing["id"]]})
    assert w["g"].validate()["statuses"][plan["id"]] == "DEPENDENCY_BLOCKED"
    with pytest.raises(ValueError, match="blocked"):
        w["g"].execute_test(plan["id"], w["rows"], actor="executor", known_at=NOW)


def test_confirmation_contract_cannot_reuse_exposed_source_root(tmp_path):
    w = world(tmp_path)
    execute(w)
    source = add(w["g"], "source", source_payload(w["rows"], stage="CONFIRMATION"), actor="curator", role="curator")
    contract = {"protocol_sha256": "1" * 64, "holdout_manifest_sha256": "2" * 64, "exposure_ledger_sha256": "3" * 64,
                "registered_at": NOW, "prior_exposure_disclosed": True, "allowed_source_ids": [source["id"]]}
    with pytest.raises(ValueError, match="already exposed"):
        w["g"].register_study({**w["study_payload"], "stage": "CONFIRMATION", "confirmation_contract": contract}, actor="researcher", known_at=NOW)


def test_research_timestamp_and_timezone_must_be_explicit(tmp_path):
    w = world(tmp_path)
    for timestamp in ("2020-01-01T00:00:00+09:00", "2026-10-02T12:00:00"):
        with pytest.raises(ValueError):
            w["g"].append_node("question", {"title": "q", "question": "q"}, actor="researcher", role="researcher", known_at=timestamp)


def test_caller_mutation_does_not_change_immutable_graph(tmp_path):
    w = world(tmp_path)
    w["plan_payload"]["parameters"]["threshold"] = 1000
    loaded = w["g"].get(w["plan"]["id"])
    assert loaded["payload"]["parameters"]["threshold"] == 0
    assert w["g"].validate()["publication_authorized"] is False


def test_new_uncited_result_requires_review_and_old_claim_cannot_be_cherry_picked(tmp_path):
    w = world(tmp_path)
    first, claim = reviewed(w)
    second_plan = add(w["g"], "test_plan", {**w["plan_payload"], "parameters": {**w["plan_payload"]["parameters"], "groups": ["B", "A"]}})
    second = execute(w, second_plan)
    assert w["g"].validate()["statuses"][claim["id"]] == "REVIEW_REQUIRED"
    with pytest.raises(ValueError, match="all existing"):
        w["g"].review_claim(claim_payload(w, first["evidence"]), actor="reviewer", known_at=NOW)
    p = claim_payload(w, first["evidence"])
    p["judgment"] = "INSUFFICIENT"
    p["evidence_relations"].append({"evidence_id": second["evidence"]["id"], "stance": "CHALLENGES", "reason": "Fixture counterexample must not be hidden"})
    revised = w["g"].review_claim(p, actor="reviewer", known_at=NOW)
    assert w["g"].validate()["statuses"][revised["id"]] == "ACTIVE"


def test_evidence_must_match_hypothesis_context(tmp_path):
    w = world(tmp_path)
    result = execute(w)
    q = add(w["g"], "question", {"title": "Different question", "question": "Unrelated phenomenon?"})
    h = add(w["g"], "hypothesis", {"question_id": q["id"], "statement": "Unrelated hypothesis", "alternatives": ["Another explanation"]})
    p = {**claim_payload(w, result["evidence"]), "hypothesis_id": h["id"]}
    with pytest.raises(ValueError, match="does not test"):
        w["g"].review_claim(p, actor="reviewer", known_at=NOW)


def test_confirmation_alias_of_same_rows_is_not_new_holdout(tmp_path):
    w = world(tmp_path)
    execute(w)
    source = add(w["g"], "source", source_payload(w["rows"], stage="CONFIRMATION", root="renamed-root"), actor="curator", role="curator")
    contract = {"protocol_sha256": "1" * 64, "holdout_manifest_sha256": "2" * 64, "exposure_ledger_sha256": "3" * 64,
                "registered_at": NOW, "prior_exposure_disclosed": True, "allowed_source_ids": [source["id"]]}
    with pytest.raises(ValueError, match="already exposed"):
        w["g"].register_study({**w["study_payload"], "stage": "CONFIRMATION", "confirmation_contract": contract}, actor="researcher", known_at=NOW)


def test_predeclared_confirmation_executes_but_cannot_adapt_or_reopen_same_holdout(tmp_path):
    w = world(tmp_path)
    source = add(w["g"], "source", source_payload(w["rows"], stage="CONFIRMATION", root="new-unexposed-fixture"), actor="curator", role="curator")
    contract = {"protocol_sha256": "1" * 64, "holdout_manifest_sha256": "2" * 64, "exposure_ledger_sha256": "3" * 64,
                "registered_at": NOW, "prior_exposure_disclosed": True, "allowed_source_ids": [source["id"]]}
    study_payload = {**w["study_payload"], "stage": "CONFIRMATION", "confirmation_contract": contract}
    study = w["g"].register_study(study_payload, actor="researcher", known_at=NOW)
    plan_payload = {**w["plan_payload"], "study_id": study["id"], "source_id": source["id"], "stage": "CONFIRMATION"}
    plan = add(w["g"], "test_plan", plan_payload)
    w["g"].choose_next_test(study["id"], [plan["id"]], actor="researcher", known_at=NOW)
    result = w["g"].execute_test(plan["id"], w["rows"], actor="executor", known_at=NOW)
    p = {**claim_payload(w, result["evidence"]), "stage": "CONFIRMATION"}
    claim = w["g"].review_claim(p, actor="reviewer", known_at=NOW)
    assert claim["payload"]["stage"] == "CONFIRMATION"
    assert result["evidence"]["payload"]["result"]["statistical_confirmation"] is False
    with pytest.raises(ValueError, match="cannot adapt"):
        add(w["g"], "test_plan", {**plan_payload, "priority": 4})
    with pytest.raises(ValueError, match="already exposed"):
        w["g"].register_study(study_payload, actor="researcher", known_at=NOW)


def test_claim_evidence_cannot_be_replaced_by_external_json(tmp_path):
    w = world(tmp_path)
    result = execute(w)
    fake = copy.deepcopy(result["evidence"])
    fake["payload"]["result"]["effect"] = 9999
    # Returned dictionaries are copies. The store, not the caller, resolves IDs.
    assert w["g"].get(fake["id"])["payload"]["result"]["effect"] == 3
    fake["id"] = "f" * 64
    with pytest.raises(ValueError, match="Missing"):
        w["g"].review_claim(claim_payload(w, fake), actor="reviewer", known_at=NOW)


def test_missing_source_cannot_be_claimed_ready_by_an_edge(tmp_path):
    w = world(tmp_path)
    source = add(w["g"], "source", {**source_payload(w["rows"]), "readiness": "PENDING"}, actor="curator", role="curator")
    plan = add(w["g"], "test_plan", {**w["plan_payload"], "source_id": source["id"]})
    assert w["g"].validate()["statuses"][plan["id"]] == "DEPENDENCY_BLOCKED"
    with pytest.raises(ValueError, match="ready source"):
        add(w["g"], "data_requirement", {"question": "Can it be used?", "discriminates": "Alternative mechanisms", "status": "SATISFIED", "source_ids": [source["id"]]})


def test_budget_reserves_declared_rows_and_does_not_allow_oversized_input(tmp_path):
    w = world(tmp_path)
    short = add(w["g"], "test_plan", {**w["plan_payload"], "row_budget": 3, "priority": 5,
                                    "parameters": {**w["plan_payload"]["parameters"], "min_rows": 2}})
    w["g"].choose_next_test(w["study"]["id"], [w["plan"]["id"], short["id"]], actor="researcher", known_at=NOW)
    with pytest.raises(ValueError, match="row budget"):
        w["g"].execute_test(short["id"], w["rows"], actor="executor", known_at=NOW)


def test_graph_root_symlinks_are_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target)
    with pytest.raises(ValueError, match="Symlink"):
        GraphStore(alias, actors=ACTORS)


def test_packet_has_all_competitors_observations_budgets_and_explicit_nontruth_warning(tmp_path):
    w = world(tmp_path)
    initial = w["g"].packet(w["study"]["id"])
    assert len(initial["hypotheses"]) == 2
    assert initial["all_evidence"] == []
    assert initial["eligible_plan_ids"] == [w["plan"]["id"]]
    assert initial["remaining_runs"] == 2 and initial["remaining_rows"] == 12
    assert set(initial["allowed_actions"]) == {"REGISTER_TEST_PLAN", "CHOOSE_NEXT_TEST", "STOP_STUDY"}
    result = execute(w)
    packet = w["g"].packet(w["study"]["id"])
    assert packet["all_evidence"] == [result["evidence"]]
    assert packet["remaining_runs"] == 1 and packet["remaining_rows"] == 8
    assert "INDEPENDENT_REVIEW" in packet["allowed_actions"]
    assert "not facts" in packet["knowledge_warning"] and packet["publication_authorized"] is False


def test_stop_is_terminal_and_does_not_promote_results(tmp_path):
    w = world(tmp_path)
    w["g"].choose_next_test(w["study"]["id"], [w["plan"]["id"]], actor="researcher", known_at=NOW)
    stop = w["g"].stop_study(w["study"]["id"], actor="researcher", known_at=NOW, reason="Expected information value is too low", status="UNRESOLVED")
    packet = w["g"].packet(w["study"]["id"])
    assert packet["stop_decision"] == stop
    assert packet["remaining_runs"] == 2 and packet["eligible_plan_ids"] == []
    assert packet["allowed_actions"] == [] and packet["reviewed_scoped_claims"] == []
    with pytest.raises(ValueError, match="exhausted"):
        w["g"].choose_next_test(w["study"]["id"], [], actor="researcher", known_at=NOW)
    with pytest.raises(ValueError, match="blocked"):
        w["g"].execute_test(w["plan"]["id"], w["rows"], actor="executor", known_at=NOW)
    with pytest.raises(ValueError, match="Stopped"):
        add(w["g"], "test_plan", {**w["plan_payload"], "priority": 4})
    with pytest.raises(ValueError, match="already stopped"):
        w["g"].stop_study(w["study"]["id"], actor="researcher", known_at=NOW, reason="Attempt to reopen through another stop")


def test_stop_after_observations_preserves_review_path_and_evidence_context(tmp_path):
    w = world(tmp_path)
    result = execute(w)
    stop = w["g"].stop_study(w["study"]["id"], actor="researcher", known_at=NOW, reason="A descriptive result is ready for independent review", status="SUFFICIENT_FOR_REVIEW")
    assert stop["payload"]["evidence_ids"] == [result["evidence"]["id"]]
    packet = w["g"].packet(w["study"]["id"])
    assert packet["allowed_actions"] == ["INDEPENDENT_REVIEW"]
    claim = w["g"].review_claim(claim_payload(w, result["evidence"]), actor="reviewer", known_at=NOW)
    assert w["g"].get(claim["id"]) == claim


def test_packet_lists_open_requirements_without_hiding_existing_eligible_plan(tmp_path):
    w = world(tmp_path)
    requirement = add(w["g"], "data_requirement", {"question": "Need receipt-time validation", "discriminates": "True response versus timestamp artifact", "status": "OPEN"})
    blocked = add(w["g"], "test_plan", {**w["plan_payload"], "requirement_ids": [requirement["id"]]})
    packet = w["g"].packet(w["study"]["id"])
    assert packet["unresolved_requirement_ids"] == [requirement["id"]]
    assert packet["statuses"][blocked["id"]] == "DEPENDENCY_BLOCKED"
    assert packet["eligible_plan_ids"] == [w["plan"]["id"]]


def test_corrected_source_can_recover_after_explicit_review_without_erasing_invalid_evidence(tmp_path):
    w = world(tmp_path)
    first, old_claim = reviewed(w)
    w["g"].invalidate(w["source"]["id"], actor="curator", known_at=NOW, reason="Fixture source version was invalid")
    source = add(w["g"], "source", {**source_payload(w["rows"]), "data_version": "corrected-v2"}, actor="curator", role="curator")
    plan = add(w["g"], "test_plan", {**w["plan_payload"], "source_id": source["id"]})
    second = execute(w, plan)
    payload = claim_payload(w, second["evidence"])
    payload["evidence_relations"].append({"evidence_id": first["evidence"]["id"], "stance": "EXCLUDED_INVALID",
                                          "reason": "Curator invalidated its source; retained as an audit reference, not a premise"})
    claim = w["g"].review_claim(payload, actor="reviewer", known_at=NOW)
    snapshot = w["g"].snapshot([claim["id"]], as_of=NOW)
    assert first["evidence"]["id"] in snapshot["node_ids"]
    assert first["evidence"]["id"] not in snapshot["required_node_ids"]
    assert snapshot["statuses"][first["evidence"]["id"]] == "DEPENDENCY_BLOCKED"
    assert snapshot["statuses"][claim["id"]] == "ACTIVE"
    strategy = w["g"].create_strategy(strategy_payload(), snapshot, actor="strategist", known_at=NOW)
    assert w["g"].validate()["statuses"][strategy["id"]] == "ACTIVE"
    assert w["g"].get(old_claim["id"]) == old_claim


def test_inconvenient_valid_evidence_cannot_be_excluded_as_invalid(tmp_path):
    w = world(tmp_path)
    result = execute(w)
    payload = claim_payload(w, result["evidence"])
    payload["judgment"] = "INSUFFICIENT"
    payload["evidence_relations"][0]["stance"] = "EXCLUDED_INVALID"
    with pytest.raises(ValueError, match="inconvenient"):
        w["g"].review_claim(payload, actor="reviewer", known_at=NOW)


def test_claim_search_excludes_software_by_default_and_exposes_scoped_context_explicitly(tmp_path):
    w = world(tmp_path)
    result, claim = reviewed(w)
    assert w["g"].search_claims("synthetic", as_of=NOW)["results"] == []
    found = w["g"].search_claims("SYNTHETIC", as_of=NOW, include_synthetic=True)
    assert found["total_matches"] == 1
    hit = found["results"][0]
    assert hit["claim"] == claim and hit["scope"] == SCOPE
    assert hit["stage"] == "EXPLORATORY" and hit["empirical_use"] == "SOFTWARE_TEST_ONLY"
    assert hit["strategy_eligible"] is False and hit["software_strategy_eligible"] is True
    assert hit["pit_policies"] == ["VERIFIED"]
    assert result["evidence"]["id"] in hit["snapshot"]["node_ids"]
    assert hit["limitations"][:2] == claim["payload"]["limitations"]
    assert hit["snapshot"]["statuses"][claim["id"]] == "ACTIVE"
    assert w["g"].validate_snapshot(hit["snapshot"]) == hit["snapshot"]
    assert found["publication_authorized"] is False


def test_claim_search_observed_metadata_fixture_and_exact_universe_filter(tmp_path):
    # OBSERVED is simulated contract metadata here, NOT an empirical finding.
    w = world(tmp_path, origin="OBSERVED")
    result = execute(w)
    p = {**claim_payload(w, result["evidence"]), "empirical_use": "DESCRIPTIVE_RESEARCH"}
    claim = w["g"].review_claim(p, actor="reviewer", known_at=NOW)
    found = w["g"].search_claims("", as_of=NOW, universe=SCOPE["universe"])
    assert [hit["claim"]["id"] for hit in found["results"]] == [claim["id"]]
    assert w["g"].search_claims("", as_of=NOW, universe="DIFFERENT_EXACT_UNIVERSE")["results"] == []
    assert w["g"].search_claims("not_in_any_allowed_text_123", as_of=NOW)["results"] == []


def test_claim_search_respects_future_research_clock_and_invalidation(tmp_path):
    w = world(tmp_path)
    result = execute(w)
    claim = w["g"].review_claim(claim_payload(w, result["evidence"]), actor="reviewer", known_at=LATER)
    assert w["g"].search_claims("", as_of=NOW, include_synthetic=True)["results"] == []
    assert w["g"].search_claims("", as_of=LATER, include_synthetic=True)["results"][0]["claim"]["id"] == claim["id"]
    after = "2026-10-02T12:02:00+09:00"
    w["g"].invalidate(w["source"]["id"], actor="curator", known_at=after, reason="Future source invalidation")
    assert w["g"].search_claims("", as_of=after, include_synthetic=True)["results"] == []
    historical = w["g"].search_claims("", as_of=LATER, include_synthetic=True)["results"][0]
    with pytest.raises(ValueError, match="Stale"):
        w["g"].validate_snapshot(historical["snapshot"])


def test_claim_search_excludes_review_required_and_superseded_claims(tmp_path):
    w = world(tmp_path)
    first, claim = reviewed(w)
    replacement = w["g"].review_claim({**claim_payload(w, first["evidence"]), "statement": "Narrower synthetic conclusion"}, actor="reviewer", known_at=NOW)
    w["g"].supersede(claim["id"], replacement["id"], actor="curator", known_at=NOW, reason="Narrower reviewed wording")
    found = w["g"].search_claims("", as_of=NOW, include_synthetic=True)
    assert [hit["claim"]["id"] for hit in found["results"]] == [replacement["id"]]
    second_plan = add(w["g"], "test_plan", {**w["plan_payload"], "parameters": {**w["plan_payload"]["parameters"], "groups": ["B", "A"]}})
    execute(w, second_plan)
    assert w["g"].search_claims("", as_of=NOW, include_synthetic=True)["results"] == []


def test_claim_search_keeps_counterevidence_and_does_not_hide_negative_judgments(tmp_path):
    w = world(tmp_path)
    first = execute(w)
    second_plan = add(w["g"], "test_plan", {**w["plan_payload"], "parameters": {**w["plan_payload"]["parameters"], "groups": ["B", "A"]}})
    second = execute(w, second_plan)
    challenge = w["g"].append_edge("challenges", second["evidence"]["id"], w["hypotheses"][0]["id"], actor="reviewer", role="reviewer", known_at=NOW,
                                  rationale="Fixture reverse contrast challenges the proposed direction")
    p = {**claim_payload(w, first["evidence"]), "judgment": "INSUFFICIENT"}
    p["evidence_relations"].append({"evidence_id": second["evidence"]["id"], "stance": "CHALLENGES", "reason": "Opposite fixture contrast must be visible"})
    claim = w["g"].review_claim(p, actor="reviewer", known_at=NOW)
    hit = w["g"].search_claims("group", as_of=NOW, include_synthetic=True)["results"][0]
    assert hit["claim"]["id"] == claim["id"] and hit["judgment"] == "INSUFFICIENT"
    assert hit["strategy_eligible"] is False
    assert second["evidence"]["id"] in hit["snapshot"]["node_ids"]
    assert challenge["id"] in hit["snapshot"]["edge_ids"]


def test_claim_search_reports_assumed_pit_as_limitation(tmp_path):
    w = world(tmp_path)
    source = add(w["g"], "source", {**source_payload(w["rows"]), "pit_policy": "PIT_ASSUMED"}, actor="curator", role="curator")
    study = w["g"].register_study({**w["study_payload"], "allowed_pit_policies": ["VERIFIED", "PIT_ASSUMED"]}, actor="researcher", known_at=NOW)
    plan = add(w["g"], "test_plan", {**w["plan_payload"], "study_id": study["id"], "source_id": source["id"]})
    altered = {**w, "study": study, "plan": plan, "source": source}
    reviewed(altered)
    hit = w["g"].search_claims("", as_of=NOW, include_synthetic=True)["results"][0]
    assert hit["pit_policies"] == ["PIT_ASSUMED"]
    assert any("not verified initial-release" in text for text in hit["limitations"])
    assert hit["source_prerequisites"][0]["pit_policy"] == "PIT_ASSUMED"


def test_claim_search_ranks_text_then_recency_never_larger_outcomes(tmp_path):
    high = world(tmp_path, row_changes=lambda rows: [row.update(y=row["y"] * 100) for row in rows])
    high_result, high_claim = reviewed(high)
    low = world(tmp_path)
    low_result = execute(low)
    low_claim = low["g"].review_claim(claim_payload(low, low_result["evidence"]), actor="reviewer", known_at=LATER)
    assert high_result["evidence"]["payload"]["result"]["effect"] > low_result["evidence"]["payload"]["result"]["effect"]
    found = low["g"].search_claims("synthetic group", as_of=LATER, include_synthetic=True, limit=1)
    assert found["total_matches"] == 2 and len(found["results"]) == 1
    assert found["results"][0]["claim"]["id"] == low_claim["id"]
    assert "NEVER_OUTCOME_PERFORMANCE" in found["ranking"]
    # The text-only scorer must not index numeric observations or arbitrary metadata.
    assert low["g"].search_claims("300.0", as_of=LATER, include_synthetic=True)["results"] == []


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": 51}, {"limit": True}, {"include_synthetic": 1}, {"universe": ""}])
def test_claim_search_rejects_invalid_bounds_and_options(tmp_path, kwargs):
    g = GraphStore(tmp_path / "graph", actors=ACTORS)
    with pytest.raises(ValueError):
        g.search_claims("", as_of=NOW, **kwargs)


def test_claim_search_no_archived_fallback_and_no_partial_counterevidence_context(tmp_path, monkeypatch):
    from engine import phenomenon_research as core
    empty = GraphStore(tmp_path / "empty", actors=ACTORS)
    assert empty.search_claims("", as_of=NOW)["results"] == []
    w = world(tmp_path)
    reviewed(w)
    monkeypatch.setattr(core, "MAX_SEARCH_CONTEXT_NODES", 1)
    with pytest.raises(ValueError, match="Complete retrieval context"):
        w["g"].search_claims("", as_of=NOW, include_synthetic=True)
    with pytest.raises(ValueError, match="2048"):
        w["g"].search_claims("x" * 2049, as_of=NOW)
    with pytest.raises(ValueError, match="32-token"):
        w["g"].search_claims(" ".join("token" + str(i) for i in range(33)), as_of=NOW)
