#!/usr/bin/env python
"""팩터 리서치 CLI.

  python scripts/run.py build                 # 패널 캐시 생성 (한 번)
  python scripts/run.py gate                  # 등록 팩터 전체 게이트 통과
  python scripts/run.py gate --factor qual_roe
  python scripts/run.py null --n 30           # T4.5 실현 FDR 측정
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
from engine import fundamentals, gate, null, panel as P, publish

BRONZE = os.environ.get("BRONZE_DIR", "/Users/mac/Documents/GitHub/TeamAlpha-data/data")
CACHE = Path(os.environ.get("CACHE_DIR", ".cache"))


def cmd_build(args):
    CACHE.mkdir(exist_ok=True)
    pan = P.build(BRONZE)
    fund = fundamentals.build(BRONZE)
    import factors.builtin  # noqa: F401  — 레지스트리 채우기
    need = [c for c in F.REGISTRY.needs]
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
        return pickle.load(fh)


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


def cmd_gate(args):
    import factors.builtin  # noqa: F401
    pan = _load()
    df = pan.monthly
    targets = [F.REGISTRY[args.factor]] if args.factor else list(F.REGISTRY)
    df = _ensure_factor_columns(pan, targets)

    # 기존 Gold 팩터의 IC 시계열 (T5.1 직교성 비교군)
    # T5 는 2-pass. 1-pass 로 하면 첫 팩터가 직교성 검사를 아예 안 받는다
    # (실측: qual_roe 앞의 3개가 전부 REJECT 라 existing 이 비어 있었다).
    all_ic = {f.name: gate._ic_series(df[pan.universe], f"f_{f.name}", "fwd_mid")
              for f in targets if f"f_{f.name}" in df.columns}
    results = []
    for f in targets:
        others = {k: v for k, v in all_ic.items() if k != f.name}
        results.append(gate.evaluate(f, pan, df, existing=others))

    print("\n" + "=" * 104)
    print(f"{'팩터':14} {'판정':12} {'순알파':>8} {'net_IR':>7} {'회전율':>8} {'IC t':>7}  실패 검사")
    print("-" * 104)
    order = {gate.Verdict.PROMOTE: 0, gate.Verdict.PROVISIONAL: 1, gate.Verdict.REJECT: 2}
    for r in sorted(results, key=lambda x: (order[x.verdict], -(x.metrics.get("net") or -99))):
        m = r.metrics
        icon = {"PROMOTE": "✅", "PROVISIONAL": "⚠️ ", "REJECT": "❌"}[r.verdict.value]
        fails = ", ".join(c.name for c in r.failed)[:44]
        print(f"{r.factor:14} {icon}{r.verdict.value:10} "
              f"{m.get('net', float('nan')):>7.2f}% {m.get('net_ir', float('nan')):>7.2f} "
              f"{m.get('turnover', float('nan')):>7.0f}% {m.get('ic_t_full', float('nan')):>7.2f}  {fails}")

    n_p = sum(1 for r in results if r.verdict == gate.Verdict.PROMOTE)
    n_v = sum(1 for r in results if r.verdict == gate.Verdict.PROVISIONAL)
    print(f"\n  PROMOTE {n_p} / PROVISIONAL {n_v} / REJECT {len(results)-n_p-n_v}  (후보 {len(results)})")
    with open(CACHE / "gate_results.pkl", "wb") as fh:
        pickle.dump(results, fh)


def cmd_null(args):
    pan = _load()
    print(f"합성 귀무 팩터 측정 (종류당 {args.n}개)...")
    out = null.measure(pan.monthly, pan.investable, n=args.n)
    out.to_parquet(CACHE / "null_dist.parquet", index=False)


def cmd_publish(args):
    """게이트 판정을 TeamAlpha-data 의 gold.factor 에 적재."""
    import factors.builtin  # noqa: F401
    pan = _load()
    df = pan.monthly
    targets = [F.REGISTRY[args.factor]] if args.factor else list(F.REGISTRY)
    df = _ensure_factor_columns(pan, targets)
    all_ic = {f.name: gate._ic_series(df[pan.universe], f"f_{f.name}", "fwd_mid")
              for f in targets if f"f_{f.name}" in df.columns}

    cutoff = str(df["trade_date"].max().date())
    rows = []
    for f in targets:
        r = gate.evaluate(f, pan, df, existing={k: v for k, v in all_ic.items() if k != f.name})
        if args.only_approved and r.verdict != gate.Verdict.PROMOTE:
            continue
        rows.append(publish.build_row(f, r, data_cutoff=cutoff))

    print(f"\n적재 대상 {len(rows)}건  (모드: {'APPLY' if args.apply else 'DRY-RUN'})")
    for r in rows:
        ev = r["evaluation"]
        print(f"  {r['factor_key']:16} → {r['status']:10} "
              f"(verdict={ev['verdict']}, 실패={len(ev['failed_checks'])}건)")
    if not rows:
        print("  (없음)")
        return

    if args.apply:
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
    p.add_argument("--only-approved", action="store_true",
                   help="PROMOTE 만 적재 (기본은 판정 전체를 기록)")
    a = ap.parse_args()
    {"build": cmd_build, "gate": cmd_gate, "null": cmd_null,
     "publish": cmd_publish}[a.cmd](a)


if __name__ == "__main__":
    main()
