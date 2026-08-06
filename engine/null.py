"""Synthetic-null calibration of the *actual* T0-T5 gate."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from engine import gate
from engine import panel as panel_engine
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


def _scope_discovery_panel(
    panel: Panel,
    *,
    data_cutoff: str,
    oos_start: pd.Period,
) -> Panel:
    """Reconstruct the immutable discovery snapshot from a confirmation panel."""
    cutoff = pd.Timestamp(data_cutoff).normalize()
    if oos_start <= cutoff.to_period("M"):
        raise ValueError("campaign OOS는 research data cutoff 다음 달 이후여야 합니다")
    frame = panel.monthly
    scoped = frame[
        pd.to_datetime(frame["trade_date"]).dt.normalize().le(cutoff)
        & frame["ym"].lt(oos_start)
    ].copy()
    if scoped.empty or pd.Timestamp(scoped["trade_date"].max()).normalize() != cutoff:
        raise ValueError(
            "귀무 보정에서 campaign cutoff snapshot을 재현할 수 없습니다: "
            f"cutoff={cutoff.date()}"
        )

    last_day = pd.Timestamp(scoped["trade_date"].max())
    last_seen = scoped.groupby("asset_id")["trade_date"].max()
    dead = last_seen[
        last_seen < last_day - pd.Timedelta(days=panel_engine.INACTIVE_DAYS)
    ]
    meta = dict(panel.meta)
    meta.update({
        "campaign_data_cutoff": str(cutoff.date()),
        "campaign_oos_start": str(oos_start),
    })
    output = Panel(monthly=scoped, dead=dead, meta=meta)
    for tag, terminal in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        output.monthly[f"fwd_{tag}"] = panel_engine.forward_returns(
            output, terminal=terminal,
        )
    return output


def _merge_discovery_and_oos(
    discovery: gate.Result,
    confirmation: gate.Result,
) -> gate.Result:
    """Attach only fixed-OOS evidence to the cutoff-bound discovery result."""
    discovery.labels = [
        label for label in discovery.labels
        if label not in {"oos_sealed", "fdr_pending", "discovery_pass"}
    ]
    discovery.metrics["evaluation_phase"] = "full"
    discovery.metrics.update({
        key: value
        for key, value in confirmation.metrics.items()
        if key.startswith("oos_")
    })
    oos_check = next(
        (check for check in confirmation.checks if check.tier == "T4.1"),
        None,
    )
    if oos_check is None:
        failures = ", ".join(
            check.name for check in confirmation.failed
        ) or "OOS 계산 불가"
        oos_check = gate.Check(
            "T4.1", "고정 OOS IC", False, None,
            f"months>={gate.TH['min_oos_months']} & IC>={gate.TH['oos_ic']}",
            failures,
        )
    discovery.checks.append(oos_check)
    if "oos_ic" in confirmation.series:
        discovery.series["oos_ic"] = confirmation.series["oos_ic"]
    return discovery


def measure(
    panel: Panel,
    *,
    n: int = 25,
    seed: int = 20260731,
    trial_count: int = 1,
    prior_sharpes: tuple[float, ...] = (),
    oos_start: pd.Period | None = None,
    oos_end: pd.Period | None = None,
    research_data_cutoff: str | None = None,
    discovery_family_size: int = 1,
    oos_family_size: int = 1,
    discovery_family_digest: str = "standalone",
    oos_family_digest: str = "standalone",
    gold_family_digest: str = "none",
    confirmation_snapshot_digest: str | None = None,
    existing: dict[str, pd.Series] | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Estimate family-wise false promotion with production-sized null campaigns.

    ``n`` is the number of null campaign families per generator, not the number
    of individual signals.  Each family contains the same number of discovery
    definitions as the bound research campaign.  Up to ``oos_family_size``
    discovery-eligible definitions are revealed together, which is a stand-in
    for human survivor selection under the global null.
    """
    if n < 1:
        raise ValueError("null campaign 반복 수 n은 1 이상이어야 합니다")
    if discovery_family_size < 1 or oos_family_size < 1:
        raise ValueError("discovery/OOS family size는 1 이상이어야 합니다")
    if oos_family_size > discovery_family_size:
        raise ValueError("OOS family size는 discovery family size보다 클 수 없습니다")
    if oos_start is None or oos_end is None or research_data_cutoff is None:
        raise ValueError(
            "귀무 보정에는 research_data_cutoff, oos_start, oos_end가 모두 필요합니다"
        )
    oos_start = pd.Period(oos_start, freq="M")
    oos_end = pd.Period(oos_end, freq="M")
    if oos_end < oos_start:
        raise ValueError("OOS end는 OOS start보다 빠를 수 없습니다")
    rng = np.random.default_rng(seed)
    df = panel.monthly
    required_month = oos_end + 1
    if df.empty or df["ym"].max() != required_month:
        raise ValueError(
            "귀무 보정 confirmation snapshot 경계가 고정 OOS와 일치하지 않습니다: "
            f"expected_last_month={required_month}"
        )
    discovery_panel = _scope_discovery_panel(
        panel, data_cutoff=research_data_cutoff, oos_start=oos_start,
    )
    confirmation_snapshot_digest = (
        confirmation_snapshot_digest or panel_engine.snapshot_digest(panel)
    )
    discovery_df = discovery_panel.monthly
    base = df.loc[panel.universe, ["ym", "asset_id"]]
    generators = {
        "random": lambda: _random_signal(base, rng),
        "ar1_095": lambda: _persistent_signal(base, rng, .95),
        "ar1_0999": lambda: _persistent_signal(base, rng, .999),
        "frozen": lambda: _frozen_signal(base, rng),
    }
    rows = []
    for kind, generate in generators.items():
        for replicate in range(n):
            family_results: list[gate.Result] = []
            factors_by_hash: dict[str, Factor] = {}
            temporary_columns: list[tuple[str, str]] = []
            for candidate_index in range(discovery_family_size):
                name = f"null_{kind}_{replicate}_{candidate_index}"
                raw_col, factor_col = f"_raw_{name}", f"f_{name}"
                df[raw_col] = np.nan
                signal = generate()
                df.loc[signal.index, raw_col] = signal
                df[factor_col] = df[raw_col]
                # Generate once on the confirmation panel, then replay the exact
                # same historical values on the sealed discovery index.
                discovery_df[raw_col] = signal.reindex(discovery_df.index)
                discovery_df[factor_col] = discovery_df[raw_col]
                factor = Factor(
                    name=name,
                    family=f"null_{kind}",
                    category="other",
                    hypothesis="합성 귀무: 미래수익에 대한 경제적 정보가 없어야 한다.",
                    predicted_sign=1,
                    params={
                        "kind": kind, "replicate": replicate,
                        "candidate": candidate_index, "seed": seed,
                    },
                    compute=lambda frame, source=raw_col: frame[source],
                )
                discovery_result = gate.evaluate(
                    factor, discovery_panel, discovery_df, existing=existing,
                    trial_count=trial_count + discovery_family_size,
                    prior_sharpes=prior_sharpes,
                    oos_start=oos_start,
                    data_cutoff=research_data_cutoff,
                    phase="discovery",
                )
                family_results.append(discovery_result)
                factors_by_hash[factor.definition_hash] = factor
                temporary_columns.append((raw_col, factor_col))

            # Survivor selection must know discovery only.  Attaching T4.1
            # before this point would let the null campaign choose candidates
            # after seeing the very OOS outcome it is supposed to calibrate.
            gate.apply_multiple_testing(
                family_results, total_trials=discovery_family_size,
            )
            eligible = [
                result for result in family_results
                if result.verdict != gate.Verdict.REJECT
            ]
            selected = sorted(
                eligible,
                key=lambda result: (
                    result.metrics.get("ic_p_investable")
                    if result.metrics.get("ic_p_investable") is not None
                    and np.isfinite(result.metrics["ic_p_investable"])
                    else float("inf"),
                    result.definition_hash,
                ),
            )[:oos_family_size]
            for index, discovery_result in enumerate(selected):
                factor = factors_by_hash[discovery_result.definition_hash]
                confirmation_result = gate.evaluate_oos(
                    factor, panel, df,
                    oos_start=oos_start, oos_end=oos_end,
                )
                selected[index] = _merge_discovery_and_oos(
                    discovery_result, confirmation_result,
                )
            gate.apply_oos_multiple_testing(selected)
            promoted = [
                result for result in selected
                if result.verdict == gate.Verdict.PROMOTE
            ]
            definition_digest = hashlib.sha256(
                "\n".join(sorted(result.definition_hash for result in family_results)).encode()
            ).hexdigest()
            ic_values = [
                float(result.metrics["ic_investable"])
                for result in family_results
                if result.metrics.get("ic_investable") is not None
                and np.isfinite(result.metrics["ic_investable"])
            ]
            for raw_col, factor_col in temporary_columns:
                del df[raw_col]
                del df[factor_col]
                del discovery_df[raw_col]
                del discovery_df[factor_col]
            rows.append({
                "calibration_unit": "null_campaign_family",
                "generator_suite": "null-v1",
                "kind": kind,
                "replicate": replicate,
                "pass": bool(promoted),
                "promoted_count": len(promoted),
                "revealed_count": len(selected),
                "discovery_family_size": discovery_family_size,
                "oos_family_size": oos_family_size,
                "discovery_family_digest": discovery_family_digest,
                "oos_family_digest": oos_family_digest,
                "gold_family_digest": gold_family_digest,
                "confirmation_snapshot_digest": confirmation_snapshot_digest,
                "null_definition_digest": definition_digest,
                "max_ic_investable": max(ic_values) if ic_values else None,
                "fdr_q": gate.TH["fdr_q"],
                "seed": seed,
                "gold_signal_count": len(existing or {}),
            })
    output = pd.DataFrame(rows)
    output["ruleset_version"] = gate.RULESET_VERSION
    output["data_cutoff"] = str(df["trade_date"].max().date())
    output["oos_start"] = str(oos_start) if oos_start is not None else None
    output["oos_end"] = str(oos_end) if oos_end is not None else None
    output["research_data_cutoff"] = research_data_cutoff
    if verbose:
        for kind in generators:
            subset = output[output["kind"] == kind]
            rate = subset["pass"].mean() * 100 if len(subset) else 0.0
            print(f"  [null] {kind:12} families={len(subset):>3}  any PROMOTE {rate:5.1f}%")
        if len(output):
            print(f"  [null] campaign-family 오류율: {output['pass'].mean() * 100:.1f}%")
    return output
