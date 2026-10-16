"""Descriptive report for a completed frozen exploration; no winner approval."""
import argparse
from collections import Counter
from html import escape
from pathlib import Path

import numpy as np

from engine import reference_snapshot_strategy as snapshot
from engine.research_generation import digest, _immutable

ASSUMPTIONS = ("MISSING_FLAT_ASSUMPTION", "MISSING_TOTAL_LOSS_ASSUMPTION")
MODEL_NAMES = {"all_usable_ridge": "전체 사용 가능 입력 + 릿지", "selected_ridge": "최대 30개 선택 + 릿지",
               "selected_pca_ridge": "선택 + PCA 10개 + 릿지", "universe": "동일 대상 전체 보유 기준선"}
PORTFOLIO_NAMES = {"q20_equal": "상위 20% · 동일가중", "q10_equal": "상위 10% · 동일가중",
                   "q20_sqrt_cap": "상위 20% · √시총", "q10_sqrt_cap": "상위 10% · √시총", "equal": "전체 · 동일가중"}


def metrics(returns):
    r = np.asarray(returns, dtype=float)
    if len(r) == 0 or not np.isfinite(r).all() or (r < -1).any():
        raise ValueError("Nonempty finite returns >= -100% required")
    nav = np.r_[1., np.cumprod(1 + r)]
    return {"months": len(r), "cumulative_return": float(nav[-1] - 1),
            "annualized_return": float(nav[-1] ** (12 / len(r)) - 1),
            "maximum_drawdown": float(np.min(nav / np.maximum.accumulate(nav) - 1)),
            "positive_month_fraction": float((r > 0).mean())}


