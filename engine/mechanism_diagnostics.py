"""Descriptive, availability-safe diagnostics for one already-oriented signal.

This module does not read data, construct future financial labels, tune signals,
or make promotion decisions. Callers must release the input sample beforehand
and certify that controls are point-in-time inputs. Returns and other outcomes
are usable only with an explicit ``<column>__known_at`` calendar date.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


MIN_MONTHS = 12
HAC_LAGS = 3
MAX_CATEGORY_LEVELS = 20
_REGIMES = {"UP_LOW", "UP_HIGH", "DOWN_LOW", "DOWN_HIGH", "UNKNOWN"}


def _section(status: str, data: Any, limitations: list[str]) -> dict:
    return {"status": status, "data": data, "limitations": list(dict.fromkeys(limitations))}


def _number(value: Any) -> float | None:
    return float(value) if value is not None and np.isfinite(value) else None


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def _month_index(values: Any, name: str) -> pd.PeriodIndex:
    try:
        result = pd.PeriodIndex(values, freq="M")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must contain monthly periods") from exc
    if result.isna().any():
        raise ValueError(f"{name} must not be missing")
    return result


def _rank_ic(signal: pd.Series, outcome: pd.Series) -> float | None:
    pair = pd.concat([signal, outcome], axis=1).dropna()
    if len(pair) < 3 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return None
    ranks = pair.rank(method="average")
    return _number(ranks.iloc[:, 0].corr(ranks.iloc[:, 1]))


def _groups(signal: pd.Series) -> pd.Series:
    """Fixed midpoint-rank bins: equal values are never split arbitrarily."""
    valid = signal.notna()
    result = pd.Series(np.nan, index=signal.index)
    n = int(valid.sum())
    if n:
        midpoint = (signal.loc[valid].rank(method="average") - 0.5) / n
        result.loc[valid] = np.floor(midpoint * 5).clip(0, 4) + 1
    return result


def _runs(months: list[pd.Period]) -> tuple[int, int]:
    if not months:
        return 0, 0
    ordered = sorted(set(months))
    runs, length, longest = 1, 1, 1
    for previous, current in zip(ordered, ordered[1:]):
        if current.ordinal == previous.ordinal + 1:
            length += 1
        else:
            runs += 1
            length = 1
        longest = max(longest, length)
    return runs, longest


def _uncertainty(records: list[dict], field: str) -> dict:
    """Newey-West uncertainty of the mean using months, never stock rows.

    Covariances use actual calendar distances. A missing month is not silently
    made adjacent to the previous observed month, nor filled with a return.
    """
    observed = [(pd.Period(row["month"], freq="M"), row.get(field)) for row in records]
    observed = [(month, float(value)) for month, value in observed
                if value is not None and np.isfinite(value)]
    months = [month for month, _ in observed]
    values = np.array([value for _, value in observed], dtype=float)
    n = len(values)
    runs, longest = _runs(months)
    result = {
        "method": "calendar_month_newey_west_bartlett_normal_95pct",
        "unit_of_observation": "calendar_month", "n_months": n,
        "minimum_months": MIN_MONTHS, "hac_lags": HAC_LAGS,
        "n_calendar_consecutive_runs": runs, "longest_consecutive_run": longest,
        "mean": _number(values.mean()) if n else None,
        "standard_error": None, "ci95": None,
        "status": "INSUFFICIENT_MONTHS" if n < MIN_MONTHS else "AVAILABLE",
    }
    if n < MIN_MONTHS:
        return result
    centered = {month.ordinal: value - values.mean() for month, value in observed}
    variance_sum = sum(value * value for value in centered.values())
    for lag in range(1, HAC_LAGS + 1):
        covariance_sum = sum(value * centered.get(month - lag, 0.0)
                             for month, value in centered.items())
        variance_sum += 2 * (1 - lag / (HAC_LAGS + 1)) * covariance_sum
    # The finite-sample correction gives sample-variance / n when lags are zero.
    se = np.sqrt(max(0.0, variance_sum) / (n * (n - 1)))
    result["standard_error"] = float(se)
    result["ci95"] = [float(values.mean() - 1.96 * se), float(values.mean() + 1.96 * se)]
    return result


def _mask_outcome(data: pd.DataFrame, name: str, cutoff_end: pd.Timestamp) -> tuple[pd.Series, dict]:
    missing = pd.Series(np.nan, index=data.index, dtype=float)
    known_name = f"{name}__known_at"
    info = {
        "name": name, "value_column_present": name in data,
        "availability_column_present": known_name in data,
        "n_rows": len(data), "n_finite_values": 0, "n_available": 0,
        "n_missing_or_invalid_known_at": 0, "n_late_known_at": 0,
        "status": "NOT_COLLECTED",
    }
    if name not in data:
        return missing, info
    values = _numeric(data[name])
    info["n_finite_values"] = int(values.notna().sum())
    if known_name not in data:
        info["n_missing_or_invalid_known_at"] = info["n_finite_values"]
        return missing, info
    try:
        # Raw integers are not dates in this contract. Pandas otherwise treats
        # them as nanoseconds after 1970 and could accidentally release labels.
        date_input = data[known_name].map(
            lambda value: None if isinstance(value, (int, float, np.number)) else value
        )
        known = pd.to_datetime(date_input, errors="coerce", format="mixed")
        if known.dt.tz is not None:
            raise ValueError(f"{known_name} must use timezone-naive dates")
    except (AttributeError, TypeError) as exc:
        raise ValueError(f"{known_name} must use timezone-naive dates") from exc
    info["n_missing_or_invalid_known_at"] = int((values.notna() & known.isna()).sum())
    info["n_late_known_at"] = int((values.notna() & (known > cutoff_end)).sum())
    masked = values.where(known.notna() & (known <= cutoff_end))
    info["n_available"] = int(masked.notna().sum())
    if info["n_available"]:
        info["status"] = "AVAILABLE" if masked.notna().all() else "PARTIAL"
    return masked, info


def _monthly_outcome(data: pd.DataFrame, signal: str, values: pd.Series) -> list[dict]:
    records = []
    for month, block in data.groupby("ym", sort=True):
        outcome = values.loc[block.index]
        signal_valid = block[signal].notna()
        pairs = signal_valid & outcome.notna()
        groups = []
        for group in range(1, 6):
            members = block["_diagnostic_group"].eq(group)
            available = members & outcome.notna()
            n_members, n_available = int(members.sum()), int(available.sum())
            groups.append({
                "group": group, "n_signal": n_members, "n_available": n_available,
                "missing_fraction": 1 - n_available / n_members if n_members else None,
                "mean": _number(outcome.loc[available].mean()) if n_available else None,
            })
        bottom, top = groups[0]["mean"], groups[-1]["mean"]
        records.append({
            "month": str(month), "n_rows": len(block),
            "n_signal": int(signal_valid.sum()), "n_outcome_available": int(outcome.notna().sum()),
            "n_pairs": int(pairs.sum()),
            "pair_coverage": float(pairs.mean()), "groups": groups,
            "rank_ic": _rank_ic(block[signal], outcome),
            "bottom_mean": bottom, "top_mean": top,
            "top_minus_bottom": top - bottom if top is not None and bottom is not None else None,
        })
    return records


def _outcome_summary(records: list[dict], *, inference: bool = True) -> dict:
    result = {
        "monthly": records,
        "rank_ic": _uncertainty(records, "rank_ic"),
        "top_minus_bottom": _uncertainty(records, "top_minus_bottom"),
    }
    if not inference:
        for field in ("rank_ic", "top_minus_bottom"):
            result[field].update({
                "method": "descriptive_monthly_mean_only", "hac_lags": None,
                "standard_error": None, "ci95": None,
                "status": "DESCRIPTIVE_ONLY_HORIZON_NOT_CONFIGURED",
            })
    return result


def _control_types(data: pd.DataFrame, controls: list[str]) -> dict[str, str]:
    types = {}
    for control in controls:
        if control not in data:
            continue
        column = data[control]
        observed = column.dropna()
        is_numeric = pd.api.types.is_numeric_dtype(column) and not pd.api.types.is_bool_dtype(column)
        if not observed.empty and not pd.api.types.is_bool_dtype(column):
            is_numeric = is_numeric or pd.to_numeric(observed, errors="coerce").notna().all()
        types[control] = "numeric" if is_numeric else "categorical"
    return types


def _selection(data: pd.DataFrame, controls: list[str], types: dict[str, str]) -> dict:
    limitations = ["Controls must be explicitly certified point-in-time inputs by the caller."]
    if not controls:
        return _section("NOT_COLLECTED", {"controls": []}, ["No controls were requested."])
    profiles = []
    partial = False
    any_values = False
    for control in controls:
        if control not in types:
            profiles.append({"name": control, "status": "NOT_COLLECTED", "monthly": []})
            partial = True
            continue
        monthly = []
        for month, block in data.groupby("ym", sort=True):
            block = block.loc[block["_diagnostic_group"].notna()]
            column = _numeric(block[control]) if types[control] == "numeric" else block[control]
            ranks = column.rank(method="average", pct=True) if types[control] == "numeric" else None
            group_rows = []
            for group in range(1, 6):
                selected = block["_diagnostic_group"].eq(group)
                observed = column.loc[selected].dropna()
                row = {"group": group, "n_signal": int(selected.sum()), "n_available": len(observed)}
                any_values |= bool(len(observed))
                partial |= len(observed) < int(selected.sum())
                if ranks is not None:
                    row["mean_percentile_rank"] = _number(ranks.loc[selected].mean())
                else:
                    counts = observed.astype(str).value_counts()
                    # A fixed bound prevents identifiers masquerading as categories
                    # from releasing company-level rows in an enormous profile.
                    kept = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:MAX_CATEGORY_LEVELS]
                    row["category_shares"] = [
                        {"category": category, "n": int(n), "share": n / len(observed)}
                        for category, n in kept
                    ]
                    row["n_other_categories"] = max(0, len(counts) - len(kept))
                    row["n_other_observations"] = len(observed) - sum(n for _, n in kept)
                    if len(counts) > MAX_CATEGORY_LEVELS:
                        partial = True
                        limitations.append("Categorical profiles retain at most 20 levels per group; the remainder is counted separately.")
                group_rows.append(row)
            monthly.append({"month": str(month), "groups": group_rows})
        profiles.append({"name": control, "type": types[control], "monthly": monthly})
    status = "NOT_COLLECTED" if not any_values else ("PARTIAL" if partial else "AVAILABLE")
    return _section(status, {"controls": profiles}, limitations)


def _controlled(data: pd.DataFrame, signal: str, returns: pd.Series,
                controls: list[str], types: dict[str, str]) -> dict:
    limitations = [
        "Association, not causality: omitted variables, measurement error and selection can remain.",
        "Raw and adjusted rank correlations use the identical complete-case sample within each month.",
        "OLS removes linear numeric-control and categorical-level associations from signal and return; residuals are then ranked.",
        "Controls are caller-certified PIT inputs; their historical availability is not inferred here.",
        "Summary uncertainty uses matched calendar-month aggregates with three-lag HAC and at least 12 months, never stock-level pseudoreplication or a p-value gate.",
    ]
    if not controls or any(control not in types for control in controls):
        return _section("NOT_COLLECTED", {"monthly": []}, limitations + ["All requested controls must be present and explicitly chosen."])
    records = []
    for month, block in data.groupby("ym", sort=True):
        numeric = {control: _numeric(block[control]) for control in controls if types[control] == "numeric"}
        complete = block[signal].notna() & returns.loc[block.index].notna()
        for control in controls:
            complete &= (numeric[control] if control in numeric else block[control]).notna()
        common = block.loc[complete]
        n = len(common)
        row = {"month": str(month), "n_signal_return_pairs": int((block[signal].notna() & returns.loc[block.index].notna()).sum()),
               "n_common": n, "n_regressors": 0, "design_rank": None,
               "minimum_n": 30, "raw_rank_ic": None, "adjusted_rank_ic": None,
               "adjusted_minus_raw": None, "status": "INSUFFICIENT_SAMPLE"}
        columns = []
        excessive_categories = False
        for control in controls:
            if control in numeric:
                values = numeric[control].loc[common.index].to_numpy(dtype=float)
                if n and np.std(values) > 0:
                    columns.append(((values - values.mean()) / values.std()).reshape(-1, 1))
            else:
                values = common[control].astype(str)
                if values.nunique() > MAX_CATEGORY_LEVELS:
                    excessive_categories = True
                    break
                dummies = pd.get_dummies(values, drop_first=True, dtype=float).to_numpy()
                if dummies.shape[1]:
                    columns.append(dummies)
        if excessive_categories:
            row["status"] = "TOO_MANY_CATEGORICAL_LEVELS"
            records.append(row)
            continue
        covariates = np.column_stack(columns) if columns else np.empty((n, 0))
        k = covariates.shape[1]
        row["n_regressors"], row["minimum_n"] = k, max(30, k + 5)
        if n < row["minimum_n"]:
            records.append(row)
            continue
        design = np.column_stack([np.ones(n), covariates])
        targets = np.column_stack([common[signal].to_numpy(dtype=float), returns.loc[common.index].to_numpy(dtype=float)])
        coefficients, _, rank, _ = np.linalg.lstsq(design, targets, rcond=None)
        residuals = targets - design @ coefficients
        row["design_rank"] = int(rank)
        row["raw_rank_ic"] = _rank_ic(pd.Series(targets[:, 0]), pd.Series(targets[:, 1]))
        # An exactly explained target has no residual rank; floating-point dust
        # must not create a spurious rank correlation.
        residual_variation = np.std(residuals, axis=0) > 1e-10 * np.maximum(np.std(targets, axis=0), 1e-12)
        if residual_variation.all():
            row["adjusted_rank_ic"] = _rank_ic(pd.Series(residuals[:, 0]), pd.Series(residuals[:, 1]))
        if row["raw_rank_ic"] is not None and row["adjusted_rank_ic"] is not None:
            row["adjusted_minus_raw"] = row["adjusted_rank_ic"] - row["raw_rank_ic"]
            row["status"] = "AVAILABLE"
        else:
            row["status"] = "NO_RESIDUAL_OR_RANK_VARIATION"
        records.append(row)
    available = sum(row["status"] == "AVAILABLE" for row in records)
    status = "NOT_COLLECTED" if not available else ("AVAILABLE" if available == len(records) else "PARTIAL")
    comparable = [row for row in records if row["status"] == "AVAILABLE"]
    return _section(status, {"monthly": records,
                            "raw_rank_ic": _uncertainty(comparable, "raw_rank_ic"),
                            "adjusted_rank_ic": _uncertainty(comparable, "adjusted_rank_ic"),
                            "adjusted_minus_raw": _uncertainty(comparable, "adjusted_minus_raw")}, limitations)


def _regime_episode_ids(context: pd.DataFrame, dimension: str) -> dict[str, int | None]:
    """Observed state transitions, never episodes invented by missing outcomes.

    UNKNOWN or absent months cannot establish a new occurrence of the same
    state. Require an observed different state between occurrences.
    """
    previous, episode = None, 0
    result = {}
    for row in context.sort_values("month").to_dict(orient="records"):
        label = row[dimension]
        if dimension == "regime" and row["status"] != "READY":
            label = "UNKNOWN"
        if label == "UNKNOWN":
            result[str(row["month"])] = None
            continue
        if label != previous:
            episode += 1
        previous = label
        result[str(row["month"])] = episode
    return result


def _regime_summary(monthly: list[dict], dimension: str, labels: set[str],
                    episode_ids: dict[str, int | None]) -> list[dict]:
    from engine.regimes import RULES

    summaries = []
    for label in sorted(labels):
        selected = [row for row in monthly if row[dimension] == label]
        episodes, longest = _runs([pd.Period(row["month"], freq="M") for row in selected])
        usable = [row for row in selected if row["rank_ic"] is not None and row["top_minus_bottom"] is not None]
        usable_episodes = len({episode_ids[row["month"]] for row in usable
                               if episode_ids.get(row["month"]) is not None})
        sufficient = (label != "UNKNOWN" and len(usable) >= RULES["minimum_descriptive_months"]
                      and usable_episodes >= RULES["minimum_descriptive_episodes"])
        row = {dimension: label, "n_months": len(selected), "n_episodes": episodes,
               "longest_episode_months": longest,
               "n_months_with_returns": sum(item["n_pairs"] > 0 for item in selected),
               "n_joint_usable_months": len(usable), "n_joint_usable_episodes": usable_episodes,
               "n_observed_state_episodes": len({episode_ids[row["month"]] for row in selected
                                                  if episode_ids.get(row["month"]) is not None}),
               "support": ("UNKNOWN_CONTEXT" if label == "UNKNOWN" else
                           "DESCRIPTIVE_SUPPORT_ONLY" if sufficient else "INSUFFICIENT_SUPPORT"),
               "rank_ic": _uncertainty(selected, "rank_ic"),
               "top_minus_bottom": _uncertainty(selected, "top_minus_bottom")}
        if not sufficient:
            for metric in ("rank_ic", "top_minus_bottom"):
                row[metric].update({"status": "INSUFFICIENT_REGIME_SUPPORT", "ci95": None,
                                    "standard_error": None})
        summaries.append(row)
    return summaries


def _regime_comparison(regimes: pd.DataFrame | None, performance: list[dict]) -> dict:
    from engine.regimes import RULES, RULE_HASHES, TREND_PHASES, VOLATILITY_PHASES, detailed_regime

    limitations = [
        "A month-t regime is the prior month-end state for the t+1 return; it is not a label for return in month t.",
        "Regime months and consecutive episodes are descriptive support counts, not independent stock observations.",
        "Support counts require observed different states between episodes; missing returns or UNKNOWN gaps do not manufacture repeated regimes.",
        "UNKNOWN is kept separate; labels are never forward-filled.",
        "Uncertainty uses calendar-distance three-lag HAC with at least 12 months; episodes are not treated as independent trials.",
        "Inspect marginal axes and coarse states before sixteen detail cells; do not select the best-performing cell.",
        "Fewer than twelve jointly usable months or three observed episodes is insufficient descriptive support; intervals are suppressed, not a failed factor gate.",
        "Multiple overlapping views are exploratory, not independent replications or multiplicity-corrected significance tests.",
    ]
    if regimes is None:
        return _section("NOT_COLLECTED", {"monthly": [], "regimes": [], "views": {}, "classification_rules": []},
                        limitations + ["No regime data supplied."])
    required = {"month", "effective_month", "regime", "status"}
    if not required.issubset(regimes.columns):
        raise ValueError(f"Regimes require {sorted(required)}")
    axes = {"trend_long": {"UP", "DOWN", "UNKNOWN"}, "trend_short": {"UP", "DOWN", "UNKNOWN"},
            "volatility_long": {"HIGH", "LOW", "UNKNOWN"}, "volatility_short": {"HIGH", "LOW", "UNKNOWN"}}
    dimensions = {**axes, "trend_phase": set(TREND_PHASES.values()) | {"UNKNOWN"},
                  "volatility_phase": set(VOLATILITY_PHASES.values()) | {"UNKNOWN"},
                  "regime_detail": {detailed_regime(lt, st, lv, sv) for lt in ("UP", "DOWN")
                                    for st in ("UP", "DOWN") for lv in ("HIGH", "LOW")
                                    for sv in ("HIGH", "LOW")} | {"UNKNOWN"}}
    extended = bool(set(dimensions) & set(regimes.columns))
    metadata = {"rules_version", "rules_sha256"}
    if extended and not (set(dimensions) | metadata | {"detail_status"}).issubset(regimes.columns):
        raise ValueError("Detailed regimes require all axes, phases and versioned rules")
    if metadata & set(regimes.columns) and not metadata.issubset(regimes.columns):
        raise ValueError("Regime rules require both version and hash")
    selected_columns = required | (set(dimensions) | {"detail_status"} if extended else set())
    selected_columns |= (metadata | {"market_id", "source_id"}) & set(regimes.columns)
    context = regimes[list(sorted(selected_columns))].copy()
    classification_rules = []
    if metadata.issubset(context.columns):
        unique = context[["rules_version", "rules_sha256"]].drop_duplicates()
        if len(unique) != 1:
            raise ValueError("Do not mix regime rules within a comparison")
        version, sha = unique.iloc[0]
        if RULE_HASHES.get(version) != sha or (extended and version != RULES["version"]):
            raise ValueError("Regime rules hash/version mismatch")
        if version == RULES["version"] and not extended:
            raise ValueError("V2 regime requires detailed axes")
        classification_rules = [{"version": version, "sha256": sha}]
    for field in ("market_id", "source_id"):
        if field in context and (context[field].isna().any() or context[field].nunique() != 1):
            raise ValueError("Do not mix regime market/source identities")
    context["month"] = _month_index(context["month"], "regime month")
    context["effective_month"] = _month_index(context["effective_month"], "regime effective_month")
    if context["month"].duplicated().any() or context["effective_month"].duplicated().any():
        raise ValueError("Duplicate regime month or effective_month")
    if (context["effective_month"] != context["month"] + 1).any():
        raise ValueError("Regime effective_month must equal signal month + 1")
    if context["regime"].isna().any() or not set(context["regime"]).issubset(_REGIMES):
        raise ValueError("Unsupported regime label")
    if not set(context["status"]).issubset({"READY", "INSUFFICIENT_DATA"}):
        raise ValueError("Unsupported regime status")
    if extended:
        for key, allowed in dimensions.items():
            if not set(context[key]).issubset(allowed):
                raise ValueError("Unsupported detailed regime label")
        for row in context.to_dict(orient="records"):
            lt, st, lv, sv = (row[key] for key in axes)
            detail = detailed_regime(lt, st, lv, sv)
            coarse = f"{lt}_{lv}" if lt != "UNKNOWN" and lv != "UNKNOWN" else "UNKNOWN"
            if (row["regime_detail"] != detail or row["regime"] != coarse
                or row["trend_phase"] != TREND_PHASES.get((lt, st), "UNKNOWN")
                or row["volatility_phase"] != VOLATILITY_PHASES.get((lv, sv), "UNKNOWN")
                or (row["detail_status"] == "READY") != (detail != "UNKNOWN")
                or (row["status"] == "READY") != (coarse != "UNKNOWN")
                or row["detail_status"] not in {"READY", "INSUFFICIENT_DATA"}):
                raise ValueError("Detailed regime labels contradict axes/status")
    lookup = context.set_index("month").to_dict(orient="index")
    monthly = []
    for record in performance:
        month = pd.Period(record["month"], freq="M")
        state = lookup.get(month)
        ready = state is not None and state["status"] == "READY" and state["regime"] != "UNKNOWN"
        monthly.append({"month": str(month), "effective_month": str(month + 1),
                        "regime": state["regime"] if ready else "UNKNOWN",
                        "regime_status": str(state["status"]) if state is not None else "NOT_COLLECTED",
                        "rank_ic": record["rank_ic"], "top_minus_bottom": record["top_minus_bottom"],
                        "n_pairs": record["n_pairs"]})
        if extended:
            monthly[-1].update({key: state[key] if state is not None else "UNKNOWN" for key in dimensions})
    summaries = _regime_summary(monthly, "regime", {row["regime"] for row in monthly},
                                _regime_episode_ids(context, "regime"))
    views = {key: _regime_summary(monthly, key, labels, _regime_episode_ids(context, key))
             for key, labels in dimensions.items()} if extended else {}
    known = sum(row["regime"] != "UNKNOWN" and row["n_pairs"] > 0 for row in monthly)
    if extended:
        any_known = any(row[key] != "UNKNOWN" and row["n_pairs"] > 0 for row in monthly for key in axes)
        all_known = bool(monthly) and all(row["regime_detail"] != "UNKNOWN" and row["n_pairs"] > 0 for row in monthly)
        status = "AVAILABLE" if all_known else "PARTIAL" if any_known else "NOT_COLLECTED"
    else:
        status = "NOT_COLLECTED" if not known else ("AVAILABLE" if known == len(monthly) else "PARTIAL")
    return _section(status, {"monthly": monthly, "regimes": summaries, "views": views,
                            "classification_rules": classification_rules,
                            "reading_order": [*axes, "regime", "trend_phase", "volatility_phase", "regime_detail"],
                            "support_policy": {"minimum_months": RULES["minimum_descriptive_months"],
                                               "minimum_episodes": RULES["minimum_descriptive_episodes"]}}, limitations)


def build_diagnostics(frame: pd.DataFrame, *, signal: str, forward_return: str,
                      controls: list[str], outcomes: list[str], as_of: str,
                      regimes: pd.DataFrame | None = None) -> dict:
    """Return JSON-safe descriptive sections without reading or mutating inputs.

    ``asset_id`` and ``ym`` must uniquely identify an asset/signal-month row.
    ``signal`` is already oriented high=favorable. Only completed signal months
    are included. Unknown/late outcome availability is always masked, including
    when all values appear otherwise complete. No future shifts are generated.
    """
    if not frame.columns.is_unique:
        raise ValueError("Duplicate column names")
    required = {"asset_id", "ym", signal}
    if not required.issubset(frame.columns):
        raise ValueError(f"Required columns: {sorted(required)}")
    if signal in {"asset_id", "ym"} or forward_return in {signal, "asset_id", "ym"}:
        raise ValueError("Signal and forward return must be distinct non-key columns")
    controls, outcomes = list(dict.fromkeys(controls)), list(dict.fromkeys(outcomes))
    forbidden_controls = {signal, forward_return, "asset_id", "ym", *outcomes}
    if any(control in forbidden_controls or control.endswith("__known_at") for control in controls):
        raise ValueError("Controls must exclude the signal, keys, outcomes and availability metadata")
    if any(outcome in {signal, "asset_id", "ym"} for outcome in outcomes):
        raise ValueError("Economic outcomes must be distinct from the signal and keys")
    cutoff = pd.Timestamp(as_of)
    if pd.isna(cutoff) or cutoff.tzinfo is not None or cutoff != cutoff.normalize():
        raise ValueError("as_of must be a timezone-naive calendar date")
    cutoff_end = cutoff + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    data = frame.copy().reset_index(drop=True)
    data["ym"] = _month_index(data["ym"], "ym")
    if data["asset_id"].isna().any():
        raise ValueError("asset_id must not be missing")
    if data.duplicated(["asset_id", "ym"]).any():
        raise ValueError("Duplicate asset-month keys")
    n_input = len(data)
    data = data.loc[data["ym"].dt.end_time <= cutoff_end].copy()
    data[signal] = _numeric(data[signal])
    data["_diagnostic_group"] = data.groupby("ym", sort=False)[signal].transform(_groups)
    values, availability = {}, {}
    for name in dict.fromkeys([forward_return, *outcomes]):
        values[name], availability[name] = _mask_outcome(data, name, cutoff_end)
    types = _control_types(data, controls)
    missing_controls = [control for control in controls if control not in data]
    limitations = [
        "Input sample release and historical PIT certification are caller responsibilities; this engine is not a sealed-data access gate.",
        "Signal is assumed pre-oriented high=favorable; no direction selection or tuning is performed.",
        "Only completed signal months are retained; outcomes need their own explicit known_at date by as_of.",
    ]
    quality = {
        "schema_version": "mechanism-diagnostics-v1", "purpose": "DESCRIPTIVE_ASSOCIATION_ONLY",
        "as_of": str(cutoff.date()), "signal": signal, "forward_return": forward_return,
        "n_input_rows": n_input, "n_included_rows": len(data),
        "n_excluded_unfinished_or_future_signal_rows": n_input - len(data),
        "n_months": int(data["ym"].nunique()), "n_assets": int(data["asset_id"].nunique()),
        "n_signal_available": int(data[signal].notna().sum()),
        "missing_controls": missing_controls, "outcome_availability": list(availability.values()),
        "group_rule": "five fixed midpoint-rank bins, average ranks for ties; ties are never split",
    }
    quality_complete = (len(data) > 0 and data[signal].notna().all() and not missing_controls
                        and all(info["status"] == "AVAILABLE" for info in availability.values()))
    quality_status = "AVAILABLE" if quality_complete else ("PARTIAL" if len(data) else "NOT_COLLECTED")
    monthly = _monthly_outcome(data, signal, values[forward_return])
    performance_status = availability[forward_return]["status"]
    if not any(row["n_pairs"] for row in monthly):
        performance_status = "NOT_COLLECTED"
    elif any(row["rank_ic"] is None or row["top_minus_bottom"] is None or row["pair_coverage"] < 1 for row in monthly):
        performance_status = "PARTIAL"
    economic = []
    for outcome in outcomes:
        records = _monthly_outcome(data, signal, values[outcome])
        outcome_status = availability[outcome]["status"]
        if not any(row["n_pairs"] for row in records):
            outcome_status = "NOT_COLLECTED"
        elif any(row["rank_ic"] is None or row["top_minus_bottom"] is None or row["pair_coverage"] < 1 for row in records):
            outcome_status = "PARTIAL"
        economic.append({"name": outcome, "status": outcome_status,
                         "availability": availability[outcome], **_outcome_summary(records, inference=False)})
    economic_statuses = [item["status"] for item in economic]
    economic_status = ("NOT_COLLECTED" if not economic_statuses or all(status == "NOT_COLLECTED" for status in economic_statuses)
                       else "AVAILABLE" if all(status == "AVAILABLE" for status in economic_statuses) else "PARTIAL")
    common_limits = [
        "Equal-weight groups are descriptively reformed monthly, not holdings or an executable backtest; costs and turnover are unavailable.",
        "Missing outcomes may be selective; each group reports available counts and missing fractions.",
        "Ties may leave groups empty or unequal; absent extremes do not produce a top-minus-bottom spread.",
        "Uncertainty uses calendar-month aggregates, requires 12 observed months, and is not a p-value or promotion gate.",
        "Three-lag HAC is descriptive and may understate dependence for longer or overlapping outcome horizons; horizon-specific preregistered inference is not supplied.",
    ]
    return {
        "input_quality": _section(quality_status, quality, limitations),
        "selection_profile": _selection(data, controls, types),
        "economic_outcomes": _section(economic_status, {"outcomes": economic}, common_limits + [
            "Only explicitly supplied forward outcomes are used; no future financial shifts or proxies are constructed.",
            "Economic-outcome standard errors and confidence intervals are suppressed: outcome horizons and overlapping-window dependence are not configured.",
        ]),
        "monthly_performance": _section(performance_status, _outcome_summary(monthly), common_limits),
        "controlled_comparison": _controlled(data, signal, values[forward_return], controls, types),
        "regime_comparison": _regime_comparison(regimes, monthly),
    }
