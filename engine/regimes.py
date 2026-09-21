"""Causal monthly market context; diagnostic only, never a promotion gate.

Input is one explicitly identified market index, not candidate returns or a
survivorship-biased reconstruction from today's listed stocks. See the regime
section in research/INSTRUCTIONS.md for the input and interpretation contract.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd


RULES_V1 = {
    "version": "monthly-trend-vol-v1",
    "trend_months": 10,
    "vol_return_months": 12,
    "vol_ddof": 1,
    "annualization": 12,
    "threshold": "expanding_median_excluding_current_month",
    "min_prior_vol_months": 24,
    "ties": "close_equal_sma_UP;vol_equal_median_LOW",
}
RULES = {
    **RULES_V1,
    "version": "monthly-trend-vol-v2",
    "short_trend": "trailing_three_month_simple_return_gte_zero",
    "short_trend_months": 3,
    "short_vol_return_months": 3,
    "short_vol_threshold": "own_expanding_median_excluding_current_month",
    "ties": "close_equal_sma_UP;return_equal_zero_UP;vol_equal_own_median_LOW",
    "hierarchy": "four_axis_marginals_then_coarse_four_then_detail_sixteen",
    "minimum_descriptive_months": 12,
    "minimum_descriptive_episodes": 3,
}
RULESETS = {rule["version"]: rule for rule in (RULES_V1, RULES)}
RULE_HASHES = {version: hashlib.sha256(json.dumps(rule, sort_keys=True).encode()).hexdigest()
               for version, rule in RULESETS.items()}
RULES_HASH = hashlib.sha256(
    json.dumps(RULES, sort_keys=True).encode()
).hexdigest()

TREND_PHASES = {
    ("UP", "UP"): "UP_CONFIRMED", ("UP", "DOWN"): "UP_PULLBACK",
    ("DOWN", "UP"): "DOWN_REBOUND", ("DOWN", "DOWN"): "DOWN_CONFIRMED",
}
VOLATILITY_PHASES = {
    ("LOW", "LOW"): "LOW_BOTH", ("LOW", "HIGH"): "SHORT_HIGH_ONLY",
    ("HIGH", "LOW"): "LONG_HIGH_ONLY", ("HIGH", "HIGH"): "HIGH_BOTH",
}


def detailed_regime(trend_long: str, trend_short: str, vol_long: str, vol_short: str) -> str:
    if (trend_long, trend_short) not in TREND_PHASES or (vol_long, vol_short) not in VOLATILITY_PHASES:
        return "UNKNOWN"
    return f"LT_{trend_long}_ST_{trend_short}_LV_{vol_long}_SV_{vol_short}"


def classify_monthly_market(
    observations: pd.DataFrame, *, as_of: str, market_id: str, source_id: str,
    rules_version: str = RULES["version"],
) -> pd.DataFrame:
    """Return completed-month context known by ``as_of`` (end of that date).

    Required columns: month (YYYY-MM), close (positive index level), known_at
    (date the *final* monthly observation was available). Rows must be immutable
    historical observations; revised/backfilled series need separate PIT review.
    known_at must be in its observation month or later. Only completed months
    and known rows are used. Month t labels are eligible for t+1 outcomes, not
    a claim of predicting month t. Missing months are never forward-filled.

    Source IDs are provenance labels, NOT proof of external data certification.
    """
    if rules_version not in RULESETS:
        raise ValueError("Unknown regime rules version")
    rules = RULESETS[rules_version]
    if not market_id.strip() or not source_id.strip():
        raise ValueError("market_id and source_id are required")
    required = {"month", "close", "known_at"}
    if not required.issubset(observations.columns):
        raise ValueError(f"Required columns: {sorted(required)}")
    cutoff = pd.Timestamp(as_of)
    if pd.isna(cutoff) or cutoff.tzinfo is not None or cutoff != cutoff.normalize():
        raise ValueError("as_of must be a timezone-naive calendar date")
    cutoff_end = cutoff + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
    data = observations[list(sorted(required))].copy()
    data["known_at"] = pd.to_datetime(data["known_at"], errors="raise")
    if data["known_at"].isna().any() or data["known_at"].dt.tz is not None:
        raise ValueError("known_at must be nonmissing timezone-naive dates")
    data["month"] = pd.PeriodIndex(data["month"], freq="M")
    if data["month"].isna().any():
        raise ValueError("month is missing")
    if (data["known_at"].dt.to_period("M") < data["month"]).any():
        raise ValueError("known_at precedes the observation month")
    # Exclude future observations before computing statistics or fingerprints.
    data = data[
        (data["known_at"] <= cutoff_end)
        & (data["month"].dt.end_time <= cutoff_end)
    ].copy()
    if data.empty:
        raise ValueError("No completed, available monthly observations")
    if data["month"].duplicated().any():
        raise ValueError("Duplicate month: revisions require explicit PIT resolution")
    data["close"] = pd.to_numeric(data["close"], errors="raise")
    if (~np.isfinite(data["close"]) | (data["close"] <= 0)).any():
        raise ValueError("Index closes must be finite and positive")
    data = data.sort_values("month").set_index("month")
    final_month = cutoff.to_period("M")
    if final_month.end_time > cutoff_end:
        final_month -= 1
    data = data.reindex(pd.period_range(data.index.min(), final_month, freq="M"))
    # A late arrival must never backfill an earlier decision's input history.
    rows = []
    for month in data.index:
        history = data.loc[:month].copy()
        available = history["known_at"] <= month.end_time
        history.loc[~available, "close"] = np.nan
        close = history["close"]
        trend_window = rules["trend_months"]
        vol_window = rules["vol_return_months"]
        sma = close.rolling(trend_window, min_periods=trend_window).mean().iloc[-1]
        returns = close.pct_change(fill_method=None)
        vols = returns.rolling(vol_window, min_periods=vol_window).std(
            ddof=rules["vol_ddof"]
        ) * np.sqrt(rules["annualization"])
        prior = vols.iloc[:-1].dropna()
        threshold = prior.median() if len(prior) >= rules["min_prior_vol_months"] else np.nan
        value, vol = close.iloc[-1], vols.iloc[-1]
        trend = "UNKNOWN" if pd.isna(sma) else ("UP" if value >= sma else "DOWN")
        risk = "UNKNOWN" if pd.isna(vol) or pd.isna(threshold) else (
            "HIGH" if vol > threshold else "LOW"
        )
        reasons = []
        if pd.isna(value):
            reasons.append("MISSING_OR_LATE_MONTH")
        if pd.isna(sma):
            reasons.append("INSUFFICIENT_TREND_HISTORY")
        if pd.isna(vol):
            reasons.append("INSUFFICIENT_VOL_HISTORY")
        if pd.isna(threshold):
            reasons.append("INSUFFICIENT_PRIOR_VOL_HISTORY")
        evidence = json.dumps({
            "market_id": market_id, "source_id": source_id,
            "observations": [
                [str(index), float(row.close), row.known_at.isoformat()]
                for index, row in history.loc[available].iterrows()
            ],
        }, sort_keys=True, allow_nan=False)
        row = {
            "month": str(month), "effective_month": str(month + 1),
            "decision_date": str(month.end_time.date()),
            "market_id": market_id, "source_id": source_id,
            "close": value, "sma_10m": sma, "vol_12m_annualized": vol,
            "prior_vol_median": threshold, "prior_vol_n": len(prior),
            "trend": trend, "volatility": risk,
            "regime": f"{trend}_{risk}" if not reasons else "UNKNOWN",
            "status": "READY" if not reasons else "INSUFFICIENT_DATA",
            "reason": ";".join(reasons),
            "rules_version": rules_version, "rules_sha256": RULE_HASHES[rules_version],
            "input_sha256": hashlib.sha256(evidence.encode()).hexdigest(),
            "purpose": "DIAGNOSTIC_ONLY",
        }
        if rules_version == RULES["version"]:
            # Require all intermediate calendar months, not just endpoints.
            short_n = rules["short_trend_months"]
            short_close = close.iloc[-(short_n + 1):]
            short_return = (short_close.iloc[-1] / short_close.iloc[0] - 1
                            if len(short_close) == short_n + 1 and short_close.notna().all() else np.nan)
            short_trend = "UNKNOWN" if pd.isna(short_return) else ("UP" if short_return >= 0 else "DOWN")
            short_vols = returns.rolling(rules["short_vol_return_months"], min_periods=rules["short_vol_return_months"]).std(
                ddof=rules["vol_ddof"]
            ) * np.sqrt(rules["annualization"])
            short_prior = short_vols.iloc[:-1].dropna()
            short_threshold = (short_prior.median() if len(short_prior) >= rules["min_prior_vol_months"] else np.nan)
            short_vol = short_vols.iloc[-1]
            short_risk = "UNKNOWN" if pd.isna(short_vol) or pd.isna(short_threshold) else (
                "HIGH" if short_vol > short_threshold else "LOW")
            short_reasons = []
            if pd.isna(short_return):
                short_reasons.append("INSUFFICIENT_SHORT_TREND_HISTORY")
            if pd.isna(short_vol):
                short_reasons.append("INSUFFICIENT_SHORT_VOL_HISTORY")
            if pd.isna(short_threshold):
                short_reasons.append("INSUFFICIENT_PRIOR_SHORT_VOL_HISTORY")
            row.update({
                "return_3m": short_return, "vol_3m_annualized": short_vol,
                "prior_short_vol_median": short_threshold, "prior_short_vol_n": len(short_prior),
                "trend_long": trend, "trend_short": short_trend,
                "volatility_long": risk, "volatility_short": short_risk,
                "trend_phase": TREND_PHASES.get((trend, short_trend), "UNKNOWN"),
                "volatility_phase": VOLATILITY_PHASES.get((risk, short_risk), "UNKNOWN"),
                "regime_detail": detailed_regime(trend, short_trend, risk, short_risk),
                "detail_status": "READY" if not reasons + short_reasons else "INSUFFICIENT_DATA",
                "detail_reason": ";".join(reasons + short_reasons),
            })
        rows.append(row)
    return pd.DataFrame(rows)
