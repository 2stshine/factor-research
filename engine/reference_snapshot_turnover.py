"""Self-financing turnover accounting for frozen monthly target weights.

No refit or return-dependent target changes. Rates are explicit scenarios, not
verified commissions/taxes. Missing prices remain two hypothetical value paths.
"""
import math

import numpy as np
import pandas as pd

from strategies.monthly_execution import _post_cost_nav, VARIANTS
from engine.reference_snapshot_strategy import MODELS

ASSUMPTIONS = ("MISSING_FLAT_ASSUMPTION", "MISSING_TOTAL_LOSS_ASSUMPTION")


def rebalance(nav, old_values, weights, *, buy_rate, sell_rate):
    if not math.isfinite(nav) or nav <= 0:
        raise ValueError("Positive finite NAV required; no restart after exhaustion")
    if any(not math.isfinite(v) or v < 0 for v in old_values.values()):
        raise ValueError("Invalid prior holdings")
    if old_values and not math.isclose(sum(old_values.values()), nav, rel_tol=1e-11, abs_tol=1e-13):
        raise ValueError("Prior holdings do not reconcile with NAV")
    if not weights or any(not math.isfinite(w) or w <= 0 for w in weights.values()) or not math.isclose(sum(weights.values()), 1., abs_tol=1e-12):
        raise ValueError("Positive normalized target weights required")
    if any(not math.isfinite(r) or not 0 <= r < 1 for r in (buy_rate, sell_rate)):
        raise ValueError("Invalid per-side cost rate")
    invested = _post_cost_nav(nav, old_values, weights, buy_rate, sell_rate)
    keys = sorted(set(old_values) | set(weights))
    target_values = {asset: invested * weight for asset, weight in weights.items()}
    changes = [target_values.get(asset, 0.) - old_values.get(asset, 0.) for asset in keys]
    buys = math.fsum(max(change, 0.) for change in changes)
    sells = math.fsum(max(-change, 0.) for change in changes)
    cost = buys * buy_rate + sells * sell_rate
    if not math.isclose(invested + cost, nav, rel_tol=1e-11, abs_tol=1e-13):
        raise ValueError("Self-financing budget does not balance")
    return target_values, {"nav_before": nav, "nav_after_cost": invested,
                           "buy_notional": buys, "sell_notional": sells,
                           "buy_cost": buys * buy_rate, "sell_cost": sells * sell_rate,
                           "cost": cost, "cost_fraction": cost / nav,
                           "turnover_buy": buys / nav, "turnover_sell": sells / nav,
                           "one_way_turnover": (buys + sells) / (2 * nav)}


def metrics(rows):
    net = np.array([r["net_return"] for r in rows])
    gross = np.array([r["gross_return"] for r in rows])
    wealth = np.r_[1., np.cumprod(1 + net)]
    return {"months": len(rows), "annualized_net_return": float(wealth[-1] ** (12 / len(rows)) - 1),
            "annualized_gross_return": float(np.prod(1 + gross) ** (12 / len(rows)) - 1),
            "cumulative_net_return": float(wealth[-1] - 1),
            "maximum_drawdown": float(np.min(wealth / np.maximum.accumulate(wealth) - 1)),
            "mean_monthly_cost_fraction": float(np.mean([r["cost_fraction"] for r in rows])),
            "mean_monthly_one_way_turnover_ex_initial": float(np.mean([r["one_way_turnover"] for r in rows[1:]])) if len(rows) > 1 else None,
            "months_with_missing_outcomes": sum(bool(r["missing_outcome_assets"]) for r in rows),
            "max_missing_outcome_weight": max(r["missing_outcome_weight"] for r in rows),
            "observed_complete_path": not any(r["missing_outcome_assets"] for r in rows)}


