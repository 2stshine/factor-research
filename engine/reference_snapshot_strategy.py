"""Offline, frozen-input exploration. No DB, refresh, or certification bypass.

This deliberately uses monthly adjusted-close PRICE returns, not open execution
or dividend-inclusive TR. Missing held-stock outcomes make a month unresolved;
they never change which stocks were selected. All model fitting is train-only.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from engine.reference_admission import admitted_features
from engine import phenomenon_ridge as ridge
from engine.reference_portfolio import fit_ridge
from engine.research_generation import digest
from strategies.monthly_execution import VARIANTS

SCHEMA = "reference-offline-snapshot-v1"
MODELS = ("all_usable_ridge", "selected_ridge", "selected_pca_ridge")


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    from engine.research_generation import _immutable, canonical
    _immutable(Path(path), canonical(value) + b"\n")


def read_json(path):
    return json.loads(Path(path).read_text())


def build_price_panel(prices):
    required = ["asset_id", "date", "known_at", "adj_close", "market_cap", "market"]
    p = prices[required].copy()
    p["date"] = pd.to_datetime(p.date)
    if p.empty or p.date.dt.tz is not None or not p.date.dt.is_month_end.all():
        raise ValueError("Nonempty calendar-month-end price input required")
    if p.duplicated(["asset_id", "date"]).any():
        raise ValueError("Duplicate price asset-month")
    if not p.asset_id.map(lambda x: not isinstance(x, bool) and int(x) == x and x > 0).all():
        raise ValueError("Positive integer asset IDs required")
    p["asset_id"] = p.asset_id.astype("int64")
    if not p.known_at.map(lambda x: pd.notna(x) and pd.Timestamp(x).tzinfo is not None).all():
        raise ValueError("Aware price availability required")
    p["known_at"] = pd.to_datetime(p.known_at, utc=True)
    p["decision_at"] = (p.date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).dt.tz_localize("Asia/Seoul").dt.tz_convert("UTC")
    if not p.known_at.le(p.decision_at).all():
        raise ValueError("Future price/universe input")
    p["month"] = p.date.dt.to_period("M").astype(str)
    p["eligible"] = (np.isfinite(p.adj_close) & p.adj_close.gt(0)
                     & np.isfinite(p.market_cap) & p.market_cap.gt(0)
                     & p.market.isin(["KOSPI", "KOSDAQ"]))
    # Exact calendar join, never shift across a missing month.
    nxt = p[["asset_id", "month", "adj_close", "known_at", "decision_at"]].copy()
    nxt["month"] = (pd.PeriodIndex(nxt.month, freq="M") - 1).astype(str)
    nxt = nxt.rename(columns={"adj_close": "next_close", "known_at": "next_known_at", "decision_at": "next_decision_at"})
    p = p.merge(nxt, on=["asset_id", "month"], how="left", validate="one_to_one")
    valid = p.eligible & np.isfinite(p.next_close) & p.next_close.gt(0)
    p["outcome"] = (p.next_close / p.adj_close - 1).where(valid)
    # Conservative label clock: no earlier than the end of its outcome month.
    p["label_known_at"] = p.next_decision_at
    return p.drop(columns=["next_close", "next_known_at", "next_decision_at"])


def prepare(*, admission_path, cache_receipt, prices_path, policy_path, output):
    """Freeze derived panel from previously live-verified Gold bytes, offline."""
    output = Path(output)
    if output.exists():
        raise ValueError("Use a new snapshot directory; existing snapshots are immutable")
    report, cache, policy = map(read_json, (admission_path, cache_receipt, policy_path))
    program = report["program_sha256"]
    allowed = admitted_features(report, program_sha256=program, origin="OBSERVED")
    if policy["program_sha256"] != program or not allowed:
        raise ValueError("Policy/admission program mismatch")
    receipts = {r["dataset_id"]: r for r in report["source_receipts"]}
    if len(receipts) != len(report["source_receipts"]):
        raise ValueError("Duplicate source receipt")
    price_sha = file_hash(prices_path)
    panel = build_price_panel(pd.read_parquet(prices_path))
    if file_hash(prices_path) != price_sha:
        raise ValueError("Price file changed during capture")
    panel = panel.set_index(["asset_id", "date"])
    fields, sources, seen, columns = [], [], set(), {}
    for did, receipt in sorted(receipts.items()):
        path = Path(cache["cache_paths"][did])
        if path.is_symlink() or not receipt["live_all_row_verified"] or file_hash(path) != receipt["cache_sha256"]:
            raise ValueError("Previously verified Gold cache hash mismatch")
        values = pd.read_parquet(path)
        if len(values) != receipt["rows"]:
            raise ValueError("Gold row count mismatch")
        for ref, rows in values.groupby("reference_id", sort=True):
            if ref not in allowed:
                continue
            if ref in seen or not rows.definition_hash.eq(allowed[ref]).all():
                raise ValueError("Duplicate reference or definition mismatch")
            seen.add(ref)
            rows = rows.copy()
            # Historical Parquet exports use both text and integer DB IDs.
            # Normalize the internal key, never stock_code (leading zeros).
            if not rows.asset_id.map(lambda x: not isinstance(x, bool) and str(x).isdigit() and int(x) > 0).all():
                raise ValueError("Invalid Gold asset ID")
            rows["asset_id"] = rows.asset_id.astype("int64")
            rows["date"] = pd.to_datetime(rows.date)
            rows["known_at"] = pd.to_datetime(rows.known_at, utc=True)
            cutoff = (rows.date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).dt.tz_localize("Asia/Seoul").dt.tz_convert("UTC")
            if rows.duplicated(["asset_id", "date"]).any() or not rows.known_at.le(cutoff).all():
                raise ValueError("Duplicate or future Gold measurement")
            if not np.isfinite(rows.value).all():
                raise ValueError("Nonfinite admitted Gold value")
            age = (cutoff - rows.known_at).dt.total_seconds() / 86400
            rows.loc[age > policy["strategy_comparison"]["max_feature_age_days"], "value"] = np.nan
            field = "f_" + ref
            columns[field] = rows.set_index(["asset_id", "date"]).value.reindex(panel.index)
            if not columns[field].notna().any():
                raise ValueError("No price/measurement overlap for admitted reference: " + ref)
            fields.append({"field": field, "reference_id": ref, "definition_sha256": allowed[ref]})
        if file_hash(path) != receipt["cache_sha256"]:
            raise ValueError("Gold cache changed while preparing snapshot")
        sources.append({"dataset_id": did, "sha256": receipt["cache_sha256"], "path": str(path.resolve())})
    if seen != set(allowed):
        raise ValueError("Missing admitted references; no silent subset")
    panel = pd.concat([panel, pd.DataFrame(columns, index=panel.index)], axis=1)
    panel = panel.reset_index().sort_values(["month", "asset_id"]).reset_index(drop=True)
    output.mkdir(parents=True)
    panel.to_parquet(output / "panel.parquet", index=False)
    write_json(output / "admission.json", report)
    write_json(output / "policy.json", policy)
    manifest = {"schema": SCHEMA, "origin": "OBSERVED", "program_sha256": program,
                "admission_sha256": report["admission_sha256"], "fields": sorted(fields, key=lambda f: f["reference_id"]),
                "files": {name: file_hash(output / name) for name in ("panel.parquet", "admission.json", "policy.json")},
                "source_prices": {"path": str(Path(prices_path).resolve()), "sha256": price_sha},
                "gold_sources": sources, "rows": len(panel), "first_month": panel.month.min(), "last_price_month": panel.month.max(),
                "last_signal_month": str(pd.Period(panel.month.max(), freq="M") - 1),
                "return_basis": "MONTH_END_ADJUSTED_CLOSE_PRICE_RETURN_NOT_TR_NOT_EXECUTABLE_FILL",
                "refresh_required": False, "live_database_rechecked": False,
                "pit_status": "PIT_ASSUMED_NOT_FIRST_VINTAGE_VERIFIED",
                "current_source_certification": "NOT_REQUIRED_FOR_FROZEN_EXPLORATION",
                "universe": "OBSERVED_HISTORICAL_PRICE_ROWS_NOT_RECONSTRUCTED_FULL_KRX_UNIVERSE",
                "builder_sha256": file_hash(__file__)}
    manifest["snapshot_sha256"] = digest(manifest)
    write_json(output / "manifest.json", manifest)
    return manifest


def load_snapshot(directory):
    directory = Path(directory)
    m = read_json(directory / "manifest.json")
    if m.get("schema") != SCHEMA or m.get("snapshot_sha256") != digest({k: v for k, v in m.items() if k != "snapshot_sha256"}):
        raise ValueError("Snapshot manifest mismatch")
    if set(m["files"]) != {"panel.parquet", "admission.json", "policy.json"}:
        raise ValueError("Exact local snapshot files required")
    for name, expected in m["files"].items():
        if not (directory / name).is_file() or file_hash(directory / name) != expected:
            raise ValueError("Frozen snapshot file changed: " + name)
    a = read_json(directory / "admission.json")
    allowed = admitted_features(a, program_sha256=m["program_sha256"], origin="OBSERVED")
    if a["admission_sha256"] != m["admission_sha256"] or {f["reference_id"]: f["definition_sha256"] for f in m["fields"]} != allowed:
        raise ValueError("Snapshot feature/admission identity mismatch")
    return pd.read_parquet(directory / "panel.parquet"), m, read_json(directory / "policy.json")


def portfolio_month(block, predictions, *, round_trip_bps):
    """Independent fully liquidated monthly baskets; no implicit turnover model."""
    if not np.isfinite(predictions).all() or not 0 <= round_trip_bps < 10000:
        raise ValueError("Finite predictions and bounded declared cost required")
    block = block.assign(score=predictions).sort_values(["score", "asset_id"], ascending=[False, True])
    universe = float(block.outcome.mean()) if block.outcome.notna().all() else None
    results = []
    for name, fraction, weighting in VARIANTS:
        selected = block.head(max(1, int(len(block) * fraction)))
        weights = np.ones(len(selected)) if weighting == "equal" else np.sqrt(selected.market_cap.to_numpy())
        weights = weights / weights.sum()
        missing = selected.outcome.isna()
        gross = None if missing.any() else float(weights @ selected.outcome.to_numpy())
        # Declared fixed haircut, not actual transaction accounting or tax model.
        net = None if gross is None else (1 + gross) * (1 - round_trip_bps / 10000) - 1
        observed_contribution = float(weights @ selected.outcome.fillna(0).to_numpy())
        missing_weight = float(weights[missing.to_numpy()].sum())
        scenarios = {"MISSING_FLAT_ASSUMPTION": observed_contribution,
                     "MISSING_TOTAL_LOSS_ASSUMPTION": observed_contribution - missing_weight}
        results.append({"portfolio": name, "selected_assets": selected.asset_id.astype(int).tolist(),
                        "weights": weights.tolist(), "missing_outcome_assets": selected.loc[missing, "asset_id"].astype(int).tolist(),
                        "missing_outcome_weight": missing_weight,
                        "sensitivity_net_returns_not_observed": {k: (1 + v) * (1 - round_trip_bps / 10000) - 1 for k, v in scenarios.items()},
                        "status": "UNRESOLVED_MISSING_OUTCOMES" if gross is None else "COMPLETE",
                        "gross_price_return": gross, "net_return_cost_scenario": net,
                        "universe_ew_price_return": universe,
                        "net_excess_universe": None if net is None or universe is None else net - universe,
                        "market_tr_excess": None, "universe_missing_outcomes": int(block.outcome.isna().sum())})
    return results


def run_month(panel, fields, settings, month, *, round_trip_bps):
    """One walk-forward fold; future outcomes never determine stock selection."""
    period = pd.Period(month, freq="M")
    cutoff = period.end_time.floor("s").tz_localize("Asia/Seoul").tz_convert("UTC")
    start, end = str(period - settings["train_window_months"]), str(period - settings["purge_gap_months"])
    train = panel.loc[panel.month.between(start, end) & panel.eligible & panel.outcome.notna() & panel.label_known_at.le(cutoff)]
    test = panel.loc[panel.month.eq(month) & panel.eligible]
    if len(train) < settings["min_train_rows"] or train.month.nunique() < settings["min_train_months"] or test.empty:
        raise ValueError("Insufficient training or prediction support for " + month)
    x, y = train[fields].to_numpy(dtype=float), train.outcome.to_numpy(dtype=float)
    ic = ridge._training_ic(x, y, train.month.to_numpy(), fields)
    outputs = {}
    for name in MODELS:
        rule = {"selection": {**settings["selection"], "method": "ALL_USABLE" if name == "all_usable_ridge" else "TRAIN_IC_CORRELATION",
                              "max_features": len(fields) if name == "all_usable_ridge" else settings["selected_max_features"]},
                "min_train_months": settings["min_train_months"]}
        kept, dropped = ridge._select(x, fields, rule, training_ic=ic)
        components = settings["pca_components"] if name == "selected_pca_ridge" else None
        if components is not None and components > len(kept):
            outputs[name] = {"status": "INSUFFICIENT_PCA_FEATURES", "selected_features": [fields[i] for i in kept], "portfolios": []}
            continue
        model = fit_ridge(x[:, kept], y, alpha=settings["alpha"], pca_components=components)
        prediction = model.predict(test[fields].to_numpy(dtype=float)[:, kept])
        outputs[name] = {"status": "SCORED", "selected_features": [fields[i] for i in kept], "dropped_features": dropped,
                         "fit": model.audit(), "portfolios": portfolio_month(test, prediction, round_trip_bps=round_trip_bps)}
    return {"signal_month": month, "train_months": sorted(train.month.unique().tolist()), "train_rows": len(train),
            "max_label_known_at": train.label_known_at.max().isoformat(), "prediction_rows": len(test),
            "training_rank_ic": ic, "models": outputs}


def summarize(folds):
    rows = []
    for model in MODELS:
        for variant, _, _ in VARIANTS:
            items = [next((p for p in f["models"][model]["portfolios"] if p["portfolio"] == variant), None) for f in folds]
            complete = [p for p in items if p is not None and p["status"] == "COMPLETE"]
            full = bool(items) and len(complete) == len(items)
            returns = np.array([p["net_return_cost_scenario"] for p in complete])
            wealth = np.r_[1., np.cumprod(1 + returns)] if full else None
            sensitivity = {}
            if items and all(p is not None for p in items):
                for assumption in ("MISSING_FLAT_ASSUMPTION", "MISSING_TOTAL_LOSS_ASSUMPTION"):
                    path = np.r_[1., np.cumprod([1 + p["sensitivity_net_returns_not_observed"][assumption] for p in items])]
                    sensitivity[assumption] = {"annualized_return_cost_scenario": float(path[-1] ** (12 / len(items)) - 1),
                                               "maximum_drawdown": float(np.min(path / np.maximum.accumulate(path) - 1)),
                                               "not_observed_performance": True}
            rows.append({"model": model, "portfolio": variant, "months": len(items), "complete_months": len(complete),
                         "continuous_history_complete": full,
                         "annualized_net_return_cost_scenario": float(wealth[-1] ** (12 / len(items)) - 1) if full else None,
                         "maximum_drawdown": float(np.min(wealth / np.maximum.accumulate(wealth) - 1)) if full else None,
                         "missing_outcome_sensitivity": sensitivity,
                         "max_missing_outcome_weight": max((p["missing_outcome_weight"] for p in items if p is not None), default=None),
                         "market_tr_excess": None})
    return rows
