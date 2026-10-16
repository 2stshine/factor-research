"""Replay immutable monthly targets with traded-notional costs, without refitting."""
import argparse
import math
from html import escape
from pathlib import Path

from engine import reference_snapshot_strategy as snapshot
from engine import reference_snapshot_turnover as turnover
from engine.research_generation import digest, _immutable
from scripts.report_reference_snapshot import MODEL_NAMES, PORTFOLIO_NAMES, metrics


def load_parent(directory, manifest):
    root = Path(directory)
    plan, result = (snapshot.read_json(root / name) for name in ("plan.json", "result.json"))
    if result["plan_sha256"] != digest(plan) or result["snapshot_sha256"] != manifest["snapshot_sha256"] or plan["snapshot_sha256"] != manifest["snapshot_sha256"]:
        raise ValueError("Parent plan/result/snapshot mismatch")
    folds, hashes = [], {}
    for month in plan["signal_months"]:
        path = root / "months" / (month + ".json")
        saved = snapshot.read_json(path)
        if saved["plan_sha256"] != digest(plan) or saved["fold_sha256"] != digest(saved["fold"]) or saved["fold"]["signal_month"] != month:
            raise ValueError("Parent checkpoint identity mismatch")
        folds.append(saved["fold"])
        hashes[month] = snapshot.file_hash(path)
    if snapshot.summarize(folds) != result["summary"]:
        raise ValueError("Parent summary differs from monthly targets")
    return plan, folds, hashes


def compare(folds, evaluated):
    rows = []
    max_error = 0.
    for key, path in evaluated["paths"].items():
        if "scenarios" not in path:
            continue
        model, variant = key.split("/")
        original = [next(p for p in f["models"][model]["portfolios"] if p["portfolio"] == variant) for f in folds]
        for assumption, replay in path["scenarios"].items():
            for portfolio, row in zip(original, replay["monthly"]):
                # Source outcomes and missing choices must remain identical to the stored basket.
                if portfolio["missing_outcome_assets"] != row["missing_outcome_assets"]:
                    raise ValueError("Missing-outcome identity changed")
                if not math.isclose(portfolio["missing_outcome_weight"], row["missing_outcome_weight"], abs_tol=1e-12):
                    raise ValueError("Missing-outcome weight changed")
                if not math.isclose(row["nav_after_cost"] + row["cost"], row["nav_before"], rel_tol=1e-11):
                    raise ValueError("Ledger budget mismatch")
                error = abs(row["net_return"] - ((1 + row["gross_return"]) * (1 - row["cost_fraction"]) - 1))
                max_error = max(max_error, error)
                if error > 1e-11:
                    raise ValueError("Return/cost ledger mismatch")
            rows.append({"model": model, "portfolio": variant, "assumption": assumption,
                         "old_fixed_cost": metrics([p["sensitivity_net_returns_not_observed"][assumption] for p in original]),
                         "turnover_cost": replay["summary"]})
    return rows, max_error


def render(output, plan, result):
    pct = lambda v: f"{100 * v:.2f}%"
    tables = []
    for assumption, label in zip(turnover.ASSUMPTIONS, ("결측 가격 유지(0% 수익) 가정", "결측 전액 손실(-100% 수익) 가정")):
        body = []
        for row in result["comparison"]:
            if row["assumption"] != assumption:
                continue
            new, old = row["turnover_cost"], row["old_fixed_cost"]
            cells = [MODEL_NAMES[row["model"]], PORTFOLIO_NAMES[row["portfolio"]], pct(new["annualized_gross_return"]),
                     pct(old["annualized_return"]), pct(new["annualized_net_return"]), pct(new["mean_monthly_cost_fraction"]),
                     pct(new["mean_monthly_one_way_turnover_ex_initial"] or 0), pct(new["maximum_drawdown"])]
            body.append("<tr>" + "".join("<td>" + escape(cell) + "</td>" for cell in cells) + "</tr>")
        base = result["baseline"][assumption]["summary"]
        tables.append(f"<h2>{label}</h2><table><thead><tr><th>모형</th><th>구성</th><th>비용 전 연율</th><th>기존 연율</th><th>교체비용 후 연율</th><th>평균 월 비용</th><th>평균 월 회전율*</th><th>최대낙폭</th></tr></thead><tbody>{''.join(body)}</tbody></table>"
                      f"<p>전체 대상 동일가중 기준선: 비용 전 연율 {pct(base['annualized_gross_return'])}, 교체비용 후 {pct(base['annualized_net_return'])}, 월평균 비용 {pct(base['mean_monthly_cost_fraction'])}.</p>")
    html = f"""<!doctype html><html lang="ko"><meta charset="utf-8"><title>거래금액 기준 비용 재계산</title>
<style>body{{font:16px/1.7 system-ui;max-width:1400px;margin:32px auto;padding:20px;color:#17212b;background:#f7f9fc}}table{{border-collapse:collapse;width:100%;font-size:14px;background:white}}td,th{{padding:10px;border-bottom:1px solid #dde3eb;text-align:right}}td:first-child,td:nth-child(2){{text-align:left}}th{{background:#e8eef7}}.warning{{padding:16px;background:#fff0cb}}h1,h2{{line-height:1.4}}</style>
<h1>매월 고정 비용 → 실제 모형상 거래금액 기준 비용</h1>
<p>{plan['signal_months'][0]}~{plan['signal_months'][-1]} 신호, {len(plan['signal_months'])}개월. 동일 데이터·모형·선택 종목·목표 비중. 갱신·재학습 없음.</p>
<p>매수금액 × {plan['buy_bps']}bp + 매도금액 × {plan['sell_bps']}bp. 직전 보유분의 가격 변동을 반영한 뒤 목표 비중과의 차이만 거래합니다.
최초 진입은 매수 비용만, 마지막 강제 청산은 포함하지 않습니다. 비용을 차감한 자산 안에서 목표 수량을 계산합니다.</p>
<div class="warning">이 표는 확정 실적이 아닌 결측 가정별 탐색입니다. 비용 단가는 실제 수수료·연도별 세금·시장충격을 검증한 값이 아닙니다.
미확인 가격의 평가·처분도 가정이며 두 경로는 신뢰구간이나 보장된 상하한이 아닙니다. 월말 가격 수익이며 배당 포함 TR·월초 실제 체결이 아닙니다.</div>
{''.join(tables)}<p>* 회전율 = (매수금액 + 매도금액) / (2 × 거래 전 자산). 평균 회전율은 최초 진입을 제외하며, 평균 월 비용에는 최초 매수도 포함합니다.</p>
<p>기존 연율은 월마다 자산의 {plan['parent_round_trip_cost_scenario_bps'] / 100:.2f}%를 차감한 비교치입니다. 전체 동일가중은 KOSPI가 아니며 낮은 매매량 때문에 비용 부담도 전략보다 작을 수 있습니다.</p>
<p>원본 결과는 보존했습니다. 모든 수치는 result.json, 매월 매수·매도·비용·NAV는 paths/scenarios/monthly에 기록했습니다. 자동 전략 승격이나 실거래는 하지 않았습니다.</p></html>"""
    _immutable(Path(output) / "report.html", html.encode())


