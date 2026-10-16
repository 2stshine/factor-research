"""Admission-gated, three-model research comparison; never strategy approval.

Uses the established monthly-open execution engine, all four portfolio variants,
identical source rows and dated costs. No graph claims or Gold records are changed.
"""
from copy import deepcopy

import pandas as pd

from engine.reference_admission import admitted_features
from engine import phenomenon_ridge as ridge, phenomenon_runtime as runtime
from engine.research_generation import digest
from strategies import monthly_execution as monthly

MODELS = ("all_usable_ridge", "selected_ridge", "selected_pca_ridge")


def model_rules(base_rule, *, selected_max_features, pca_components):
    """All thresholds must be frozen before reading evaluation-period returns."""
    count = len(base_rule["features"])
    if not (type(selected_max_features) is int and 1 <= selected_max_features <= count
            and type(pca_components) is int and 1 <= pca_components <= selected_max_features):
        raise ValueError("Invalid frozen feature/PCA budget")
    rules = {}
    for name in MODELS:
        rule = deepcopy(base_rule)
        rule["selection"]["method"] = "ALL_USABLE" if name == "all_usable_ridge" else "TRAIN_IC_CORRELATION"
        rule["selection"]["max_features"] = count if name == "all_usable_ridge" else selected_max_features
        rule["pca_components"] = pca_components if name == "selected_pca_ridge" else None
        rules[name] = rule
    return rules


def compare(bundle, contract, admission, *, program_sha256, selected_max_features, pca_components, registered_at,
            measurement_verification=None):
    """Execute only explicit eligible inputs, with no automatic best-model choice.

The graph layer must independently review any resulting economic claim. This
function is a diagnostic comparison, not a bypass to strategy publication.
"""
    allowed = admitted_features(admission, program_sha256=program_sha256, origin=bundle["origin"])
    feature_specs = contract["score_rule"]["features"]
    refs = [f["reference_id"] for f in feature_specs]
    if len(set(refs)) != len(refs) or not refs or any(allowed.get(f["reference_id"]) != f["definition_sha256"] for f in feature_specs):
        raise ValueError("All strategy features must match admitted definitions; no silent filtering")
    if bundle["origin"] == "OBSERVED":
        expected = {"schema": "reference-strategy-gold-binding-v1", "input_bundle_sha256": digest(bundle),
                    "admission_sha256": admission["admission_sha256"], "program_sha256": program_sha256,
                    "reference_ids": sorted(refs), "live_gold_all_rows_verified": True,
                    "feature_values_and_clocks_match": True}
        if measurement_verification != expected:
            raise ValueError("Observed comparison requires exact live Gold value/clock binding")
    # Reuse the full source/time/cost/hash contract validation, without inventing
    # graph nodes, reviewers, or empirical knowledge approval.
    costs = contract["costs"]
    payload = {"runtime_contract": contract, "benchmarks": runtime.BENCHMARKS,
               "execution": runtime.EXECUTION, "purpose": "SOFTWARE_TEST_ONLY" if bundle["origin"] == "SYNTHETIC" else "HISTORICAL_RESEARCH",
               "costs": {"commission_bps": costs["buy_rate"] * 10000, "slippage_bps": 0.,
                         "tax_model": "DATED_SELL_TAX_SCHEDULE", "sell_tax_by_year": costs["sell_tax_by_year"]}}
    runtime._validate_contract({"payload": payload}, bundle, registered_at)
    rules = model_rules(contract["score_rule"], selected_max_features=selected_max_features, pca_components=pca_components)
    outputs, common_keys = {}, None
    for name, rule in rules.items():
        scored = ridge.generate_scores(bundle["measurements"], bundle["training_features"], bundle["training_labels"], bundle["sessions"],
                                       rule=rule, reference=bundle["reference"], origin=bundle["origin"], research_as_of=bundle["evidence"]["as_of"])
        keys = [(r["signal_month"], r["asset_id"], r["eligible"]) for r in scored["scores"]]
        if common_keys is not None and keys != common_keys:
            raise ValueError("Models changed the common sample")
        common_keys = keys
        execution = monthly.run_monthly_execution(pd.DataFrame(scored["scores"]), pd.DataFrame(bundle["sessions"]),
                       pd.DataFrame(bundle["asset_windows"]), pd.DataFrame(bundle["market_windows"]), evidence=bundle["evidence"],
                       costs=monthly.ExecutionCosts(costs["buy_rate"], costs["sell_rate"], {int(k): v for k, v in costs["sell_tax_by_year"].items()}),
                       initial_nav=contract["initial_nav"])
        outputs[name] = {"ridge": scored, "execution": execution, "summary": summarize(execution)}
    return runtime._json_output({"schema": "reference-strategy-comparison-v1", "origin": bundle["origin"],
             "empirical_use": "SOFTWARE_TEST_ONLY" if bundle["origin"] == "SYNTHETIC" else "HISTORICAL_REUSE",
             "admission_sha256": admission["admission_sha256"], "program_sha256": program_sha256,
             "measurement_verification": measurement_verification,
             "contract_sha256": digest(contract), "rules": rules, "models": outputs,
             "selected_model": None, "alpha_approved": False, "orders_authorized": False,
             "strategy_admission_status": "NOT_DECIDED_BY_THIS_COMPARISON",
             "limitations": ["Incremental value is assessed by the paired model comparison, not univariate IC alone.",
                             "Do not choose and report a winner on these same historical evaluation outcomes.",
                             "Costs are declared approximations, not measured market impact or capacity.",
                             "No independent empirical graph claim or production strategy approval is created."]})


