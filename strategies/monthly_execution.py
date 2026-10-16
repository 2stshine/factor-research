"""Pure monthly opening-price execution model; no data access or research gates.

The caller authenticates the supplied evidence and data digest. This module
checks their declared contract and temporal/numerical consistency, not source
authenticity or actual fills. Returns must be externally validated gross total
return wealth multipliers from entry open to next rebalance open. They are never
inferred from a raw-open/adjusted-close ratio.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Mapping

import numpy as np
import pandas as pd


EVIDENCE_SCHEMA = "monthly-execution-evidence-v1"
RESULT_SCHEMA = "monthly-execution-result-v1"
VARIANTS = (
    ("q20_equal", 0.20, "equal"),
    ("q10_equal", 0.10, "equal"),
    ("q20_sqrt_cap", 0.20, "sqrt_cap"),
    ("q10_sqrt_cap", 0.10, "sqrt_cap"),
)
EVIDENCE_FLAGS = (
    "calendar_verified", "asset_open_prices_verified",
    "total_return_multipliers_verified", "market_total_return_verified",
    "pit_inputs_verified",
)


@dataclass(frozen=True)
class ExecutionCosts:
    """Explicit proportional rates (fractions, not bps); tax applies to sales.

    buy_rate/sell_rate include the caller's commission/slippage assumptions.
    Tax has no guessed/default year and uses the actual entry session's year.
    """

    buy_rate: float
    sell_rate: float
    sell_tax_by_year: Mapping[int, float]


def _finite(value, label, *, lower=0.0, upper=None):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{label}: numeric value required")
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label}: finite numeric value required") from exc
    if not math.isfinite(number) or number < lower or (upper is not None and number >= upper):
        raise ValueError(f"{label}: value outside allowed range")
    return number


def _stamp(value, label):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tzinfo is None:
        raise ValueError(f"{label}: timezone-aware timestamp required")
    return stamp.tz_convert("Asia/Seoul")


def _month(value):
    if isinstance(value, pd.Period) and value.freqstr == "M":
        return value
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ValueError("Months must be YYYY-MM or monthly Period values")
    return pd.Period(value, freq="M")


def _frame(frame, columns, keys, label):
    if not isinstance(frame, pd.DataFrame) or not frame.columns.is_unique:
        raise ValueError(f"{label}: unique DataFrame columns required")
    if not set(columns).issubset(frame.columns):
        raise ValueError(f"{label}: required columns {columns}")
    out = frame.loc[:, columns].copy(deep=True)
    month_col = "session_month" if "session_month" in columns else "signal_month"
    out[month_col] = out[month_col].map(_month)
    if "asset_id" in columns:
        values = out["asset_id"]
        if values.map(lambda x: isinstance(x, (bool, np.bool_))).any():
            raise ValueError(f"{label}: integer asset_id required")
        numeric = pd.to_numeric(values, errors="raise")
        if numeric.isna().any() or not np.isfinite(numeric).all() or (numeric <= 0).any() or (numeric % 1 != 0).any():
            raise ValueError(f"{label}: positive integer asset_id required")
        out["asset_id"] = numeric.astype("int64")
    if out.duplicated(keys).any():
        raise ValueError(f"{label}: duplicate keys")
    return out


def _validate(scores, sessions, asset_windows, market_windows, evidence, costs):
    if not isinstance(evidence, Mapping):
        raise ValueError("Explicit execution evidence mapping required")
    if evidence.get("schema_version") != EVIDENCE_SCHEMA:
        raise ValueError("Unsupported execution evidence schema")
    if not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("data_sha256", ""))):
        raise ValueError("Execution evidence requires data_sha256")
    if any(evidence.get(flag) is not True for flag in EVIDENCE_FLAGS):
        raise ValueError("Externally verified execution evidence required")
    as_of = _stamp(evidence.get("as_of"), "evidence.as_of")
    if not isinstance(costs, ExecutionCosts):
        raise ValueError("Explicit ExecutionCosts required")
    buy_rate = _finite(costs.buy_rate, "buy_rate", upper=1)
    sell_rate = _finite(costs.sell_rate, "sell_rate", upper=1)
    if not isinstance(costs.sell_tax_by_year, Mapping):
        raise ValueError("sell_tax_by_year mapping required")

    scores = _frame(scores, ["signal_month", "asset_id", "signed_score", "eligible", "market_cap", "available_at"],
                    ["signal_month", "asset_id"], "scores")
    sessions = _frame(sessions, ["session_month", "open_at"], ["session_month"], "sessions")
    assets = _frame(asset_windows, ["signal_month", "asset_id", "entry_at", "exit_at", "entry_open",
                                   "gross_total_return_multiplier", "return_available_at"],
                    ["signal_month", "asset_id"], "asset_windows")
    market = _frame(market_windows, ["signal_month", "entry_at", "exit_at",
                                    "gross_total_return_multiplier", "return_available_at"],
                    ["signal_month"], "market_windows")
    if scores.empty:
        raise ValueError("No signal months supplied")
    months = sorted(scores.signal_month.unique())
    if months != list(pd.period_range(months[0], months[-1], freq="M")):
        raise ValueError("Signal months must be consecutive; no silent skipped periods")
    if set(market.signal_month) != set(months) or not set(assets.signal_month).issubset(months):
        raise ValueError("Asset/market windows must match the signal months")
    if not scores.eligible.map(lambda x: isinstance(x, (bool, np.bool_))).all():
        raise ValueError("eligible must contain explicit booleans")
    scores["signed_score"] = pd.to_numeric(scores.signed_score, errors="raise")
    if np.isinf(scores.signed_score).any():
        raise ValueError("signed_score may be missing but cannot be infinite")
    scores["available_at"] = scores.available_at.map(lambda x: _stamp(x, "available_at"))
    sessions["open_at"] = sessions.open_at.map(lambda x: _stamp(x, "open_at"))
    for row in sessions.itertuples(index=False):
        if row.open_at.tz_localize(None).to_period("M") != row.session_month:
            raise ValueError("Session open must belong to its declared calendar month")
    calendar = sessions.set_index("session_month").open_at.to_dict()
    for frame in (assets, market):
        for field in ("entry_at", "exit_at", "return_available_at"):
            frame[field] = frame[field].map(lambda x: _stamp(x, field))
        frame["gross_total_return_multiplier"] = frame.gross_total_return_multiplier.map(
            lambda x: _finite(x, "gross_total_return_multiplier"))
        for row in frame.itertuples(index=False):
            if row.entry_at != calendar.get(row.signal_month + 1) or row.exit_at != calendar.get(row.signal_month + 2):
                raise ValueError("Return window must use verified next-month and following-month session opens")
            if row.exit_at <= row.entry_at:
                raise ValueError("Return window exit must follow entry")
            if row.return_available_at < row.exit_at or row.return_available_at > as_of:
                raise ValueError("Return availability must be at/after exit and no later than evidence.as_of")
    assets["entry_open"] = assets.entry_open.map(lambda x: _finite(x, "entry_open"))
    if (assets.entry_open <= 0).any():
        raise ValueError("entry_open must be positive")
    assets = assets.set_index(["signal_month", "asset_id"])
    market = market.set_index("signal_month")
    blocks, tax_rates = {}, {}
    for month in months:
        decision = month.end_time.floor("s").tz_localize("Asia/Seoul")
        if month + 1 not in calendar or month + 2 not in calendar:
            raise ValueError("Missing verified first session open")
        if calendar[month + 1] <= decision:
            raise ValueError("Execution must follow the month-end decision")
        block = scores.loc[scores.signal_month == month].copy()
        if (block.available_at > decision).any():
            raise ValueError("Input availability exceeds month-end decision cutoff")
        block = block.loc[block.eligible].copy()
        if block.empty:
            raise ValueError("Every month requires an eligible universe")
        block["market_cap"] = block.market_cap.map(lambda x: _finite(x, "market_cap"))
        if (block.market_cap <= 0).any():
            raise ValueError("Eligible market_cap must be positive")
        required = {(month, int(asset)) for asset in block.asset_id}
        if not required.issubset(assets.index):
            raise ValueError("Missing eligible asset holding return/open; cannot change the common sample")
        if block.signed_score.notna().sum() < max(1, math.floor(len(block) * .20)):
            raise ValueError("Insufficient available scores for fixed top-20% selection")
        year = calendar[month + 1].year
        if year not in costs.sell_tax_by_year:
            raise ValueError(f"Missing explicit sell tax for execution year {year}")
        tax = _finite(costs.sell_tax_by_year[year], "sell_tax", upper=1)
        if sell_rate + tax >= 1:
            raise ValueError("Combined sell costs must be below one")
        tax_rates[month] = tax
        blocks[month] = block.sort_values(["signed_score", "asset_id"], ascending=[False, True], kind="mergesort")
    return months, blocks, calendar, assets, market, buy_rate, sell_rate, tax_rates


def _post_cost_nav(nav, old_values, weights, buy_rate, sell_rate):
    """Solve the fully invested budget including costs on actual traded notional."""
    keys = sorted(set(old_values) | set(weights))

    def required(value):
        changes = [weights.get(asset, 0.0) * value - old_values.get(asset, 0.0) for asset in keys]
        return value + buy_rate * sum(max(change, 0.0) for change in changes) + sell_rate * sum(max(-change, 0.0) for change in changes)

    low, high = 0.0, nav
    for _ in range(100):
        middle = low + (high - low) / 2
        if required(middle) > nav:
            high = middle
        else:
            low = middle
    return low + (high - low) / 2


def run_monthly_execution(scores: pd.DataFrame, sessions: pd.DataFrame,
                          asset_windows: pd.DataFrame, market_windows: pd.DataFrame,
                          *, evidence: Mapping, costs: ExecutionCosts,
                          initial_nav: float = 1.0) -> dict:
    """Run all four fixed variants on identical eligible months and benchmarks.

    Score rows are keyed by signal_month/asset_id; available_at must represent
    the latest availability of score, eligibility and market cap. A missing
    score cannot be selected but remains in the eligible denominator/benchmark.
    Session rows are the externally verified first regular session of each
    session_month, including special opening times. Asset windows include all
    eligible assets AND any prior holdings needing sale at that month's open.
    Even exiting assets need a complete validated row under this strict API.

    Scores are already signed; this model neither changes signs nor picks a
    winning variant. k=max(1,floor(eligible_count*quantile)), not gate's min-10.
    Fractional reinvested wealth positions are used. No integer-lot, order book,
    capacity, actual-fill, or final liquidation model is implied.
    """
    initial_nav = _finite(initial_nav, "initial_nav")
    if initial_nav <= 0:
        raise ValueError("initial_nav must be positive")
    months, blocks, calendar, assets, market, buy_rate, sell_rate, taxes = _validate(
        scores, sessions, asset_windows, market_windows, evidence, costs)
    output = {}
    for name, quantile, weighting in VARIANTS:
        nav, old_values = initial_nav, {}
        monthly, trades, positions = [], [], []
        universe_nav = market_nav = initial_nav
        for month in months:
            if nav <= 0:
                raise ValueError("Portfolio exhausted; cannot silently skip or restart")
            block = blocks[month]
            k = max(1, math.floor(len(block) * quantile))
            selected = block.loc[block.signed_score.notna()].head(k)
            raw = np.ones(k) if weighting == "equal" else np.sqrt(selected.market_cap.to_numpy(dtype=float))
            # Scaling before summation avoids overflow for large capitalizations.
            raw = raw / raw.max()
            weights = {int(asset): float(weight) for asset, weight in zip(selected.asset_id, raw / raw.sum())}
            keys = sorted(set(old_values) | set(weights))
            for asset in keys:
                if (month, asset) not in assets.index:
                    raise ValueError("Missing prior-held asset execution/return evidence; cannot silently liquidate")
            investable_nav = _post_cost_nav(nav, old_values, weights, buy_rate, sell_rate + taxes[month])
            if not math.isfinite(investable_nav) or investable_nav <= 0:
                raise ValueError("Invalid post-cost portfolio value")
            buys = sells = buy_cost = sell_cost = sell_tax = 0.0
            new_values = {}
            for asset in keys:
                before = old_values.get(asset, 0.0)
                after = weights.get(asset, 0.0) * investable_nav
                change = after - before
                bought, sold = max(change, 0.0), max(-change, 0.0)
                bc, sc, tax = bought * buy_rate, sold * sell_rate, sold * taxes[month]
                buys += bought
                sells += sold
                buy_cost += bc
                sell_cost += sc
                sell_tax += tax
                trades.append(dict(signal_month=month, asset_id=asset, entry_at=calendar[month + 1],
                                   entry_open=float(assets.loc[(month, asset), "entry_open"]),
                                   value_before=before, target_weight=weights.get(asset, 0.0), value_after=after,
                                   buy_notional=bought, sell_notional=sold, buy_cost=bc, sell_cost=sc, sell_tax=tax))
                if asset in weights:
                    multiplier = float(assets.loc[(month, asset), "gross_total_return_multiplier"])
                    new_values[asset] = after * multiplier
                    if not math.isfinite(new_values[asset]):
                        raise ValueError("Non-finite holding wealth after return application")
            total_cost = buy_cost + sell_cost + sell_tax
            if not math.isclose(investable_nav + total_cost, nav, rel_tol=1e-12, abs_tol=1e-14):
                raise ValueError("Self-financing budget did not balance")
            try:
                end_nav = math.fsum(new_values.values())
            except OverflowError as exc:
                raise ValueError("Non-finite portfolio wealth") from exc
            gross_return = end_nav / investable_nav - 1.0
            net_return = end_nav / nav - 1.0
            universe_return = math.fsum(float(assets.loc[(month, int(asset)), "gross_total_return_multiplier"]) / len(block)
                                       for asset in block.asset_id) - 1.0
            market_return = float(market.loc[month, "gross_total_return_multiplier"]) - 1.0
            universe_nav *= 1 + universe_return
            market_nav *= 1 + market_return
            if not all(math.isfinite(value) for value in (end_nav, gross_return, net_return, universe_nav, market_nav)):
                raise ValueError("Non-finite portfolio or benchmark result")
            for asset, value in new_values.items():
                positions.append(dict(signal_month=month, asset_id=asset, target_weight=weights[asset],
                                      value_after_cost=weights[asset] * investable_nav, value_at_exit=value,
                                      end_weight=value / end_nav if end_nav > 0 else np.nan,
                                      gross_total_return_multiplier=float(assets.loc[(month, asset), "gross_total_return_multiplier"])))
            monthly.append(dict(signal_month=month, decision_at=month.end_time.floor("s").tz_localize("Asia/Seoul"),
                                entry_at=calendar[month + 1], exit_at=calendar[month + 2],
                                n_eligible=len(block), n_signal_available=int(block.signed_score.notna().sum()),
                                n_selected=k, score_coverage=float(block.signed_score.notna().mean()),
                                nav_before_rebalance=nav, nav_after_cost=investable_nav, nav_exit=end_nav,
                                gross_return=gross_return, net_return=net_return, cost_fraction=total_cost / nav,
                                cost_drag_return=gross_return - net_return,
                                buy_notional=buys, sell_notional=sells, buy_cost=buy_cost, sell_cost=sell_cost, sell_tax=sell_tax,
                                turnover_buy=buys / nav, turnover_sell=sells / nav,
                                universe_ew_return=universe_return, market_total_return=market_return,
                                net_excess_universe=net_return - universe_return, net_excess_market=net_return - market_return,
                                universe_ew_nav=universe_nav, market_nav=market_nav))
            nav, old_values = end_nav, {asset: value for asset, value in new_values.items() if value > 0}
        output[name] = dict(quantile=quantile, weighting=weighting, monthly=pd.DataFrame(monthly),
                            trades=pd.DataFrame(trades), positions=pd.DataFrame(positions))
    return dict(schema_version=RESULT_SCHEMA, variant_order=[name for name, _, _ in VARIANTS],
                variants=output, evidence=dict(evidence), initial_nav=initial_nav,
                actual_fill_verified=False, orders_submitted=False, final_liquidation_included=False,
                assumptions=[
                    "Caller authenticates supplied evidence and data_sha256; engine checks declared consistency only.",
                    "Verified first regular-session opens, not guessed weekdays or a fixed 09:00 time.",
                    "Externally validated open-to-open gross total-return multipliers; no raw/adjusted-price ratio inference.",
                    "Fractional reinvested-wealth holdings; no integer-lot, order-book or capacity model; supplied costs are assumptions.",
                    "All four prespecified variants use identical months and eligible-universe/market gross benchmarks; no winner selection.",
                    "Top fraction uses max(1,floor(eligible_count*quantile)); missing scores remain in benchmark and denominator.",
                    "Final positions are marked at the final exit open without forced liquidation costs.",
                ])
