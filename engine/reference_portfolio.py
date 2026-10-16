"""Research-only monthly return prediction, NOT a portfolio optimizer.

Median imputation, scaling, optional PCA of raw stock characteristics, and ridge
are fitted anew inside each chronological training fold. This is not RP-PCA or
latent return-factor estimation. Ridge shrinks coefficients; it does not perform
sparse factor selection. No DB, Gold import, ranking or full-sample selection.

Primary implementation references:
https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html
https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html
https://scikit-learn.org/stable/common_pitfalls.html
https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
The split below is calendar-month grouped, unlike ordinary row TimeSeriesSplit.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re

import numpy as np
import pandas as pd

VERSION = "reference-ridge-characteristic-pca-research-v1"
MONTH = re.compile(r"\d{4}-(?:0[1-9]|1[0-2])\Z")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _instant(value, field):
    try:
        stamp = pd.Timestamp(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid {field}") from exc
    _require(pd.notna(stamp) and stamp.tzinfo is not None, f"Explicit timezone required: {field}")
    return stamp.tz_convert("UTC")


def _month(value):
    _require(isinstance(value, str) and MONTH.fullmatch(value), "signal_month must be YYYY-MM")
    return pd.Period(value, freq="M")


@dataclass(frozen=True)
class WalkForwardConfig:
    first_test_month: str
    last_test_month: str | None = None
    min_train_months: int = 24
    outer_train_months: int = 60
    inner_train_months: int = 36
    inner_validation_months: int = 3
    inner_splits: int = 3
    purge_gap_months: int = 1
    alphas: tuple[float, ...] = (0.1, 1.0, 10.0)
    pca_components: tuple[int | None, ...] = (None, 1, 2)
    max_feature_age_days: int = 400

    def validate(self, feature_count):
        first = _month(self.first_test_month)
        if self.last_test_month is not None:
            _require(_month(self.last_test_month) >= first, "Invalid outer test range")
        for name in ("min_train_months", "outer_train_months", "inner_train_months", "inner_validation_months", "inner_splits", "purge_gap_months", "max_feature_age_days"):
            _require(type(getattr(self, name)) is int and getattr(self, name) >= 1, f"Positive integer required: {name}")
        _require(self.min_train_months >= 2 and self.outer_train_months >= self.min_train_months
                 and self.inner_train_months >= self.min_train_months, "Training month configuration invalid")
        _require(self.alphas and len(set(self.alphas)) == len(self.alphas)
                 and all(type(a) in (int, float) and np.isfinite(a) and a > 0 for a in self.alphas), "Positive finite predeclared ridge alpha grid required")
        _require(None in self.pca_components and len(set(self.pca_components)) == len(self.pca_components)
                 and all(k is None or type(k) is int and 1 <= k <= feature_count for k in self.pca_components),
                 "PCA grid must include None and valid component counts")
        _require(len(self.alphas) * len(self.pca_components) <= 30, "Predeclared tuning budget exceeded")


@dataclass
class FittedRidge:
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    components: np.ndarray
    coefficients: np.ndarray
    intercept: float
    alpha: float
    pca_components: int | None

    def transform(self, values):
        values = np.asarray(values, dtype=float)
        _require(values.ndim == 2 and values.shape[1] == len(self.medians) and not np.isinf(values).any(), "Invalid prediction feature matrix")
        imputed = np.where(np.isnan(values), self.medians, values)
        return ((imputed - self.means) / self.scales) @ self.components.T

    def predict(self, values):
        return self.transform(values) @ self.coefficients + self.intercept

    def audit(self):
        return {"medians": self.medians.tolist(), "means": self.means.tolist(), "scales": self.scales.tolist(),
                "components": self.components.tolist(), "coefficients": self.coefficients.tolist(),
                "intercept": self.intercept, "alpha": self.alpha, "pca_components": self.pca_components}


def fit_ridge(values, targets, *, alpha, pca_components=None):
    """SSE + alpha*||beta||², with an unpenalized intercept and train-only SVD."""
    x, y = np.asarray(values, dtype=float), np.asarray(targets, dtype=float)
    _require(x.ndim == 2 and y.shape == (len(x),) and len(x) >= 2 and x.shape[1] > 0, "Invalid train shapes")
    _require(not np.isinf(x).any() and np.isfinite(y).all(), "Nonfinite training targets or infinite features")
    _require(np.isfinite(x).sum(axis=0).min() >= 2, "Every feature needs two observed training values")
    _require(np.isfinite(alpha) and alpha > 0, "Positive ridge alpha required")
    _require(pca_components is None or type(pca_components) is int and 1 <= pca_components <= min(x.shape[1], len(x) - 1), "Invalid PCA dimension")
    medians = np.nanmedian(x, axis=0)
    x = np.where(np.isnan(x), medians, x)
    means, scales = x.mean(axis=0), x.std(axis=0, ddof=0)
    scales = np.where(scales > 0, scales, 1.0)
    x = (x - means) / scales
    components = np.eye(x.shape[1])
    if pca_components is not None:
        _, _, vt = np.linalg.svd(x, full_matrices=False)
        components = vt[:pca_components].copy()
        # SVD signs are arbitrary; fix them for auditable deterministic output.
        for row in components:
            if row[np.argmax(np.abs(row))] < 0:
                row *= -1
    z = x @ components.T
    intercept = float(y.mean())
    beta = np.linalg.solve(z.T @ z + float(alpha) * np.eye(z.shape[1]), z.T @ (y - intercept))
    _require(np.isfinite(beta).all(), "Nonfinite model coefficients")
    return FittedRidge(medians, means, scales, components, beta, intercept, float(alpha), pca_components)


def _generation_entries(manifest, frame, decision_at=None):
    # This local registry never falls back to old Gold or archived generation.
    from engine.research_generation import validate_factor_inputs
    entries = frame.attrs.get("feature_entries")
    _require(isinstance(entries, list) and entries, "Explicit raw feature generation lineage required")
    approved = validate_factor_inputs(manifest, entries, expected_generation_id=manifest["generation_id"], decision_at=decision_at)
    _require([entry["factor_id"] for entry in approved] == [entry["factor_id"] for entry in manifest["approved_factors"]],
             "Exact ordered predeclared generation feature set required; no silent factor subset selection")
    return approved


def _validated_frame(frame, manifest, config):
    entries = _generation_entries(manifest, frame)
    features = [entry["factor_id"] for entry in entries]
    _require(features and len(set(features)) == len(features), "Unique approved feature IDs required")
    reserved = {"asset_id", "signal_month", "decision_at", "label_end_at", "label_available_at", "next_month_return", "_month", "_asset_sort"}
    _require(not set(features) & reserved and all(not feature.startswith(("fwd_", "label_"))
             and not feature.endswith("__known_at") for feature in features), "Labels and metadata cannot be feature IDs")
    config.validate(len(features))
    required = {"asset_id", "signal_month", "decision_at", "label_end_at", "label_available_at", "next_month_return", *features,
                *(f"{feature}__known_at" for feature in features)}
    _require(required.issubset(frame.columns), f"Missing required columns: {sorted(required - set(frame.columns))}")
    d = frame[list(required)].copy(deep=True)
    _require(not d.empty and d.asset_id.notna().all(), "Nonempty identified asset panel required")
    _require(not d.duplicated(["asset_id", "signal_month"]).any(), "Duplicate asset-month")
    d["_month"] = d.signal_month.map(_month)
    for field in ("decision_at", "label_end_at", "label_available_at"):
        d[field] = d[field].map(lambda value: _instant(value, field))
    for month, group in d.groupby("_month"):
        _require(group.decision_at.nunique() == 1, "A month must have one common signal decision cutoff")
        _require(group.decision_at.iloc[0].tz_convert("Asia/Seoul").strftime("%Y-%m") == str(month), "Signal month/decision mismatch")
        _require(all(value.tz_convert("Asia/Seoul").strftime("%Y-%m") == str(month + 1) for value in group.label_end_at), "Label must end in the next calendar month")
    _require((d.label_end_at > d.decision_at).all() and (d.label_available_at >= d.label_end_at).all(), "Invalid label availability chronology")
    for feature in features:
        field = f"{feature}__known_at"
        d[field] = d[field].map(lambda value: _instant(value, field))
        _require((d[field] <= d.decision_at).all(), f"Future feature unavailable at decision: {feature}")
        _require(((d.decision_at - d[field]) <= pd.Timedelta(days=config.max_feature_age_days)).all(), f"Stale feature: {feature}")
        d[feature] = pd.to_numeric(d[feature], errors="raise")
        _require(not np.isinf(d[feature].to_numpy(dtype=float)).any(), f"Infinite feature: {feature}")
    d["next_month_return"] = pd.to_numeric(d.next_month_return, errors="raise")
    # Use a stable asset ordering, not a result-dependent stock ranking.
    d["_asset_sort"] = d.asset_id.map(str)
    return d.sort_values(["_month", "_asset_sort"]).reset_index(drop=True), entries


def _eligible_training(d, prediction_month, cutoff, *, window, gap):
    # gap=1 excludes the immediately preceding signal month. Availability is
    # still mandatory even if delayed labels require a longer effective purge.
    upper = prediction_month - gap
    candidate = d.loc[d._month.lt(upper) & d._month.ge(upper - window)]
    usable_months, excluded = [], []
    for month, group in candidate.groupby("_month", sort=True):
        if (group.label_available_at < cutoff).all() and np.isfinite(group.next_month_return.to_numpy(dtype=float)).all():
            usable_months.append(month)
        else:
            excluded.append(str(month))
    return candidate.loc[candidate._month.isin(usable_months)].copy(), excluded


def _inner_folds(outer_train, config):
    months = sorted(outer_train._month.unique())
    folds = []
    block = config.inner_validation_months
    for number in range(config.inner_splits):
        end = len(months) - (config.inner_splits - 1 - number) * block
        validation_months = months[max(0, end - block):end]
        if len(validation_months) != block or list(pd.period_range(validation_months[0], validation_months[-1], freq="M")) != validation_months:
            continue
        validation = outer_train.loc[outer_train._month.isin(validation_months)]
        cutoff = validation.decision_at.min()
        train, excluded = _eligible_training(outer_train, validation_months[0], cutoff, window=config.inner_train_months, gap=config.purge_gap_months)
        if train._month.nunique() < config.min_train_months:
            continue
        folds.append((train, validation, {"train_months": sorted(train.signal_month.unique().tolist()),
            "validation_months": [str(month) for month in validation_months], "fit_cutoff": cutoff.isoformat(),
            "max_train_label_available_at": train.label_available_at.max().isoformat(), "unavailable_label_months_excluded": excluded}))
    _require(len(folds) == config.inner_splits, "Insufficient chronological inner training/validation support")
    return folds


def walk_forward_predict(frame, generation_manifest, config):
    """Predict each outer month without using its outcomes to fit, tune or score.

    Declared registry lineage is checked, but authenticated raw-artifact loading
    and genuine historical universe/label certification remain production hooks.
    A 2026 approval cannot be backdated to a 2018 forecast by this strict API.
    Target column types are validated; past realized labels can enter a later
    month's fit after their availability cutoff. No outer performance is scored.
    """
    d, entries = _validated_frame(frame, generation_manifest, config)
    features = [entry["factor_id"] for entry in entries]
    first = _month(config.first_test_month)
    last = _month(config.last_test_month) if config.last_test_month else d._month.max()
    requested_months = list(pd.period_range(first, last, freq="M"))
    observed_months = sorted(d.loc[d._month.between(first, last), "_month"].unique())
    _require(requested_months and observed_months == requested_months,
             "Missing requested outer prediction months; silent partial evaluation is forbidden")
    prediction_rows, audits = [], []
    for month in requested_months:
        test = d.loc[d._month.eq(month)]
        cutoff = test.decision_at.iloc[0]
        _generation_entries(generation_manifest, frame, decision_at=cutoff.isoformat())
        train, excluded = _eligible_training(d, month, cutoff, window=config.outer_train_months, gap=config.purge_gap_months)
        _require(train._month.nunique() >= config.min_train_months, "Insufficient outer training months")
        inner = _inner_folds(train, config)
        for _, _, audit in inner:
            _generation_entries(generation_manifest, frame, decision_at=audit["fit_cutoff"])
        trials = []
        for components in config.pca_components:
            for alpha in config.alphas:
                month_errors = []
                for fit, validation, _ in inner:
                    model = fit_ridge(fit[features].to_numpy(dtype=float), fit.next_month_return.to_numpy(dtype=float), alpha=alpha, pca_components=components)
                    errors = (model.predict(validation[features].to_numpy(dtype=float)) - validation.next_month_return.to_numpy(dtype=float)) ** 2
                    scored = pd.DataFrame({"month": validation.signal_month.to_numpy(), "error": errors})
                    month_errors.extend(scored.groupby("month").error.mean().tolist())
                trials.append({"alpha": float(alpha), "pca_components": components, "inner_month_balanced_mse": float(np.mean(month_errors))})
        # Stable predeclared grid order breaks exact ties, not test performance.
        best = min(trials, key=lambda trial: trial["inner_month_balanced_mse"])
        baseline = min((trial for trial in trials if trial["pca_components"] is None), key=lambda trial: trial["inner_month_balanced_mse"])
        pca_trials = [trial for trial in trials if trial["pca_components"] is not None]
        best_pca = min(pca_trials, key=lambda trial: trial["inner_month_balanced_mse"]) if pca_trials else None
        models = {}
        for name, trial in (("selected", best), ("ridge", baseline), ("pca", best_pca)):
            if trial is not None:
                models[name] = fit_ridge(train[features].to_numpy(dtype=float), train.next_month_return.to_numpy(dtype=float),
                    alpha=trial["alpha"], pca_components=trial["pca_components"])
        predictions = {name: model.predict(test[features].to_numpy(dtype=float)) for name, model in models.items()}
        for i, row in enumerate(test.itertuples()):
            prediction_rows.append({"asset_id": row.asset_id.item() if isinstance(row.asset_id, np.generic) else row.asset_id,
                "signal_month": str(month), "decision_at": cutoff.isoformat(),
                "prediction_selected": float(predictions["selected"][i]), "prediction_ridge_no_pca": float(predictions["ridge"][i]),
                "prediction_pca_ridge": float(predictions["pca"][i]) if "pca" in predictions else None})
        audits.append({"signal_month": str(month), "fit_cutoff": cutoff.isoformat(), "train_months": sorted(train.signal_month.unique().tolist()),
            "max_train_label_available_at": train.label_available_at.max().isoformat(), "unavailable_label_months_excluded": excluded,
            "inner_folds": [audit for _, _, audit in inner], "trials": trials, "selected": best,
            "models": {name: model.audit() for name, model in models.items()}, "test_labels_scored": False})
    _require(prediction_rows, "No requested outer prediction months")
    return {"schema_version": VERSION, "status": "RESEARCH_NUMERICAL_BASELINE_NOT_PRODUCTION",
        "generation_id": generation_manifest["generation_id"], "generation_sha256": generation_manifest["generation_sha256"],
        "feature_ids": features, "config": asdict(config), "config_sha256": _hash(asdict(config)),
        "predictions": prediction_rows, "folds": audits,
        "implementation": {"chronological_month_grouped_nested_folds": True, "availability_purge": "label_available_at < fit_cutoff",
            "preprocessing": "TRAIN_ONLY_MEDIAN_THEN_STANDARDIZATION_THEN_OPTIONAL_CHARACTERISTIC_PCA",
            "training_loss": "POOLED_STOCK_ROW_SSE_PLUS_ALPHA_L2_UNPENALIZED_INTERCEPT",
            "tuning_loss": "EQUAL_WEIGHT_MONTHLY_CROSS_SECTIONAL_MSE", "outer_test_metrics_computed": False,
            "raw_feature_content_authenticated": False, "lineage_validation": "EXACT_DECLARED_GENERATION_ENTRY_DIGESTS_ONLY",
            "random_row_cv": False, "sparse_factor_selection": False, "portfolio_optimization": False,
            "database_calls": 0, "gold_reads_or_writes": 0},
        "missing_production_hooks": ["AUTHENTICATED_RAW_FEATURE_ARTIFACT_LOADER", "HISTORICAL_UNIVERSE_AND_LABEL_CERTIFICATION",
            "IMMUTABLE_STRATEGY_PREREGISTRATION_AND_SEALED_OUTER_EVALUATION", "FACTOR_DIAGNOSTIC_AND_LESSON_REVIEW_LINKAGE",
            "EXECUTION_COSTS_TURNOVER_POSITION_CONSTRAINTS_AND_PORTFOLIO_OPTIMIZER"],
        "financial_claims": False}
