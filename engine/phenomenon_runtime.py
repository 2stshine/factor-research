"""Immutable graph-to-monthly-execution bridge, never a strategy approver.

The graph strategy must already contain the exact runtime_contract before any
execution. Direct reference measurement scores are signed once by a declared
orientation. Four existing monthly variants run together; none is selected by
its outcome. Artifact hashes establish identity, not source/PIT authenticity.
Synthetic origins remain SOFTWARE_TEST_ONLY and observed runs are explicitly
historical reuse, not new independent confirmation or orders.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from engine.phenomenon_research import GraphStore, canonical, digest
from engine import phenomenon_ridge
from engine import reference_portfolio
from strategies import monthly_execution as monthly


SCHEMA = "phenomenon-monthly-runtime-v1"
ARRAYS = ("measurements", "sessions", "asset_windows", "market_windows")
VARIANTS = ("q20_equal", "q10_equal", "q20_sqrt_cap", "q10_sqrt_cap")
VARIANT_DEFINITIONS = (("q20_equal", .20, "equal"), ("q10_equal", .10, "equal"), ("q20_sqrt_cap", .20, "sqrt_cap"), ("q10_sqrt_cap", .10, "sqrt_cap"))
BENCHMARKS = ["MARKET_TR", "UNIVERSE_EQUAL_WEIGHT"]
EXECUTION = {"rebalance": "MONTHLY", "signal_cutoff": "MONTH_END_AFTER_CLOSE", "fill": "NEXT_MONTH_FIRST_TRADABLE_OPEN", "unavailable_price_rule": "FAIL_CLOSED_COMMON_SAMPLE", "corporate_action_policy": "VERIFIED_OPEN_TO_OPEN_TOTAL_RETURN"}
WARNINGS = ["All four variants are reported; no result-based winner selection.", "Knowledge and input selection are part of historical development; this is not fresh OOS.", "Source/PIT verification is an upstream attestation, not proven by matching hashes.", "Gross market TR and universe-EW are diagnostics; selected-portfolio returns include declared costs.", "Fractional holdings only; no order-book/capacity, actual fills or final liquidation.", "No empirical claim, Gold approval or publication is created by this execution."]


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _time(value):
    parsed = datetime.fromisoformat(value)
    _require(parsed.tzinfo is not None, "Aware runtime timestamp required")
    return parsed


def _finite(value, label, *, positive=False):
    _require(type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0), f"Invalid {label}")
    return float(value)


def bundle_data_sha256(bundle: dict) -> str:
    """Bind four execution arrays plus separate training arrays when present."""
    names = (*ARRAYS, *phenomenon_ridge.EXTRA_ARRAYS) if any(name in bundle for name in phenomenon_ridge.EXTRA_ARRAYS) else ARRAYS
    return digest({name: bundle[name] for name in names})


def _write(path: Path, body: dict) -> str:
    raw = canonical(body) + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o444)
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path, expected: str | None = None):
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 100_000_000, "Invalid runtime artifact path/size")
    raw = path.read_bytes()
    _require(expected is None or hashlib.sha256(raw).hexdigest() == expected, "Runtime artifact hash mismatch")
    return json.loads(raw)


def _code_identity():
    paths = {"runtime": Path(__file__), "monthly_execution": Path(monthly.__file__), "ridge_adapter": Path(phenomenon_ridge.__file__), "ridge_kernel": Path(reference_portfolio.__file__)}
    return {"files": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}, "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__}


@contextmanager
def _locked(path: Path):
    lock = path / ".runtime.lock"
    _require(not lock.is_symlink(), "Runtime lock symlink rejected")
    with lock.open("a+b") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _validate_contract(strategy: dict, bundle: dict, registered_at: str) -> dict:
    p = strategy["payload"]
    contract = p.get("runtime_contract")
    required = {"schema", "score_rule", "variants", "benchmarks", "costs", "initial_nav", "scope", "execution", "decision_clock", "historical_reuse_acknowledged", "source_artifacts", "input_bundle_sha256"}
    _require(isinstance(contract, dict) and set(contract) == required and contract["schema"] == SCHEMA, "Predeclared exact runtime_contract required on strategy")
    kind = contract["score_rule"].get("kind")
    _require(kind in {"DIRECT_REFERENCE", "TRAIN_ONLY_RIDGE"}, "Unsupported predeclared score rule")
    array_names = (*ARRAYS, *phenomenon_ridge.EXTRA_ARRAYS) if kind == "TRAIN_ONLY_RIDGE" else ARRAYS
    _require(set(bundle) == {"origin", "reference", "evidence", *array_names}, "Unexpected or missing input bundle fields")
    _require(contract["input_bundle_sha256"] == digest(bundle), "Input bundle differs from strategy registration")
    _require(set(contract["source_artifacts"]) == set(array_names), "All declared input artifact digests required")
    for name in array_names:
        rows = bundle[name]
        _require(isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows), f"Nonempty row array required: {name}")
        _require(len(rows) <= 1_000_000 and contract["source_artifacts"][name] == digest(rows), f"Input artifact digest/size mismatch: {name}")
    _require(contract["variants"] == list(VARIANTS) and tuple(monthly.VARIANTS) == VARIANT_DEFINITIONS, "All four fixed variants required; no injection/selection")
    _require(contract["benchmarks"] == BENCHMARKS and p["benchmarks"] == BENCHMARKS, "Exact two benchmark contract required")
    _require(contract["execution"] == EXECUTION and p["execution"] == EXECUTION, "Execution timing/missing-price/corporate-action contract mismatch")
    _require(contract["decision_clock"] == "CALENDAR_MONTH_END_23_59_59_ASIA_SEOUL", "Explicit monthly decision clock required")
    _require(contract["historical_reuse_acknowledged"] is True, "Historical selection/exposure must be acknowledged; not fresh OOS")
    _finite(contract["initial_nav"], "initial_nav", positive=True)
    scope = contract["scope"]
    _require(set(scope) == {"origin", "universe", "signal_months"} and isinstance(scope["universe"], str) and scope["universe"], "Explicit universe/origin/month scope required")
    _require(scope["origin"] == bundle["origin"] and bundle["origin"] in {"SYNTHETIC", "OBSERVED"}, "Origin mismatch")
    if bundle["origin"] == "SYNTHETIC":
        _require(p["purpose"] == "SOFTWARE_TEST_ONLY", "Synthetic execution cannot become observed performance")
    _require(scope["signal_months"] == sorted({row["signal_month"] for row in bundle["measurements"]}), "Requested months differ from measurement scope")
    rule = contract["score_rule"]
    ref = bundle["reference"]
    if kind == "DIRECT_REFERENCE":
        _require(set(rule) == {"kind", "field", "orientation", "reference_id", "definition_sha256"}, "Exact DIRECT_REFERENCE rule required")
        _require(type(rule["orientation"]) is int and rule["orientation"] in {-1, 1}, "Predeclared orientation must be -1 or +1")
        _require(isinstance(rule["field"], str) and rule["field"] and rule["field"] not in {"asset_id", "signal_month", "eligible", "market_cap", "available_at"}, "Explicit distinct measurement field required")
        _require(set(ref) == {"reference_id", "definition_sha256", "role", "provenance", "origin"}, "Exact reference measurement metadata required")
        _require(ref["role"] == "MEASUREMENT_ONLY_NO_ALPHA_APPROVAL" and ref["reference_id"] == rule["reference_id"] and ref["definition_sha256"] == rule["definition_sha256"], "Reference identity/role mismatch")
        _require(isinstance(ref["definition_sha256"], str) and len(ref["definition_sha256"]) == 64 and all(c in "0123456789abcdef" for c in ref["definition_sha256"]), "Invalid reference definition hash")
        _require(ref["origin"] == bundle["origin"] and isinstance(ref["provenance"], str) and ref["provenance"], "Reference provenance/origin required")
        fields = {"signal_month", "asset_id", "eligible", "market_cap", "available_at", rule["field"]}
    else:
        names = phenomenon_ridge.validate_rule(rule, ref, bundle["origin"])
        fields = {"signal_month", "asset_id", "eligible", "market_cap", "available_at", *names, *(name + "__known_at" for name in names)}
    _require(all(set(row) == fields for row in bundle["measurements"]), "Measurement inputs cannot smuggle outcome/score fields")
    costs = contract["costs"]
    _require(set(costs) == {"buy_rate", "sell_rate", "sell_tax_by_year"}, "Exact rates and dated sales tax schedule required")
    rate = (_finite(p["costs"]["commission_bps"], "commission_bps") + _finite(p["costs"]["slippage_bps"], "slippage_bps")) / 10000
    _require(_finite(costs["buy_rate"], "buy_rate") == rate and _finite(costs["sell_rate"], "sell_rate") == rate and rate < 1, "Execution rates differ from strategy commission plus slippage")
    _require(p["costs"].get("tax_model") == "DATED_SELL_TAX_SCHEDULE" and p["costs"].get("sell_tax_by_year") == costs["sell_tax_by_year"], "Strategy and runtime tax schedules differ")
    _require(isinstance(costs["sell_tax_by_year"], dict) and costs["sell_tax_by_year"], "Empty tax schedule")
    for year, tax in costs["sell_tax_by_year"].items():
        _require(isinstance(year, str) and year.isdigit() and len(year) == 4 and 1900 <= int(year) <= 2200, "Tax years must be four-digit strings")
        _require(_finite(tax, "sell tax") + rate < 1, "Invalid combined sell cost")
    evidence = bundle["evidence"]
    _require(set(evidence) == {"schema_version", "data_sha256", "as_of", *monthly.EVIDENCE_FLAGS}, "Exact execution evidence contract required")
    _require(evidence["schema_version"] == monthly.EVIDENCE_SCHEMA and evidence["data_sha256"] == bundle_data_sha256(bundle), "Execution evidence does not bind supplied data")
    _require(all(evidence[flag] is True for flag in monthly.EVIDENCE_FLAGS), "Missing upstream execution/PIT verification attestation")
    _require(_time(evidence["as_of"]) <= _time(registered_at), "Execution evidence cannot come from future research time")
    return contract


def _check_graph(graph: GraphStore, strategy_id: str, snapshot: dict):
    from engine.phenomenon_inputs import assert_source_bindings
    assert_source_bindings(graph)
    graph.validate_snapshot(snapshot, require_current=True)
    strategy = graph.get(strategy_id)
    _require(strategy["kind"] == "strategy" and graph.validate()["statuses"][strategy_id] == "ACTIVE", "Strategy is not active")
    original = strategy["payload"]["knowledge_snapshot"]
    graph.validate_snapshot(original, require_current=False)
    for key in ("claim_ids", "node_ids", "edge_ids", "statuses"):
        _require(snapshot[key] == original[key], "Knowledge context changed since strategy design; create a reviewed strategy version")
    return strategy


def register_execution(graph: GraphStore, strategy_id: str, bundle: dict, output_root: str | Path, *, registered_at: str) -> dict:
    """Freeze a strategy's already-bound inputs and current graph context on disk."""
    bundle = json.loads(canonical(bundle))
    strategy = graph.get(strategy_id)
    _require(strategy["kind"] == "strategy" and _time(strategy["known_at"]) <= _time(registered_at), "Strategy/time mismatch")
    snapshot = graph.snapshot(strategy["payload"]["claim_ids"], as_of=registered_at)
    strategy = _check_graph(graph, strategy_id, snapshot)
    contract = _validate_contract(strategy, bundle, registered_at)
    source_origins = {graph.get(node_id)["payload"]["origin"] for node_id in snapshot["node_ids"] if graph.get(node_id)["kind"] == "source"}
    _require(source_origins == {bundle["origin"]}, "Knowledge/input source origins differ")
    for node_id in snapshot["claim_ids"]:
        _require(graph.get(node_id)["payload"]["scope"]["universe"] == contract["scope"]["universe"], "Execution universe differs from claim scope; new hypothesis required")
    registration = {"schema": SCHEMA, "strategy_id": strategy_id, "strategy_record_sha256": digest(strategy), "registered_at": registered_at,
                    "knowledge_snapshot": snapshot, "input_bundle_sha256": digest(bundle), "runtime_contract_sha256": digest(contract), "code_identity": _code_identity(),
                    "publication_authorized": False, "orders_authorized": False}
    run_id = digest(registration)
    parent = Path(output_root).absolute()
    _require(".." not in parent.parts and not any(x.is_symlink() for x in (parent, *parent.parents)), "Unsafe runtime root")
    parent.mkdir(parents=True, exist_ok=True)
    path = parent / run_id
    path.mkdir(exist_ok=False)
    bundle_file_hash = _write(path / "input_bundle.json", bundle)
    strategy_file_hash = _write(path / "strategy.json", strategy)
    receipt = {**registration, "run_id": run_id, "files": {"input_bundle.json": bundle_file_hash, "strategy.json": strategy_file_hash}}
    receipt["registration_sha256"] = digest(receipt)
    _write(path / "registration.json", receipt)
    _check_graph(graph, strategy_id, snapshot)
    return {"run_dir": str(path), "run_id": run_id, "registration_sha256": receipt["registration_sha256"]}