def summarize(execution):
    """Paired descriptive net performance, no hypothesis or winner verdict."""
    import numpy as np
    rows = []
    for name, item in execution["variants"].items():
        f = item["monthly"]
        returns = f.net_return.to_numpy()
        wealth = np.r_[1., np.cumprod(1 + returns)]
        rows.append({"portfolio": name, "months": len(f), "cumulative_net_return": float(wealth[-1] - 1),
                     "annualized_net_return": float(wealth[-1] ** (12 / len(f)) - 1),
                     "maximum_drawdown": float(np.min(wealth / np.maximum.accumulate(wealth) - 1)),
                     "mean_monthly_net_excess_market": float(f.net_excess_market.mean()),
                     "mean_monthly_net_excess_universe": float(f.net_excess_universe.mean()),
                     "mean_monthly_turnover_buy_plus_sell": float((f.turnover_buy + f.turnover_sell).mean()),
                     "mean_monthly_cost_fraction": float(f.cost_fraction.mean())})
    return rows


def verify_feature_projection(bundle, reference_id, field, gold_frame):
    """Match both history and prediction inputs to raw Gold, including NaN holes.

    Call only after the existing live Gold loader has verified the full dataset.
    Rank/sign transformations are model operations, not silently substituted data.
    """
    import numpy as np
    source = gold_frame.loc[gold_frame.reference_id.eq(reference_id), ["asset_id", "date", "value", "known_at"]].copy()
    source["signal_month"] = pd.to_datetime(source.date).dt.strftime("%Y-%m")
    source["known_at"] = pd.to_datetime(source.known_at, utc=True)
    for array in ("measurements", "training_features"):
        rows = pd.DataFrame([{k: row[k] for k in ("asset_id", "signal_month", field, field + "__known_at")} for row in bundle[array]])
        if rows.duplicated(["asset_id", "signal_month"]).any():
            raise ValueError("Duplicate strategy feature projection")
        merged = rows.merge(source, on=["asset_id", "signal_month"], how="left", validate="one_to_one")
        a, b = pd.to_numeric(merged[field]), pd.to_numeric(merged.value)
        if not ((a.isna() & b.isna()) | (a == b)).all() or np.isinf(a).any():
            raise ValueError("Strategy values differ from admitted Gold measurements")
        present = b.notna()
        clocks = pd.to_datetime(merged.loc[present, field + "__known_at"], utc=True)
        if not clocks.eq(merged.loc[present, "known_at"]).all():
            raise ValueError("Strategy known_at differs from admitted Gold clocks")
