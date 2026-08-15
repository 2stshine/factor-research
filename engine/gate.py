"""Deterministic factor promotion gate.

The order is intentional: definition and sample integrity first, execution and
robustness next, statistical selection control after that, and finally marginal
value versus the already-approved Gold catalog.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats

from engine.factors import Factor
from engine.panel import Panel, verify_return_roles
from engine import research_policy, silver
from engine.research_policy import COMMON_EVALUATION_START


RULESET_VERSION = "fr-3.13.0"
RESEARCH_START = COMMON_EVALUATION_START
EVALUATION_PHASES = {"discovery", "full"}

SECURITIES_TAX = {
    2015: .0030, 2016: .0030, 2017: .0030, 2018: .0030, 2019: .0025,
    2020: .0025, 2021: .0023, 2022: .0023, 2023: .0020, 2024: .0018,
    2025: .0015, 2026: .0015,
}
COMMISSION = 0.00015
IMPACT = 0.0010

TH = {
    "min_months": 60,
    "min_oos_months": 36,
    "coverage": 0.50,
    "monthly_coverage_p10": 0.30,
    "min_ic": 0.03,
    "min_investable_ic": 0.03,
    "min_rank_icir": 0.15,
    "turnover_warn": 250.0,
    "turnover_fail": 400.0,
    "subperiod_agree": 3,
    "max_gold_corr": 0.70,
    "min_gold_corr_months": 36,
    "candidate_duplicate_corr": 0.80,
    "regime_conc": 0.60,
    "neutral_ic": 0.01,
    "neutral_ic_retention": 0.30,
    "oos_ic": 0.02,
    "oos_ic_retention": 0.50,
    "fdr_q": 0.10,
    "max_missing_return": 0.01,
}
# Effect-size cutoffs are pre-declared research policy, not fitted to candidate
# outcomes.  Definitions, power checks, and literature are documented in
# docs/factor-promotion-criteria.md; changing one requires a new ruleset.


class Verdict(str, Enum):
    PROMOTE = "PROMOTE"
    PROVISIONAL = "PROVISIONAL"
    REJECT = "REJECT"


def _label_return_certified(panel: Panel) -> bool:
    try:
        verify_return_roles(panel)
        evidence = silver.verify_total_return_validation_evidence(
            panel.meta.get("return_contract_validation_evidence"),
        )
    except RuntimeError:
        return False
    return bool(
        panel.meta.get("label_return_field") == "total_return_close"
        and panel.meta.get("label_return_methodology") == silver.TOTAL_RETURN_METHOD
        and panel.meta.get("label_return_usage") == silver.LABEL_RETURN_USAGE
        and panel.meta.get("label_candidate_access") is False
        and panel.meta.get("feature_price_field") == "adj_close"
        and panel.meta.get("feature_return_methodology")
        == silver.FEATURE_RETURN_METHOD
        and panel.meta.get("label_return_contract_status") == "CERTIFIED"
        and panel.meta.get("return_contract_validation_status") == "VERIFIED"
        and panel.meta.get("return_contract_run_id")
        == evidence["quality_run_id"]
        and panel.meta.get("return_contract_evidence_sha256")
        == evidence["evidence_sha256"]
    )


@dataclass
class Check:
    tier: str
    name: str
    passed: bool | None
    value: float | None = None
    threshold: str = ""
    note: str = ""


@dataclass
class Result:
    factor: str
    definition_hash: str
    verdict: Verdict = Verdict.REJECT
    checks: list[Check] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    labels: list[str] = field(default_factory=list)
    series: dict[str, pd.Series] = field(default_factory=dict, repr=False)

    @property
    def failed(self) -> list[Check]:
        return [check for check in self.checks if check.passed is False]

    @property
    def pending(self) -> list[Check]:
        return [check for check in self.checks if check.passed is None]

    def tier_failed(self, prefix: str) -> bool:
        return any(c.passed is False and c.tier.startswith(prefix) for c in self.checks)


@dataclass(frozen=True)
class EvaluationContext:
    """Invocation-local static scope shared by repeated gate evaluations."""

    panel: Panel = field(repr=False)
    frame: pd.DataFrame = field(repr=False)
    phase: str
    data_cutoff: str | None
    oos_start: pd.Period | None
    work_index: pd.Index = field(repr=False)
    work_eligible: np.ndarray = field(repr=False)
    research_index: pd.Index = field(repr=False)
    research_eligible: np.ndarray = field(repr=False)
    research_month_positions: tuple[tuple[pd.Period, np.ndarray], ...] = field(
        repr=False,
    )
    investable_month_positions: tuple[tuple[pd.Period, np.ndarray], ...] = field(
        repr=False,
    )


@dataclass(frozen=True)
class InternalNullSignalContract:
    """One-frame capability for engine-generated synthetic null signals."""

    generator_suite: str
    kind: str
    replicate: int
    candidate: int
    seed: int
    factor_name: str
    definition_hash: str
    raw_column: str
    factor_column: str
    frame_identity: int
    signal_digest: str


@dataclass(frozen=True)
class ConfirmationSignalContract:
    """Current OOS signal bound to an authenticated Discovery T0 result."""

    factor_name: str
    definition_hash: str
    factor_column: str
    frame_identity: int
    signal_digest: str


_INTERNAL_NULL_GENERATOR_SUITE = "null-v2"
_INTERNAL_NULL_KINDS = frozenset({"random", "ar1_095", "ar1_0999", "frozen"})


def _series_digest(series: pd.Series) -> str:
    digest = hashlib.sha256()
    digest.update(str(series.dtype).encode("utf-8"))
    digest.update(pd.util.hash_pandas_object(
        series, index=True, categorize=True,
    ).values.tobytes())
    return digest.hexdigest()


def certify_internal_null_signal(
    factor: Factor,
    df: pd.DataFrame,
    *,
    generator_suite: str,
    kind: str,
    replicate: int,
    candidate: int,
    seed: int,
    raw_column: str,
    factor_column: str,
) -> InternalNullSignalContract:
    """Certify one engine-owned null signal without executing candidate T0."""
    expected_name = f"null_{kind}_{replicate}_{candidate}"
    expected_params = {
        "kind": kind, "replicate": replicate, "candidate": candidate,
        "seed": seed,
    }
    if (
        generator_suite != _INTERNAL_NULL_GENERATOR_SUITE
        or kind not in _INTERNAL_NULL_KINDS
        or replicate < 0
        or candidate < 0
        or factor.name != expected_name
        or factor.family != f"null_{kind}"
        or factor.category != "other"
        or factor.predicted_sign != 1
        or factor.rebalance_months != 1
        or factor.needs
        or factor.params != expected_params
        or raw_column != f"_raw_{expected_name}"
        or factor_column != f"f_{expected_name}"
    ):
        raise ValueError("engine null signal 계약이 닫힌 generator identity와 다릅니다")
    if raw_column not in df or factor_column not in df:
        raise ValueError("engine null signal raw/factor column이 없습니다")
    raw = df[raw_column]
    signed = df[factor_column]
    if (
        not raw.index.equals(df.index)
        or not signed.index.equals(df.index)
        or not pd.api.types.is_numeric_dtype(raw)
        or not pd.api.types.is_numeric_dtype(signed)
        or np.isinf(pd.to_numeric(raw, errors="coerce")).any()
        or np.isinf(pd.to_numeric(signed, errors="coerce")).any()
        or not np.allclose(
            raw.to_numpy(dtype=float), signed.to_numpy(dtype=float),
            equal_nan=True,
        )
    ):
        raise ValueError("engine null signal 값·인덱스·유한성 계약이 다릅니다")
    return InternalNullSignalContract(
        generator_suite=generator_suite,
        kind=kind,
        replicate=replicate,
        candidate=candidate,
        seed=seed,
        factor_name=factor.name,
        definition_hash=factor.definition_hash,
        raw_column=raw_column,
        factor_column=factor_column,
        frame_identity=id(df),
        signal_digest=_series_digest(signed),
    )


def _internal_null_checks(
    factor: Factor,
    df: pd.DataFrame,
    cached: str,
    contract: InternalNullSignalContract,
) -> list[Check]:
    if (
        contract.generator_suite != _INTERNAL_NULL_GENERATOR_SUITE
        or contract.kind not in _INTERNAL_NULL_KINDS
        or contract.factor_name != factor.name
        or contract.definition_hash != factor.definition_hash
        or contract.factor_column != cached
        or contract.frame_identity != id(df)
        or cached not in df
        or contract.signal_digest != _series_digest(df[cached])
    ):
        raise ValueError("engine null signal 인증이 현재 factor/frame과 다릅니다")
    note = "closed engine null generator; candidate code path not used"
    return [
        Check("T0.1", "미선언 상수", True, 0, "0개", note),
        Check("T0.2", "단일 팩터 계약", True, 0, "합성 신호 0개", note),
        Check("T0.3", "최대 룩백", True, 0, "engine null generator", note),
        Check("T0.4", "연구 입력 하한", True, None, f">={research_policy.RESEARCH_INPUT_START}", note),
        Check("T0.5", "label 전용 입력 차단", True, 0, "0개", note),
        Check("T0.6", "입력 계약", True, 0, "누락 0개", note),
        Check("T0.8", "출력 타입·인덱스", True, None, "numeric Series / 동일 index", note),
        Check("T0.9", "유한값", True, None, "±inf 없음", note),
        Check("T0.10", "결정성", True, None, "동결 generator bytes", note),
        Check("T0.11", "36개월 인과성", True, None, "engine generator는 label 비참조", note),
        Check("T0.12", "캐시 정의 일치", True, None, "raw=factor exact bytes", note),
    ]


def certify_confirmation_signal(
    factor: Factor,
    df: pd.DataFrame,
    discovery: Result,
) -> ConfirmationSignalContract:
    """Bind current computed values to a candidate whose T0 already passed."""
    required = {
        "미선언 상수", "단일 팩터 계약", "최대 룩백", "연구 입력 하한",
        "label 전용 입력 차단", "입력 계약", "출력 타입·인덱스",
        "유한값", "결정성", "36개월 인과성", "캐시 정의 일치",
    }
    passed = {
        check.name for check in discovery.checks
        if check.tier.startswith("T0") and check.passed is True
    }
    column = f"f_{factor.name}"
    if (
        discovery.factor != factor.name
        or discovery.definition_hash != factor.definition_hash
        or not required.issubset(passed)
        or any(
            check.passed is not True
            for check in discovery.checks if check.tier.startswith("T0")
        )
        or column not in df
        or not df.index.is_unique
        or not pd.api.types.is_numeric_dtype(df[column])
        or np.isinf(pd.to_numeric(df[column], errors="coerce")).any()
    ):
        raise ValueError(
            f"동결 Discovery T0/current OOS signal 계약이 다릅니다: {factor.name}"
        )
    return ConfirmationSignalContract(
        factor_name=factor.name,
        definition_hash=factor.definition_hash,
        factor_column=column,
        frame_identity=id(df),
        signal_digest=_series_digest(df[column]),
    )


def _confirmation_signal_check(
    factor: Factor,
    df: pd.DataFrame,
    cached: str,
    contract: ConfirmationSignalContract,
) -> list[Check]:
    if (
        contract.factor_name != factor.name
        or contract.definition_hash != factor.definition_hash
        or contract.factor_column != cached
        or contract.frame_identity != id(df)
        or cached not in df
        or contract.signal_digest != _series_digest(df[cached])
    ):
        raise ValueError("OOS candidate signal이 인증 뒤 변경되었습니다")
    return [Check(
        "T0.C", "동결 Discovery T0/current signal binding", True, None,
        "definition+strategy+T0+signal bytes exact",
    )]


def _month_positions(
    months: pd.Series,
    eligible: np.ndarray | None = None,
) -> tuple[tuple[pd.Period, np.ndarray], ...]:
    values = pd.PeriodIndex(months, freq="M").to_numpy()
    allowed = (
        np.ones(len(values), dtype=bool)
        if eligible is None else np.asarray(eligible, dtype=bool)
    )
    if len(allowed) != len(values):
        raise ValueError("gate context의 월별 mask 길이가 다릅니다")
    return tuple(
        (pd.Period(month, freq="M"), np.flatnonzero((values == month) & allowed))
        for month in sorted(pd.unique(values))
    )


def build_evaluation_context(
    panel: Panel,
    df: pd.DataFrame,
    *,
    oos_start: pd.Period | None = None,
    data_cutoff: str | pd.Timestamp | None = None,
    phase: str = "full",
) -> EvaluationContext:
    """Freeze factor-independent masks and monthly groups for one invocation."""
    if phase not in EVALUATION_PHASES:
        raise ValueError(f"지원하지 않는 평가 phase={phase!r}")
    if not df.index.is_unique:
        raise ValueError("gate context는 고유한 frame index가 필요합니다")
    frozen_oos = pd.Period(oos_start, freq="M") if oos_start is not None else None
    cutoff_text = (
        str(pd.Timestamp(data_cutoff).normalize().date())
        if data_cutoff is not None else None
    )
    universe = panel.universe.reindex(df.index).fillna(False).astype(bool)
    investable = panel.investable.reindex(df.index).fillna(False).astype(bool)
    work_mask = universe & df["ym"].ge(RESEARCH_START)
    work_index = df.index[work_mask]
    work_eligible = investable.loc[work_index].to_numpy(dtype=bool)
    research_mask = np.ones(len(work_index), dtype=bool)
    work_rows = df.loc[work_index]
    if data_cutoff is not None:
        cutoff = pd.Timestamp(data_cutoff).normalize()
        research_mask &= (
            pd.to_datetime(work_rows["trade_date"]).dt.normalize().le(cutoff)
            & work_rows["ym"].lt(cutoff.to_period("M"))
        ).to_numpy(dtype=bool)
    if frozen_oos is not None:
        research_mask &= work_rows["ym"].lt(frozen_oos - 1).to_numpy(dtype=bool)
    research_index = work_index[research_mask]
    research_eligible = work_eligible[research_mask]
    research_months = df.loc[research_index, "ym"]
    return EvaluationContext(
        panel=panel,
        frame=df,
        phase=phase,
        data_cutoff=cutoff_text,
        oos_start=frozen_oos,
        work_index=work_index.copy(),
        work_eligible=work_eligible,
        research_index=research_index.copy(),
        research_eligible=research_eligible,
        research_month_positions=_month_positions(research_months),
        investable_month_positions=_month_positions(
            research_months, research_eligible,
        ),
    )


def discovery_evidence_digest(
    result: Result,
    *,
    ruleset_version: str | None = None,
) -> str:
    """Hash immutable T0-T3 development evidence, excluding OOS and live Gold."""
    def value(raw):
        if isinstance(raw, (np.bool_, np.integer, np.floating)):
            raw = raw.item()
        if isinstance(raw, float):
            return round(raw, 14) if np.isfinite(raw) else None
        return raw

    metrics = {
        key: value(raw)
        for key, raw in result.metrics.items()
        if key.startswith(("ic_", "rank_icir_", "neutral_"))
        and not key.startswith("oos_")
    }
    payload = {
        "ruleset_version": ruleset_version or RULESET_VERSION,
        "definition_hash": result.definition_hash,
        "checks": [
            {
                "tier": check.tier,
                "name": check.name,
                "passed": value(check.passed),
                "value": value(check.value),
                "threshold": check.threshold,
                "note": check.note,
            }
            for check in result.checks
            if check.tier.startswith(("T0", "T1", "T2", "T3"))
        ],
        "metrics": metrics,
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _hac_mean_test(values: pd.Series, *, alternative: str = "greater") -> tuple[float, float, float]:
    """Mean, Newey-West t statistic, and one/two-sided p-value."""
    x = pd.Series(values, dtype=float).replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), float("nan")
    mean = float(x.mean())
    centered = x - mean
    lag = min(n - 1, max(1, int(np.floor(4 * (n / 100) ** (2 / 9)))))
    long_run = float(centered @ centered / n)
    for j in range(1, lag + 1):
        weight = 1 - j / (lag + 1)
        gamma = float(centered[j:] @ centered[:-j] / n)
        long_run += 2 * weight * gamma
    se = np.sqrt(max(long_run, 0.0) / n)
    t_value = mean / se if se > 0 else float("nan")
    if not np.isfinite(t_value):
        return mean, t_value, float("nan")
    if alternative == "greater":
        pvalue = float(stats.t.sf(t_value, df=n - 1))
    else:
        pvalue = float(2 * stats.t.sf(abs(t_value), df=n - 1))
    return mean, float(t_value), pvalue


def _ic_series(df: pd.DataFrame, col: str, fwd: str, min_n: int = 30) -> pd.Series:
    values: dict[pd.Period, float] = {}
    for ym, group in df.groupby("ym"):
        sample = group[[col, fwd]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(sample) < min_n:
            continue
        correlation = stats.spearmanr(sample[col], sample[fwd]).statistic
        if pd.notna(correlation):
            values[ym] = float(correlation)
    return pd.Series(values, dtype=float).sort_index()


def _ic_series_from_positions(
    df: pd.DataFrame,
    col: str,
    fwd: str,
    positions: tuple[tuple[pd.Period, np.ndarray], ...],
    min_n: int = 30,
) -> pd.Series:
    """Exact pairwise Spearman IC over precomputed monthly row positions."""
    left = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
    right = pd.to_numeric(df[fwd], errors="coerce").to_numpy(dtype=float)
    values: dict[pd.Period, float] = {}
    for ym, indices in positions:
        valid = indices[np.isfinite(left[indices]) & np.isfinite(right[indices])]
        if len(valid) < min_n:
            continue
        correlation = stats.spearmanr(left[valid], right[valid]).statistic
        if pd.notna(correlation):
            values[ym] = float(correlation)
    return pd.Series(values, dtype=float).sort_index()


def batch_signal_orthogonality(
    df: pd.DataFrame,
    signals: dict[str, pd.Series],
    *,
    eligible: pd.Series,
) -> dict:
    """Select one deterministic Gold survivor from each correlated batch.

    The statistic is the same monthly investable-universe median absolute
    Spearman correlation used by T5.  Selection never uses IC, OOS, or
    portfolio outcomes: factor names are visited in lexical order and a later
    factor is suppressed only when it conflicts with an already-kept factor.
    """
    names = sorted(signals)
    if len(names) != len(set(names)):
        raise ValueError("batch 직교성 대상 factor 이름은 고유해야 합니다")
    if not {"ym"}.issubset(df.columns):
        raise ValueError("batch 직교성 계산에 ym이 필요합니다")
    if not eligible.index.equals(df.index):
        raise ValueError("batch 직교성 investable mask index가 다릅니다")
    for name, values in signals.items():
        if not values.index.equals(df.index):
            raise ValueError(f"batch 직교성 signal index가 다릅니다: {name}")

    sample = df.loc[eligible.fillna(False).astype(bool), ["ym"]].copy()
    for name in names:
        sample[name] = pd.to_numeric(signals[name], errors="coerce").reindex(
            sample.index
        )

    pairs: list[dict] = []
    conflicts: dict[str, set[str]] = {name: set() for name in names}
    for left_index, left in enumerate(names):
        for right in names[left_index + 1:]:
            monthly: list[float] = []
            for _, group in sample.groupby("ym"):
                valid = group[[left, right]].replace(
                    [np.inf, -np.inf], np.nan
                ).dropna()
                if len(valid) < 30:
                    continue
                rho = stats.spearmanr(valid[left], valid[right]).statistic
                if pd.notna(rho):
                    monthly.append(abs(float(rho)))
            months = len(monthly)
            if months < TH["min_gold_corr_months"]:
                raise ValueError(
                    "batch 직교성 비교월이 부족합니다: "
                    f"{left}/{right}={months}, "
                    f"required={TH['min_gold_corr_months']}"
                )
            correlation = float(np.median(monthly))
            conflict = bool(correlation > TH["max_gold_corr"])
            if conflict:
                conflicts[left].add(right)
                conflicts[right].add(left)
            pairs.append({
                "left": left,
                "right": right,
                "median_absolute_spearman": correlation,
                "comparison_months": months,
                "conflict": conflict,
            })

    survivors: list[str] = []
    suppressed: list[dict] = []
    for name in names:
        blockers = sorted(conflicts[name].intersection(survivors))
        if blockers:
            suppressed.append({
                "factor": name,
                "kept_factor": blockers[0],
                "reason": "batch_signal_correlation_above_threshold",
            })
        else:
            survivors.append(name)
    return {
        "schema_version": "gold-batch-orthogonality-v1",
        "policy": "lexical_first_independent_of_research_outcomes_v1",
        "threshold": TH["max_gold_corr"],
        "minimum_comparison_months": TH["min_gold_corr_months"],
        "candidate_factors": names,
        "pairs": pairs,
        "survivors": survivors,
        "suppressed": suppressed,
    }


def _weights(group: pd.DataFrame, weighting: str) -> dict[int, float]:
    if weighting == "equal":
        raw = pd.Series(1.0, index=group["asset_id"].astype(int))
    elif weighting == "sqrt_cap":
        raw = pd.Series(
            np.sqrt(group["market_cap"].clip(lower=0).astype(float).to_numpy()),
            index=group["asset_id"].astype(int),
        )
    else:
        raise ValueError(f"지원하지 않는 weighting={weighting}")
    total = raw.sum()
    if not np.isfinite(total) or total <= 0:
        return {}
    return (raw / total).to_dict()


def _turnover(old: dict[int, float], new: dict[int, float]) -> float:
    if not old:
        return 1.0
    keys = set(old) | set(new)
    return 0.5 * sum(abs(new.get(k, 0.0) - old.get(k, 0.0)) for k in keys)


def backtest(
    df: pd.DataFrame,
    col: str,
    fwd: str,
    *,
    hold: int = 1,
    quantile: float = 0.2,
    weighting: str = "equal",
    cost_multiplier: float = 1.0,
    min_months: int | None = None,
    month_positions: tuple[tuple[pd.Period, np.ndarray], ...] | None = None,
) -> dict | None:
    """Fixed-universe long-only portfolio with next-period realized returns.

    ``_eligible`` controls formation and the benchmark.  Existing holdings stay
    in the return frame even if they later fall below the liquidity threshold.
    Factor missingness never changes the benchmark.
    """
    required = {"ym", "asset_id", col, fwd, "market_cap"}
    if not required.issubset(df.columns):
        return None
    minimum = TH["min_months"] if min_months is None else min_months
    current: dict[int, float] = {}
    rows: list[tuple] = []
    missing_held = held_observations = 0
    grouped = (
        month_positions
        if month_positions is not None
        else tuple(
            (pd.Period(ym, freq="M"), np.flatnonzero(df["ym"].eq(ym).to_numpy()))
            for ym in sorted(df["ym"].dropna().unique())
        )
    )

    for i, (ym, positions) in enumerate(grouped):
        group = df.iloc[positions].copy()
        eligible = group.get("_eligible", pd.Series(True, index=group.index)).fillna(False).astype(bool)
        benchmark_rows = group[eligible & group[fwd].notna()]
        eligible_count = int(eligible.sum())
        if eligible_count < 50 or len(benchmark_rows) < max(30, int(eligible_count * .95)):
            continue

        if not current or i % hold == 0:
            signal_ok = group[col].replace([np.inf, -np.inf], np.nan).notna()
            formation = group[eligible & signal_ok]
            k = max(int(eligible_count * quantile), 10)
            if len(formation) < k:
                continue
            selected = formation.nlargest(k, col)
            new = _weights(selected, weighting)
            turn = _turnover(current, new)
            current = new
        else:
            turn = 0.0

        held = group[group["asset_id"].isin(current)]
        held_observations += len(current)
        missing_held += max(len(current) - int(held[fwd].notna().sum()), 0)
        if len(held) != len(current) or held[fwd].isna().any():
            continue
        portfolio_return = sum(
            current[int(row.asset_id)] * float(getattr(row, fwd))
            for row in held[["asset_id", fwd]].itertuples(index=False)
        )
        benchmark_return = float(benchmark_rows[fwd].mean())
        tax = SECURITIES_TAX.get(int(ym.year), .0015)
        cost = turn * ((COMMISSION + IMPACT) * 2 + tax) * cost_multiplier
        rows.append((ym, portfolio_return, benchmark_return, turn, cost))

    if len(rows) < minimum:
        return None
    performance = pd.DataFrame(
        rows, columns=["ym", "ret", "bench", "turn", "cost"]
    ).set_index("ym")
    excess = performance["ret"] - performance["bench"] - performance["cost"]
    gross = performance["ret"] - performance["bench"]
    sd = excess.std(ddof=1)
    mean, hac_t, hac_p = _hac_mean_test(excess)
    missing_rate = missing_held / max(held_observations, 1)
    return {
        "months": len(performance),
        "turnover": float(performance["turn"].mean() * 12 * 100),
        "gross": float(gross.mean() * 12 * 100),
        "cost": float(performance["cost"].mean() * 12 * 100),
        "net": float(excess.mean() * 12 * 100),
        "net_ir": float(excess.mean() / sd * np.sqrt(12)) if sd > 0 else float("nan"),
        "hac_t": hac_t,
        "hac_pvalue": hac_p,
        "missing_return_rate": float(missing_rate),
        "_excess": excess,
        "_gross": gross,
    }


def _public_metrics(backtest_result: dict) -> dict:
    return {key: value for key, value in backtest_result.items() if not key.startswith("_")}


def attach_portfolio_diagnostics(
    result: Result,
    factor: Factor,
    panel: Panel,
    df: pd.DataFrame,
    *,
    context: EvaluationContext,
) -> Result:
    """Attach non-decision portfolio diagnostics after qualification only."""
    if "portfolio_diagnostics_deferred" not in result.labels:
        return result
    if (
        context.panel is not panel
        or context.frame is not df
        or context.phase != "discovery"
    ):
        raise ValueError("portfolio diagnostics context가 discovery frame과 다릅니다")
    col = f"f_{factor.name}"
    research = df.loc[context.research_index].copy()
    research["_eligible"] = context.research_eligible
    measured = backtest(
        research, col, "fwd_mid", hold=factor.rebalance_months,
        min_months=TH["min_oos_months"],
        month_positions=context.research_month_positions,
    )
    result.labels.remove("portfolio_diagnostics_deferred")
    if measured is None:
        result.labels.append("portfolio_diagnostics_unavailable")
        return result
    result.metrics.update(_public_metrics(measured))
    if measured["turnover"] > TH["turnover_warn"]:
        result.labels.append("high_turnover")
    if measured["turnover"] > TH["turnover_fail"]:
        result.labels.append("very_high_turnover")
    if measured["missing_return_rate"] > TH["max_missing_return"]:
        result.labels.append("high_missing_return")
    return result


def _deflated_sharpe_probability(
    excess: pd.Series,
    *,
    trial_count: int,
    prior_sharpes: tuple[float, ...] | list[float],
    observed_ir: float,
) -> float:
    values = pd.Series(excess, dtype=float).dropna()
    if len(values) < 3 or values.std(ddof=1) <= 0:
        return float("nan")
    monthly_sr = float(values.mean() / values.std(ddof=1))
    annual_sharpes = [float(x) for x in prior_sharpes if np.isfinite(x)] + [observed_ir]
    sigma_annual = float(np.std(annual_sharpes, ddof=1)) if len(annual_sharpes) > 1 else 0.0
    if trial_count > 1 and sigma_annual == 0:
        sigma_annual = np.sqrt(12 / len(values))
    gamma = 0.5772156649015329
    if trial_count > 1:
        expected_max_annual = sigma_annual * (
            (1 - gamma) * stats.norm.ppf(1 - 1 / trial_count)
            + gamma * stats.norm.ppf(1 - 1 / (trial_count * np.e))
        )
    else:
        expected_max_annual = 0.0
    benchmark_sr = expected_max_annual / np.sqrt(12)
    skew = float(stats.skew(values, bias=False))
    kurtosis = float(stats.kurtosis(values, fisher=False, bias=False))
    denominator = np.sqrt(
        max(1 - skew * monthly_sr + ((kurtosis - 1) / 4) * monthly_sr ** 2, 1e-12)
    )
    z = (monthly_sr - benchmark_sr) * np.sqrt(len(values) - 1) / denominator
    return float(stats.norm.cdf(z))


def _neutralized_signal(df: pd.DataFrame, col: str, category: str) -> pd.Series:
    output = pd.Series(np.nan, index=df.index, dtype=float)
    for _, group in df.groupby("ym"):
        eligible = group.get("_eligible", pd.Series(True, index=group.index)).fillna(False)
        columns = [col, "market_cap", "adv20", "market"]
        sample = group.loc[eligible, columns].replace([np.inf, -np.inf], np.nan).dropna(
            subset=[col, "adv20", "market_cap"]
        )
        if len(sample) < 50:
            continue
        y = sample[col].rank(pct=True).to_numpy(dtype=float)
        controls = [np.ones(len(sample)), np.log(sample["adv20"].clip(lower=1)).to_numpy()]
        if category != "size":
            controls.append(np.log(sample["market_cap"].clip(lower=1)).to_numpy())
        controls.append(sample["market"].eq("KOSDAQ").astype(float).to_numpy())
        matrix = np.column_stack(controls)
        residual = y - matrix @ np.linalg.lstsq(matrix, y, rcond=None)[0]
        output.loc[sample.index] = residual
    return output


def _validate_factor(factor: Factor, df: pd.DataFrame, cached: str) -> list[Check]:
    checks: list[Check] = []
    undeclared = factor.undeclared_constants()
    checks.append(Check("T0.1", "미선언 상수", not undeclared, len(undeclared), "0개", str(undeclared)))
    composite = factor.composite_evidence()
    checks.append(Check(
        "T0.2", "단일 팩터 계약", not composite, len(composite),
        "합성 신호 0개", str(composite),
    ))
    try:
        lookback = research_policy.assert_allowed_lookback(
            name=factor.name, source=factor.source, params=factor.params,
        )
        lookback_ok = True
        lookback_note = ""
    except ValueError as exc:
        lookback = None
        lookback_ok = False
        lookback_note = str(exc)
    checks.append(Check(
        "T0.3", "최대 룩백", lookback_ok, lookback,
        f"<={research_policy.MAX_FACTOR_LOOKBACK_MONTHS}개월", lookback_note,
    ))
    try:
        research_policy.assert_research_input_frame(df)
        input_floor_ok = True
        input_floor_note = ""
    except ValueError as exc:
        input_floor_ok = False
        input_floor_note = str(exc)
    checks.append(Check(
        "T0.4", "연구 입력 하한", input_floor_ok, None,
        f">={research_policy.RESEARCH_INPUT_START}", input_floor_note,
    ))
    forbidden_inputs = research_policy.forbidden_candidate_inputs(factor.needs)
    checks.append(Check(
        "T0.5", "label 전용 입력 차단", not forbidden_inputs,
        len(forbidden_inputs), "0개", str(forbidden_inputs),
    ))
    missing = sorted(set(factor.needs) - set(df.columns))
    checks.append(Check("T0.6", "입력 계약", not missing, len(missing), "누락 0개", str(missing)))
    if forbidden_inputs or missing or not lookback_ok or not input_floor_ok:
        return checks
    try:
        first = research_policy.authoritative_factor_values(factor, df, cached)
        if first is None:
            first = research_policy.compute_factor(factor, df)
        second = research_policy.compute_factor(factor, df)
        valid_series = isinstance(first, pd.Series) and first.index.equals(df.index)
        numeric = valid_series and pd.api.types.is_numeric_dtype(first)
        finite = numeric and not np.isinf(pd.to_numeric(first, errors="coerce")).any()
        deterministic = (
            numeric
            and isinstance(second, pd.Series)
            and second.index.equals(df.index)
            and np.allclose(first.to_numpy(dtype=float), second.to_numpy(dtype=float), equal_nan=True)
        )
        cache_match = (
            cached in df
            and numeric
            and np.allclose(
                (first * factor.predicted_sign).to_numpy(dtype=float),
                df[cached].to_numpy(dtype=float),
                equal_nan=True,
            )
        )
        causal_ok, causal_note = (
            research_policy.causal_lookback_check(factor, df, first)
            if numeric else (False, "출력이 numeric Series가 아닙니다")
        )
    except Exception as exc:
        valid_series = numeric = finite = deterministic = cache_match = causal_ok = False
        causal_note = f"{type(exc).__name__}: {exc}"
        checks.append(Check("T0.7", "계산 예외", False, None, "없음", f"{type(exc).__name__}: {exc}"))
    checks.extend([
        Check("T0.8", "출력 타입·인덱스", bool(valid_series and numeric), None, "numeric Series / 동일 index"),
        Check("T0.9", "유한값", bool(finite), None, "±inf 없음"),
        Check("T0.10", "결정성", bool(deterministic), None, "동일 입력 2회 일치"),
        Check("T0.11", "36개월 인과성", bool(causal_ok), None, "36개월 이전·미래 행 비의존", causal_note),
        Check("T0.12", "캐시 정의 일치", bool(cache_match), None, "현재 정의와 캐시 일치"),
    ])
    return checks


def _finalize(result: Result) -> None:
    hard = [c for c in result.failed if c.tier.startswith(("T0", "T1", "T2", "T4", "T5"))]
    soft = [c for c in result.failed if c.tier.startswith("T3")]
    pending = [c for c in result.pending if c.tier.startswith(("T0", "T1", "T2", "T4", "T5"))]
    if hard or len(soft) > 1:
        result.verdict = Verdict.REJECT
    elif len(soft) == 1:
        result.verdict = Verdict.PROVISIONAL
        label = f"soft_fail:{soft[0].name}"
        if label not in result.labels:
            result.labels.append(label)
    else:
        if pending or "oos_sealed" in result.labels:
            result.verdict = Verdict.PROVISIONAL
            if "discovery_pass" not in result.labels:
                result.labels.append("discovery_pass")
        else:
            result.verdict = Verdict.PROMOTE


def oos_effect_threshold_label() -> str:
    """Human-readable contract shared by formal and fallback OOS paths."""
    return (
        f"months=={TH['min_oos_months']} & "
        f"OOS IC>={TH['oos_ic']} & "
        f"OOS/Discovery>={TH['oos_ic_retention']}"
    )


def _oos_effect_check(
    oos_series: pd.Series,
    oos_ic: float,
    discovery_ic: float | None,
) -> tuple[float, float, Check]:
    """Require both an absolute OOS effect and retained discovery strength."""
    discovery = (
        float(discovery_ic)
        if discovery_ic is not None and np.isfinite(discovery_ic) and discovery_ic > 0
        else float("nan")
    )
    retention = (
        float(oos_ic / discovery)
        if np.isfinite(discovery) and np.isfinite(oos_ic)
        else float("nan")
    )
    required_ic = (
        max(TH["oos_ic"], TH["oos_ic_retention"] * discovery)
        if np.isfinite(discovery)
        else float("nan")
    )
    passed = bool(
        len(oos_series) == TH["min_oos_months"]
        and np.isfinite(oos_ic)
        and np.isfinite(required_ic)
        and oos_ic >= required_ic
    )
    note = (
        f"Discovery IC={discovery:.6g}, OOS 유지율={retention:.6g}; "
        "HAC p는 동시 확인되는 자동 통과 후보의 BY 입력값"
        if np.isfinite(discovery)
        else "인증된 Discovery IC가 없거나 비양수여서 유지율을 계산할 수 없음"
    )
    return retention, required_ic, Check(
        "T4.1", "고정 OOS IC", passed, oos_ic,
        oos_effect_threshold_label(), note,
    )


def evaluate(
    factor: Factor,
    panel: Panel,
    df: pd.DataFrame,
    *,
    existing: dict[str, pd.Series] | None = None,
    trial_count: int = 1,
    prior_sharpes: tuple[float, ...] | list[float] = (),
    oos_start: pd.Period | None = None,
    oos_end: pd.Period | None = None,
    data_cutoff: str | pd.Timestamp | None = None,
    phase: str = "full",
    context: EvaluationContext | None = None,
    internal_null_contract: InternalNullSignalContract | None = None,
    include_diagnostics: bool = True,
) -> Result:
    """Run the integrity/IC/robustness gate.

    Portfolio returns and costs are retained as diagnostics, never as promotion
    criteria. Call ``apply_multiple_testing`` on the result batch afterward.
    """
    if phase not in EVALUATION_PHASES:
        raise ValueError(f"지원하지 않는 평가 phase={phase!r}: {sorted(EVALUATION_PHASES)}")
    if oos_start is not None and data_cutoff is not None:
        from engine.boundaries import CampaignWindow

        window = CampaignWindow.create(
            discovery_data_cutoff=str(pd.Timestamp(data_cutoff).date()),
            oos_start=oos_start,
            oos_months=TH["min_oos_months"],
        )
        if phase == "full" and oos_end is not None:
            window.validate_oos_end(oos_end)
    col = f"f_{factor.name}"
    result = Result(factor=factor.name, definition_hash=factor.definition_hash)
    result.metrics["research_start"] = str(RESEARCH_START)
    result.metrics["evaluation_phase"] = phase
    if phase == "discovery":
        result.labels.append("oos_sealed")
    add = result.checks.append
    result.checks.extend(
        _internal_null_checks(factor, df, col, internal_null_contract)
        if internal_null_contract is not None
        else _validate_factor(factor, df, col)
    )
    if result.tier_failed("T0"):
        return result

    if context is not None:
        expected_cutoff = (
            str(pd.Timestamp(data_cutoff).normalize().date())
            if data_cutoff is not None else None
        )
        expected_oos = (
            pd.Period(oos_start, freq="M") if oos_start is not None else None
        )
        if (
            context.panel is not panel
            or context.frame is not df
            or context.phase != phase
            or context.data_cutoff != expected_cutoff
            or context.oos_start != expected_oos
        ):
            raise ValueError("gate context가 현재 panel/frame/평가 범위와 다릅니다")
        work = df.loc[context.work_index].copy()
        work["_eligible"] = context.work_eligible
        research = df.loc[context.research_index].copy()
        research["_eligible"] = context.research_eligible
        full_month_positions = context.research_month_positions
        investable_month_positions = context.investable_month_positions
    else:
        universe = panel.universe
        investable = panel.investable
        # Use one pre-declared start for every factor. Financial PIT coverage is not
        # broad enough before 2018-03, and warm-up missingness must not be mistaken
        # for a failed signal.
        work = df.loc[universe & df["ym"].ge(RESEARCH_START)].copy()
        work["_eligible"] = investable.loc[work.index].astype(bool)

        # Every discovery check remains bound to the campaign's original Silver
        # snapshot.  In particular, a delayed OOS start must not turn the intervening
        # years into new development data at reveal time.
        research = work
        if data_cutoff is not None:
            cutoff = pd.Timestamp(data_cutoff).normalize()
            research = research[
                pd.to_datetime(research["trade_date"]).dt.normalize().le(cutoff)
                & research["ym"].lt(cutoff.to_period("M"))
            ].copy()
        if oos_start is not None:
            research = research[research["ym"] < (oos_start - 1)].copy()
        full_month_positions = None
        investable_month_positions = None

    def scoped_ic(column: str, forward: str, *, investable_only: bool = False):
        positions = (
            investable_month_positions if investable_only
            else full_month_positions
        )
        if positions is not None:
            return _ic_series_from_positions(research, column, forward, positions)
        frame = research[research["_eligible"]] if investable_only else research
        return _ic_series(frame, column, forward)

    coverage = research[col].notna().mean()
    monthly_coverage = research.groupby("ym")[col].apply(lambda x: x.notna().mean())
    coverage_p10 = float(monthly_coverage.quantile(.10)) if len(monthly_coverage) else 0.0
    add(Check("T1.1", "전체 커버리지", coverage >= TH["coverage"], coverage, f">={TH['coverage']:.0%}"))
    add(Check("T1.1", "월별 커버리지 하위10%", coverage_p10 >= TH["monthly_coverage_p10"], coverage_p10, f">={TH['monthly_coverage_p10']:.0%}"))

    ic_scenarios: dict[str, pd.Series] = {}
    scenario_means: dict[str, float] = {}
    for tag in ("opt", "mid", "pess"):
        fwd = f"fwd_{tag}"
        if fwd in research:
            series = scoped_ic(col, fwd)
            ic_scenarios[tag] = series
            scenario_means[tag] = float(series.mean()) if len(series) else float("nan")
    terminal_stable = len(scenario_means) == 3 and all(value > 0 for value in scenario_means.values())
    add(Check("T1.2", "종착수익률 3점 방향", terminal_stable, None, "세 시나리오 IC > 0", str({k: round(v, 4) for k, v in scenario_means.items()})))
    total_return_certified = _label_return_certified(panel)
    add(Check(
        "T1.3", "배당 포함 총수익 계약", total_return_certified, None,
        "feature=adj_close / label=total_return_close v3(CERTIFIED) / candidate label 차단",
    ))
    if result.tier_failed("T1"):
        return result

    if research["ym"].nunique() < TH["min_months"]:
        add(Check("T2.0", "개발 표본", False, research["ym"].nunique(), f">={TH['min_months']}개월"))
        return result

    ic_full_series = ic_scenarios.get("mid")
    if ic_full_series is None:
        ic_full_series = scoped_ic(col, "fwd_mid")
    ic_full, ic_full_t, ic_full_p = _hac_mean_test(ic_full_series)
    result.metrics.update({"ic_full": ic_full, "ic_t_full": ic_full_t, "ic_p_full": ic_full_p})
    add(Check(
        "T2.1", "전체 IC 최소요건",
        bool(ic_full >= TH["min_ic"]), ic_full, f">={TH['min_ic']}",
    ))
    ic_investable_series = scoped_ic(col, "fwd_mid", investable_only=True)
    ic_inv, ic_inv_t, ic_inv_p = _hac_mean_test(ic_investable_series)
    ic_inv_std = float(ic_investable_series.std(ddof=1))
    rank_icir = ic_inv / ic_inv_std if np.isfinite(ic_inv_std) and ic_inv_std > 0 else float("nan")
    retention = ic_inv / ic_full if ic_full > 0 else float("nan")
    result.metrics.update({
        "ic_investable": ic_inv,
        "ic_std_investable": ic_inv_std,
        "rank_icir_investable": rank_icir,
        "ic_t_investable": ic_inv_t,
        "ic_p_investable": ic_inv_p,
        "ic_retention": retention,
    })
    add(Check(
        "T2.1", "투자가능 IC 최소요건",
        bool(ic_inv >= TH["min_investable_ic"]), ic_inv,
        f">={TH['min_investable_ic']}",
    ))
    add(Check(
        "T2.1", "투자가능 Rank ICIR 최소요건",
        bool(rank_icir >= TH["min_rank_icir"]), rank_icir,
        f">={TH['min_rank_icir']} (월평균 Rank IC / 월별 Rank IC 표준편차, 비연율화)",
    ))
    # The raw HAC p-value is the input to campaign-wide BY correction.  It is
    # reported, but a second p<=q hard check would be logically redundant.

    base = (
        backtest(
            research, col, "fwd_mid", hold=factor.rebalance_months,
            min_months=TH["min_oos_months"],
            month_positions=full_month_positions,
        )
        if include_diagnostics else None
    )
    # Execution and return outputs are diagnostics only.  Missing or expensive
    # portfolios do not alter the IC research verdict in ruleset v3.
    if not include_diagnostics:
        result.labels.append("portfolio_diagnostics_deferred")
    elif base is None:
        result.labels.append("portfolio_diagnostics_unavailable")
    else:
        result.metrics.update(_public_metrics(base))
        if base["turnover"] > TH["turnover_warn"]:
            result.labels.append("high_turnover")
        if base["turnover"] > TH["turnover_fail"]:
            result.labels.append("very_high_turnover")
        if base["missing_return_rate"] > TH["max_missing_return"]:
            result.labels.append("high_missing_return")
    if result.tier_failed("T2"):
        return result

    periods = pd.PeriodIndex(research["ym"].unique()).sort_values()
    segments = np.array_split(periods, 4)
    segment_ics = []
    for segment in segments:
        segment_ic = ic_investable_series.reindex(segment).dropna()
        segment_ics.append(float(segment_ic.mean()) if len(segment_ic) else float("nan"))
    agree = sum(np.isfinite(x) and x > 0 for x in segment_ics)
    add(Check("T3.1", "비중첩 구간 IC 방향", agree >= TH["subperiod_agree"], agree, f">={TH['subperiod_agree']}/4", str([round(x, 4) for x in segment_ics])))
    positive_segments = [max(x, 0.0) for x in segment_ics if np.isfinite(x)]
    concentration = max(positive_segments) / sum(positive_segments) if positive_segments and sum(positive_segments) > 0 else 1.0
    add(Check("T3.1", "IC 레짐 집중도", concentration <= TH["regime_conc"], concentration, f"<={TH['regime_conc']}"))

    research["_neutral"] = _neutralized_signal(research, col, factor.category)
    neutral_series = scoped_ic("_neutral", "fwd_mid", investable_only=True)
    neutral_ic, neutral_t, neutral_p = _hac_mean_test(neutral_series)
    neutral_retention = (
        neutral_ic / ic_inv
        if np.isfinite(neutral_ic) and np.isfinite(ic_inv) and ic_inv > 0
        else float("nan")
    )
    result.metrics.update({
        "neutral_ic": neutral_ic,
        "neutral_ic_t": neutral_t,
        "neutral_ic_p": neutral_p,
        "neutral_ic_retention": neutral_retention,
    })
    add(Check(
        "T3.2", "시장구분·유동성·비의도 규모 노출 제거 후 IC·유지율",
        bool(
            neutral_ic >= TH["neutral_ic"]
            and neutral_retention >= TH["neutral_ic_retention"]
        ),
        neutral_ic,
        f"IC>={TH['neutral_ic']} & neutral/investable>={TH['neutral_ic_retention']} "
        "(size category는 규모 노출 보존; HAC p는 진단값)",
        f"neutral/investable={neutral_retention:.6g}",
    ))
    if phase == "discovery":
        # The final holdout belongs to the campaign, not to an individual cycle.
        # Do not create a failed placeholder: absence is intentional and sealed.
        pass
    elif oos_start is None:
        add(Check("T4.1", "고정 OOS 설정", False, None, "campaign OOS_START 고정"))
    else:
        fixed_end = oos_end or (oos_start + TH["min_oos_months"] - 1)
        if fixed_end < oos_start:
            raise ValueError("OOS end는 OOS start보다 빠를 수 없습니다")
        oos = work[
            (work["ym"] >= oos_start)
            & (work["ym"] <= fixed_end)
            & work["_eligible"]
        ]
        oos_series = _ic_series(oos, col, "fwd_mid")
        oos_ic, oos_t, oos_p = _hac_mean_test(oos_series)
        result.metrics.update({
            "oos_start": str(oos_start),
            "oos_end": str(fixed_end),
            "oos_months": len(oos_series),
            "oos_ic": oos_ic,
            "oos_ic_t": oos_t,
            "oos_ic_p": oos_p,
        })
        oos_retention, oos_required_ic, oos_check = _oos_effect_check(
            oos_series, oos_ic, ic_inv,
        )
        result.metrics.update({
            "oos_discovery_ic": ic_inv,
            "oos_ic_retention": oos_retention,
            "oos_required_ic": oos_required_ic,
        })
        add(oos_check)

    result.metrics.update({"n_trials": trial_count})
    add(Check("T4.3", "다중검정 FDR", None, None, f"BY q<={TH['fdr_q']}", "배치 보정 대기"))

    if existing:
        signal_correlations: dict[str, float] = {}
        comparison_months: dict[str, int] = {}
        insufficient_comparisons: list[str] = []
        for name, values in existing.items():
            gold_col = f"_gold_{name}"
            aligned = values.reindex(df.index)
            research[gold_col] = aligned.reindex(research.index)
            monthly_corr = []
            for _, group in research[research["_eligible"]].groupby("ym"):
                sample = group[[col, gold_col]].dropna()
                if len(sample) >= 30:
                    rho = stats.spearmanr(sample[col], sample[gold_col]).statistic
                    if pd.notna(rho):
                        monthly_corr.append(abs(float(rho)))
            comparison_months[name] = len(monthly_corr)
            if len(monthly_corr) >= TH["min_gold_corr_months"]:
                signal_correlations[name] = float(np.median(monthly_corr))
            else:
                insufficient_comparisons.append(name)
        if signal_correlations:
            worst_signal, max_signal = max(
                signal_correlations.items(), key=lambda item: item[1]
            )
        else:
            worst_signal, max_signal = "", float("nan")
        result.metrics.update({
            "max_gold_signal_corr": max_signal,
            "gold_signal_comparison_months": comparison_months,
        })
        comparison_complete = not insufficient_comparisons and np.isfinite(max_signal)
        note = f"최대 상관 팩터={worst_signal}, 비교월={comparison_months.get(worst_signal, 0)}"
        if insufficient_comparisons:
            note += (
                f"; {TH['min_gold_corr_months']}개월 미만="
                f"{sorted(insufficient_comparisons)}"
            )
        add(Check(
            "T5.1", "Gold 신호 직교성",
            bool(comparison_complete and max_signal <= TH["max_gold_corr"]),
            max_signal,
            f"각 Gold 비교월>={TH['min_gold_corr_months']} & "
            f"max_j median_t |rho|<={TH['max_gold_corr']}",
            note,
        ))
    else:
        result.metrics.update({
            "max_gold_signal_corr": 0.0,
            "gold_signal_comparison_months": {},
        })
        add(Check("T5.1", "Gold 직교성", True, 0.0, "기존 APPROVED와 비교", "APPROVED 팩터 없음"))

    return result


def evaluate_oos(
    factor: Factor,
    panel: Panel,
    df: pd.DataFrame,
    *,
    oos_start: pd.Period,
    oos_end: pd.Period,
    data_cutoff: str,
    discovery_ic: float | None,
    internal_null_contract: InternalNullSignalContract | None = None,
    confirmation_signal_contract: ConfirmationSignalContract | None = None,
) -> Result:
    """Evaluate only the sealed OOS endpoint on its own fixed snapshot.

    Discovery evidence belongs to the cutoff snapshot and is merged by the
    caller.  Keeping this path separate prevents confirmation-boundary dead/
    forward labels from rewriting historical T1-T3 evidence.
    """
    from engine.boundaries import CampaignWindow

    window = CampaignWindow.create(
        discovery_data_cutoff=data_cutoff,
        oos_start=oos_start,
        oos_months=TH["min_oos_months"],
    )
    window.validate_oos_end(oos_end)
    col = f"f_{factor.name}"
    result = Result(factor=factor.name, definition_hash=factor.definition_hash)
    # The frozen window is audit metadata even when confirmation cannot be
    # computed.  A legitimate T0/data-contract failure must close the campaign
    # as REJECT, not leave it permanently unrevealable because the window keys
    # disappeared on an early return.
    result.metrics.update({
        "evaluation_phase": "confirmation_oos",
        "oos_start": str(oos_start),
        "oos_end": str(oos_end),
        "oos_months": 0,
        "oos_ic": None,
        "oos_ic_t": None,
        "oos_ic_p": None,
        "oos_discovery_ic": discovery_ic,
        "oos_ic_retention": None,
        "oos_required_ic": None,
    })
    if internal_null_contract is not None and confirmation_signal_contract is not None:
        raise ValueError("OOS signal 인증 계약은 하나만 허용됩니다")
    result.checks.extend(
        _internal_null_checks(factor, df, col, internal_null_contract)
        if internal_null_contract is not None
        else _confirmation_signal_check(
            factor, df, col, confirmation_signal_contract,
        )
        if confirmation_signal_contract is not None
        else _validate_factor(factor, df, col)
    )
    if result.tier_failed("T0"):
        return result
    if not _label_return_certified(panel):
        result.checks.append(Check(
            "T4.1", "고정 OOS IC", False, None,
            "feature/label 역할 분리 + 인증된 label total_return_close",
            "수익률 역할 또는 label 총수익 계약 실패",
        ))
        return result
    work = df.loc[
        panel.universe
        & panel.investable
        & df["ym"].ge(oos_start)
        & df["ym"].le(oos_end)
    ].copy()
    oos_series = _ic_series(work, col, "fwd_mid")
    oos_ic, oos_t, oos_p = _hac_mean_test(oos_series)
    result.metrics.update({
        "oos_start": str(oos_start),
        "oos_end": str(oos_end),
        "oos_months": len(oos_series),
        "oos_ic": oos_ic,
        "oos_ic_t": oos_t,
        "oos_ic_p": oos_p,
    })
    oos_retention, oos_required_ic, oos_check = _oos_effect_check(
        oos_series, oos_ic, discovery_ic,
    )
    result.metrics.update({
        "oos_discovery_ic": discovery_ic,
        "oos_ic_retention": oos_retention,
        "oos_required_ic": oos_required_ic,
    })
    result.checks.append(oos_check)
    result.series["oos_ic"] = oos_series
    return result


def by_qvalues(
    pvalues: dict[str, float]
    | tuple[tuple[str, float], ...]
    | list[tuple[str, float]],
) -> dict[str, float]:
    """Benjamini-Yekutieli q-values, valid under arbitrary dependence."""
    if not isinstance(pvalues, dict):
        pvalues = dict(pvalues)
    clean = {
        str(key): min(max(float(value), 0.0), 1.0)
        for key, value in pvalues.items()
        if value is not None and np.isfinite(value)
    }
    ordered = sorted(clean.items(), key=lambda item: item[1])
    m = len(ordered)
    if not m:
        return {}
    dependence_penalty = sum(1 / rank for rank in range(1, m + 1))
    adjusted = [
        min(1.0, p * m * dependence_penalty / rank)
        for rank, (_, p) in enumerate(ordered, 1)
    ]
    for i in range(m - 2, -1, -1):
        adjusted[i] = min(adjusted[i], adjusted[i + 1])
    return {ordered[i][0]: adjusted[i] for i in range(m)}


def apply_multiple_testing(
    results: list[Result],
    historical_pvalues: tuple[tuple[str, float], ...] | list[tuple[str, float]] = (),
    *,
    defer: bool = False,
    total_trials: int | None = None,
) -> None:
    """Apply discovery IC BY-FDR, or leave it pending for an epoch batch."""
    if defer:
        for result in results:
            if "fdr_pending" not in result.labels:
                result.labels.append("fdr_pending")
            _finalize(result)
        return

    pvalues = {key: float(value) for key, value in historical_pvalues if np.isfinite(value)}
    for result in results:
        pvalue = result.metrics.get("ic_p_investable")
        if pvalue is not None and np.isfinite(pvalue):
            pvalues[result.definition_hash] = float(pvalue)
    target_count = max(int(total_trials or 0), len(pvalues))
    for index in range(target_count - len(pvalues)):
        pvalues[f"__untested_definition_{index}"] = 1.0
    qvalues = by_qvalues(pvalues)
    ordered = sorted(pvalues.items(), key=lambda item: item[1])
    m = len(ordered)

    for result in results:
        for index, check in enumerate(result.checks):
            if check.tier == "T4.3" and check.name == "다중검정 FDR":
                qvalue = qvalues.get(result.definition_hash, float("nan"))
                result.metrics["fdr_qvalue"] = qvalue
                result.checks[index] = Check(
                    "T4.3", "다중검정 FDR",
                    bool(np.isfinite(qvalue) and qvalue <= TH["fdr_q"]),
                    qvalue, f"BY q<={TH['fdr_q']}", f"전체 고유 시행 {m}개",
                )
                break
        _finalize(result)


def apply_oos_multiple_testing(results: list[Result]) -> None:
    """Control BY-FDR across every automatically qualified factor."""
    # A qualified factor that stops before T4 still counts as an attempted confirmation.
    # Assigning p=1 preserves the registered family size without manufacturing
    # OOS evidence for a result that never reached the OOS test.
    hashes = [result.definition_hash for result in results]
    if len(hashes) != len(set(hashes)):
        raise ValueError("OOS 자동 통과 후보 definition hash는 고유해야 합니다")
    pvalues = {
        result.definition_hash: (
            float(result.metrics["oos_ic_p"])
            if result.metrics.get("oos_ic_p") is not None
            and np.isfinite(result.metrics["oos_ic_p"])
            else 1.0
        )
        for result in results
    }
    qvalues = by_qvalues(pvalues)
    m = len(pvalues)
    for result in results:
        pvalue = result.metrics.get("oos_ic_p")
        qvalue = qvalues[result.definition_hash]
        result.metrics["oos_fdr_qvalue"] = qvalue
        testable = pvalue is not None and np.isfinite(pvalue)
        result.metrics["oos_fdr_status"] = (
            "PASS" if testable and qvalue <= TH["fdr_q"]
            else "FAIL" if testable else "NOT_TESTABLE"
        )
        result.checks.append(Check(
            "T4.2", "OOS 다중검정 FDR",
            bool(testable and qvalue <= TH["fdr_q"]), qvalue,
            f"BY q<={TH['fdr_q']}",
            f"동시 확인 자동 통과 후보 {m}개; "
            + ("유효 HAC p" if testable else "HAC p 누락으로 p=1 대입"),
        ))
        _finalize(result)


def apply_null_calibration(
    results: list[Result],
    calibration: pd.DataFrame | None,
    *,
    data_cutoff: str,
    oos_start: str | pd.Period | None = None,
    discovery_family_size: int | None = None,
    oos_family_size: int | None = None,
    discovery_family_digest: str | None = None,
    oos_family_digest: str | None = None,
    gold_family_digest: str | None = None,
    confirmation_snapshot_digest: str | None = None,
    research_data_cutoff: str | None = None,
    oos_end: str | pd.Period | None = None,
    qualification_policy: str | None = None,
    min_nulls: int = 100,
    min_nulls_per_kind: int = 25,
    max_false_positive_rate: float = .10,
) -> None:
    """Require a recent full-gate null calibration before allowing PROMOTE."""
    valid = calibration is not None and not calibration.empty
    note = ""
    rate = float("nan")
    worst_kind_rate = float("nan")
    count = 0
    if valid:
        required = {
            "ruleset_version", "data_cutoff", "pass", "calibration_unit", "fdr_q",
            "kind", "generator_suite", "qualification_policy",
        }
        if oos_start is not None:
            required.update({
                "oos_start", "discovery_family_size", "oos_family_size",
                "discovery_family_digest", "oos_family_digest", "gold_family_digest",
                "confirmation_snapshot_digest", "research_data_cutoff", "oos_end",
            })
        valid = required.issubset(calibration.columns)
        if valid:
            current = calibration[
                calibration["ruleset_version"].eq(RULESET_VERSION)
                & calibration["data_cutoff"].astype(str).eq(data_cutoff)
                & calibration["calibration_unit"].eq("null_campaign_family")
                & calibration["fdr_q"].eq(TH["fdr_q"])
                & calibration["generator_suite"].eq("null-v2")
            ]
            if oos_start is not None:
                if (
                    discovery_family_size is None
                    or oos_family_size is None
                    or discovery_family_digest is None
                    or oos_family_digest is None
                    or gold_family_digest is None
                    or confirmation_snapshot_digest is None
                    or research_data_cutoff is None
                    or oos_end is None
                    or qualification_policy is None
                ):
                    current = current.iloc[0:0]
                else:
                    current = current[
                        current["oos_start"].astype(str).eq(str(pd.Period(oos_start, freq="M")))
                        & current["discovery_family_size"].eq(int(discovery_family_size))
                        & current["oos_family_size"].eq(int(oos_family_size))
                        & current["discovery_family_digest"].astype(str).eq(discovery_family_digest)
                        & current["oos_family_digest"].astype(str).eq(oos_family_digest)
                        & current["gold_family_digest"].astype(str).eq(gold_family_digest)
                        & current["confirmation_snapshot_digest"].astype(str).eq(
                            confirmation_snapshot_digest
                        )
                        & current["research_data_cutoff"].astype(str).eq(research_data_cutoff)
                        & current["oos_end"].astype(str).eq(str(pd.Period(oos_end, freq="M")))
                        & current["qualification_policy"].astype(str).eq(
                            qualification_policy
                        )
                    ]
            count = len(current)
            rate = float(current["pass"].astype(bool).mean()) if count else float("nan")
            expected_kinds = {"random", "ar1_095", "ar1_0999", "frozen"}
            kind_counts = current.groupby("kind").size().to_dict()
            kind_rates = current.groupby("kind")["pass"].apply(
                lambda values: float(values.astype(bool).mean())
            ).to_dict()
            worst_kind_rate = max(kind_rates.values(), default=float("nan"))
            valid = (
                count >= min_nulls
                and expected_kinds.issubset(kind_counts)
                and all(kind_counts[kind] >= min_nulls_per_kind for kind in expected_kinds)
                and np.isfinite(rate)
                and np.isfinite(worst_kind_rate)
                and worst_kind_rate <= max_false_positive_rate
            )
            scope = (
                "동일 snapshot/ruleset/OOS/campaign family"
                if oos_start is not None else "동일 snapshot/ruleset"
            )
            note = (
                f"{scope} 귀무 campaign {count}개, 전체/최악 종류 오류율 "
                f"{rate:.1%}/{worst_kind_rate:.1%}"
                if count else f"{scope} 기록 없음"
            )
    if not note:
        note = "null_dist.parquet 없음 또는 구형 형식"
    for result in results:
        result.metrics["null_count"] = count
        result.metrics["null_family_error_rate"] = rate if np.isfinite(rate) else None
        result.metrics["null_worst_kind_error_rate"] = (
            worst_kind_rate if np.isfinite(worst_kind_rate) else None
        )
        result.metrics["null_discovery_family_size"] = discovery_family_size
        result.metrics["null_oos_family_size"] = oos_family_size
        result.metrics["null_oos_family_digest"] = oos_family_digest
        result.metrics["null_gold_family_digest"] = gold_family_digest
        result.metrics["null_confirmation_snapshot_digest"] = confirmation_snapshot_digest
        result.metrics["null_qualification_policy"] = qualification_policy
        if any(check.tier.startswith("T4") for check in result.checks):
            calibrated = Check(
                "T4.4", "게이트 귀무 보정", bool(valid), rate if np.isfinite(rate) else None,
                f"n>={min_nulls}, kind n>={min_nulls_per_kind}, "
                f"worst FPR<={max_false_positive_rate:.0%}", note,
            )
            existing_index = next(
                (i for i, check in enumerate(result.checks) if check.tier == "T4.4"),
                None,
            )
            if existing_index is None:
                result.checks.append(calibrated)
            else:
                result.checks[existing_index] = calibrated
        _finalize(result)


def assert_null_calibration(
    calibration: pd.DataFrame | None,
    **scope,
) -> dict:
    """Abort before sealed OOS computation unless null calibration is valid."""
    probe = Result(
        factor="__null_calibration_preflight__",
        definition_hash="__preflight__",
        checks=[Check("T4.4", "게이트 귀무 보정", None)],
    )
    apply_null_calibration([probe], calibration, **scope)
    check = next(
        item for item in probe.checks
        if item.tier == "T4.4" and item.name == "게이트 귀무 보정"
    )
    if check.passed is not True:
        raise ValueError(
            "봉인 OOS 공개 전 귀무 보정 사전조건 실패: "
            f"{check.note}. `python scripts/run.py null --campaign <id> --n 25`를 "
            "현재 snapshot에서 다시 실행하세요. OOS는 아직 계산하지 않았습니다."
        )
    return dict(probe.metrics)
