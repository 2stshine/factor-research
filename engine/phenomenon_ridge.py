"""Frozen train-only feature selection, optional PCA and ridge score adapter.

This is a historical research calculation, not alpha/factor approval. It reuses
the existing numerical ridge kernel but never accesses a registry, DB, holdout
or test returns. Hyperparameters and candidate feature order are fixed by the
strategy. Selection uses only training availability/variance/correlation, not
outcome performance by default. TRAIN_IC_CORRELATION explicitly ranks candidates
by absolute mean monthly training Rank IC before redundancy pruning. It is a
screening heuristic, not a conditional alpha significance test. Labels enter training
only after the declared open-to-open holding period has completed and is known.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

from engine.phenomenon_research import digest
from engine.reference_portfolio import fit_ridge


SCHEMA = "phenomenon-train-only-ridge-v2"
EXTRA_ARRAYS = ("training_features", "training_labels")
RESERVED = {"signal_month", "asset_id", "available_at", "eligible", "market_cap", "signed_score", "next_month_return", "entry_at", "exit_at", "return_available_at", "gross_total_return_multiplier"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _stamp(value):
    parsed = pd.Timestamp(value)
    _require(not pd.isna(parsed) and parsed.tzinfo is not None, "Aware ridge timestamp required")
    return parsed.tz_convert("Asia/Seoul")


def _month(value):
    _require(isinstance(value, str) and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value), "Ridge month must be YYYY-MM")
    return pd.Period(value, freq="M")


def _cutoff(month):
    return month.end_time.floor("s").tz_localize("Asia/Seoul")


def _number(value, *, missing=False):
    if missing and value is None:
        return float("nan")
    _require(type(value) in (float, int) and math.isfinite(value), "Finite numeric ridge value required")
    return float(value)


def validate_rule(rule: dict, reference: dict, origin: str) -> list[str]:
    required = {"kind", "features", "alpha", "pca_components", "selection", "train_window_months", "min_train_months", "min_train_rows", "purge_gap_months", "max_feature_age_days", "label_contract"}
    _require(set(rule) == required and rule["kind"] == "TRAIN_ONLY_RIDGE", "Exact TRAIN_ONLY_RIDGE rule required")
    features = rule["features"]
    _require(isinstance(features, list) and 1 <= len(features) <= 128 and all(isinstance(f, dict) and set(f) == {"field", "reference_id", "definition_sha256"} for f in features), "Explicit ordered ridge feature definitions required")
    names = [f["field"] for f in features]
    _require(len(set(names)) == len(names) and all(isinstance(name, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) and name not in RESERVED and not name.startswith(("label_", "fwd_")) and not name.endswith("__known_at") for name in names), "Outcome/metadata cannot be ridge feature names")
    _require(set(reference) == {"features", "role", "origin", "provenance"} and reference["features"] == features, "Ordered reference feature identity mismatch")
    _require(reference["role"] == "MEASUREMENT_ONLY_NO_ALPHA_APPROVAL" and reference["origin"] == origin and isinstance(reference["provenance"], str) and reference["provenance"], "Reference role/origin/provenance mismatch")
    for feature in features:
        _require(isinstance(feature["reference_id"], str) and feature["reference_id"], "Reference id required")
        _require(isinstance(feature["definition_sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", feature["definition_sha256"]), "Reference definition hash required")
    _require(_number(rule["alpha"]) > 0, "Fixed positive ridge alpha required")
    _require(rule["pca_components"] is None or type(rule["pca_components"]) is int and 1 <= rule["pca_components"] <= len(names), "Fixed PCA components invalid")
    for key in ("train_window_months", "min_train_months", "min_train_rows", "purge_gap_months", "max_feature_age_days"):
        _require(type(rule[key]) is int and 1 <= rule[key] <= 100000, f"Positive bounded {key} required")
    _require(2 <= rule["min_train_months"] <= rule["train_window_months"] <= 240 and rule["min_train_rows"] >= 2, "Training month/row support invalid")
    selection = rule["selection"]
    _require(set(selection) == {"method", "max_abs_correlation", "max_missing_fraction", "min_variance", "max_features"}, "Exact train-only selection contract required")
    _require(selection["method"] in {"ALL", "ALL_USABLE", "TRAIN_CORRELATION", "TRAIN_IC_CORRELATION"} and 0 < _number(selection["max_abs_correlation"]) <= 1 and 0 <= _number(selection["max_missing_fraction"]) < 1 and _number(selection["min_variance"]) >= 0, "Invalid feature selection thresholds")
    _require(type(selection["max_features"]) is int and 1 <= selection["max_features"] <= len(names), "Invalid max_features")
    if selection["method"] in {"ALL", "ALL_USABLE"}:
        _require(selection["max_features"] == len(names), "ALL selection cannot silently subset features")
    _require(rule["label_contract"] == "VERIFIED_NEXT_OPEN_TO_FOLLOWING_OPEN_GROSS_RETURN_MINUS_ONE", "Ridge target must agree with monthly execution horizon")
    return names


def _features(rows, names, max_age, *, predictions=False):
    fields = {"signal_month", "asset_id", "available_at", "eligible", *names, *(name + "__known_at" for name in names)}
    if predictions:
        fields.add("market_cap")
    checked = []
    seen = set()
    for row in rows:
        _require(set(row) == fields, "Ridge feature rows cannot contain labels/extra fields")
        month = _month(row["signal_month"])
        _require(type(row["asset_id"]) is int and row["asset_id"] > 0 and type(row["eligible"]) is bool, "Explicit asset/eligibility required")
        key = (row["signal_month"], row["asset_id"])
        _require(key not in seen, "Duplicate ridge asset-month feature row")
        seen.add(key)
        cutoff, available = _cutoff(month), _stamp(row["available_at"])
        _require(available <= cutoff, "Future feature/eligibility availability at decision")
        values = []
        for name in names:
            # A missing measurement has no invented historical availability.
            if row[name] is None and row[name + "__known_at"] is None:
                values.append(float("nan"))
                continue
            known = _stamp(row[name + "__known_at"])
            _require(known <= available <= cutoff, "Future feature known_at exceeds input/decision availability")
            _require(cutoff - known <= pd.Timedelta(days=max_age), "Stale feature exceeds frozen age limit")
            values.append(_number(row[name], missing=True))
        if predictions:
            _require(_number(row["market_cap"]) > 0, "Prediction market cap must be positive")
        checked.append({"key": key, "month": month, "values": values, "row": row})
    _require(checked, "Empty ridge features")
    return checked


def _training_ic(x, y, months, names):
    """Equal month weights, pairwise observed ranks; never use prediction labels."""
    records = {}
    months = np.asarray(months)
    for index, name in enumerate(names):
        estimates = []
        for month in sorted(set(months)):
            mask = (months == month) & np.isfinite(x[:, index]) & np.isfinite(y)
            a, b = pd.Series(x[mask, index]), pd.Series(y[mask])
            if len(a) >= 3 and a.nunique() > 1 and b.nunique() > 1:
                estimates.append(float(a.rank().corr(b.rank())))
        records[name] = {"mean_rank_ic": float(np.mean(estimates)) if estimates else None,
                         "valid_months": len(estimates)}
    return records


def _select(x, names, rule, *, training_ic=None):
    selection = rule["selection"]
    kept, dropped = [], {}
    imputed = {}
    order = list(range(len(names)))
    if selection["method"] == "TRAIN_IC_CORRELATION":
        _require(training_ic is not None, "Training-only IC evidence required")
        order.sort(key=lambda i: (-abs(training_ic[names[i]]["mean_rank_ic"] or 0.), names[i]))
    for index in order:
        name = names[index]
        values = x[:, index]
        finite = np.isfinite(values)
        if selection["method"] == "TRAIN_IC_CORRELATION" and training_ic[name]["valid_months"] < rule["min_train_months"]:
            reason = "INSUFFICIENT_TRAIN_IC_MONTHS"
        elif finite.sum() < 2 or 1 - finite.mean() > selection["max_missing_fraction"]:
            reason = "INSUFFICIENT_TRAIN_OBSERVATIONS"
        else:
            column = np.where(finite, values, np.nanmedian(values))
            imputed[index] = column
            if np.var(column) <= selection["min_variance"]:
                reason = "TRAIN_VARIANCE_TOO_LOW"
            elif selection["method"] in {"TRAIN_CORRELATION", "TRAIN_IC_CORRELATION"} and any(abs(float(np.corrcoef(column, imputed[j])[0, 1])) >= selection["max_abs_correlation"] for j in kept):
                reason = "TRAIN_CORRELATED_WITH_EARLIER_DECLARED_FEATURE" if selection["method"] == "TRAIN_CORRELATION" else "TRAIN_CORRELATED_WITH_HIGHER_IC_FEATURE"
            elif len(kept) >= selection["max_features"]:
                reason = "PREDECLARED_FEATURE_LIMIT"
            else:
                kept.append(index)
                continue
        dropped[name] = reason
    if selection["method"] == "ALL":
        _require(not dropped, "ALL feature rule lacks declared training coverage/variance")
    _require(kept, "No usable train-only features; cannot fabricate scores")
    return kept, dropped


def generate_scores(measurements: list[dict], training_features: list[dict], training_labels: list[dict], sessions: list[dict], *, rule: dict, reference: dict, origin: str, research_as_of: str) -> dict:
    """Walk forward with fixed parameters; prediction-period outcomes are absent."""
    names = validate_rule(rule, reference, origin)
    prediction = _features(measurements, names, rule["max_feature_age_days"], predictions=True)
    history = _features(training_features, names, rule["max_feature_age_days"])
    calendar = {}
    for session in sessions:
        month, stamp = _month(session["session_month"]), _stamp(session["open_at"])
        _require(month not in calendar and stamp.tz_localize(None).to_period("M") == month, "Invalid/duplicate verified session month")
        calendar[month] = stamp
    cutoff_research = _stamp(research_as_of)
    labels = {}
    label_fields = {"signal_month", "asset_id", "entry_at", "exit_at", "return_available_at", "gross_total_return_multiplier"}
    history_keys = {row["key"] for row in history}
    for row in training_labels:
        _require(set(row) == label_fields and type(row["asset_id"]) is int and row["asset_id"] > 0, "Exact separate training label rows required")
        month = _month(row["signal_month"])
        key = (row["signal_month"], row["asset_id"])
        _require(key not in labels and key in history_keys, "Duplicate/orphan training label")
        entry, exit, available = (_stamp(row[field]) for field in ("entry_at", "exit_at", "return_available_at"))
        _require(entry == calendar.get(month + 1) and exit == calendar.get(month + 2) and exit > entry > _cutoff(month), "Training label horizon differs from verified open-to-open execution")
        _require(exit <= available <= cutoff_research, "Invalid training outcome availability chronology")
        multiplier = _number(row["gross_total_return_multiplier"])
        _require(multiplier >= 0, "Negative wealth multiplier")
        labels[key] = {"value": multiplier - 1., "available": available, "row": row}
    months = sorted({row["month"] for row in prediction})
    _require(months == list(pd.period_range(months[0], months[-1], freq="M")), "Requested ridge months must be consecutive")
    scores, folds, baseline_predictions = [], [], []
    for month in months:
        cutoff = _cutoff(month)
        _require(cutoff <= cutoff_research, "Prediction decision is after research cutoff")
        candidates = [row for row in history if month - rule["train_window_months"] <= row["month"] <= month - rule["purge_gap_months"] and row["row"]["eligible"]]
        train = [row for row in candidates if row["key"] in labels and labels[row["key"]]["available"] <= cutoff]
        _require(len(train) >= rule["min_train_rows"] and len({row["month"] for row in train}) >= rule["min_train_months"], "Insufficient known-label training support; no silent skipped month")
        x = np.asarray([row["values"] for row in train], dtype=float)
        y = np.asarray([labels[row["key"]]["value"] for row in train], dtype=float)
        ic = _training_ic(x, y, [str(row["month"]) for row in train], names) if rule["selection"]["method"] == "TRAIN_IC_CORRELATION" else None
        selected, dropped = _select(x, names, rule, training_ic=ic)
        configured = fit_ridge(x[:, selected], y, alpha=rule["alpha"], pca_components=rule["pca_components"])
        baseline = configured if rule["pca_components"] is None else fit_ridge(x[:, selected], y, alpha=rule["alpha"], pca_components=None)
        test = [row for row in prediction if row["month"] == month]
        test_values = np.asarray([row["values"] for row in test], dtype=float)[:, selected]
        predictions, raw_predictions = configured.predict(test_values), baseline.predict(test_values)
        _require(np.isfinite(predictions).all() and np.isfinite(raw_predictions).all(), "Nonfinite ridge prediction")
        for index, item in enumerate(test):
            row = item["row"]
            scores.append({"signal_month": row["signal_month"], "asset_id": row["asset_id"], "eligible": row["eligible"], "market_cap": row["market_cap"], "available_at": cutoff.isoformat(), "signed_score": float(predictions[index])})
            baseline_predictions.append({"signal_month": row["signal_month"], "asset_id": row["asset_id"], "prediction_ridge_no_pca": float(raw_predictions[index])})
        folds.append({"signal_month": str(month), "fit_cutoff": cutoff.isoformat(), "train_months": sorted({str(row["month"]) for row in train}), "train_rows": len(train),
                      "train_feature_rows_sha256": digest([row["row"] for row in train]), "train_label_rows_sha256": digest([labels[row["key"]]["row"] for row in train]),
                      "max_label_available_at": max(labels[row["key"]]["available"] for row in train).isoformat(), "unavailable_or_missing_label_rows_excluded": len(candidates) - len(train),
                      "selected_features": [names[index] for index in selected], "dropped_features": dropped,
                      "selection_used_outcomes": ic is not None, "selection_outcome_scope": "KNOWN_TRAIN_LABELS_ONLY" if ic is not None else "NONE",
                      "training_rank_ic": ic,
                      "models": {"configured": configured.audit(), "ridge_no_pca": baseline.audit()}, "test_labels_used": False})
    return {"schema": SCHEMA, "scores": scores, "folds": folds, "baseline_predictions": baseline_predictions, "rule_sha256": digest(rule),
            "origin": origin, "empirical_use": "SOFTWARE_TEST_ONLY" if origin == "SYNTHETIC" else "HISTORICAL_REUSE_DESCRIPTIVE_RESEARCH",
            "hyperparameter_search": False, "winner_selected": False, "learned_claims": [], "publication_authorized": False,
            "limitations": ["Train-only coverage/variance/correlation and optional monthly Rank IC screening are not proof of incremental alpha.", "Fixed ridge/PCA settings; no outer-outcome tuning or causal/market confirmation.", "Pooled asset-row ridge loss; calendar grouping and label availability do not establish sampling independence.", "Source timestamps and execution labels require upstream authentic provenance; matching hashes alone are not PIT proof."]}
