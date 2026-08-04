#!/usr/bin/env python
"""팩터 리서치 CLI.

  python scripts/run.py build                 # 패널 캐시 생성 (한 번)
  python scripts/run.py null --n 30           # 실제 T0~T5 실현 위양성률 측정
  python scripts/run.py gate                  # 등록 팩터 전체 게이트 통과
  python scripts/run.py gate --factor qual_roe
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import factors as F
from engine import fundamentals, gate, null, panel as P, publish, silver, trials

CACHE = Path(os.environ.get("CACHE_DIR", ".cache"))
TRIAL_DB = CACHE / "trials.sqlite3"


def load_registry():
    """Load stable builtins plus agent-authored candidates, idempotently."""
    import factors.builtin  # noqa: F401
    from factors.candidate_loader import load_candidates

    load_candidates(F.REGISTRY)
    return F.REGISTRY


def cmd_build(args):
    CACHE.mkdir(exist_ok=True)
    load_registry()
    with silver.connect(read_only=True) as conn:
        pan = P.build(conn)
        fund = fundamentals.build(conn)
    need = list(F.REGISTRY.needs)
    df = fundamentals.attach(pan.monthly, fund, need)
    df = df.sort_values(["Code", "ym"]).reset_index(drop=True)
    pan.monthly = df
    for tag, term in (("opt", 0.0), ("mid", -0.50), ("pess", -1.00)):
        df[f"fwd_{tag}"] = P.forward_returns(pan, terminal=term)   # 인덱스 정렬 (위치대입 금지)
    df = F.compute_all(F.REGISTRY, df)
    pan.monthly = df
    with open(CACHE / "panel.pkl", "wb") as fh:
        pickle.dump(pan, fh)
    print(f"\n캐시 저장: {CACHE/'panel.pkl'}  ({len(df):,}행 × {len(F.REGISTRY)}팩터)")


def _load():
    with open(CACHE / "panel.pkl", "rb") as fh:
        panel = pickle.load(fh)
    required = {"asset_id", "return_close", "total_return_close", "quality_run_id"}
    if panel.meta.get("source") != "RDS public Silver" or not required.issubset(panel.monthly.columns):
        raise SystemExit(
            "캐시가 Bronze/v1 형식입니다. `uv run python scripts/run.py build`로 "
            "인증 Silver 캐시를 다시 만드세요."
        )
    return panel


def _ensure_factor_columns(pan, targets):
    """캐시에 없는 팩터만 즉석 계산한다.

    팩터 값은 build 때 캐시되지만, 새로 등록한 팩터는 컬럼이 없다.
    재무 컬럼(needs)이 이미 패널에 있으면 10분짜리 재빌드 없이 여기서 채운다.
    needs 가 부족하면 build 를 다시 돌려야 한다.
    """
    df = pan.monthly
    missing = [f for f in targets if f"f_{f.name}" not in df.columns]
    if not missing:
        return df
    lacking = {c for f in missing for c in f.needs if c not in df.columns}
    if lacking:
        raise SystemExit(
            f"패널에 없는 컬럼이 필요합니다: {sorted(lacking)}\n"
            f"  → uv run python scripts/run.py build  (재빌드 필요)")
    print(f"[gate] 신규 팩터 {len(missing)}개 즉석 계산: "
          f"{', '.join(f.name for f in missing)}")
    for f in missing:
        try:
            df[f"f_{f.name}"] = f.compute(df) * f.predicted_sign
        except Exception as exc:
            df[f"f_{f.name}"] = float("nan")
            print(f"  ⚠️  {f.name} 계산 실패: {type(exc).__name__}: {exc}")
    pan.monthly = df
    return df


def _approved_signals(conn, df: pd.DataFrame) -> dict[str, pd.Series]:
    values = silver.load_approved_values(conn)
    if values.empty:
        return {}
    values["ym"] = pd.to_datetime(values["as_of_date"]).dt.to_period("M")
    target = pd.MultiIndex.from_arrays([df["asset_id"], df["ym"]])
    output = {}
    for name, group in values.groupby("factor_key"):
        keyed = (group.sort_values("as_of_date")
                 .drop_duplicates(["asset_id", "ym"], keep="last")
                 .set_index(["asset_id", "ym"])["value"])
        output[str(name)] = pd.Series(keyed.reindex(target).to_numpy(dtype=float), index=df.index)
    return output


def _evaluate(args):
    load_registry()
    pan = _load()
    df = pan.monthly
    targets = [F.REGISTRY[args.factor]] if args.factor else list(F.REGISTRY)
    df = _ensure_factor_columns(pan, targets)
    ledger = trials.TrialLedger(TRIAL_DB)
    oos_start = ledger.fixed_oos_start(
        list(df["ym"].unique()), requested=os.environ.get("OOS_START")
    )
    with silver.connect(read_only=True) as conn:
        approved = _approved_signals(conn, df)
        gold_trials = silver.load_gold_trial_history(conn)
    # Gold's legacy trial rows contain return Sharpe/p-values.  They still count
    # as attempted definitions, but must not enter v3's IC multiple testing.
    external = [
        (str(row.definition_hash), None, None)
        for row in gold_trials.itertuples(index=False)
    ]
    summary = ledger.summary(
        [factor.definition_hash for factor in targets], external=external,
        ruleset_version=gate.RULESET_VERSION,
    )
    results: list[gate.Result] = []
    for f in targets:
        # A new version of an already-approved factor is compared with other Gold
        # families, not with its own currently active version.
        existing = {name: values for name, values in approved.items() if name != f.name}
        results.append(gate.evaluate(
            f, pan, df, existing=existing, trial_count=summary.count,
            prior_sharpes=summary.sharpes, oos_start=oos_start,
        ))
    gate.apply_multiple_testing(results, summary.pvalues)
    cutoff = str(df["trade_date"].max().date())
    calibration_path = CACHE / "null_dist.parquet"
    calibration = pd.read_parquet(calibration_path) if calibration_path.exists() else None
    gate.apply_null_calibration(results, calibration, data_cutoff=cutoff)
    for factor, result in zip(targets, results, strict=True):
        ledger.record(factor, result, data_cutoff=cutoff, ruleset_version=gate.RULESET_VERSION)
    return pan, df, targets, results


def cmd_gate(args):
    _, _, _, results = _evaluate(args)

    print("\n" + "=" * 104)
    print(f"{'팩터':24} {'판정':12} {'IC':>7} {'투자가능IC':>10} {'OOS IC':>8} {'회전율':>8}  실패 검사")
    print("-" * 104)
    order = {gate.Verdict.PROMOTE: 0, gate.Verdict.PROVISIONAL: 1, gate.Verdict.REJECT: 2}
    for r in sorted(results, key=lambda x: (order[x.verdict], -(x.metrics.get("ic_investable") or -99))):
        m = r.metrics
        icon = {"PROMOTE": "✅", "PROVISIONAL": "⚠️ ", "REJECT": "❌"}[r.verdict.value]
        fails = ", ".join(c.name for c in r.failed)[:44]
        print(f"{r.factor:24} {icon}{r.verdict.value:10} "
              f"{m.get('ic_full', float('nan')):>7.3f} "
              f"{m.get('ic_investable', float('nan')):>10.3f} "
              f"{m.get('oos_ic', float('nan')):>8.3f} "
              f"{m.get('turnover', float('nan')):>7.0f}%  {fails}")

    n_p = sum(1 for r in results if r.verdict == gate.Verdict.PROMOTE)
    n_v = sum(1 for r in results if r.verdict == gate.Verdict.PROVISIONAL)
    print(f"\n  PROMOTE {n_p} / PROVISIONAL {n_v} / REJECT {len(results)-n_p-n_v}  (후보 {len(results)})")
    with open(CACHE / "gate_results.pkl", "wb") as fh:
        pickle.dump(results, fh)


def cmd_null(args):
    pan = _load()
    print(f"합성 귀무 팩터 측정 (종류당 {args.n}개)...")
    ledger = trials.TrialLedger(TRIAL_DB)
    with silver.connect(read_only=True) as conn:
        gold_trials = silver.load_gold_trial_history(conn)
    summary = ledger.summary(external=[
        (str(row.definition_hash), None, None)
        for row in gold_trials.itertuples(index=False)
    ], ruleset_version=gate.RULESET_VERSION)
    oos_start = ledger.fixed_oos_start(
        list(pan.monthly["ym"].unique()), requested=os.environ.get("OOS_START")
    )
    out = null.measure(
        pan, n=args.n, trial_count=summary.count,
        prior_sharpes=summary.sharpes, historical_pvalues=summary.pvalues,
        oos_start=oos_start,
    )
    out.to_parquet(CACHE / "null_dist.parquet", index=False)


def cmd_publish(args):
    """게이트 판정을 TeamAlpha-data 의 gold.factor 에 적재."""
    pan, df, targets, results = _evaluate(args)
    cutoff = str(df["trade_date"].max().date())
    rows = []
    for f, r in zip(targets, results, strict=True):
        if args.only_approved and r.verdict != gate.Verdict.PROMOTE:
            continue
        rows.append(publish.build_row(
            f, r, n_trials=r.metrics.get("n_trials"),
            realized_fdr=r.metrics.get("realized_fdr"), data_cutoff=cutoff,
            approved_by=args.approved_by,
        ))

    print(f"\n적재 대상 {len(rows)}건  (모드: {'APPLY' if args.apply else 'DRY-RUN'})")
    for r in rows:
        ev = r["evaluation"]
        print(f"  {r['factor_key']:16} → {r['status']:10} "
              f"(verdict={ev['verdict']}, 실패={len(ev['failed_checks'])}건)")
    if not rows:
        print("  (없음)")
        return

    if args.apply:
        if any(row["status"] == "APPROVED" for row in rows) and not args.approved_by:
            raise SystemExit("APPROVED 적재에는 --approved-by '검토자 이름'이 필요합니다")
        conn = publish.connect()
        try:
            done = publish.publish(conn, rows, apply=True)
        finally:
            conn.close()
    else:
        done = publish.publish(None, rows, apply=False)   # dry-run 은 DB 불필요
    print()
    for d in done:
        print(f"  {d['factor_key']:16} v{d['version']}  {d['status']}"
              + (f"  factor_id={d['factor_id']}" if d["factor_id"] else ""))
    if not args.apply:
        print("\n  실제로 쓰려면 --apply")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    g = sub.add_parser("gate"); g.add_argument("--factor")
    n = sub.add_parser("null"); n.add_argument("--n", type=int, default=30)
    p = sub.add_parser("publish")
    p.add_argument("--factor"); p.add_argument("--apply", action="store_true")
    p.add_argument("--approved-by", help="PROMOTE를 최종 확인한 사람")
    p.add_argument("--only-approved", action="store_true",
                   help="PROMOTE 만 적재 (기본은 판정 전체를 기록)")
    a = ap.parse_args()
    {"build": cmd_build, "gate": cmd_gate, "null": cmd_null,
     "publish": cmd_publish}[a.cmd](a)


if __name__ == "__main__":
    main()
