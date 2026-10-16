"""Seeded synthetic diagnostic laboratory; no market data, I/O, or gate calls.

Only ``public_case`` and ``run`` belong to the researcher interface. ``oracle``
is a grader interface, not evidence. Python privacy is logical isolation only;
the harness must not give an untrusted researcher the lab object or its source.
All uncertainty is descriptive monthly HAC, not sequential inference or proof
of an economic mechanism. Nothing here authorizes real-data research.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np


DIAGNOSTIC_CATALOG = {
    "input_audit": {"cost": 1, "description": "Check keys, missingness and formation-time availability."},
    "association": {"cost": 2, "description": "Measure monthly rank association and gross top-minus-bottom spread."},
    "controls": {"cost": 3, "description": "Compare association on one sample with sector, size and liquidity controls."},
    "execution_cost": {"cost": 3, "description": "Subtract turnover-based costs from fixed-portfolio gross returns."},
    "regime_interaction": {"cost": 3, "description": "Estimate the direct difference in controlled slopes across regimes."},
    "economic_link": {"cost": 3, "description": "Inspect optional economic outcomes; observational evidence only."},
}
SCENARIOS = (
    "clean", "lookahead", "sector_confounding", "exposure_confounding",
    "costs", "regime", "mixed", "weak", "mechanism_missing",
)
FINDING_IDS = (
    "LOOKAHEAD", "SECTOR_EXPOSURE", "SIZE_LIQUIDITY_EXPOSURE", "COST_ERASURE",
    "REGIME_DEPENDENCE", "NO_CLEAR_EFFECT", "MECHANISM_UNIDENTIFIED",
)
_TRUTHS = {
    "clean": ([], ["ASSOCIATION_REMAINS"]),
    "lookahead": (["LOOKAHEAD"], ["INPUT_INVALID"]),
    "sector_confounding": (["SECTOR_EXPOSURE"], ["EXPLAINED_BY_EXPOSURES"]),
    "exposure_confounding": (["SIZE_LIQUIDITY_EXPOSURE"], ["EXPLAINED_BY_EXPOSURES"]),
    "costs": (["COST_ERASURE"], ["COST_ERASED"]),
    "regime": (["REGIME_DEPENDENCE"], ["CONDITIONAL"]),
    "mixed": (["SECTOR_EXPOSURE", "SIZE_LIQUIDITY_EXPOSURE", "COST_ERASURE", "REGIME_DEPENDENCE"],
              ["MIXED", "COST_ERASED", "CONDITIONAL"]),
    "weak": (["NO_CLEAR_EFFECT"], ["INCONCLUSIVE"]),
    "mechanism_missing": (["MECHANISM_UNIDENTIFIED"], ["ASSOCIATION_REMAINS", "NEEDS_DATA"]),
}
_LIMITS = [
    "Synthetic development evidence; no real-market or independent-OOS claim.",
    "Monthly HAC intervals are descriptive under adaptive inspection; no sequential error-control guarantee.",
    "Observed associations and controls do not identify an economic causal mechanism.",
]


def _z(values: np.ndarray) -> np.ndarray:
    centered = values - values.mean(axis=-1, keepdims=True)
    return centered / np.maximum(values.std(axis=-1, keepdims=True), 1e-12)


def _rank(values: np.ndarray) -> np.ndarray:
    # Generated signals/outcomes are continuous, so there are no tied ranks.
    return np.argsort(np.argsort(values, axis=-1), axis=-1).astype(float)


def _ar(rng: np.random.Generator, shape: tuple[int, ...], rho: float) -> np.ndarray:
    values = rng.normal(size=shape)
    for t in range(1, shape[0]):
        values[t] = rho * values[t - 1] + np.sqrt(1 - rho * rho) * values[t]
    return values


def _estimate(values: np.ndarray, design: np.ndarray | None = None,
              coefficient: int = 0) -> dict[str, Any]:
    """OLS HAC on monthly values; missing/group months retain calendar spacing."""
    y = np.asarray(values, dtype=float)
    x = np.ones((len(y), 1)) if design is None else np.asarray(design, dtype=float)
    valid = np.isfinite(y) & np.isfinite(x).all(axis=1)
    n, k = int(valid.sum()), x.shape[1]
    result = {"mean": None, "standard_error": None, "ci95": None, "n_months": n,
              "method": "monthly_hac_bartlett_3_descriptive"}
    if n <= k or np.linalg.matrix_rank(x[valid]) < k:
        return result
    beta = np.linalg.lstsq(x[valid], y[valid], rcond=None)[0]
    scores = np.zeros_like(x)
    scores[valid] = x[valid] * (y[valid] - x[valid] @ beta)[:, None]
    meat = scores.T @ scores
    for lag in range(1, 4):
        covariance = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag / 4) * (covariance + covariance.T)
    bread = np.linalg.pinv(x[valid].T @ x[valid])
    variance = bread @ meat @ bread * n / (n - k)
    estimate = float(beta[coefficient])
    se = float(np.sqrt(max(0.0, variance[coefficient, coefficient])))
    return {**result, "mean": estimate, "standard_error": se,
            "ci95": [estimate - 1.96 * se, estimate + 1.96 * se]}


class DiagnosticLab:
    """Generate one anonymous monthly panel and release requested diagnostics."""

    def __init__(self, seed: int, scenario: str):
        if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if scenario not in SCENARIOS:
            raise ValueError("unknown synthetic scenario")
        self._seed, self._scenario = int(seed), scenario
        self._n_months, self._n_assets = 96, 120
        self._cache: dict[str, dict] = {}
        self._generate()

    def public_case(self) -> dict[str, Any]:
        """Identical metadata across cases: no seed, label, oracle or free test."""
        return {
            "schema_version": "synthetic-diagnostic-case-v1",
            "question": "Does the signal predict next-month returns beyond sector, size and liquidity exposures, and survive costs?",
            "mechanism_question": "Any economic mechanism remains an observational, separately assessed claim.",
            "data_kind": "SYNTHETIC_MONTHLY_CROSS_SECTION",
            "month_count": self._n_months, "asset_count": self._n_assets,
            "formation_frequency": "monthly", "target_horizon_months": 1,
            "inventory": {
                "core_panel": ["formation_month", "asset_id", "signal", "next_month_return",
                               "signal_known_month", "sector", "size", "liquidity", "controls_known_month"],
                "execution": ["per_asset_one_way_cost", "fixed_equal_weight_quintile_portfolios"],
                "regime": ["formation_time_binary_macro_state"],
                "optional": ["next_period_economic_change", "economic_change_known_month"],
                "optional_availability": "disclosed when the relevant diagnostic is requested",
            },
            "diagnostics": deepcopy(DIAGNOSTIC_CATALOG),
            "uncertainty": "Monthly HAC descriptive intervals; repeated adaptive inspection has no formal error-rate guarantee.",
            "isolation_level": "LOGICAL_ONLY",
        }

    def _generate(self) -> None:
        rng = np.random.default_rng(self._seed)
        t, n = self._n_months, self._n_assets
        self._sector = np.arange(n) % 6
        sector_score = _z(np.linspace(-1, 1, 6))[self._sector]
        self._size = rng.normal(size=n)[None, :] + .2 * _ar(rng, (t, n), .8)
        self._liquidity = -.6 * self._size + rng.normal(size=n)[None, :] * .5 + .4 * _ar(rng, (t, n), .6)
        self._size, self._liquidity = _z(self._size), _z(self._liquidity)
        latent = _ar(rng, (t, n), .25)
        # The state is known at formation and persistent, with both states represented.
        self._regime = ((np.arange(t) + int(rng.integers(0, 12))) // 12 % 2).astype(float)
        common_shock = .012 * _ar(rng, (t, 1), .45)
        sector_shock = .01 * _ar(rng, (t, 6), .35)[:, self._sector]
        asset_effect = .002 * rng.normal(size=n)[None, :]
        noise = .045 * _ar(rng, (t, n), .2)
        self._signal = latent + .1 * sector_score + .1 * self._size
        returns = common_shock + sector_shock + asset_effect + noise
        beta = np.full((t, 1), .012)
        self._cost_rate = .0005 + .0003 * (1 / (1 + np.exp(self._liquidity)))
        if self._scenario == "sector_confounding":
            self._signal = 1.2 * sector_score + .35 * latent
            beta[:] = 0
            returns += .025 * sector_score
        elif self._scenario == "exposure_confounding":
            self._signal = self._size - .9 * self._liquidity + .35 * latent
            beta[:] = 0
            returns += .014 * self._size - .012 * self._liquidity
        elif self._scenario == "costs":
            beta[:] = .006
            self._cost_rate *= 40
        elif self._scenario == "regime":
            beta = np.where(self._regime[:, None] == 1, .016, -.009)
        elif self._scenario == "mixed":
            self._signal = .6 * latent + 1.1 * sector_score + .7 * self._size - .65 * self._liquidity
            beta = np.where(self._regime[:, None] == 1, .015, -.01)
            returns += .013 * sector_score + .007 * self._size - .006 * self._liquidity
            self._cost_rate *= 180
        elif self._scenario == "weak":
            beta[:] = 0
            noise *= 1.5
            returns = common_shock + sector_shock + asset_effect + noise
        self._returns = returns + beta * latent
        months = np.broadcast_to(np.arange(t)[:, None], (t, n)).copy()
        self._formation_month = months
        self._asset_id = np.broadcast_to(np.arange(n)[None, :], (t, n)).copy()
        self._signal_known_month = months.copy()
        self._controls_known_month = months.copy()
        if self._scenario == "lookahead":
            # The feature improperly incorporates the actual target period outcome.
            self._signal = .4 * latent + _z(self._returns)
            self._signal_known_month += 1
        self._economic_change = .03 * latent + .06 * _ar(rng, (t, n), .3)
        self._economic_known_month = months + 2
        if self._scenario == "mechanism_missing":
            self._economic_change = None

    def _correlations(self, first: np.ndarray, second: np.ndarray) -> np.ndarray:
        return (_z(_rank(first)) * _z(_rank(second))).mean(axis=1)

    def _controls(self) -> tuple[dict[str, np.ndarray], np.ndarray]:
        signal, target = _z(self._signal), self._returns
        series = {name: np.empty(self._n_months) for name in
                  ("raw_ic", "sector_adjusted_ic", "size_liquidity_adjusted_ic", "fully_adjusted_ic")}
        slopes = np.empty(self._n_months)
        sector = np.eye(6)[self._sector, 1:]
        for month in range(self._n_months):
            exposures = np.column_stack((self._size[month], self._liquidity[month]))
            for key, columns in (
                ("raw_ic", np.empty((self._n_assets, 0))),
                ("sector_adjusted_ic", sector),
                ("size_liquidity_adjusted_ic", exposures),
                ("fully_adjusted_ic", np.column_stack((sector, exposures))),
            ):
                design = np.column_stack((np.ones(self._n_assets), columns))
                pair = np.column_stack((signal[month], target[month]))
                residual = pair - design @ np.linalg.lstsq(design, pair, rcond=None)[0]
                series[key][month] = self._correlations(residual[:, 0][None, :], residual[:, 1][None, :])[0]
            # Continuous-return coefficient, standardized within-month signal.
            design = np.column_stack((np.ones(self._n_assets), sector, exposures, _z(self._signal[month])))
            slopes[month] = np.linalg.lstsq(design, self._returns[month], rcond=None)[0][-1]
        series["sector_attenuation"] = series["raw_ic"] - series["sector_adjusted_ic"]
        series["size_liquidity_attenuation"] = series["raw_ic"] - series["size_liquidity_adjusted_ic"]
        return series, slopes

    def _portfolio(self) -> dict[str, np.ndarray]:
        ranks = _rank(self._signal)
        count = self._n_assets // 5
        weights = (ranks >= self._n_assets - count).astype(float) / count - (ranks < count).astype(float) / count
        previous = np.vstack((np.zeros((1, self._n_assets)), weights[:-1]))
        # Previous target weights drift with the intervening return before rebalancing.
        if self._n_months > 1:
            long = np.maximum(previous[1:], 0) * (1 + self._returns[:-1])
            short = np.minimum(previous[1:], 0) * (1 + self._returns[:-1])
            previous[1:] = long / long.sum(axis=1, keepdims=True) + short / (-short.sum(axis=1, keepdims=True))
        trades = np.abs(weights - previous)
        gross = (weights * self._returns).sum(axis=1)
        costs = (trades * self._cost_rate).sum(axis=1)
        return {"gross_spread": gross, "estimated_cost": costs, "net_spread": gross - costs,
                "turnover": trades.sum(axis=1)}

    def run(self, diagnostic_id: str) -> dict[str, Any]:
        """Compute only the requested report; no truth-dependent diagnoses."""
        if diagnostic_id not in DIAGNOSTIC_CATALOG:
            raise ValueError("unknown diagnostic_id")
        if diagnostic_id in self._cache:
            return deepcopy(self._cache[diagnostic_id])
        result: dict[str, Any] = {"diagnostic_id": diagnostic_id, "status": "AVAILABLE",
                                 "metrics": {}, "limitations": list(_LIMITS)}
        metrics = result["metrics"]
        if diagnostic_id == "input_audit":
            keys = np.column_stack((self._formation_month.ravel(), self._asset_id.ravel()))
            metrics.update({
                "n_rows": int(self._signal.size),
                "duplicate_key_count": int(len(keys) - len(np.unique(keys, axis=0))),
                "late_signal_fraction": float((self._signal_known_month > self._formation_month).mean()),
                "late_control_fraction": float((self._controls_known_month > self._formation_month).mean()),
                "missing_signal_fraction": float((~np.isfinite(self._signal)).mean()),
                "missing_return_fraction": float((~np.isfinite(self._returns)).mean()),
                "availability_rule": "input_known_month <= formation_month; future outcomes are labels only",
            })
        elif diagnostic_id == "association":
            metrics.update({"raw_ic": _estimate(self._correlations(self._signal, self._returns)),
                            "gross_spread": _estimate(self._portfolio()["gross_spread"])})
        elif diagnostic_id == "controls":
            series, _ = self._controls()
            metrics.update({name: _estimate(values) for name, values in series.items()})
            metrics.update({"n_rows": int(self._signal.size), "sample_policy": "identical complete-case rows for every comparison"})
            result["limitations"].append("Rank correlations follow linear residualization of signal and returns on observed controls; omitted exposures can remain.")
        elif diagnostic_id == "execution_cost":
            metrics.update({name: _estimate(values) for name, values in self._portfolio().items()})
            metrics["cost_model"] = "absolute per-asset traded weight times one-way cost; gross exposure 2; initial entry included"
            result["limitations"].append("Stylized costs include no borrow availability, capacity constraint or real fill guarantee.")
        elif diagnostic_id == "regime_interaction":
            _, slopes = self._controls()
            for state in (0, 1):
                metrics[f"regime_{state}"] = _estimate(np.where(self._regime == state, slopes, np.nan))
            design = np.column_stack((np.ones(self._n_months), self._regime))
            metrics["interaction"] = _estimate(slopes, design, coefficient=1)
            metrics["estimand"] = "regime_1 minus regime_0 controlled return-on-standardized-signal slope"
            result["limitations"].append("Direct interaction uncertainty is reported; differing subgroup significance is not an interaction test.")
        elif self._economic_change is None:
            result.update({"status": "NOT_COMPUTED", "missing_datasets": ["next_period_economic_change"]})
            result["limitations"].append("Missing economic outcomes leave the mechanism unidentified, without invalidating return association.")
        else:
            metrics.update({
                "signal_to_economic_change_ic": _estimate(self._correlations(self._signal, self._economic_change)),
                "economic_change_to_return_ic": _estimate(self._correlations(self._economic_change, self._returns)),
                "causal_identification": False,
                "outcome_availability_lag_months": int((self._economic_known_month - self._formation_month).max()),
            })
        self._cache[diagnostic_id] = deepcopy(result)
        return result

    def oracle(self) -> dict[str, Any]:
        """Grader-only generating truth, never an authorized researcher report."""
        findings, conclusions = _TRUTHS[self._scenario]
        return {"scenario": self._scenario, "seed": self._seed,
                "expected_findings": list(findings), "acceptable_conclusions": list(conclusions),
                "mechanism_identified": False, "multiple_causes": len(findings) > 1,
                "optional_data_missing": self._economic_change is None,
                "truth_scope": "generating process, not guaranteed finite-sample detectability"}
