"""Run the full new research/strategy path on explicit synthetic fixtures only.

Usage: python -m scripts.phenomenon_demo --output FRESH_DIRECTORY
No database, market download, legacy research, Gold publication or orders.
The independent reviewer is a separate scripted fixture actor, not an actual
LLM review or empirical finding. This is a persistent software integration test.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pandas as pd

from engine.phenomenon_research import GraphStore, canonical, digest
from engine import phenomenon_runtime as runtime
from engine import research_data_sources as discovery
from engine.phenomenon_inputs import import_discovery_snapshot, assert_source_bindings, load_source_rows
from strategies import monthly_execution


# Explicit future SOFTWARE clock: source validation records real current time;
# graph imports must not be backdated before it. Never used as a market clock.
NOW = "2030-10-02T12:00:00+09:00"
LATER = "2030-10-02T12:01:00+09:00"
UNIVERSE = "SYNTHETIC_TEN_ASSETS_NOT_KRX"
SCOPE = {"universe": UNIVERSE, "start": "2020-01-30T00:00:00+09:00",
         "end": "2020-01-30T23:59:59+09:00"}
ACTORS = {"demo_researcher": ["researcher", "reviewer"], "demo_executor": ["executor"],
          "demo_independent_reviewer": ["reviewer"], "demo_curator": ["curator"],
          "demo_strategist": ["strategist"]}


def _write(path: Path, value):
    with path.open("xb") as stream:
        stream.write(canonical(value) + b"\n")
    path.chmod(0o444)


def synthetic_research_rows():
    """A known group contrast and an intentionally incomplete explanatory proxy."""
    return [{"row_id": f"synthetic-{i}", "observation_at": "2020-01-30T15:30:00+09:00",
             "decision_at": "2020-01-31T23:59:59+09:00",
             "feature_known_at": "2020-01-31T16:00:00+09:00",
             "outcome_known_at": "2020-03-02T16:00:00+09:00",
             "group": "A" if i < 3 else "B", "attention_proxy": "NOT_OBSERVED" if i == 0 else float(i),
             "outcome": outcome}
            for i, outcome in enumerate([6.0, 5.0, 4.0, 1.0, 2.0, 3.0])]


def synthetic_execution_bundle():
    """Two artificial open-to-open windows; supplied dates are NOT a KRX calendar."""
    opens = {"2020-02": "2020-02-03T10:00:00+09:00", "2020-03": "2020-03-02T10:00:00+09:00",
             "2020-04": "2020-04-01T10:00:00+09:00"}
    measurements, assets, markets = [], [], []
    for month, entry_month, exit_month, cutoff in [
        ("2020-01", "2020-02", "2020-03", "2020-01-31T23:59:59+09:00"),
        ("2020-02", "2020-03", "2020-04", "2020-02-29T23:59:59+09:00"),
    ]:
        for asset in range(1, 11):
            measurements.append({"signal_month": month, "asset_id": asset, "eligible": True,
                                 "market_cap": float(100 + asset * 10), "available_at": cutoff,
                                 "reference_value": float(11 - asset if month == "2020-01" else asset)})
            assets.append({"signal_month": month, "asset_id": asset, "entry_at": opens[entry_month],
                           "exit_at": opens[exit_month], "entry_open": float(100 + asset),
                           "gross_total_return_multiplier": 1 + (asset - 5) / 1000,
                           "return_available_at": opens[exit_month]})
        markets.append({"signal_month": month, "entry_at": opens[entry_month], "exit_at": opens[exit_month],
                        "gross_total_return_multiplier": 1.002, "return_available_at": opens[exit_month]})
    bundle = {"origin": "SYNTHETIC", "reference": {
        "reference_id": "synthetic_direct_measurement_v1", "definition_sha256": digest({"formula": "fixture rank input"}),
        "role": "MEASUREMENT_ONLY_NO_ALPHA_APPROVAL", "provenance": "fixture://software-test-no-market-data",
        "origin": "SYNTHETIC"},
        "measurements": measurements, "sessions": [{"session_month": month, "open_at": stamp} for month, stamp in opens.items()],
        "asset_windows": assets, "market_windows": markets}
    bundle["evidence"] = {"schema_version": monthly_execution.EVIDENCE_SCHEMA,
                          "data_sha256": runtime.bundle_data_sha256(bundle), "as_of": NOW,
                          **{flag: True for flag in monthly_execution.EVIDENCE_FLAGS}}
    return bundle


def capture_synthetic_source(output, graph, question_id):
    """Exercise reviewed local capture, immutable validation and graph import.

    A categorical NOT_OBSERVED token is intentionally nonnumeric for coverage.
    Discovery requires declared variables to exist; it does not infer that a
    nonnumeric availability token is a valid numeric explanatory measurement.
    """
    raw_rows = [{**row, "observation_date": "2020-01-30"} for row in synthetic_research_rows()]
    raw_path = output / "research-rows.json"
    _write(raw_path, raw_rows)
    case = discovery.create_requirement(output / "discovery", {
        "requirement_id": "synthetic-group-measurement", "question_id": question_id,
        "research_question": "Validate synthetic group/outcome rows and explicit measurement availability",
        "discriminates": "Group association versus unsupported explanatory interpretation",
        "market": UNIVERSE, "frequency": "event", "start_date": "2020-01-30", "end_date": "2020-01-30",
        "variables": ["group", "attention_proxy", "outcome"], "numeric_variables": ["outcome"],
        "known_at_column": "feature_known_at", "entity_column": "row_id",
        "required_entities": [row["row_id"] for row in raw_rows], "expected_dates": ["2020-01-30"],
        "budget": {"searches": 1, "fetches": 1, "bytes": 100000, "elapsed_seconds": 120}})
    source_id = discovery.register_source(case, {
        "source_id": "synthetic-local-v1", "title": "Synthetic fixture, not public market evidence",
        "url": "https://example.com/synthetic-fixture-not-downloaded", "provenance_url": "https://example.com/synthetic-fixture-not-downloaded",
        "format": "json", "market": UNIVERSE, "frequency": "event", "pit_status": "verified",
        "pit_evidence": "Constructed fixture clock ordering only; no real historical PIT claim",
        "expected_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest()})
    review = {"reviewer": "demo_source_reviewer", "authorization_reference": "Software-test-owned fixture only",
              "license_reference": "Locally generated synthetic data", "public_download_permitted": True,
              "research_use_permitted": True, "pit_approved": True,
              "notes": "Permission covers exact local capture only; no network operation is invoked."}
    discovery.review_source(case, source_id, review)
    captured = discovery.capture_local(case, source_id, raw_path)
    validated = discovery.validate_artifact(case, captured["artifact_id"])
    if validated["status"] != "READY":
        raise ValueError(f"Synthetic discovery validation failed: {validated['errors']}")
    imported = import_discovery_snapshot(graph, case, validated["snapshot_id"], scope=SCOPE,
        field_roles={"group": "FEATURE", "attention_proxy": "FEATURE", "outcome": "OUTCOME"},
        origin="SYNTHETIC", stage="EXPLORATORY", actor="demo_curator", known_at=NOW)
    receipt = {"case_dir": str(case), "question_id": question_id, "source_id": source_id,
               "artifact_id": captured["artifact_id"], "snapshot_id": validated["snapshot_id"],
               "graph_source_id": imported["source"]["id"], "status": validated["status"],
               "method": captured["method"], "empirical_use": "SOFTWARE_TEST_ONLY", "network_accessed": False}
    _write(output / "data-intake-receipt.json", receipt)
    return imported, receipt, review


def synthetic_strategy_payload(bundle):
    ref = bundle["reference"]
    costs = {"buy_rate": .0015, "sell_rate": .0015, "sell_tax_by_year": {"2020": .002}}
    contract = {"schema": runtime.SCHEMA, "score_rule": {
        "kind": "DIRECT_REFERENCE", "field": "reference_value", "orientation": 1,
        "reference_id": ref["reference_id"], "definition_sha256": ref["definition_sha256"]},
        "variants": list(runtime.VARIANTS), "benchmarks": runtime.BENCHMARKS, "costs": costs,
        "initial_nav": 1.0, "scope": {"origin": "SYNTHETIC", "universe": UNIVERSE,
                                       "signal_months": ["2020-01", "2020-02"]},
        "execution": runtime.EXECUTION, "decision_clock": "CALENDAR_MONTH_END_23_59_59_ASIA_SEOUL",
        "historical_reuse_acknowledged": True, "source_artifacts": {name: digest(bundle[name]) for name in runtime.ARRAYS},
        "input_bundle_sha256": digest(bundle)}
    return {"name": "Synthetic knowledge-to-monthly-execution integration", "purpose": "SOFTWARE_TEST_ONLY",
            "execution": runtime.EXECUTION, "costs": {"commission_bps": 5, "slippage_bps": 10,
                "tax_model": "DATED_SELL_TAX_SCHEDULE", "sell_tax_by_year": costs["sell_tax_by_year"]},
            "benchmarks": runtime.BENCHMARKS, "entry_rule": "Use only the declared synthetic direct measurement",
            "exit_rule": "Rebalance at next supplied monthly open", "sizing_rule": "Run all four frozen variants; select no winner",
            "risk_limits": "No leverage; synthetic fixture only; no actual trading",
            "validation_plan": "Software contract test only; no alpha, causality or market confirmation",
            "runtime_contract": contract}


def synthetic_ridge_inputs():
    """Fixed train-only selection/PCA/ridge contract; no tuning or market data."""
    base = synthetic_execution_bundle()
    payload = deepcopy(synthetic_strategy_payload(base))
    bundle = deepcopy(base)
    names = ["synthetic_quality", "synthetic_size", "synthetic_duplicate"]
    features = [{"field": name, "reference_id": name + "_v1",
                 "definition_sha256": digest({"synthetic_definition": name})} for name in names]
    bundle["reference"] = {"features": features, "role": "MEASUREMENT_ONLY_NO_ALPHA_APPROVAL",
                           "origin": "SYNTHETIC", "provenance": "fixture://three-artificial-measurements-not-market-factors"}
    calendar = {row["session_month"]: row["open_at"] for row in bundle["sessions"]}
    for month in pd.period_range("2019-09", "2020-01", freq="M"):
        calendar[str(month)] = str(month) + "-03T10:00:00+09:00"
    bundle["sessions"] = [{"session_month": month, "open_at": calendar[month]} for month in sorted(calendar)]

    def row(month, index, asset, *, predict=False):
        cutoff = month.end_time.floor("s").tz_localize("Asia/Seoul").isoformat()
        quality = asset / 10 + index / 100
        size = (asset % 3 - 1) / 10 + index / 50
        record = {"signal_month": str(month), "asset_id": asset, "eligible": True, "available_at": cutoff,
                  "synthetic_quality": quality, "synthetic_size": size, "synthetic_duplicate": 2 * quality,
                  **{name + "__known_at": cutoff for name in names}}
        if predict:
            record["market_cap"] = float(100 + 10 * asset)
        return record

    history, labels = [], []
    for index, month in enumerate(pd.period_range("2019-08", "2019-12", freq="M")):
        for asset in range(1, 11):
            record = row(month, index, asset)
            history.append(record)
            labels.append({"signal_month": str(month), "asset_id": asset,
                           "entry_at": calendar[str(month + 1)], "exit_at": calendar[str(month + 2)],
                           "return_available_at": calendar[str(month + 2)],
                           "gross_total_return_multiplier": 1 + .01 * record["synthetic_quality"] - .005 * record["synthetic_size"]})
    bundle["training_features"], bundle["training_labels"] = history, labels
    bundle["measurements"] = [row(month, index + 5, asset, predict=True)
                              for index, month in enumerate(pd.period_range("2020-01", "2020-02", freq="M"))
                              for asset in range(1, 11)]
    bundle["evidence"]["data_sha256"] = runtime.bundle_data_sha256(bundle)
    rule = {"kind": "TRAIN_ONLY_RIDGE", "features": features, "alpha": 1.0, "pca_components": 1,
            "selection": {"method": "TRAIN_CORRELATION", "max_abs_correlation": .95,
                          "max_missing_fraction": .5, "min_variance": 0.0, "max_features": 2},
            "train_window_months": 24, "min_train_months": 2, "min_train_rows": 20,
            "purge_gap_months": 1, "max_feature_age_days": 400,
            "label_contract": "VERIFIED_NEXT_OPEN_TO_FOLLOWING_OPEN_GROSS_RETURN_MINUS_ONE"}
    payload["name"] = "Synthetic train-only selection, PCA and ridge monthly integration"
    payload["entry_rule"] = "Fixed train-only correlation selection and one-component PCA/ridge predictions"
    payload["runtime_contract"].update({"score_rule": rule, "input_bundle_sha256": digest(bundle),
        "source_artifacts": {name: digest(bundle[name]) for name in (*runtime.ARRAYS, "training_features", "training_labels")}})
    return bundle, payload


def run_demo(output: str | Path) -> dict:
    output = Path(output).absolute()
    if output.exists():
        raise ValueError("Use a fresh output directory; demo artifacts are immutable")
    if ".." in output.parts or any(part.is_symlink() for part in (output, *output.parents)):
        raise ValueError("Unsafe demo output path")
    output.mkdir(parents=True, exist_ok=False)
    checks: dict[str, bool] = {}
    expected_failures: list[dict] = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks[name] = True

    def reject(name, callback):
        try:
            callback()
        except ValueError as error:
            expected_failures.append({"case": name, "error_type": type(error).__name__, "reason": str(error), "expected": True})
            checks[name] = True
        else:
            raise AssertionError(f"Expected rejection did not occur: {name}")

    try:
        graph = GraphStore(output / "graph", actors=ACTORS)

        def add(kind, payload, actor="demo_researcher", role="researcher"):
            return graph.append_node(kind, payload, actor=actor, role=role, known_at=NOW)

        question = add("question", {"title": "합성 현상의 설명 구분", "question": "A/B 관측 차이가 있는가, 측정 자료만으로 정보 지연 원인까지 말할 수 있는가?"})
        hypotheses = [add("hypothesis", {"question_id": question["id"], "statement": statement,
                                         "alternatives": ["합성 그룹 차이가 없다", "측정 누락이 설명을 제한한다"]})
                      for statement in ["합성 A 그룹의 결과 평균이 B보다 높다", "합성 그룹 평균 차이는 없다"]]
        graph.append_edge("competes_with", hypotheses[0]["id"], hypotheses[1]["id"], actor="demo_researcher", role="researcher", known_at=NOW,
                          rationale="Competing fixture explanations, not empirical causal links")
        prediction = add("prediction", {"hypothesis_id": hypotheses[0]["id"], "statement": "A-B 평균 차이가 0보다 크다",
                                         "observable": "두 그룹 평균 차이", "assumptions": ["행과 그룹의 합성 생성 정의가 보존됐다"]})
        argument = add("argument", {"premise_ids": [hypotheses[0]["id"], prediction["id"]], "premise_mode": "all",
                                    "inference_type": "DEDUCTION", "conclusion": "가정이 성립하면 양의 그룹 차이를 관찰해야 한다",
                                    "assumptions": ["측정이 그룹 구분과 결과를 정확히 보존한다"],
                                    "warrant": "조건부 예측이며 관측 성공이 원인 증명은 아니다", "epistemic_status": "PROPOSED"})
        imported, intake, source_review = capture_synthetic_source(output, graph, question["id"])
        source, rows = imported["source"], imported["rows"]
        check("local_capture_validated_and_imported", intake["status"] == "READY" and intake["method"] == "explicit_local_exact_hash")
        check("data_requirement_bound_to_question", discovery.load_snapshot(intake["case_dir"], intake["snapshot_id"])["requirement"]["question_id"] == question["id"])
        check("imported_source_bindings_verified", assert_source_bindings(graph) == [source["id"]] and load_source_rows(graph, source["id"]) == rows)
        requirement = add("data_requirement", {"question": "독립적으로 측정한 관심도가 필요한가?",
                                                "discriminates": "그룹 평균 차이와 정보 반영 지연이라는 기제를 구분하려면 추가 측정이 필요하다",
                                                "status": "OPEN", "source_ids": []})
        study = graph.register_study({"question_id": question["id"], "hypothesis_ids": [h["id"] for h in hypotheses],
                                     "stage": "EXPLORATORY", "scope": SCOPE, "max_runs": 2, "max_rows": 12,
                                     "allowed_pit_policies": ["VERIFIED"]}, actor="demo_researcher", known_at=NOW)
        common = {"study_id": study["id"], "prediction_id": prediction["id"], "source_id": source["id"],
                  "stage": "EXPLORATORY", "row_budget": 6, "discriminates": [h["id"] for h in hypotheses],
                  "if_consistent": "해당 범위의 관측만 검토한다", "if_inconsistent": "반대 설명과 측정 제한을 유지한다"}
        contrast = add("test_plan", {**common, "operator": "mean_difference", "priority": 4,
                                     "selection_reason": "가장 직접적인 그룹 차이를 먼저 구분한다",
                                     "parameters": {"value_field": "outcome", "group_field": "group", "groups": ["A", "B"],
                                                    "threshold": 0.0, "direction": "ABOVE", "min_rows": 6}})
        coverage = add("test_plan", {**common, "operator": "coverage", "priority": 2,
                                     "selection_reason": "추가 기제 설명의 측정 자료가 충분한지 확인한다",
                                     "parameters": {"value_field": "attention_proxy", "threshold": .95, "direction": "ABOVE", "min_rows": 6}})
        blocked = add("test_plan", {**common, "operator": "mean_difference", "priority": 5,
                                    "selection_reason": "독립 자료가 있으면 대안 설명을 확인하되 아직 실행하지 않는다",
                                    "requirement_ids": [requirement["id"]], "parameters": contrast["payload"]["parameters"]})
        packet = graph.packet(study["id"])
        _write(output / "initial-packet.json", packet)
        check("missing_data_plan_excluded", blocked["id"] not in packet["eligible_plan_ids"] and requirement["id"] in packet["unresolved_requirement_ids"])
        selection = graph.choose_next_test(study["id"], packet["eligible_plan_ids"], actor="demo_researcher", known_at=NOW)
        check("adaptive_declared_priority_selected_contrast", selection["payload"]["chosen_plan_id"] == contrast["id"])
        tampered = deepcopy(rows)
        tampered[0]["outcome"] = 900.0
        reject("tampered_source_rejected", lambda: graph.execute_test(contrast["id"], tampered, actor="demo_executor", known_at=NOW))
        first = graph.execute_test(contrast["id"], load_source_rows(graph, source["id"]), actor="demo_executor", known_at=NOW)
        packet = graph.packet(study["id"])
        selection2 = graph.choose_next_test(study["id"], packet["eligible_plan_ids"], actor="demo_researcher", known_at=NOW)
        check("second_choice_bound_to_prior_evidence", selection2["payload"]["prior_evidence_ids"] == [first["evidence"]["id"]])
        second = graph.execute_test(coverage["id"], load_source_rows(graph, source["id"]), actor="demo_executor", known_at=NOW)
        check("two_runs_consumed_exact_budget", graph.packet(study["id"])["remaining_runs"] == 0 and graph.packet(study["id"])["remaining_rows"] == 0)
        check("known_fixture_results", first["evidence"]["payload"]["result"]["effect"] == 3.0 and second["evidence"]["payload"]["result"]["effect"] == 5 / 6)
        reject("third_run_budget_rejected", lambda: graph.choose_next_test(study["id"], [], actor="demo_researcher", known_at=NOW))
        claim_payload = {"statement": "합성 fixture의 A 평균이 B보다 높다. 관심도 결측 때문에 원인 설명은 확인하지 못했다.",
                         "conclusion_type": "ASSOCIATION", "hypothesis_id": hypotheses[0]["id"], "scope": SCOPE,
                         "limitations": ["SOFTWARE_TEST_ONLY: 실제 시장 자료가 아니다", "평균 차이는 원인이나 매매 유효성의 증거가 아니다", "관심도 설명 변수 결측과 추가 자료 요청이 남아 있다"],
                         "judgment": "SUPPORTED", "stage": "EXPLORATORY", "epistemic_status": "INDEPENDENT_REVIEWED",
                         "empirical_use": "SOFTWARE_TEST_ONLY", "argument_ids": [argument["id"]],
                         "evidence_relations": [{"evidence_id": first["evidence"]["id"], "stance": "SUPPORTS", "reason": "합성 A-B 관측 차이는 3이다"},
                                                {"evidence_id": second["evidence"]["id"], "stance": "INCONCLUSIVE", "reason": "관심도 자료가 5/6으로 기제 구분의 충분성을 보장하지 못한다"}]}
        reject("self_review_rejected", lambda: graph.review_claim(claim_payload, actor="demo_researcher", known_at=NOW))
        reject("synthetic_market_claim_rejected", lambda: graph.review_claim({**claim_payload, "empirical_use": "DESCRIPTIVE_RESEARCH"}, actor="demo_independent_reviewer", known_at=NOW))
        claim = graph.review_claim(claim_payload, actor="demo_independent_reviewer", known_at=NOW)
        check("review_addresses_all_evidence", len(claim["payload"]["evidence_relations"]) == 2)
        snapshot = graph.snapshot([claim["id"]], as_of=NOW)
        _write(output / "knowledge-snapshot.json", snapshot)
        bundle = synthetic_execution_bundle()
        strategy = graph.create_strategy(synthetic_strategy_payload(bundle), snapshot, actor="demo_strategist", known_at=NOW)
        registration = runtime.register_execution(graph, strategy["id"], bundle, output / "runtime", registered_at=NOW)
        runtime_result = runtime.execute_registered(graph, registration["run_dir"])
        check("monthly_execution_all_four_variants", runtime_result["variant_order"] == list(runtime.VARIANTS) and runtime_result["selected_variant"] is None)
        check("runtime_stays_software_only", runtime_result["empirical_use"] == "SOFTWARE_TEST_ONLY" and not runtime_result["publication_authorized"] and not runtime_result["orders_submitted"])
        check("runtime_readback_verified", runtime.verify_result(graph, registration["run_dir"])["manifest_sha256"] == runtime_result["manifest_sha256"])
        reject("repeat_execution_rejected", lambda: runtime.execute_registered(graph, registration["run_dir"]))
        ridge_bundle, ridge_payload = synthetic_ridge_inputs()
        ridge_snapshot = graph.snapshot([claim["id"]], as_of=NOW)
        ridge_strategy = graph.create_strategy(ridge_payload, ridge_snapshot, actor="demo_strategist", known_at=NOW)
        ridge_registration = runtime.register_execution(graph, ridge_strategy["id"], ridge_bundle, output / "ridge-runtime", registered_at=NOW)
        ridge_result = runtime.execute_registered(graph, ridge_registration["run_dir"])
        ridge_audit = json.loads((Path(ridge_registration["run_dir"]) / "ridge_audit.json").read_text())
        check("ridge_executes_all_four_variants_without_winner", ridge_result["variant_order"] == list(runtime.VARIANTS) and ridge_result["selected_variant"] is None)
        check("ridge_train_only_selection_and_pca", len(ridge_audit["folds"]) == 2 and
              all(fold["selected_features"] == ["synthetic_quality", "synthetic_size"] and
                  "synthetic_duplicate" in fold["dropped_features"] and not fold["test_labels_used"] and
                  not fold["selection_used_outcomes"] for fold in ridge_audit["folds"]))
        check("ridge_label_availability_purge", "2019-12" not in ridge_audit["folds"][0]["train_months"] and
              "2019-12" in ridge_audit["folds"][1]["train_months"])
        check("ridge_no_pca_baseline_preserved", len(ridge_audit["baseline_predictions"]) == 20 and
              all("ridge_no_pca" in fold["models"] for fold in ridge_audit["folds"]))
        check("ridge_runtime_readback_verified", runtime.verify_result(graph, ridge_registration["run_dir"])["manifest_sha256"] == ridge_result["manifest_sha256"])
        discovery.review_source(intake["case_dir"], intake["source_id"], {**source_review, "research_use_permitted": False})
        reject("revoked_intake_source_rejected", lambda: load_source_rows(graph, source["id"]))
        graph.invalidate(source["id"], actor="demo_curator", known_at=LATER, reason="Deliberate synthetic source permission revocation and invalidation fault injection")
        statuses = graph.validate()["statuses"]
        check("invalidation_blocks_claim_and_strategy", statuses[claim["id"]] == "DEPENDENCY_BLOCKED" and statuses[strategy["id"]] == "DEPENDENCY_BLOCKED" and statuses[ridge_strategy["id"]] == "DEPENDENCY_BLOCKED")
        reject("invalidated_strategy_runtime_rejected", lambda: runtime.register_execution(graph, strategy["id"], bundle, output / "blocked-runtime", registered_at=LATER))
        reject("stale_runtime_current_use_rejected", lambda: runtime.verify_result(graph, registration["run_dir"]))
        check("archived_runtime_remains_verifiable", runtime.verify_result(graph, registration["run_dir"], require_current=False)["manifest_sha256"] == runtime_result["manifest_sha256"])
        check("archived_ridge_remains_verifiable", runtime.verify_result(graph, ridge_registration["run_dir"], require_current=False)["manifest_sha256"] == ridge_result["manifest_sha256"])
        stop = graph.stop_study(study["id"], actor="demo_researcher", known_at=LATER,
                                reason="Synthetic two-run budget consumed; source invalidation leaves explanation unusable", status="DATA_BLOCKED")
        packet = graph.packet(study["id"])
        check("explicit_terminal_stop", packet["stop_decision"]["id"] == stop["id"] and not packet["eligible_plan_ids"])
        _write(output / "final-packet.json", packet)
        reopened = GraphStore(output / "graph")
        graph_validation = reopened.validate()
        check("persistent_graph_readback", reopened.get(strategy["id"]) == strategy)
        report = {"schema": "phenomenon-software-demo-v1", "status": "ALL_CHECKS_PASSED", "empirical_use": "SOFTWARE_TEST_ONLY",
                  "origin": "SYNTHETIC", "real_llm_review_performed": False, "market_findings_created": False,
                  "database_accessed": False, "gold_published": False, "orders_submitted": False,
                  "checks": checks, "expected_failures": expected_failures, "graph": graph_validation,
                  "study_id": study["id"], "claim_id": claim["id"], "strategy_id": strategy["id"],
                  "unresolved_requirement_id": requirement["id"], "runtime": registration,
                  "data_intake": intake, "software_research_clock": NOW,
                  "ridge_strategy_id": ridge_strategy["id"], "ridge_runtime": ridge_registration,
                  "ridge_runtime_manifest_sha256": ridge_result["manifest_sha256"],
                  "runtime_manifest_sha256": runtime_result["manifest_sha256"],
                  "notes": ["The reviewer is an independent scripted actor for software validation, not a live LLM scientific review.",
                            "Execution input verification flags refer only to constructed fixture consistency, not KRX evidence.",
                            "The future 2030 research clock is a synthetic ordering fixture after actual source validation, never a market-known-at assumption.",
                            "The final strategy is deliberately blocked by source invalidation; its successful prior run is preserved as history."]}
        report["manifest_sha256"] = digest(report)
        _write(output / "manifest.json", report)
        return report
    except Exception as error:
        _write(output / "failure.json", {"status": "FAILED_SOFTWARE_TEST", "empirical_use": "SOFTWARE_TEST_ONLY",
                                         "error_type": type(error).__name__, "message": str(error), "completed_checks": checks,
                                         "expected_failures": expected_failures, "gold_published": False, "orders_submitted": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run_demo(args.output)
    print(json.dumps({"status": result["status"], "empirical_use": result["empirical_use"], "checks_passed": len(result["checks"]),
                      "expected_rejections": len(result["expected_failures"]), "manifest": str(args.output.absolute() / "manifest.json"),
                      "runtime_variants": list(runtime.VARIANTS), "final_strategy_state": result["graph"]["statuses"][result["strategy_id"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
