"""Offline reference strategy exploration. Never logs in or refreshes data.

Prepare once: python -m scripts.run_reference_snapshot prepare
Run repeatedly: python -m scripts.run_reference_snapshot run --output <new-dir>
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from pathlib import Path

import pandas as pd

from engine import reference_snapshot_strategy as snapshot
from engine import reference_snapshot_turnover as turnover
from engine.research_generation import digest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "research/phenomena/snapshot-strategy-defaults.json"


def _worker_init(directory, expected_snapshot):
    global _worker_panel, _worker_fields, _worker_settings
    _worker_panel, manifest, policy = snapshot.load_snapshot(directory)
    if manifest["snapshot_sha256"] != expected_snapshot:
        raise ValueError("Worker snapshot identity differs from registered plan")
    _worker_fields = [f["field"] for f in manifest["fields"]]
    _worker_settings = policy["strategy_comparison"]


def _worker_month(month, costs):
    return snapshot.run_month(_worker_panel, _worker_fields, _worker_settings, month, round_trip_bps=costs)


def run(args):
    config = snapshot.read_json(DEFAULT)
    directory = Path(args.snapshot or ROOT / config["snapshot"])
    if args.command == "prepare":
        m = snapshot.prepare(admission_path=ROOT / config["admission"], cache_receipt=ROOT / config["cache_receipt"],
                             prices_path=ROOT / config["prices"], policy_path=ROOT / config["policy"], output=directory)
        print({"status": "FROZEN_OFFLINE_READY", "snapshot": str(directory), "references": len(m["fields"]),
               "last_signal_month": m["last_signal_month"], "snapshot_sha256": m["snapshot_sha256"]}, flush=True)
        return m
    if not args.output:
        raise ValueError("run requires --output (a new directory or matching checkpoint)")
    if not 1 <= args.workers <= 4:
        raise ValueError("workers must be between 1 and 4")
    panel, manifest, policy = snapshot.load_snapshot(directory)
    if args.snapshot is None and manifest["snapshot_sha256"] != config["snapshot_sha256"]:
        raise ValueError("Default snapshot differs from pinned identity; explicitly select another snapshot")
    settings = policy["strategy_comparison"]
    # Fixed warm-up based only on minimum declared history, not observed performance.
    first = args.first_month or str(pd.Period(manifest["first_month"], freq="M") + settings["min_train_months"])
    last = args.last_month or manifest["last_signal_month"]
    if first < manifest["first_month"] or last > manifest["last_signal_month"] or first > last:
        raise ValueError("Requested months outside completed snapshot history")
    months = [str(m) for m in pd.period_range(first, last, freq="M")]
    costs = config["round_trip_cost_scenario_bps"] if args.round_trip_bps is None else args.round_trip_bps
    if not 0 <= costs < 10000:
        raise ValueError("Cost scenario must be 0 <= bps < 10000")
    buy_bps = args.buy_bps if args.buy_bps is not None else (costs / 2 if args.round_trip_bps is not None else config["buy_cost_scenario_bps"])
    sell_bps = args.sell_bps if args.sell_bps is not None else (costs / 2 if args.round_trip_bps is not None else config["sell_cost_scenario_bps"])
    if not 0 <= buy_bps < 10000 or not 0 <= sell_bps < 10000:
        raise ValueError("Per-side cost rates must be 0 <= bps < 10000")
    output = Path(args.output)
    plan = {"schema": "reference-offline-run-plan-v1", "snapshot_sha256": manifest["snapshot_sha256"],
            "signal_months": months, "settings": settings, "round_trip_cost_scenario_bps": costs,
            "cost_model": "ACTUAL_SIMULATED_TRADE_NOTIONAL_WITH_PRETRADE_WEIGHT_DRIFT",
            "buy_bps": buy_bps, "sell_bps": sell_bps,
            "legacy_comparison_cost_model": "FIXED_MONTHLY_HAIRCUT",
            "missing_outcome_sensitivity": ["MISSING_FLAT_ASSUMPTION", "MISSING_TOTAL_LOSS_ASSUMPTION"],
            "return_basis": manifest["return_basis"], "code_sha256": {
                "runner": snapshot.file_hash(__file__), "engine": snapshot.file_hash(snapshot.__file__),
                "turnover": snapshot.file_hash(turnover.__file__),
                "cost_kernel": snapshot.file_hash(turnover._post_cost_nav.__code__.co_filename),
                "selection": snapshot.file_hash(snapshot.ridge.__file__),
                "ridge_kernel": snapshot.file_hash(snapshot.fit_ridge.__code__.co_filename)},
            "empirical_use": "FROZEN_SNAPSHOT_EXPLORATION_HISTORICAL_REUSE",
            "refresh_required": False, "orders_authorized": False}
    snapshot.write_json(output / "plan.json", plan)
    plan_hash = digest(plan)
    folds, pending = [], []
    fields = [f["field"] for f in manifest["fields"]]
    for month in months:
        checkpoint = output / "months" / (month + ".json")
        if checkpoint.exists():
            saved = snapshot.read_json(checkpoint)
            if saved["plan_sha256"] != plan_hash or saved["fold_sha256"] != digest(saved["fold"]):
                raise ValueError("Checkpoint identity/content mismatch")
            fold = saved["fold"]
            if fold["signal_month"] != month:
                raise ValueError("Checkpoint month differs from filename")
            folds.append(fold)
        else:
            pending.append(month)

    def record(fold):
        month = fold["signal_month"]
        snapshot.write_json(output / "months" / (month + ".json"),
                            {"plan_sha256": plan_hash, "fold_sha256": digest(fold), "fold": fold})
        folds.append(fold)
        print(f"{len(folds)}/{len(months)} {month}: {fold['train_rows']} training rows; {fold['prediction_rows']} scored stocks; offline", flush=True)

    if args.workers == 1:
        for month in pending:
            record(snapshot.run_month(panel, fields, settings, month, round_trip_bps=costs))
    elif pending:
        # Each month is an independent chronological fit, never cross-worker training.
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context("spawn"),
                                 initializer=_worker_init, initargs=(str(directory), manifest["snapshot_sha256"])) as pool:
            jobs = {pool.submit(_worker_month, month, costs): month for month in pending}
            for job in as_completed(jobs):
                record(job.result())
    folds.sort(key=lambda f: f["signal_month"])
    if [f["signal_month"] for f in folds] != months:
        raise ValueError("Incomplete or duplicate monthly evaluation scope")
    accounting = turnover.evaluate(panel, folds, buy_bps=buy_bps, sell_bps=sell_bps)
    accounting.update(plan_sha256=plan_hash, snapshot_sha256=manifest["snapshot_sha256"],
                      selected_model=None, alpha_approved=False, pit_status=manifest["pit_status"],
                      model_refitted=True, targets_changed=True,
                      empirical_use=plan["empirical_use"])
    snapshot.write_json(output / "turnover-result.json", accounting)
    result = {"schema": "reference-offline-result-v1", "plan_sha256": plan_hash,
              "snapshot_sha256": manifest["snapshot_sha256"], "origin": "OBSERVED", "empirical_use": plan["empirical_use"],
              "return_basis": manifest["return_basis"], "round_trip_cost_scenario_bps": costs,
              "summary": snapshot.summarize(folds), "selected_model": None,
              "summary_cost_basis": "LEGACY_FIXED_HAIRCUT_COMPARISON_ONLY",
              "primary_cost_model": plan["cost_model"], "primary_result": "turnover-result.json",
              "primary_result_sha256": snapshot.file_hash(output / "turnover-result.json"),
              "live_database_rechecked": False, "refresh_performed": False, "alpha_approved": False,
              "orders_authorized": False, "pit_status": manifest["pit_status"],
              "limitations": ["Monthly adjusted-close price returns, not dividends/TR or next-open execution.",
                              "Month-end information paired with same-close entry is an exploratory timing approximation, not an executable fill.",
                              "Historical source corrections are intentionally not applied; current certification is not claimed.",
                              "Observed historical price-row universe may have missing/delisted securities; not complete KRX coverage.",
                              "Missing selected-stock outcomes remain unresolved; no zero-fill, survivor-only selection, or stitched CAGR.",
                              "Separate missing-flat and missing-total-loss sensitivity paths are hypothetical, not observed returns or statistical bounds.",
                              "Primary accounting charges simulated buy/sell notional after weight drift; fee rates remain assumptions, not dated actual taxes.",
                              "Legacy monthly summary is fixed-haircut comparison only; use the primary turnover-result.json for current cost performance.",
                              "Market TR benchmark unavailable; never substitute price returns and call them TR.",
                              "No new independent OOS, graph claim, or automatic strategy approval."]}
    snapshot.write_json(output / "result.json", result)
    print({"status": "OFFLINE_EXPLORATION_COMPLETE", "months": len(folds), "references": len(fields),
           "refresh_performed": False, "output": str(output)}, flush=True)
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["prepare", "run"])
    p.add_argument("--snapshot", help="Explicit frozen directory; never replaced by current DB")
    p.add_argument("--output")
    p.add_argument("--first-month")
    p.add_argument("--last-month")
    p.add_argument("--round-trip-bps", type=float, help="Legacy fixed comparison rate; also split equally across sides unless per-side rates supplied")
    p.add_argument("--buy-bps", type=float, help="Cost per actually modeled buy notional; default 25bp")
    p.add_argument("--sell-bps", type=float, help="Cost per actually modeled sell notional; default 25bp")
    p.add_argument("--workers", type=int, default=1, help="1-4 independent monthly fits; no model/period changes")
    return p


if __name__ == "__main__":
    run(parser().parse_args())