def run(args):
    panel, manifest, _ = snapshot.load_snapshot(args.snapshot)
    parent, folds, checkpoints = load_parent(args.run, manifest)
    if any(not math.isfinite(rate) or not 0 <= rate < 10000 for rate in (args.buy_bps, args.sell_bps)):
        raise ValueError("Invalid cost rates")
    plan = {"schema": "reference-turnover-replay-plan-v1", "snapshot_sha256": manifest["snapshot_sha256"],
            "parent_run": str(Path(args.run).resolve()), "parent_plan_sha256": digest(parent),
            "parent_result_file_sha256": snapshot.file_hash(Path(args.run) / "result.json"),
            "parent_checkpoint_file_sha256": checkpoints, "signal_months": parent["signal_months"],
            "buy_bps": args.buy_bps, "sell_bps": args.sell_bps,
            "parent_round_trip_cost_scenario_bps": parent["round_trip_cost_scenario_bps"],
            "targets_changed": False, "model_refitted": False, "source_refreshed": False,
            "revision_reason": "USER_REQUESTED_TRADE_NOTIONAL_ACCOUNTING_AFTER_VIEWING_FIXED_COST_RESULTS_NOT_NEW_OOS",
            "code_sha256": {"runner": snapshot.file_hash(__file__), "accounting": snapshot.file_hash(turnover.__file__),
                            "cost_kernel": snapshot.file_hash(turnover._post_cost_nav.__code__.co_filename)}}
    output = Path(args.output)
    snapshot.write_json(output / "plan.json", plan)
    print({"status": "PLAN_FROZEN", "months": len(folds), "models": len(snapshot.MODELS), "refit": False}, flush=True)
    result = turnover.evaluate(panel, folds, buy_bps=args.buy_bps, sell_bps=args.sell_bps)
    comparison, error = compare(folds, result)
    # Independent old-basket algebra check ensures that the return source is unchanged.
    multiplier = 1 - parent["round_trip_cost_scenario_bps"] / 10000
    for key, path in result["paths"].items():
        if "scenarios" not in path:
            continue
        model, variant = key.split("/")
        for assumption, replay in path["scenarios"].items():
            for fold, row in zip(folds, replay["monthly"]):
                old = next(p for p in fold["models"][model]["portfolios"] if p["portfolio"] == variant)
                if not math.isclose((1 + row["gross_return"]) * multiplier - 1, old["sensitivity_net_returns_not_observed"][assumption], abs_tol=1e-12):
                    raise ValueError("Gross outcome differs from original experiment")
    result.update(plan_sha256=digest(plan), snapshot_sha256=manifest["snapshot_sha256"], comparison=comparison,
                  empirical_use="FROZEN_SNAPSHOT_EXPLORATION_HISTORICAL_REUSE", alpha_approved=False,
                  pit_status=manifest["pit_status"], selected_model=None,
                  audit={"budget_and_return_algebra_verified": True, "old_gross_outcomes_identical": True,
                         "maximum_return_reconciliation_error": error,
                         "portfolio_scenario_months": sum(len(p["monthly"]) for v in result["paths"].values() for p in v.get("scenarios", {}).values())})
    snapshot.write_json(output / "result.json", result)
    render(output, plan, result)
    print({"status": "TURNOVER_REPLAY_COMPLETE", "output": str(output), "audit": result["audit"]}, flush=True)
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--buy-bps", type=float, default=25.)
    p.add_argument("--sell-bps", type=float, default=25.)
    return p


if __name__ == "__main__":
    run(parser().parse_args())
