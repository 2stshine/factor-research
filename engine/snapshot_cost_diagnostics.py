"""Descriptive cost and market/size diagnostics, not causal or OOS approval."""
from pathlib import Path
import math

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from engine.reference_snapshot_strategy import file_hash
from scripts.report_reference_snapshot import metrics

SIZE_NAMES = ("LARGE_GE_1TR_KRW", "MID_300BN_TO_1TR_KRW", "SMALL_LT_300BN_KRW")
SECTORS = ("음식료·담배", "섬유·의류", "종이·목재", "화학", "제약", "비금속", "금속", "기계·장비",
           "전기전자", "의료·정밀기기", "운송장비·부품", "유통", "전기·가스", "건설", "운송·창고",
           "통신", "금융", "증권", "보험", "일반서비스", "오락·문화", "IT 서비스", "부동산")


def tax_bps(trade_date, config):
    dates = [r["from_trade_date"] for r in config["tax_schedule"]]
    if dates != sorted(set(dates)):
        raise ValueError("Unique sorted tax intervals required")
    day = pd.Timestamp(trade_date).strftime("%Y-%m-%d")
    if day < dates[0] or day > config["tax_valid_through"]:
        raise ValueError("Trade date outside researched tax coverage")
    return next(r["total_sell_tax_bps"] for r in reversed(config["tax_schedule"]) if r["from_trade_date"] <= day)


def collect_benchmarks(root, months):
    """Read only retained local KRX month-end files. No network or backfill."""
    periods = [str(p) for p in pd.period_range(months[0], str(pd.Period(months[-1], freq="M") + 1), freq="M")]
    values, files, sessions = {}, [], {}
    for month in periods:
        for market, name in (("KOSPI", "코스피"), ("KOSDAQ", "코스닥")):
            paths = sorted(Path(root).glob(f"date={month}-*/{market.lower()}.parquet"))
            if not paths:
                raise ValueError("Missing index month " + month)
            path = paths[-1]
            day = path.parent.name.removeprefix("date=")
            if (pd.Period(month).end_time.normalize() - pd.Timestamp(day)).days > 7:
                raise ValueError("Index month may be incomplete")
            if month in sessions and sessions[month] != day:
                raise ValueError("Markets have different last sessions")
            sessions[month] = day
            before = file_hash(path)
            frame = pq.ParquetFile(path).read().to_pandas()
            if before != file_hash(path) or not frame.BAS_DD.astype(str).eq(day.replace("-", "")).all():
                raise ValueError("Index source date/hash mismatch")
            if frame.IDX_NM.duplicated().any():
                raise ValueError("Duplicate index names")
            series = pd.to_numeric(frame.set_index("IDX_NM").CLSPRC_IDX.str.replace(",", ""), errors="coerce")
            if name not in series or not math.isfinite(series[name]) or series[name] <= 0:
                raise ValueError("Missing positive official index close")
            selected = [name] + (list(SECTORS) + ["코스피 대형주", "코스피 중형주", "코스피 소형주"] if market == "KOSPI" else [])
            values.setdefault(month, {}).update({n: float(series[n]) for n in selected if n in series and pd.notna(series[n]) and series[n] > 0})
            files.append({"path": str(path.resolve()), "sha256": before, "market": market, "date": day})
    returns = {}
    for month in months:
        nxt = str(pd.Period(month) + 1)
        returns[month] = {m: values[nxt][n] / values[month][n] - 1 for m, n in (("KOSPI", "코스피"), ("KOSDAQ", "코스닥"))}
    context = []
    for label, first, last in (("FULL", periods[0], periods[-1]), ("2025", "2024-12", "2025-12"), ("2026_YTD", "2025-12", "2026-09")):
        if first not in values or last not in values:
            continue
        for name in list(SECTORS) + ["코스피 대형주", "코스피 중형주", "코스피 소형주", "코스피", "코스닥"]:
            if name in values[first] and name in values[last]:
                context.append({"period": label, "index_name": name, "first_date": sessions[first], "last_date": sessions[last],
                                "return": values[last][name] / values[first][name] - 1})
    return {"sessions": sessions, "prices": values, "returns": returns, "source_files": files, "industry_and_size_index_context": context,
            "source_scope": "Retained KRX index files; current provider historical labels, not vintage-certified index memberships",
            "benchmark_costs": "NONE_PRICE_INDEX_NOT_AN_INVESTABLE_ETF", "dividends": "NOT_INCLUDED"}


def components(path, config, slippage, sessions):
    """Expose fee/tax/slippage separately; preserve exact self-financing costs."""
    for row in path["monthly"]:
        date = sessions[row["signal_month"]]
        tax = tax_bps(date, config)
        volume = row["buy_notional"] + row["sell_notional"]
        row.update(trade_date=date, commission_bps=config["commission_bps_each_side"], sell_tax_bps=tax, slippage_bps_each_side=slippage,
                   commission_cost=volume * config["commission_bps_each_side"] / 10000,
                   tax_cost=row["sell_notional"] * tax / 10000, slippage_cost=volume * slippage / 10000)
        if not math.isclose(sum(row[k] for k in ("commission_cost", "tax_cost", "slippage_cost")), row["cost"], rel_tol=1e-11, abs_tol=1e-13):
            raise ValueError("Cost components do not reconcile")
    for key in ("commission", "tax", "slippage"):
        path["summary"]["mean_monthly_" + key + "_fraction"] = float(np.mean([r[key + "_cost"] / r["nav_before"] for r in path["monthly"]]))


