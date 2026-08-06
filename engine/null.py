"""Synthetic-null calibration of the *actual* T0-T5 gate."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import gate
from engine.factors import Factor
from engine.panel import Panel


def _random_signal(base: pd.DataFrame, rng) -> pd.Series:
    return pd.Series(rng.standard_normal(len(base)), index=base.index)


def _persistent_signal(base: pd.DataFrame, rng, rho: float) -> pd.Series:
    assets = base["asset_id"].unique()
    state = pd.Series(rng.standard_normal(len(assets)), index=assets)
    output = pd.Series(np.nan, index=base.index, dtype=float)
    for ym in sorted(base["ym"].unique()):
        state = rho * state + np.sqrt(max(1 - rho ** 2, 1e-9)) * pd.Series(
            rng.standard_normal(len(assets)), index=assets
        )
        group = base[base["ym"] == ym]
        output.loc[group.index] = state.reindex(group["asset_id"]).to_numpy()
    return output


def _frozen_signal(base: pd.DataFrame, rng) -> pd.Series:
    assets = base["asset_id"].unique()
    state = pd.Series(rng.standard_normal(len(assets)), index=assets)
    return pd.Series(state.reindex(base["asset_id"]).to_numpy(), index=base.index)


def measure(
    panel: Panel,
    *,
    n: int = 30,
    seed: int = 20260731,
    trial_count: int = 1,
    prior_sharpes: tuple[float, ...] = (),
    historical_pvalues: tuple[tuple[str, float], ...] = (),
    oos_start: pd.Period | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Generate null signals and send every one through the production evaluator."""
    rng = np.random.default_rng(seed)
    df = panel.monthly
    base = df.loc[panel.universe, ["ym", "asset_id"]]
    generators = {
        "random": lambda: _random_signal(base, rng),
        "ar1_095": lambda: _persistent_signal(base, rng, .95),
        "ar1_0999": lambda: _persistent_signal(base, rng, .999),
        "frozen": lambda: _frozen_signal(base, rng),
    }
    evaluated: list[tuple[str, gate.Result]] = []
    total_new = len(generators) * n
    for kind, generate in generators.items():
        for replicate in range(n):
            name = f"null_{kind}_{replicate}"
            raw_col, factor_col = f"_raw_{name}", f"f_{name}"
            df[raw_col] = np.nan
            signal = generate()
            df.loc[signal.index, raw_col] = signal
            df[factor_col] = df[raw_col]
            factor = Factor(
                name=name,
                family=f"null_{kind}",
                category="other",
                hypothesis="합성 귀무: 미래수익에 대한 경제적 정보가 없어야 한다.",
                predicted_sign=1,
                params={"kind": kind, "replicate": replicate, "seed": seed},
                compute=lambda frame, source=raw_col: frame[source],
            )
            result = gate.evaluate(
                factor, panel, df, trial_count=trial_count + total_new,
                prior_sharpes=prior_sharpes, oos_start=oos_start,
            )
            evaluated.append((kind, result))
            del df[raw_col]
            del df[factor_col]

    results = [result for _, result in evaluated]
    gate.apply_multiple_testing(results, historical_pvalues)
    rows = []
    for kind, result in evaluated:
        rows.append({
            "kind": kind,
            "factor": result.factor,
            "verdict": result.verdict.value,
            "pass": result.verdict == gate.Verdict.PROMOTE,
            **{key: value for key, value in result.metrics.items() if np.isscalar(value)},
        })
    output = pd.DataFrame(rows)
    output["ruleset_version"] = gate.RULESET_VERSION
    output["data_cutoff"] = str(df["trade_date"].max().date())
    output["oos_start"] = str(oos_start) if oos_start is not None else None
    if verbose:
        for kind in generators:
            subset = output[output["kind"] == kind]
            rate = subset["pass"].mean() * 100 if len(subset) else 0.0
            print(f"  [null] {kind:12} n={len(subset):>3}  전체 게이트 PROMOTE {rate:5.1f}%")
        if len(output):
            print(f"  [null] 전체 실현 위양성률: {output['pass'].mean() * 100:.1f}%")
    return output
