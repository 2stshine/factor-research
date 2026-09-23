"""Descriptive input profiles; never infer a factor's runtime dependencies.

The caller supplies an already scoped Discovery sample. This module neither
loads data nor executes candidate code, and does not certify input units/PIT.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


VERSION = "raw-input-profile-v2"
# Common certified price-panel fields, not proof that a particular factor read
# them. Ex-post total_return_close/fwd_* labels and raw close are excluded.
COMMON_MARKET_FIELDS = (
    "adj_close", "adv20", "market_cap", "trading_value", "shares",
    "amihud_illiquidity_1m", "amihud_observations_1m",
    "daily_volatility_252d", "daily_return_observations_252d",
    "max_daily_return_1m", "max_daily_return_observations_1m",
    "price_high_252d", "price_high_observations_252d",
)
CONTROL_SOURCES = {"market": "market", "market_cap": "log_market_cap", "adv20": "log_adv20"}


def profile_contract(declared_inputs, control_sources):
    return {
        "schema_version": VERSION,
        "sample": "frozen_discovery_investable_signal_month_rows; no OOS/embargo",
        "history_scope": "formation-row distributions, not every trailing-window observation",
        "declared_factor_inputs": list(dict.fromkeys(declared_inputs)),
        "common_market_fields": list(COMMON_MARKET_FIELDS),
        "auxiliary_control_sources": dict(control_sources),
        "factor_runtime_input_usage": "NOT_TRACED",
        "count_semantics": {
            "n_rows": "eligible formation rows; not independent observations",
            "n_missing": "original null values in a present column",
            "n_nonnumeric": "non-null values not accepted as numeric, including booleans",
            "n_nonfinite": "numeric positive/negative infinity; original nulls counted separately",
            "n_present": "finite numeric values (legacy name retained)",
            "n_missing_or_nonnumeric": "legacy aggregate of null, nonnumeric, and nonfinite values",
            "n_zero": "finite exact zeros; not automatically an error",
            "quantiles": "0.01, 0.5, 0.99 of finite numeric values only, without imputation",
        },
        "missing_column_semantics": "NOT_COLLECTED with null distribution counts, not observed all-null rows",
        "unit_semantics": "UNKNOWN unless independently supplied by a versioned source contract; no unit inferred from names",
    }


def build_input_profiles(data, declared_inputs, control_sources):
    """Profile declared/common/control sources once, preserving their roles."""
    declared = tuple(dict.fromkeys(declared_inputs))
    fields = tuple(dict.fromkeys((*declared, *COMMON_MARKET_FIELDS, *control_sources)))
    profiles = []
    for column in fields:
        roles = []
        if column in declared:
            roles.append("DECLARED_FACTOR_INPUT")
        if column in COMMON_MARKET_FIELDS:
            roles.append("COMMON_MARKET_INPUT")
        if column in control_sources:
            roles.append("AUXILIARY_CONTROL_SOURCE")
        categorical = column == "market"
        row = {
            "name": column, "roles": roles,
            "factor_usage": "DECLARED_NOT_RUNTIME_TRACED" if column in declared else "NOT_ESTABLISHED",
            "auxiliary_control": control_sources.get(column),
            "profile_type": "CATEGORICAL" if categorical else "NUMERIC",
            "unit": "NOT_APPLICABLE" if categorical else "UNKNOWN",
            "unit_basis": "category label" if categorical else "NOT_SUPPLIED_BY_CAPTURE_CONTRACT",
            "column_present": column in data, "n_rows": len(data),
            "status": "NOT_COLLECTED", "n_missing": None,
            "n_present": None, "n_nonnumeric": None, "n_nonfinite": None,
            "n_missing_or_nonnumeric": None, "n_zero": None,
            "quantiles": {str(q): None for q in (.01, .5, .99)},
        }
        if column in data:
            raw = data[column]
            row["n_missing"] = int(raw.isna().sum())
            if categorical:
                row.update(status="AVAILABLE" if raw.notna().any() else "NO_OBSERVATIONS",
                           n_nonmissing=int(raw.notna().sum()), n_unique=int(raw.nunique(dropna=True)))
            else:
                booleans = raw.map(lambda value: isinstance(value, (bool, np.bool_)))
                numeric = pd.to_numeric(raw.mask(booleans), errors="coerce")
                finite = numeric.notna() & np.isfinite(numeric)
                row.update(
                    status="AVAILABLE" if finite.any() else "NO_FINITE_VALUES",
                    n_present=int(finite.sum()),
                    n_nonnumeric=int((raw.notna() & numeric.isna()).sum()),
                    n_nonfinite=int((numeric.notna() & ~np.isfinite(numeric)).sum()),
                    n_missing_or_nonnumeric=int((~finite).sum()),
                    n_zero=int(numeric.loc[finite].eq(0).sum()),
                    quantiles={str(q): float(numeric.loc[finite].quantile(q)) if finite.any() else None
                               for q in (.01, .5, .99)},
                )
        profiles.append(row)
    return profiles