def report(run_directory, snapshot_directory):
    root = Path(run_directory)
    result, plan = snapshot.read_json(root / "result.json"), snapshot.read_json(root / "plan.json")
    if result["plan_sha256"] != digest(plan):
        raise ValueError("Result/plan mismatch")
    panel, manifest, _ = snapshot.load_snapshot(snapshot_directory)
    if result["snapshot_sha256"] != manifest["snapshot_sha256"]:
        raise ValueError("Report snapshot mismatch")
    admission_path = Path(snapshot_directory) / "admission.json"
    names = {r["reference_id"]: r.get("name_ko", r["reference_id"])
             for r in snapshot.read_json(admission_path)["decisions"]} if admission_path.exists() else {}
    folds = []
    for month in plan["signal_months"]:
        saved = snapshot.read_json(root / "months" / (month + ".json"))
        if saved["plan_sha256"] != digest(plan) or saved["fold_sha256"] != digest(saved["fold"]) or saved["fold"]["signal_month"] != month:
            raise ValueError("Monthly checkpoint identity mismatch")
        folds.append(saved["fold"])
    if snapshot.summarize(folds) != result["summary"]:
        raise ValueError("Result summary differs from underlying months")
    if result.get("primary_result") == "turnover-result.json":
        from scripts.replay_reference_snapshot_costs import compare, render
        primary = root / "turnover-result.json"
        if snapshot.file_hash(primary) != result["primary_result_sha256"]:
            raise ValueError("Primary turnover accounting changed")
        audit = snapshot.read_json(primary)
        if audit["plan_sha256"] != digest(plan) or audit["snapshot_sha256"] != manifest["snapshot_sha256"]:
            raise ValueError("Turnover accounting identity mismatch")
        comparison, error = compare(folds, audit)
        audit.update(comparison=comparison, maximum_return_reconciliation_error=error)
        snapshot.write_json(root / "analysis.json", audit)
        render(root, {**plan, "parent_round_trip_cost_scenario_bps": plan["round_trip_cost_scenario_bps"]}, audit)
        print({"report": str(root / "report.html"), "cost_model": result["primary_cost_model"], "months": len(folds)}, flush=True)
        return audit
    baseline = []
    cost_multiplier = 1 - plan["round_trip_cost_scenario_bps"] / 10000
    for month in plan["signal_months"]:
        block = panel.loc[panel.month.eq(month) & panel.eligible]
        missing = float(block.outcome.isna().mean())
        flat = float(block.outcome.fillna(0).mean())
        baseline.append({"signal_month": month, "missing_weight": missing,
                         "returns": {ASSUMPTIONS[0]: (1 + flat) * cost_multiplier - 1,
                                     ASSUMPTIONS[1]: (1 + flat - missing) * cost_multiplier - 1}})
    series, rows, selections = [], [], {}
    for model in snapshot.MODELS:
        counter = Counter()
        for fold in folds:
            counter.update(fold["models"][model]["selected_features"])
        selections[model] = counter.most_common()
        for variant, _, _ in snapshot.VARIANTS:
            items = [next((p for p in f["models"][model]["portfolios"] if p["portfolio"] == variant), None) for f in folds]
            if any(item is None for item in items):
                rows.append({"model": model, "portfolio": variant, "status": "INCOMPLETE_MODEL_MONTHS"})
                continue
            row = {"model": model, "portfolio": variant, "status": "HYPOTHETICAL_MISSING_OUTCOME_SENSITIVITY",
                   "observed_complete_months": sum(p["status"] == "COMPLETE" for p in items),
                   "mean_missing_weight": float(np.mean([p["missing_outcome_weight"] for p in items])),
                   "max_missing_weight": max(p["missing_outcome_weight"] for p in items), "scenarios": {}}
            for assumption in ASSUMPTIONS:
                values = [p["sensitivity_net_returns_not_observed"][assumption] for p in items]
                excess = [r - b["returns"][assumption] for r, b in zip(values, baseline)]
                row["scenarios"][assumption] = {**metrics(values), "mean_monthly_excess_universe_same_assumption": float(np.mean(excess))}
                years = {}
                for month, value in zip(plan["signal_months"], values):
                    years.setdefault(month[:4], []).append(value)
                    series.append({"model": model, "portfolio": variant, "assumption": assumption,
                                   "signal_month": month, "return": value})
                row["scenarios"][assumption]["signal_year_returns"] = {
                    year: {"months": len(vals), "compounded_return": float(np.prod(1 + np.array(vals)) - 1)} for year, vals in years.items()}
            rows.append(row)
    baseline_metrics = {a: metrics([b["returns"][a] for b in baseline]) for a in ASSUMPTIONS}
    audit = {"schema": "reference-snapshot-descriptive-report-v1", "plan_sha256": digest(plan),
             "result_file_sha256": snapshot.file_hash(root / "result.json"), "reporter_sha256": snapshot.file_hash(__file__),
             "snapshot_sha256": manifest["snapshot_sha256"], "months": len(folds),
             "first_signal_month": plan["signal_months"][0], "last_signal_month": plan["signal_months"][-1],
             "reference_candidates": len(manifest["fields"]), "rows": rows, "baseline": baseline_metrics,
             "feature_selection_frequency": selections, "monthly_scenario_series": series,
             "feature_names": names,
             "selected_model": None, "alpha_approved": False, "refresh_performed": False,
             "limitations": result["limitations"]}
    snapshot.write_json(root / "analysis.json", audit)
    pct = lambda x: f"{x * 100:,.2f}%"
    table = []
    for row in rows:
        if "scenarios" not in row:
            table.append(f"<tr><td>{escape(MODEL_NAMES[row['model']])}</td><td>{escape(PORTFOLIO_NAMES[row['portfolio']])}</td><td colspan='6'>일부 모델-월 미실행</td></tr>")
            continue
        a, b = (row["scenarios"][k] for k in ASSUMPTIONS)
        table.append("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in [MODEL_NAMES[row['model']], PORTFOLIO_NAMES[row['portfolio']],
                      pct(a['annualized_return']), pct(b['annualized_return']), pct(a['maximum_drawdown']), pct(b['maximum_drawdown']),
                      f"{row['observed_complete_months']}/{len(folds)}", pct(row['max_missing_weight'])]) + "</tr>")
    baseline_html = " / ".join(pct(baseline_metrics[k]["annualized_return"]) for k in ASSUMPTIONS)
    selection_html = "".join(f"<h3>{escape(MODEL_NAMES[k])}</h3><ol>" + "".join(f"<li>{escape(names.get(name.removeprefix('f_'), name.removeprefix('f_')))}: {n}/{len(folds)}개월</li>" for name, n in selections[k][:15]) + "</ol>" for k in snapshot.MODELS[1:])
    html = f"""<!doctype html><html lang="ko"><meta charset="utf-8"><title>고정 스냅샷 전략 탐색</title>
<style>body{{font:16px/1.65 system-ui,sans-serif;max-width:1250px;margin:40px auto;padding:0 24px;color:#17212b;background:#f7f9fc}}table{{border-collapse:collapse;width:100%;background:white;font-size:14px}}td,th{{padding:11px;border-bottom:1px solid #dde3eb;text-align:right}}td:first-child,td:nth-child(2),th:first-child,th:nth-child(2){{text-align:left}}th{{background:#e8eef7}}.warning{{background:#fff0cb;padding:18px;border-left:5px solid #b77a00}}h1,h2,h3{{line-height:1.3}}small{{color:#526171}}</style>
<h1>고정 스냅샷 전략 탐색</h1><p>{audit['first_signal_month']}~{audit['last_signal_month']} 신호 · {len(folds)}개월 · {len(manifest['fields'])}개 후보 · 데이터 갱신 없음</p>
<div class="warning"><b>아래 숫자는 확정 성과가 아닌 결측 가정별 탐색 결과입니다.</b><br>
가격 유지: 다음 가격이 없는 종목의 해당 월 수익률을 0%로 가정.<br>전액 손실: 해당 월 -100%로 가정.
두 가정은 신뢰구간/상하한이 아닙니다. 월말 수정가격 기준이며 배당 포함 TR·실제 월초 매매가 아닙니다.</div>
<h2>12개 조합 비교</h2><p>비용: 매월 독립 바스켓에 왕복 {plan['round_trip_cost_scenario_bps']}bp 고정 차감. 실제 회전율·세금 모형이 아닙니다.
정규화 강도 10, 과거 최대 60개월, 선택 최대 30개, PCA 10성분을 유지했습니다.</p>
<table><thead><tr><th>모델</th><th>구성</th><th>연율: 가격 유지</th><th>연율: 전액 손실</th><th>낙폭: 가격 유지</th><th>낙폭: 전액 손실</th><th>결측 없는 월</th><th>최대 결측 비중</th></tr></thead><tbody>{''.join(table)}</tbody></table>
<h2>같은 대상 전체 동일가중 기준선</h2><p>동일 비용·동일 결측 가정의 연율 수익률(가격 유지 / 전액 손실): {baseline_html}.
KOSPI 지수나 시장 TR이 아닙니다. 최초 유니버스 자체에 없는 상장폐지 종목 등은 복원하지 않았습니다.</p>
<h2>학습 중 자주 선택된 측정치</h2><p>선택 빈도는 양의 효과·계수 크기·인과관계·알파 승인과 다릅니다. 음의 IC도 선택될 수 있습니다.</p>{selection_html}
<h2>해석의 경계</h2><ul>{''.join('<li>'+escape(x)+'</li>' for x in result['limitations'])}</ul>
<p>모든 조합을 보존했습니다. 최고 결과를 보고 자동으로 전략을 승인하거나 설정을 재조정하지 않았습니다.</p>
<small>스냅샷 {manifest['snapshot_sha256']}<br>월별 원본: months/ · 정량 분석: analysis.json · 실행 설정: plan.json</small></html>"""
    _immutable(root / "report.html", html.encode())
    print({"report": str(root / "report.html"), "months": len(folds), "comparisons": len(rows), "baseline": baseline_metrics}, flush=True)
    return audit


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", required=True)
    p.add_argument("--snapshot", required=True)
    args = p.parse_args()
    report(args.run, args.snapshot)