def _registration(path: Path):
    receipt = _read(path / "registration.json")
    expected = {"schema", "strategy_id", "strategy_record_sha256", "registered_at", "knowledge_snapshot", "input_bundle_sha256", "runtime_contract_sha256", "code_identity", "publication_authorized", "orders_authorized", "run_id", "files", "registration_sha256"}
    _require(set(receipt) == expected and receipt["schema"] == SCHEMA and receipt["publication_authorized"] is False and receipt["orders_authorized"] is False, "Invalid registration schema/authorization")
    _require(set(receipt["files"]) == {"input_bundle.json", "strategy.json"}, "Registration input file set mismatch")
    _require(receipt["registration_sha256"] == digest({k: v for k, v in receipt.items() if k != "registration_sha256"}), "Registration hash mismatch")
    body = {k: v for k, v in receipt.items() if k not in {"registration_sha256", "run_id", "files"}}
    _require(receipt["run_id"] == digest(body) and path.name == receipt["run_id"], "Run identity mismatch")
    return receipt


def _manifest(receipt, strategy, bundle, contract, files):
    expected_outputs = {name + ".json" for name in VARIANTS} | {"scores.json"}
    if contract["score_rule"]["kind"] == "TRAIN_ONLY_RIDGE":
        expected_outputs.add("ridge_audit.json")
    _require(set(files) == expected_outputs, "Exact output artifact set required")
    manifest = {"schema": SCHEMA, "status": "COMPLETED_RESEARCH_ONLY", "run_id": receipt["run_id"], "registration_sha256": receipt["registration_sha256"],
                "strategy_id": receipt["strategy_id"], "knowledge_snapshot_sha256": receipt["knowledge_snapshot"]["snapshot_sha256"],
                "input_bundle_sha256": receipt["input_bundle_sha256"], "input_artifact_sha256": contract["source_artifacts"], "input_file_sha256": receipt["files"], "output_file_sha256": files,
                "origin": bundle["origin"], "empirical_use": "SOFTWARE_TEST_ONLY" if strategy["payload"]["purpose"] == "SOFTWARE_TEST_ONLY" else "HISTORICAL_REUSE_DESCRIPTIVE_RESEARCH",
                "variant_order": list(VARIANTS), "selected_variant": None, "costs": contract["costs"], "benchmarks": BENCHMARKS, "execution": EXECUTION, "code_identity": receipt["code_identity"],
                "score_model": contract["score_rule"]["kind"], "hyperparameter_search": False,
                "publication_authorized": False, "orders_submitted": False, "actual_fill_verified": False, "independent_confirmation": False, "warnings": WARNINGS}
    manifest["manifest_sha256"] = digest(manifest)
    return manifest