def replay_path(targets, lookup, *, assumption, buy_bps, sell_bps, rates_by_month=None):
    if assumption not in ASSUMPTIONS or not targets:
        raise ValueError("Explicit assumption and nonempty targets required")
    months = [m for m, _ in targets]
    if months != [str(p) for p in pd.period_range(months[0], months[-1], freq="M")]:
        raise ValueError("Consecutive ordered target months required")
    if rates_by_month is not None and set(rates_by_month) != set(months):
        raise ValueError("Dated rates must cover every target month exactly")
    nav, old_values, unpriced, rows = 1., {}, set(), []
    for month, weights in targets:
        buy, sell = (buy_bps, sell_bps) if rates_by_month is None else rates_by_month[month]
        new_values, accounting = rebalance(nav, old_values, weights, buy_rate=buy / 10000, sell_rate=sell / 10000)
        missing, returns = [], {}
        for asset in weights:
            value = lookup.get((month, asset), float("nan"))
            if pd.isna(value):
                missing.append(asset)
                value = 0. if assumption == ASSUMPTIONS[0] else -1.
            if not math.isfinite(value) or value < -1:
                raise ValueError("Invalid outcome multiplier")
            returns[asset] = float(value)
        end_values = {asset: value * (1 + returns[asset]) for asset, value in new_values.items()}
        end_nav = math.fsum(end_values.values())
        gross = math.fsum(weights[a] * returns[a] for a in weights)
        rows.append({"signal_month": month, **accounting, "nav_exit": end_nav,
                     "gross_return": gross, "net_return": end_nav / nav - 1,
                     "missing_outcome_assets": missing, "missing_outcome_weight": sum(weights[a] for a in missing),
                     "assumed_prior_valuation_assets_at_trade": sorted(unpriced), "target_count": len(weights)})
        unpriced = ((unpriced & set(weights)) | set(missing)) & {a for a, v in end_values.items() if v > 0}
        nav, old_values = end_nav, {a: v for a, v in end_values.items() if v > 0}
    return {"summary": metrics(rows), "monthly": rows, "final_liquidation_included": False}


def evaluate(panel, folds, *, buy_bps=25., sell_bps=25., rates_by_month=None):
    if not folds:
        raise ValueError("No frozen target folds")
    if panel.duplicated(["month", "asset_id"]).any():
        raise ValueError("Duplicate panel asset-month keys")
    lookup = panel.set_index(["month", "asset_id"]).outcome.to_dict()
    paths = {}
    for model in MODELS:
        for variant, _, _ in VARIANTS:
            targets = []
            for fold in folds:
                portfolio = next((p for p in fold["models"][model]["portfolios"] if p["portfolio"] == variant), None)
                if portfolio is None:
                    break
                assets, weights = portfolio["selected_assets"], portfolio["weights"]
                if len(assets) != len(weights) or len(set(assets)) != len(assets):
                    raise ValueError("Target asset/weight identity mismatch")
                targets.append((fold["signal_month"], dict(zip(assets, weights))))
            key = model + "/" + variant
            paths[key] = {"status": "INCOMPLETE_MODEL_MONTHS"} if len(targets) != len(folds) else {
                "status": "EXPLORATORY_SCENARIOS", "scenarios": {a: replay_path(targets, lookup, assumption=a, buy_bps=buy_bps, sell_bps=sell_bps, rates_by_month=rates_by_month) for a in ASSUMPTIONS}}
    baseline = []
    for fold in folds:
        block = panel.loc[panel.month.eq(fold["signal_month"]) & panel.eligible]
        baseline.append((fold["signal_month"], {int(a): 1 / len(block) for a in block.asset_id}))
    return {"schema": "reference-snapshot-turnover-v1", "buy_bps": buy_bps, "sell_bps": sell_bps,
            "cost_basis": "ACTUAL_SIMULATED_TRADE_NOTIONAL_WITH_PRETRADE_WEIGHT_DRIFT",
            "rates_are_assumptions_not_verified_fees_or_taxes": True,
            "paths": paths, "baseline": {a: replay_path(baseline, lookup, assumption=a, buy_bps=buy_bps, sell_bps=sell_bps, rates_by_month=rates_by_month) for a in ASSUMPTIONS},
            "rates_by_month": rates_by_month,
            "source_refreshed": False, "targets_changed": False, "model_refitted": False,
            "actual_fills_verified": False, "final_liquidation_included": False,
            "limitations": ["Monthly adjusted-close prices, not dividends/TR or next-open fills.",
                            "Missing-return paths and disposal valuations are hypothetical; no evidence of executable trades for unpriced securities.",
                            "Costs apply to each modeled buy/sell notional; constant rates are not an audited tax/impact schedule.",
                            "No fresh independent OOS or automatic strategy approval."]}
