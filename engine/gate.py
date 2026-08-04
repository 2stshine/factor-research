"""Deterministic factor promotion gate.

The order is intentional: definition and sample integrity first, execution and
robustness next, statistical selection control after that, and finally marginal
value versus the already-approved Gold catalog.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats

from engine.factors import Factor
from engine.panel import Panel


RULESET_VERSION = "fr-3.1.0"
RESEARCH_START = pd.Period("2018-03", freq="M")

SECURITIES_TAX = {
    2015: .0030, 2016: .0030, 2017: .0030, 2018: .0030, 2019: .0025,
    2020: .0025, 2021: .0023, 2022: .0023, 2023: .0020, 2024: .0018,
    2025: .0015, 2026: .0015,
}
COMMISSION = 0.00015
IMPACT = 0.0010

TH = {
    "min_months": 60,
    "min_oos_months": 24,
    "coverage": 0.50,
    "monthly_coverage_p10": 0.30,
    "min_ic": 0.02,
    "min_investable_ic": 0.01,
    "investable_retention": 0.50,
    "ic_p": 0.10,
    "turnover_warn": 250.0,
    "turnover_fail": 400.0,
    "subperiod_agree": 3,
    "max_corr": 0.80,
    "regime_conc": 0.60,
    "neutral_ic": 0.01,
    "oos_ic": 0.01,
    "oos_p": 0.10,
    "fdr_q": 0.10,
    "max_missing_return": 0.01,
}


class Verdict(str, Enum):
    PROMOTE = "PROMOTE"
    PROVISIONAL = "PROVISIONAL"
    REJECT = "REJECT"


@dataclass
class Check:
    tier: str
    name: str
    passed: bool
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
        return [check for check in self.checks if not check.passed]

    def tier_failed(self, prefix: str) -> bool:
        return any(not c.passed and c.tier.startswith(prefix) for c in self.checks)


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
    months = sorted(df["ym"].dropna().unique())

    for i, ym in enumerate(months):
        group = df[df["ym"] == ym].copy()
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
        if "sector" in group.columns:
            columns.append("sector")
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
        if "sector" in sample.columns:
            dummies = pd.get_dummies(sample["sector"], drop_first=True, dtype=float)
            controls.extend(dummies[column].to_numpy() for column in dummies)
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
        "T0.1", "단일 팩터 계약", not composite, len(composite),
        "합성 신호 0개", str(composite),
    ))
    missing = sorted(set(factor.needs) - set(df.columns))
    checks.append(Check("T0.2", "입력 계약", not missing, len(missing), "누락 0개", str(missing)))
    if missing:
        return checks
    try:
        first = factor.compute(df)
        second = factor.compute(df)
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
    except Exception as exc:
        valid_series = numeric = finite = deterministic = cache_match = False
        checks.append(Check("T0.3", "계산 예외", False, None, "없음", f"{type(exc).__name__}: {exc}"))
    checks.extend([
        Check("T0.3", "출력 타입·인덱스", bool(valid_series and numeric), None, "numeric Series / 동일 index"),
        Check("T0.3", "유한값", bool(finite), None, "±inf 없음"),
        Check("T0.4", "결정성", bool(deterministic), None, "동일 입력 2회 일치"),
        Check("T0.4", "캐시 정의 일치", bool(cache_match), None, "현재 정의와 캐시 일치"),
    ])
    return checks


def _finalize(result: Result) -> None:
    hard = [c for c in result.failed if c.tier.startswith(("T0", "T1", "T2", "T4", "T5"))]
    soft = [c for c in result.failed if c.tier.startswith("T3")]
    if hard or len(soft) > 1:
        result.verdict = Verdict.REJECT
    elif len(soft) == 1:
        result.verdict = Verdict.PROVISIONAL
        label = f"soft_fail:{soft[0].name}"
        if label not in result.labels:
            result.labels.append(label)
    else:
        result.verdict = Verdict.PROMOTE


def evaluate(
    factor: Factor,
    panel: Panel,
    df: pd.DataFrame,
    *,
    existing: dict[str, pd.Series] | None = None,
    trial_count: int = 1,
    prior_sharpes: tuple[float, ...] | list[float] = (),
    oos_start: pd.Period | None = None,
) -> Result:
    """Run the integrity/IC/robustness gate.

    Portfolio returns and costs are retained as diagnostics, never as promotion
    criteria. Call ``apply_multiple_testing`` on the result batch afterward.
    """
    col = f"f_{factor.name}"
    result = Result(factor=factor.name, definition_hash=factor.definition_hash)
    result.metrics["research_start"] = str(RESEARCH_START)
    add = result.checks.append
    result.checks.extend(_validate_factor(factor, df, col))
    if result.tier_failed("T0"):
        return result

    universe = panel.universe
    investable = panel.investable
    # Use one pre-declared start for every factor. Financial PIT coverage is not
    # broad enough before 2018-03, and warm-up missingness must not be mistaken
    # for a failed signal.
    work = df.loc[universe & df["ym"].ge(RESEARCH_START)].copy()
    work["_eligible"] = investable.loc[work.index].astype(bool)

    coverage = work[col].notna().mean()
    monthly_coverage = work.groupby("ym")[col].apply(lambda x: x.notna().mean())
    coverage_p10 = float(monthly_coverage.quantile(.10)) if len(monthly_coverage) else 0.0
    add(Check("T1.1", "전체 커버리지", coverage >= TH["coverage"], coverage, f">={TH['coverage']:.0%}"))
    add(Check("T1.1", "월별 커버리지 하위10%", coverage_p10 >= TH["monthly_coverage_p10"], coverage_p10, f">={TH['monthly_coverage_p10']:.0%}"))

    ic_scenarios: dict[str, pd.Series] = {}
    scenario_means: dict[str, float] = {}
    for tag in ("opt", "mid", "pess"):
        fwd = f"fwd_{tag}"
        if fwd in work:
            series = _ic_series(work, col, fwd)
            ic_scenarios[tag] = series
            scenario_means[tag] = float(series.mean()) if len(series) else float("nan")
    terminal_stable = len(scenario_means) == 3 and all(value > 0 for value in scenario_means.values())
    add(Check("T1.2", "종착수익률 3점 방향", terminal_stable, None, "세 시나리오 IC > 0", str({k: round(v, 4) for k, v in scenario_means.items()})))
    add(Check("T1.3", "총수익 필드", panel.meta.get("return_field") == "total_return_close", None, "Silver total_return_close"))
    if result.tier_failed("T1"):
        return result

    # T2/T3 are development-sample tests.  The month immediately preceding the
    # OOS formation boundary is embargoed because its forward label overlaps OOS.
    research = work
    if oos_start is not None:
        research = work[work["ym"] < (oos_start - 1)].copy()
    if research["ym"].nunique() < TH["min_months"]:
        add(Check("T2.0", "개발 표본", False, research["ym"].nunique(), f">={TH['min_months']}개월"))
        return result

    ic_full_series = _ic_series(research, col, "fwd_mid")
    ic_full, ic_full_t, ic_full_p = _hac_mean_test(ic_full_series)
    result.metrics.update({"ic_full": ic_full, "ic_t_full": ic_full_t, "ic_p_full": ic_full_p})
    add(Check(
        "T2.1", "전체 IC 최소요건",
        bool(ic_full >= TH["min_ic"]), ic_full, f">={TH['min_ic']}",
    ))
    add(Check(
        "T2.1", "전체 IC HAC 유의성",
        bool(ic_full_p <= TH["ic_p"]), ic_full_p, f"one-sided p<={TH['ic_p']}",
    ))

    ic_investable_series = _ic_series(research[research["_eligible"]], col, "fwd_mid")
    ic_inv, ic_inv_t, ic_inv_p = _hac_mean_test(ic_investable_series)
    retention = ic_inv / ic_full if ic_full > 0 else float("nan")
    result.metrics.update({
        "ic_investable": ic_inv,
        "ic_t_investable": ic_inv_t,
        "ic_p_investable": ic_inv_p,
        "ic_retention": retention,
    })
    add(Check(
        "T2.1", "투자가능 IC 최소요건",
        bool(ic_inv >= TH["min_investable_ic"]), ic_inv,
        f">={TH['min_investable_ic']}",
    ))
    add(Check("T2.1", "투자가능 IC 유지율", bool(retention >= TH["investable_retention"]), retention, f">={TH['investable_retention']}"))
    add(Check("T2.1", "투자가능 IC HAC 유의성", bool(ic_inv_p <= TH["ic_p"]), ic_inv_p, f"one-sided p<={TH['ic_p']}"))

    base = backtest(
        research, col, "fwd_mid", hold=factor.rebalance_months,
        min_months=TH["min_oos_months"],
    )
    # Execution and return outputs are diagnostics only.  Missing or expensive
    # portfolios do not alter the IC research verdict in ruleset v3.
    if base is None:
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
        segment_ic = _ic_series(
            research[research["ym"].isin(segment) & research["_eligible"]],
            col, "fwd_mid",
        )
        segment_ics.append(float(segment_ic.mean()) if len(segment_ic) else float("nan"))
    agree = sum(np.isfinite(x) and x > 0 for x in segment_ics)
    add(Check("T3.1", "비중첩 구간 IC 방향", agree >= TH["subperiod_agree"], agree, f">={TH['subperiod_agree']}/4", str([round(x, 4) for x in segment_ics])))
    positive_segments = [max(x, 0.0) for x in segment_ics if np.isfinite(x)]
    concentration = max(positive_segments) / sum(positive_segments) if positive_segments and sum(positive_segments) > 0 else 1.0
    add(Check("T3.1", "IC 레짐 집중도", concentration <= TH["regime_conc"], concentration, f"<={TH['regime_conc']}"))

    research["_neutral"] = _neutralized_signal(research, col, factor.category)
    neutral_series = _ic_series(research[research["_eligible"]], "_neutral", "fwd_mid")
    neutral_ic, neutral_t, neutral_p = _hac_mean_test(neutral_series)
    result.metrics.update({
        "neutral_ic": neutral_ic,
        "neutral_ic_t": neutral_t,
        "neutral_ic_p": neutral_p,
    })
    add(Check(
        "T3.2", "시장·규모·유동성 중립 IC",
        bool(neutral_ic >= TH["neutral_ic"] and neutral_p <= TH["ic_p"]),
        neutral_ic, f"IC>={TH['neutral_ic']} & p<={TH['ic_p']}",
    ))
    sector_available = "sector" in research.columns and research["sector"].notna().mean() >= .80
    add(Check("T3.4", "섹터 중립화 가능", sector_available, research["sector"].notna().mean() if "sector" in research else 0.0, ">=80% sector coverage", "Silver sector 컬럼 필요" if not sector_available else ""))

    if oos_start is None:
        add(Check("T4.1", "고정 OOS 설정", False, None, "OOS_START 고정"))
    else:
        oos = work[(work["ym"] >= oos_start) & work["_eligible"]]
        oos_series = _ic_series(oos, col, "fwd_mid")
        oos_ic, oos_t, oos_p = _hac_mean_test(oos_series)
        result.metrics.update({
            "oos_start": str(oos_start),
            "oos_months": len(oos_series),
            "oos_ic": oos_ic,
            "oos_ic_t": oos_t,
            "oos_ic_p": oos_p,
        })
        oos_pass = bool(
            len(oos_series) >= TH["min_oos_months"]
            and oos_ic >= TH["oos_ic"]
            and oos_p <= TH["oos_p"]
        )
        add(Check("T4.1", "고정 OOS IC", oos_pass, oos_ic, f"IC>={TH['oos_ic']} & p<={TH['oos_p']}"))

    result.metrics.update({"n_trials": trial_count})
    add(Check("T4.3", "다중검정 FDR", False, None, f"BY q<={TH['fdr_q']}", "배치 보정 대기"))

    if existing:
        max_signal = 0.0
        worst_signal = ""
        for name, values in existing.items():
            gold_col = f"_gold_{name}"
            aligned = values.reindex(df.index)
            work[gold_col] = aligned.reindex(work.index)
            monthly_corr = []
            for _, group in work[work["_eligible"]].groupby("ym"):
                sample = group[[col, gold_col]].dropna()
                if len(sample) >= 30:
                    rho = stats.spearmanr(sample[col], sample[gold_col]).statistic
                    if pd.notna(rho):
                        monthly_corr.append(abs(float(rho)))
            signal_corr = float(np.median(monthly_corr)) if monthly_corr else 0.0
            if signal_corr > max_signal:
                max_signal, worst_signal = signal_corr, name
        add(Check("T5.1", "Gold 신호 직교성", max_signal <= TH["max_corr"], max_signal, f"median |rho|<={TH['max_corr']}", worst_signal))
    else:
        add(Check("T5.1", "Gold 직교성", True, 0.0, "기존 APPROVED와 비교", "APPROVED 팩터 없음"))

    return result


def apply_multiple_testing(
    results: list[Result],
    historical_pvalues: tuple[tuple[str, float], ...] | list[tuple[str, float]] = (),
) -> None:
    """Apply Benjamini-Yekutieli FDR control, valid under arbitrary dependence."""
    pvalues = {key: float(value) for key, value in historical_pvalues if np.isfinite(value)}
    for result in results:
        pvalue = result.metrics.get("ic_p_investable")
        if pvalue is not None and np.isfinite(pvalue):
            pvalues[result.definition_hash] = float(pvalue)
    ordered = sorted(pvalues.items(), key=lambda item: item[1])
    m = len(ordered)
    qvalues: dict[str, float] = {}
    if m:
        dependence_penalty = sum(1 / rank for rank in range(1, m + 1))
        adjusted = [min(1.0, p * m * dependence_penalty / rank) for rank, (_, p) in enumerate(ordered, 1)]
        for i in range(m - 2, -1, -1):
            adjusted[i] = min(adjusted[i], adjusted[i + 1])
        qvalues = {ordered[i][0]: adjusted[i] for i in range(m)}

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


def apply_null_calibration(
    results: list[Result],
    calibration: pd.DataFrame | None,
    *,
    data_cutoff: str,
    min_nulls: int = 100,
    max_false_positive_rate: float = .10,
) -> None:
    """Require a recent full-gate null calibration before allowing PROMOTE."""
    valid = calibration is not None and not calibration.empty
    note = ""
    rate = float("nan")
    count = 0
    if valid:
        required = {"ruleset_version", "data_cutoff", "pass"}
        valid = required.issubset(calibration.columns)
        if valid:
            current = calibration[
                calibration["ruleset_version"].eq(RULESET_VERSION)
                & calibration["data_cutoff"].astype(str).eq(data_cutoff)
            ]
            count = len(current)
            rate = float(current["pass"].astype(bool).mean()) if count else float("nan")
            valid = count >= min_nulls and np.isfinite(rate) and rate <= max_false_positive_rate
            note = f"동일 snapshot/ruleset 귀무 {count}개, 위양성률 {rate:.1%}" if count else "동일 snapshot/ruleset 기록 없음"
    if not note:
        note = "null_dist.parquet 없음 또는 구형 형식"
    for result in results:
        result.metrics["null_count"] = count
        result.metrics["realized_fdr"] = rate if np.isfinite(rate) else None
        if any(check.tier.startswith("T4") for check in result.checks):
            calibrated = Check(
                "T4.4", "게이트 귀무 보정", bool(valid), rate if np.isfinite(rate) else None,
                f"n>={min_nulls} & FPR<={max_false_positive_rate:.0%}", note,
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
