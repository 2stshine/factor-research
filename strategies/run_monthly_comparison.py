"""Frozen, development-only implementation comparisons; no DB, orders or OOS reveal.

The input bundle must contain externally reconciled open-to-open total returns.
This runner never manufactures adjusted opens from close-only return indices.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import pandas as pd

from strategies.comparison_contract import (
    assert_observation_bounds, canonical_manifest_hash, fixed_variants, validate_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
ENGINE_FILES = ("strategies/comparison_contract.py", "strategies/monthly_execution.py",
                "strategies/run_monthly_comparison.py")
MISSING_INPUTS = [
    "Verified first-session open timestamps, including exceptional opening hours",
    "Frozen signed factor scores, eligible universe and cap with input availability times",
    "Tradable asset opens and corporate-action/dividend reconciled open-to-open total returns",
    "Named market gross-total-return benchmark over exactly the same open-to-open intervals",
    "Source files, SHA-256 bindings and explicit evidence for each input role",
]


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def implementation_binding():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ENGINE_FILES}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def protected_windows(research_root):
    """Read metadata only, including future shadow reservations. Never result files."""
    root = Path(research_root)
    if not (root / "campaigns").is_dir():
        raise ValueError("Campaign metadata directory missing; cannot establish sealed boundaries")
    windows = []
    for path in sorted((root / "campaigns").glob("*/manifest.json")):
        campaign = read_json(path)
        oos = campaign.get("oos")
        if not isinstance(oos, dict):
            raise ValueError("Campaign OOS metadata missing; cannot establish sealed boundaries")
        if oos.get("status") == "SEALED":
            windows.append({"campaign_id": campaign["campaign_id"],
                            "signal_start": oos["start"], "signal_end": oos["signal_end"],
                            "return_end": oos["return_end"]})
        else:
            terminal_pairs = {("REVEALED", "REVEALED"),
                              ("CLOSED_RETROSPECTIVE_ONLY", "NOT_USED"),
                              ("CLOSED_NO_QUALIFIED", "NOT_USED"),
                              ("SUPERSEDED_BOUNDARY_POLICY", "NOT_USED"),
                              ("CLOSED_INVALIDATED_INPUT_IDENTITY", "NOT_USED"),
                              ("CLOSED_ABORTED", "NOT_USED")}
            if (campaign.get("status"), oos.get("status")) not in terminal_pairs:
                raise ValueError("Unknown campaign lifecycle; refusing to assume its OOS is unsealed")
    for path in sorted((root / "prospective-shadow").glob("*.json")):
        shadow = read_json(path)
        if shadow.get("status") == "COLLECTING":
            start = pd.Period(shadow["start_month"], freq="M")
            end = start + int(shadow["required_months"]) - 1
            windows.append({"campaign_id": "shadow:" + shadow["campaign_id"],
                            "signal_start": str(start), "signal_end": str(end),
                            "return_end": str(end + 1)})
        else:
            raise ValueError("Unknown shadow lifecycle; refusing to assume its future window is available")
    return windows


def _kst_month(value, end=False):
    period = pd.Period(value, freq="M")
    stamp = period.end_time.floor("s") if end else period.start_time
    return stamp.tz_localize("Asia/Seoul").isoformat()


def prepare(catalog_path, *, decision_start, decision_end, output, research_root=ROOT / "research"):
    """Freeze all snapshot-approved factors, not the best past performer/subset.

    Cost parameters are inherited research assumptions, NOT verified current tax
    law or AUM-specific execution estimates. Existing gates/results are untouched.
    """
    catalog_path = Path(catalog_path)
    raw = catalog_path.read_bytes()
    catalog = json.loads(raw)
    factors = sorted(catalog["factors"], key=lambda row: row["name"])
    if not factors or any(row["status"] != "APPROVED" for row in factors):
        raise ValueError("Expected a nonempty approved-factor snapshot")
    start, end = pd.Period(decision_start, freq="M"), pd.Period(decision_end, freq="M")
    # Broad allowed timestamp bounds; exact first-session timestamps come from the
    # verified calendar, never guessed here. Last signal needs two following opens.
    legacy_tax = {2015: .003, 2016: .003, 2017: .003, 2018: .003, 2019: .0025,
                  2020: .0025, 2021: .0023, 2022: .0023, 2023: .002, 2024: .0018,
                  2025: .0015, 2026: .0015}
    years = range((start + 1).year, (end + 1).year + 1)
    if any(year not in legacy_tax for year in years):
        raise ValueError("No declared research cost assumption for the requested years")
    plan = {
        "schema_version": "strategy-comparison-plan-v1",
        "research_scope": "development_only", "independent_oos": False,
        "source_evidence_grade": "HISTORICAL_REUSED", "calendar_timezone": "Asia/Seoul",
        "factor_bindings": [{"factor_id": row["name"], "definition_hash": row["definition_hash"]}
                            for row in factors],
        "variants": fixed_variants(),
        "bounds": {"input_start": _kst_month(start), "input_end": _kst_month(end, True),
                   "decision_start": str(start), "decision_end": str(end),
                   "signal_start": _kst_month(start, True), "signal_end": _kst_month(end, True),
                   "trade_start": _kst_month(start + 1), "trade_end": _kst_month(end + 1, True),
                   "return_start": _kst_month(start + 1), "return_end": _kst_month(end + 2, True),
                   "return_support_end": _kst_month(end + 2, True),
                   "allowed_data_time": _kst_month(end + 2, True)},
        "catalog": {"path": str(catalog_path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
                    "as_of": catalog.get("as_of"), "status": catalog.get("status"),
                    "is_live": False, "note": "Frozen local snapshot, not current live approval verification"},
        "costs": {"buy_rate": .00115, "sell_rate": .00115,
                  "sell_tax_by_year": {str(year): legacy_tax[year] for year in years},
                  "basis": "Legacy gate research assumptions; no current-law or capacity certification"},
        "portfolio_policy": {"rebalance_months": 1, "factor_combination": False,
                             "selection": "floor(eligible_count*fraction), min 1; score descending, asset_id ascending",
                             "initial_nav": 1.0, "last_exit_liquidation": False,
                             "automatic_winner_selection": False},
        "benchmark_policy": {"return_type": "gross_total_return", "currency": "KRW",
                             "interval": "same_entry_open_to_exit_open", "market_id": "KRX300_TR",
                             "scope_note": "KOSPI+KOSDAQ blue-chip comparator, not an exact all-cap universe match"},
        "input_contract": "monthly-comparison-inputs-v1",
        "implementation_sha256": implementation_binding(),
    }
    unresolved = [row["factor_id"] for row in plan["factor_bindings"]
                  if not re.fullmatch(r"(?:[a-f0-9]{16}|[a-f0-9]{64})", str(row["definition_hash"] or ""))]
    if unresolved:
        # Do not quietly backtest the locally available subset of the catalog.
        # This is a frozen request, NOT a complete executable preregistration.
        envelope = {"plan": plan, "request_sha256": digest(plan),
                    "registered_at": pd.Timestamp.now(tz="UTC").isoformat(),
                    "registration_type": "INCOMPLETE_REQUEST_NOT_EXECUTION_PLAN",
                    "unresolved_factor_ids": unresolved}
    else:
        plan = validate_manifest(plan, sealed_campaigns=protected_windows(research_root))
        envelope = {"plan": plan, "plan_sha256": canonical_manifest_hash(plan),
                    "registered_at": pd.Timestamp.now(tz="UTC").isoformat(),
                    "registration_type": "HISTORICAL_DEVELOPMENT_DESIGN_NOT_PRISTINE_OOS"}
    save_new(output, envelope)
    return envelope


def load_plan(path, research_root):
    registered = read_json(path)
    if registered.get("registration_type") == "INCOMPLETE_REQUEST_NOT_EXECUTION_PLAN":
        raise ValueError("Frozen catalog contains unbound factors; resolve all identities before execution")
    plan = validate_manifest(registered["plan"], sealed_campaigns=protected_windows(research_root))
    if canonical_manifest_hash(plan) != registered["plan_sha256"]:
        raise ValueError("Registered plan digest mismatch; do not edit an existing plan")
    if plan.get("implementation_sha256") != implementation_binding():
        raise ValueError("Execution code differs from the registered plan; register a new version")
    return plan, registered


def load_inputs(path, plan):
    bundle = read_json(path)
    if bundle.get("schema_version") != "monthly-comparison-inputs-v1":
        raise ValueError("Unsupported input bundle schema")
    data, evidence = bundle["data"], bundle["evidence"]
    if data.get("data_kind") not in {"HISTORICAL_MARKET", "SYNTHETIC_TEST"}:
        raise ValueError("Input data_kind must distinguish market data from synthetic tests")
    if evidence.get("data_sha256") != digest(data):
        raise ValueError("Input data SHA-256 mismatch")
    if sorted(data["factor_bindings"], key=lambda x: x["factor_id"]) != plan["factor_bindings"]:
        raise ValueError("Input factor exact set/definitions differ from the frozen plan")
    market = data["market_benchmark"]
    for key, expected in (("return_type", "gross_total_return"), ("currency", "KRW"),
                          ("interval", "same_entry_open_to_exit_open"),
                          ("market_id", plan["benchmark_policy"]["market_id"])):
        if market.get(key) != expected:
            raise ValueError(f"Market benchmark {key} mismatch; no price-index or ETF substitution")
    if not data.get("source_files"):
        raise ValueError("Source evidence files are required; booleans alone are not provenance")
    for ref in data["source_files"]:
        source = Path(ref["path"])
        if not source.is_absolute():
            source = Path(path).parent / source
        if hashlib.sha256(source.read_bytes()).hexdigest() != ref["sha256"]:
            raise ValueError("Source evidence SHA-256 mismatch")
    score_factors = {row["factor_id"] for row in data["scores"]}
    if score_factors != {row["factor_id"] for row in plan["factor_bindings"]}:
        raise ValueError("Every frozen factor must be present, without extra factors")
    return data, evidence


def _jsonable(value):
    if isinstance(value, pd.DataFrame):
        return [_jsonable(row) for row in value.to_dict("records")]
    if isinstance(value, (pd.Timestamp, pd.Period)):
        return str(value)
    if isinstance(value, dict):
        # A total loss has no defined residual portfolio weights; preserve that
        # explicit missing value, but reject other nonfinite numerical results.
        return {str(k): None if k == "end_weight" and isinstance(v, float) and math.isnan(v)
                else _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(x) for x in value]
    if hasattr(value, "item"):
        return _jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite output cannot be silently serialized")
    return value


def summarize(monthly):
    net = monthly["net_return"].astype(float)
    equity = pd.concat([pd.Series([1.0]), (1 + net).cumprod()], ignore_index=True)
    n = len(net)
    return {"months": n, "net_total_return": float(equity.iloc[-1] - 1),
            "net_cagr": float(equity.iloc[-1] ** (12 / n) - 1),
            "net_mdd": float((equity / equity.cummax() - 1).min()),
            "annualized_arithmetic_net_excess_universe": float(monthly.net_excess_universe.mean() * 12),
            "annualized_arithmetic_net_excess_market": float(monthly.net_excess_market.mean() * 12),
            "annualized_buy_turnover": float(monthly.turnover_buy.mean() * 12),
            "annualized_sell_turnover": float(monthly.turnover_sell.mean() * 12)}


def run(plan_path, *, inputs=None, output, research_root=ROOT / "research"):
    """Missing input yields a readiness report, never invented performance."""
    from strategies.monthly_execution import ExecutionCosts, run_monthly_execution

    registered = read_json(plan_path)
    incomplete = registered.get("registration_type") == "INCOMPLETE_REQUEST_NOT_EXECUTION_PLAN"
    if incomplete:
        if inputs is not None:
            raise ValueError("Unbound factors prevent execution; no input bundle was read")
        plan = registered["plan"]
        if digest(plan) != registered["request_sha256"]:
            raise ValueError("Frozen incomplete request digest mismatch")
    else:
        plan, registered = load_plan(plan_path, research_root)
    out = Path(output)
    if out.exists():
        raise FileExistsError("Use a new output directory; previous evidence is immutable")
    base = {"schema_version": "monthly-comparison-report-v1", "plan_sha256": registered.get("plan_sha256"),
            "request_sha256": registered.get("request_sha256"),
            "factor_count": len(plan["factor_bindings"]), "variant_order": [v["variant_id"] for v in plan["variants"]],
            "independent_oos": False, "research_scope": "development_only",
            "actual_fill_verified": False, "orders_submitted": False,
            "benchmark_policy": plan["benchmark_policy"], "cost_basis": plan["costs"]["basis"]}
    if inputs is None:
        base.update(status="BLOCKED_MISSING_EXECUTION_INPUTS", missing_inputs=MISSING_INPUTS,
                    real_performance_computed=False,
                    unresolved_factor_ids=registered.get("unresolved_factor_ids", []),
                    executable_plan_registered=not incomplete)
        save_new(out / "readiness.json", base)
        with (out / "report.md").open("x", encoding="utf-8") as stream:
            stream.write("# 월초 실행 비교 — 입력 준비 미완료\n\n"
                         f"고정 팩터 {base['factor_count']}개 × 비교 규칙 4개. 실제 성과는 계산하지 않았습니다.\n\n"
                         "20% 동일가중을 기준선으로 10% 동일가중·20%/10% √시총 가중을 함께 비교합니다.\n"
                         "시장 비교는 KRX300 총수익 지수이며, 혼합시장 대형주 중심 지수라는 차이를 남깁니다.\n\n"
                         + "\n".join("- " + item for item in MISSING_INPUTS) + "\n\n"
                         + ("정의 해시가 없는 팩터(조용히 제외하지 않고 실행 보류): "
                            + ", ".join(base["unresolved_factor_ids"]) + "\n\n" if incomplete else "")
                         + "기존 팩터 IC·OOS·월말 종가 수익 결과와 Gold 상태는 변경하지 않았습니다.\n")
        return base

    data, evidence = load_inputs(inputs, plan)
    if pd.Timestamp(evidence["as_of"]) > pd.Timestamp(plan["bounds"]["allowed_data_time"]):
        raise ValueError("Input evidence as_of exceeds the frozen data boundary")
    costs = ExecutionCosts(buy_rate=plan["costs"]["buy_rate"], sell_rate=plan["costs"]["sell_rate"],
                           sell_tax_by_year={int(k): v for k, v in plan["costs"]["sell_tax_by_year"].items()})
    expected_months = list(map(str, pd.period_range(plan["bounds"]["decision_start"],
                                                  plan["bounds"]["decision_end"], freq="M")))
    frames = {key: pd.DataFrame(data[key]) for key in ("scores", "sessions", "asset_windows", "market_windows")}
    # Reject surplus dates before calculation: do not consume a superset then crop.
    for key in ("scores", "asset_windows", "market_windows"):
        if sorted(set(frames[key].signal_month.astype(str))) != expected_months:
            raise ValueError(f"{key}: exact frozen signal-month set required")
    expected_sessions = list(map(str, pd.period_range(pd.Period(expected_months[0]) + 1,
                                                      pd.Period(expected_months[-1]) + 2, freq="M")))
    if sorted(set(frames["sessions"].session_month.astype(str))) != expected_sessions:
        raise ValueError("sessions: exact frozen entry/exit session-month set required")
    results = {}
    for binding in plan["factor_bindings"]:
        factor_id = binding["factor_id"]
        scores = frames["scores"].loc[frames["scores"].factor_id.eq(factor_id)].drop(columns="factor_id")
        result = run_monthly_execution(scores, frames["sessions"], frames["asset_windows"],
                                       frames["market_windows"], evidence=evidence, costs=costs)
        for variant in result["variants"].values():
            monthly = variant["monthly"]
            if list(monthly.signal_month.astype(str)) != expected_months:
                raise ValueError("Comparison may not silently drop a month")
            for row in monthly.itertuples():
                assert_observation_bounds(plan, signal_time=row.decision_at.isoformat(),
                                          trade_time=row.entry_at.isoformat(), label_exit_time=row.exit_at.isoformat())
            variant["summary"] = summarize(monthly)
        results[factor_id] = _jsonable(result)
    synthetic = data["data_kind"] == "SYNTHETIC_TEST"
    base.update(status="SYNTHETIC_TEST_ONLY" if synthetic else "COMPLETED_DEVELOPMENT_COMPARISON",
                real_performance_computed=not synthetic,
                input_data_sha256=evidence["data_sha256"], results=results)
    save_new(out / "comparison.json", base)
    lines = ["# 월말 신호 · 월초 실행 비교", "",
             "합성 데이터 테스트이며 시장 성과가 아닙니다." if synthetic else "과거 개발용 비교입니다. 독립 OOS·실제 체결 인증이 아닙니다.", "",
             "비용 후 절대수익과 두 기준선의 초과수익을 함께 표시합니다. 초과수익은 월평균×12이며 CAGR 차이가 아닙니다.", "",
             "| 팩터 | 방식 | 순 CAGR | 순 MDD | 연환산 초과: 전체 EW | 연환산 초과: 시장 TR |",
             "|---|---|---:|---:|---:|---:|"]
    for factor_id, result in results.items():
        for variant_id in base["variant_order"]:
            s = result["variants"][variant_id]["summary"]
            lines.append(f"| {factor_id} | {variant_id} | {s['net_cagr']:.2%} | {s['net_mdd']:.2%} | "
                         f"{s['annualized_arithmetic_net_excess_universe']:.2%}p | "
                         f"{s['annualized_arithmetic_net_excess_market']:.2%}p |")
    lines += ["", "동일한 종목·월을 사용하는 네 방식 전부를 표시하며 최고 성과를 자동 선택하지 않습니다.",
              "가정: 분할 가능한 보유단위, 입력 총수익의 기업행사/배당 처리, 선언 비용. 실제 주문·AUM 용량 검증 없음.",
              "초기 매수에 매도세를 부과하지 않습니다. 마지막 시점은 평가액이며 강제청산 비용은 포함하지 않습니다."]
    with (out / "report.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    return {k: v for k, v in base.items() if k != "results"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--catalog", type=Path, required=True)
    prep.add_argument("--decision-start", required=True)
    prep.add_argument("--decision-end", required=True)
    prep.add_argument("--output", type=Path, required=True)
    execute = commands.add_parser("run")
    execute.add_argument("--plan", type=Path, required=True)
    execute.add_argument("--inputs", type=Path)
    execute.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        registered = prepare(args.catalog, decision_start=args.decision_start,
                             decision_end=args.decision_end, output=args.output)
        result = {"status": "BLOCKED_FACTOR_BINDINGS" if registered.get("unresolved_factor_ids") else "PLAN_REGISTERED",
                  "plan_sha256": registered.get("plan_sha256"), "request_sha256": registered.get("request_sha256"),
                  "unresolved_factor_ids": registered.get("unresolved_factor_ids", []),
                  "factors": len(registered["plan"]["factor_bindings"])}
    else:
        result = run(args.plan, inputs=args.inputs, output=args.output)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    if result.get("status", "").startswith("BLOCKED"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