def _json_output(value):
    if isinstance(value, pd.DataFrame):
        return [_json_output(row) for row in value.to_dict(orient="records")]
    if isinstance(value, dict):
        return {str(k): _json_output(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_output(v) for v in value]
    if isinstance(value, pd.Period):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _json_output(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        _require(math.isnan(value), "Infinite runtime output")
        return None
    return value


def execute_registered(graph: GraphStore, run_dir: str | Path) -> dict:
    """One execution only. Failure retains a receipt and never publishes results."""
    path = Path(run_dir).absolute()
    _require(not path.is_symlink() and path.is_dir(), "Invalid registered run directory")
    with _locked(path):
        _require(not (path / "attempt.json").exists(), "Execution already attempted; do not silently retry or overwrite outcomes")
        receipt = _registration(path)
        strategy = _check_graph(graph, receipt["strategy_id"], receipt["knowledge_snapshot"])
        frozen = _read(path / "strategy.json", receipt["files"]["strategy.json"])
        _require(strategy == frozen and digest(strategy) == receipt["strategy_record_sha256"], "Frozen strategy differs from graph")
        bundle = _read(path / "input_bundle.json", receipt["files"]["input_bundle.json"])
        _require(digest(bundle) == receipt["input_bundle_sha256"], "Input bundle hash mismatch")
        contract = _validate_contract(strategy, bundle, receipt["registered_at"])
        _require(digest(contract) == receipt["runtime_contract_sha256"] and _code_identity() == receipt["code_identity"], "Runtime code/contract changed after registration")
        _write(path / "attempt.json", {"schema": SCHEMA, "registration_sha256": receipt["registration_sha256"], "state": "STARTED", "no_implicit_retry": True})
        try:
            rule = contract["score_rule"]
            ridge_result = None
            if rule["kind"] == "DIRECT_REFERENCE":
                scores = [{"signal_month": row["signal_month"], "asset_id": row["asset_id"], "eligible": row["eligible"], "market_cap": row["market_cap"], "available_at": row["available_at"],
                           "signed_score": None if row[rule["field"]] is None else _finite_signed(row[rule["field"]]) * rule["orientation"]} for row in bundle["measurements"]]
            else:
                ridge_result = phenomenon_ridge.generate_scores(bundle["measurements"], bundle["training_features"], bundle["training_labels"], bundle["sessions"], rule=rule,
                            reference=bundle["reference"], origin=bundle["origin"], research_as_of=bundle["evidence"]["as_of"])
                scores = ridge_result["scores"]
            costs = contract["costs"]
            result = monthly.run_monthly_execution(pd.DataFrame(scores), pd.DataFrame(bundle["sessions"]), pd.DataFrame(bundle["asset_windows"]), pd.DataFrame(bundle["market_windows"]),
                        evidence=bundle["evidence"], costs=monthly.ExecutionCosts(costs["buy_rate"], costs["sell_rate"], {int(k): v for k, v in costs["sell_tax_by_year"].items()}), initial_nav=contract["initial_nav"])
            _require(result["variant_order"] == list(VARIANTS) and set(result["variants"]) == set(VARIANTS), "Runtime omitted or injected a variant")
            _require(result.get("orders_submitted") is False and result.get("actual_fill_verified") is False, "Execution cannot claim actual orders/fills")
            for name, quantile, weighting in VARIANT_DEFINITIONS:
                variant = result["variants"][name]
                _require(variant["quantile"] == quantile and variant["weighting"] == weighting, "Variant definition changed")
                _require([str(x) for x in variant["monthly"].signal_month] == contract["scope"]["signal_months"], "Variant periods differ from frozen scope")
            _check_graph(graph, receipt["strategy_id"], receipt["knowledge_snapshot"])
            _require(_code_identity() == receipt["code_identity"], "Runtime code changed during execution")
            files = {}
            for name in VARIANTS:
                filename = name + ".json"
                files[filename] = _write(path / filename, _json_output(result["variants"][name]))
            files["scores.json"] = _write(path / "scores.json", {"score_rule": rule, "rows": scores})
            if ridge_result is not None:
                files["ridge_audit.json"] = _write(path / "ridge_audit.json", ridge_result)
            manifest = _manifest(receipt, strategy, bundle, contract, files)
            _check_graph(graph, receipt["strategy_id"], receipt["knowledge_snapshot"])
            _write(path / "result_manifest.json", manifest)
            return manifest
        except Exception as exc:
            _write(path / "failure.json", {"schema": SCHEMA, "state": "FAILED_NO_PUBLISH", "error_type": type(exc).__name__, "hypothesis_verdict": "NO_EVIDENCE", "registration_sha256": receipt["registration_sha256"]})
            raise


def _finite_signed(value):
    _require(type(value) in (int, float) and math.isfinite(value), "Reference score must be finite numeric or null")
    return float(value)


def verify_result(graph: GraphStore, run_dir: str | Path, *, require_current: bool = True) -> dict:
    """Verify exact artifacts; stale results can be read only as archived history."""
    path = Path(run_dir).absolute()
    receipt = _registration(path)
    manifest = _read(path / "result_manifest.json")
    _require(manifest["manifest_sha256"] == digest({k: v for k, v in manifest.items() if k != "manifest_sha256"}), "Result manifest hash mismatch")
    strategy = graph.get(receipt["strategy_id"])
    frozen = _read(path / "strategy.json", receipt["files"]["strategy.json"])
    _require(strategy == frozen and digest(strategy) == receipt["strategy_record_sha256"], "Frozen strategy differs from graph")
    bundle = _read(path / "input_bundle.json", receipt["files"]["input_bundle.json"])
    _require(digest(bundle) == receipt["input_bundle_sha256"], "Input bundle hash mismatch")
    contract = _validate_contract(strategy, bundle, receipt["registered_at"])
    _require(digest(contract) == receipt["runtime_contract_sha256"], "Runtime contract hash mismatch")
    expected = _manifest(receipt, strategy, bundle, contract, manifest["output_file_sha256"])
    _require(manifest == expected, "Result manifest semantics differ from frozen registration/strategy")
    for name, expected in {**manifest["input_file_sha256"], **manifest["output_file_sha256"]}.items():
        _require(Path(name).name == name, "Unsafe result artifact name")
        _read(path / name, expected)
    if require_current:
        _check_graph(graph, receipt["strategy_id"], receipt["knowledge_snapshot"])
    else:
        graph.validate_snapshot(receipt["knowledge_snapshot"], require_current=False)
    return manifest