def size_labels(caps):
    return np.where(caps >= 1e12, SIZE_NAMES[0], np.where(caps >= 3e11, SIZE_NAMES[1], SIZE_NAMES[2]))


def link_effects(rows):
    """Exact terminal wealth difference, not a sum of annualized returns.

    X_T-Y_T = sum_t X_(t-1)*(rP_t-rB_t)*prod_(u>t)(1+rB_u).
    """
    net = np.array([r["net_return"] for r in rows])
    benchmark = np.array([r["benchmark_return"] for r in rows])
    prior = np.r_[1., np.cumprod(1 + net)[:-1]]
    future = np.r_[np.cumprod((1 + benchmark)[::-1])[::-1][1:], 1.]
    weights = prior * future
    names = list(rows[0]["effects"])
    linked = {n: float(sum(w * r["effects"][n] for w, r in zip(weights, rows))) for n in names}
    gap = float(np.prod(1 + net) - np.prod(1 + benchmark))
    if not math.isclose(sum(linked.values()), gap, abs_tol=1e-10, rel_tol=1e-10):
        raise ValueError("Linked effects do not reconcile with wealth gap")
    return {"months": len(rows), "terminal_wealth_gap": gap, "linked_effects": linked,
            "mean_monthly_effects": {n: float(np.mean([r["effects"][n] for r in rows])) for n in names},
            "strategy": metrics(net), "kospi": metrics(benchmark)}


def attribute(panel, folds, key, path, benchmark, assumption):
    """Hierarchical allocation/selection against official market indexes.

    Official -> available panel cap-weight proxy residual is explicit; it is
    never silently attributed to skill or treated as exact KOSPI replication.
    """
    model, variant = key.split("/")
    rows, groups = [], []
    for fold, ledger in zip(folds, path["monthly"]):
        month = fold["signal_month"]
        if ledger["signal_month"] != month:
            raise ValueError("Ledger month differs from targets")
        b = panel.loc[panel.month.eq(month) & panel.eligible, ["asset_id", "market", "market_cap", "outcome"]].set_index("asset_id").copy()
        p = next(p for p in fold["models"][model]["portfolios"] if p["portfolio"] == variant)
        w = pd.Series(p["weights"], index=p["selected_assets"])
        if not w.index.isin(b.index).all():
            raise ValueError("Selected assets outside attributed universe")
        b["weight"] = w.reindex(b.index, fill_value=0.)
        b["size"] = size_labels(b.market_cap)
        b["r"] = b.outcome.fillna(0. if assumption == "MISSING_FLAT_ASSUMPTION" else -1.)
        kospi = benchmark[month]["KOSPI"]
        effects = {"market_allocation": 0., "index_proxy_residual": 0., "size_allocation_within_market": 0., "stock_selection_within_market_size": 0.}
        for market, market_block in b.groupby("market"):
            wm = float(market_block.weight.sum())
            total_cap = float(market_block.market_cap.sum())
            rb = float((market_block.market_cap * market_block.r).sum() / total_cap)
            rm = benchmark[month][market]
            effects["market_allocation"] += wm * (rm - kospi)
            effects["index_proxy_residual"] += wm * (rb - rm)
            for size, cell in market_block.groupby("size"):
                wp = float(cell.weight.sum())
                wb = float(cell.market_cap.sum() / total_cap)
                rg = float((cell.market_cap * cell.r).sum() / cell.market_cap.sum())
                contribution = float((cell.weight * cell.r).sum())
                allocation = (wp - wm * wb) * (rg - rb)
                selection = contribution - wp * rg
                effects["size_allocation_within_market"] += allocation
                effects["stock_selection_within_market_size"] += selection
                groups.append({"signal_month": month, "market": market, "size": size, "portfolio_weight": wp,
                               "market_weight": wm, "cap_weight_within_market": wb, "group_price_return": rg,
                               "portfolio_return_contribution": contribution, "size_allocation": allocation, "within_cell_selection": selection,
                               "portfolio_missing_weight": float(cell.loc[cell.outcome.isna(), "weight"].sum()),
                               "proxy_missing_cap_weight_within_market": float(cell.loc[cell.outcome.isna(), "market_cap"].sum() / total_cap)})
        gross = float((b.weight * b.r).sum())
        if not math.isclose(gross, ledger["gross_return"], abs_tol=1e-12):
            raise ValueError("Attribution gross return mismatch")
        for component in ("commission", "tax", "slippage"):
            effects[component + "_drag"] = -ledger[component + "_cost"] / ledger["nav_before"] * (1 + gross)
        if not math.isclose(sum(effects.values()), ledger["net_return"] - kospi, abs_tol=1e-11):
            raise ValueError("Monthly attribution identity failed")
        rows.append({"signal_month": month, "return_month": str(pd.Period(month) + 1),
                     "net_return": ledger["net_return"], "benchmark_return": kospi, "effects": effects})
    periods = {"FULL": rows, "THROUGH_2024": [r for r in rows if r["return_month"] <= "2024-12"],
               "2025_ONWARD": [r for r in rows if r["return_month"] >= "2025-01"]}
    return {"periods": {k: link_effects(v) for k, v in periods.items() if v}, "monthly": rows, "groups": groups,
            "industry_attribution": "NOT_IDENTIFIED_NO_HISTORICAL_ASSET_SECTOR_MEMBERSHIPS",
            "size_definition": "Own thresholds: >=1tr KRW, 300bn-1tr, <300bn; not KRX large/mid/small membership",
            "interpretation": "Descriptive accounting, order-dependent hierarchy. Proxy gap is not selection skill. No causal claims."}
