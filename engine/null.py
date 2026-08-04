"""T4.5 실현 FDR 측정 — 게이트를 '설계된 물건'에서 '측정되는 물건'으로 바꾼다.

에이전트가 게이트 최적화를 시작하는 순간 **합성 귀무의 통과율이 즉시 튀어오른다.**
다른 방어는 특정 우회로를 막지만 이것은 '아직 모르는 우회로'까지 탐지한다.
임계 초과 시 임계값 40개를 개별 조정하지 말 것 — 그 조정 자체가 대조군에 대한
과최적화다. **전역 엄격도 스칼라 하나**만 움직인다.

실측(2026-07-31, 320개):
  순수난수 120     통과 0   순알파 중앙 −4.62%  회전율 991%
  AR1 ρ=.95  70    통과 0   순알파 중앙 −1.34%  회전율 342%
  AR1 ρ=.99  30    통과 0   순알파 최대 +0.73%  회전율 239%
  AR1 ρ=.999 30    통과 0   순알파 최대 +2.36%  회전율 184%  ← 가장 위험
  완전정적    30    통과 0   순알파 최대 +0.79%  회전율 166%
  ROE 셔플    40    통과 0   순알파 중앙 −4.46%
→ 저회전 귀무 99퍼센타일 +1.22% vs 임계 3.0% (2.5배 여유)
→ 주가수준(레드팀 'High-Price Quality' 공격): 순알파 −3.00% 차단
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.gate import TH, backtest


def _skeleton(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    return df[mask][["ym", "Code", "fwd_mid"]].dropna(subset=["fwd_mid"]).copy()


def random_null(skel: pd.DataFrame, rng) -> pd.DataFrame:
    """순수 난수 — 회전율이 극도로 높아 비용에서 죽는다."""
    return skel.assign(v=rng.standard_normal(len(skel)))


def persistent_null(skel: pd.DataFrame, rng, rho: float = 0.99) -> pd.DataFrame:
    """지속성 있는 난수 — 회전율이 낮아 **비용 방어를 우회한다**. 가장 위험한 귀무."""
    codes = skel["Code"].unique()
    state = pd.Series(rng.standard_normal(len(codes)), index=codes)
    out = []
    for ym in sorted(skel["ym"].unique()):
        state = rho * state + np.sqrt(max(1 - rho ** 2, 1e-9)) * pd.Series(
            rng.standard_normal(len(codes)), index=codes)
        g = skel[skel["ym"] == ym]
        out.append(g.assign(v=state.reindex(g["Code"]).values))
    return pd.concat(out, ignore_index=True)


def frozen_null(skel: pd.DataFrame, rng) -> pd.DataFrame:
    """완전 정적 — 한 번 뽑고 영원히 고정. 회전율 ≈ 0 인 극단."""
    codes = skel["Code"].unique()
    fixed = pd.Series(rng.standard_normal(len(codes)), index=codes)
    return skel.assign(v=fixed.reindex(skel["Code"]).values)


def shuffle_null(skel: pd.DataFrame, real: pd.Series, rng) -> pd.DataFrame:
    """실제 팩터를 월별 횡단면에서 셔플 — 분포는 보존하고 정보만 파괴."""
    s = skel.assign(v=real.reindex(skel.index).values).dropna(subset=["v"])
    return pd.concat([g.assign(v=rng.permutation(g["v"].values))
                      for _, g in s.groupby("ym")], ignore_index=True)


def measure(df: pd.DataFrame, mask: pd.Series, *, n: int = 30, seed: int = 20260731,
            verbose: bool = True) -> pd.DataFrame:
    """합성 귀무를 게이트에 통과시켜 실현 FDR 측정."""
    rng = np.random.default_rng(seed)
    skel = _skeleton(df, mask)
    kinds = [
        ("random", lambda: random_null(skel, rng)),
        ("ar1_0.95", lambda: persistent_null(skel, rng, 0.95)),
        ("ar1_0.999", lambda: persistent_null(skel, rng, 0.999)),
        ("frozen", lambda: frozen_null(skel, rng)),
    ]
    rows = []
    for name, fn in kinds:
        for _ in range(n):
            # 생성기는 skel 에서 파생되므로 fwd_mid 를 이미 갖고 있다(재머지 금지)
            m = fn()
            b = backtest(m, "v", "fwd_mid", hold=1)
            if not b:
                continue
            passed = (b["net"] >= TH["net_alpha"] and b["net_ir"] >= TH["net_ir"]
                      and b["turnover"] <= TH["turnover_pass"])
            rows.append({"kind": name, **b, "pass": passed})
        if verbose:
            sub = [r for r in rows if r["kind"] == name]
            pr = np.mean([r["pass"] for r in sub]) * 100 if sub else 0
            print(f"  [null] {name:12} n={len(sub):>3}  통과율 {pr:5.1f}%  "
                  f"순알파 중앙 {np.median([r['net'] for r in sub]):+6.2f}%  "
                  f"최대 {max(r['net'] for r in sub):+6.2f}%", flush=True)
    out = pd.DataFrame(rows)
    if verbose and len(out):
        print(f"  [null] 전체 실현 FDR: {out['pass'].mean()*100:.1f}%  "
              f"(임계 ≤10%)  귀무 99퍼센타일 순알파 {out['net'].quantile(.99):+.2f}%")
    return out
