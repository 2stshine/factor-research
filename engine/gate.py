"""승격 게이트 T0~T5.

설계 원칙(레드팀 18개 공격에서 도출):
**통계를 마지막에 둔다.** 성공한 공격 18개 중 통계적 요행은 0개였고, 전부 표본틀 오류
(상장폐지 종착수익률 결측·체결불가 가격·거래정지 가짜 0·배당 갭)를 수확했다.
순열검정·부트스트랩·홀드아웃은 전부 같은 표본의 재표본이라, 표본틀이 틀리면 넷이
동시에 같은 방향으로 틀린다. SQL 한 줄로 죽는 것을 통계로 잡으려 하면 안 된다.

임계값은 합성 귀무 팩터 320개로 보정했다(engine/null.py):
  고회전 귀무 99퍼센타일  순알파 −0.10%
  저회전 귀무 99퍼센타일  순알파 +1.22%  ← 정적 베팅이 가장 위험
  현행 임계 net ≥ 3.0%   → 귀무 통과율 0.0% (320/320 차단)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats

from engine.factors import Factor
from engine.panel import Panel

# ---- 비용 모델 (T2.4 — 시변 세율 필수. 단일 세율 가정은 그 자체로 실격) ----
SECURITIES_TAX = {2015: .0030, 2016: .0030, 2017: .0030, 2018: .0030, 2019: .0025,
                  2020: .0025, 2021: .0023, 2022: .0023, 2023: .0020, 2024: .0018,
                  2025: .0015, 2026: .0015}
COMMISSION = 0.00015      # 위탁수수료 편도
IMPACT = 0.0010           # 시장충격 편도 (ADV≥5억 구간 보수적)

# ---- 임계값 ----
TH = {
    "min_months": 24,
    "investable_retention": 0.50,   # T2.1 |IC_inv| ≥ 0.5×|IC_full|
    "investable_t": 2.0,
    "turnover_pass": 250.0,         # T2.2 %/yr
    "turnover_fail": 400.0,
    "net_alpha": 3.0,               # T2.4 %/yr — 저회전 귀무 99%ile(1.22%)의 2.5배
    "net_ir": 0.74,                 # T2.4 t≈2.5 대응
    "subperiod_agree": 3,           # T3.2 비중첩 4구간 중 부호 일치 최소
    "plateau_ratio": 3.0,           # T3.1 리밸주기 간 순알파 최대/최소
    "december_delta": 0.15,         # T3.5c 12월 제외 시 상대 변화 상한
    "max_corr": 0.70,               # T5.1 기존 팩터와 상관 상한
    "regime_conc": 0.60,            # T3.6 한 구간이 전체 알파의 60% 초과면 사건
}


class Verdict(str, Enum):
    PROMOTE = "PROMOTE"
    PROVISIONAL = "PROVISIONAL"
    REJECT = "REJECT"


@dataclass
class Check:
    tier: str
    name: str
    passed: bool
    value: float | None = None
    threshold: str = ""
    note: str = ""


@dataclass
class Result:
    factor: str
    verdict: Verdict
    checks: list[Check] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    labels: list[str] = field(default_factory=list)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]

    def tier_failed(self, tier: str) -> bool:
        return any(not c.passed and c.tier == tier for c in self.checks)


# ---------------------------------------------------------------- 계산 헬퍼
def _ic_series(df: pd.DataFrame, col: str, fwd: str, min_n: int = 30) -> pd.Series:
    out = {}
    for ym, g in df.groupby("ym"):
        s = g[[col, fwd]].dropna()
        if len(s) < min_n:
            continue
        r = stats.spearmanr(s[col], s[fwd]).statistic
        if pd.notna(r):
            out[ym] = r
    return pd.Series(out)


def _ic_t(ics: pd.Series) -> tuple[float, float]:
    if len(ics) < 2:
        return float("nan"), float("nan")
    mu, sd = ics.mean(), ics.std(ddof=1)
    return mu, (mu / sd * np.sqrt(len(ics)) if sd else float("nan"))


def backtest(df: pd.DataFrame, col: str, fwd: str, *, hold: int = 1,
             quantile: float = 0.2) -> dict | None:
    """롱온리 상위분위 동일가중 — 비용 차감 후 초과수익.

    T3.3: 롱온리가 주 판정이다. 표본의 43.5%가 공매도 제약 구간이고 부분재개기에도
    숏 가능 종목은 13~14%뿐이라, 롱숏 IR 단독으로는 어떤 팩터도 승격시킬 수 없다.
    """
    months = sorted(df["ym"].unique())
    cur, rows = None, []
    for i, ym in enumerate(months):
        g = df[df["ym"] == ym][[col, fwd, "Code"]].dropna()
        if len(g) < 50:
            continue
        if cur is None or i % hold == 0:
            k = max(int(len(g) * quantile), 10)
            new = set(g.nlargest(k, col)["Code"])
            turn = 1.0 if cur is None else len(new - cur) / max(len(new), 1)
            cur = new
        else:
            turn = 0.0
        held = g[g["Code"].isin(cur)]
        if len(held) < 5:
            continue
        rows.append((held[fwd].mean(), g[fwd].mean(), turn, ym.year))

    if len(rows) < TH["min_months"]:
        return None
    p = pd.DataFrame(rows, columns=["ret", "bench", "turn", "year"])
    tax = p["year"].map(SECURITIES_TAX).fillna(0.0015)
    cost = p["turn"] * (COMMISSION + IMPACT) * 2 + p["turn"] * tax
    ex = p["ret"] - p["bench"] - cost
    sd = ex.std(ddof=1)
    return {
        "months": len(p),
        "turnover": p["turn"].mean() * 12 * 100,
        "gross": (p["ret"] - p["bench"]).mean() * 12 * 100,
        "cost": cost.mean() * 12 * 100,
        "net": ex.mean() * 12 * 100,
        "net_ir": ex.mean() / sd * np.sqrt(12) if sd else float("nan"),
        "net_t": ex.mean() / sd * np.sqrt(len(p)) if sd else float("nan"),
    }


# ---------------------------------------------------------------- 게이트
def evaluate(factor: Factor, panel: Panel, df: pd.DataFrame, *,
             existing: dict[str, pd.Series] | None = None,
             verbose: bool = False) -> Result:
    """T0~T5 순차 실행. 앞 tier 에서 죽으면 뒤는 계산하지 않는다(컴퓨트 절약)."""
    col = f"f_{factor.name}"
    res = Result(factor=factor.name, verdict=Verdict.REJECT)
    add = res.checks.append

    # ============ T0 등록·결정성 (백테스트 0회) ============
    undecl = factor.undeclared_constants()
    add(Check("T0", "미선언 상수", not undecl, len(undecl),
              "0개", f"발견: {undecl}" if undecl else ""))
    add(Check("T0", "가설 등록", bool(factor.hypothesis.strip()), None, "필수"))
    if res.tier_failed("T0"):
        return res

    if col not in df.columns or df[col].notna().sum() == 0:
        add(Check("T0", "계산 가능", False, 0, "값 존재"))
        return res

    # ============ T1 표본틀 무결성 (SQL 수준, 백테스트 0회) ============
    univ, inv = panel.universe, panel.investable
    cov = df.loc[univ, col].notna().mean()
    add(Check("T1", "커버리지", cov >= 0.30, cov * 100, "≥30%"))

    # T1.2 상장폐지 종착수익률 3점 스트레스 — 부호가 뒤집히면 표본틀이 거짓말
    ics = {}
    for tag, fwd in (("opt", "fwd_opt"), ("mid", "fwd_mid"), ("pess", "fwd_pess")):
        if fwd in df.columns:
            ics[tag] = _ic_series(df[univ], col, fwd)
    signs = {t: np.sign(s.mean()) for t, s in ics.items() if len(s)}
    stable = len(set(signs.values())) == 1 if signs else False
    add(Check("T1", "종착수익률 3점 스트레스", stable, None, "부호 유지",
              f"{ {k: round(v.mean(), 4) for k, v in ics.items()} }"))
    if res.tier_failed("T1"):
        return res

    ic_full, t_full = _ic_t(ics.get("mid", pd.Series(dtype=float)))
    res.metrics["ic_full"] = ic_full
    res.metrics["ic_t_full"] = t_full

    # ============ T2 체결가능성 ============
    ic_inv_s = _ic_series(df[inv], col, "fwd_mid")
    ic_inv, t_inv = _ic_t(ic_inv_s)
    retention = abs(ic_inv) / abs(ic_full) if ic_full else float("nan")
    same_sign = np.sign(ic_inv) == np.sign(ic_full)
    add(Check("T2.1", "투자가능 IC 유지율", bool(same_sign and retention >= TH["investable_retention"]),
              retention, f"≥{TH['investable_retention']} & 부호일치"))
    add(Check("T2.1", "투자가능 IC 유의성", abs(t_inv) >= TH["investable_t"], t_inv,
              f"|t|≥{TH['investable_t']}"))

    bt = backtest(df[inv], col, "fwd_mid", hold=factor.rebalance_months)
    if bt is None:
        add(Check("T2", "백테스트 표본", False, None, f"≥{TH['min_months']}개월"))
        return res
    res.metrics.update(bt)

    add(Check("T2.2", "회전율", bt["turnover"] <= TH["turnover_fail"], bt["turnover"],
              f"≤{TH['turnover_fail']}%/yr"))
    if bt["turnover"] > TH["turnover_pass"]:
        res.labels.append("high_turnover")
    add(Check("T2.4", "실비용 순알파", bt["net"] >= TH["net_alpha"], bt["net"],
              f"≥{TH['net_alpha']}%/yr"))
    add(Check("T2.4", "net_IR", bt["net_ir"] >= TH["net_ir"], bt["net_ir"],
              f"≥{TH['net_ir']}"))
    if res.tier_failed("T2") or res.tier_failed("T2.1") or res.tier_failed("T2.2") or res.tier_failed("T2.4"):
        return res

    # ============ T3 강건성 ============
    # T3.1 리밸주기 고원성 — 절벽이면 과최적화
    nets = []
    for h in (1, 3, 6):
        b = backtest(df[inv], col, "fwd_mid", hold=h)
        if b:
            nets.append(b["net"])
    plateau = (len(nets) == 3 and min(nets) > 0
               and max(nets) / max(min(nets), 0.01) <= TH["plateau_ratio"])
    add(Check("T3.1", "리밸주기 고원성", plateau, None, f"1/3/6개월 비 ≤{TH['plateau_ratio']}",
              f"{[round(n, 2) for n in nets]}"))

    # T3.2 비중첩 구간 (겹치는 롤링 창은 순수 노이즈도 100% 통과한다 — 폐기됨)
    per = pd.PeriodIndex(df["ym"].unique()).sort_values()
    segs = np.array_split(per, 4)
    ic_mid = ics.get("mid", pd.Series(dtype=float))
    agree = sum(1 for e in segs
                if len(ic_mid[ic_mid.index.isin(e)]) >= 12
                and np.sign(ic_mid[ic_mid.index.isin(e)].mean()) == np.sign(ic_full))
    add(Check("T3.2", "비중첩 구간 부호", agree >= TH["subperiod_agree"], agree,
              f"≥{TH['subperiod_agree']}/4"))

    # T3.3 롱온리가 주 판정 (위 T2.4 가 이미 롱온리 기준) — 여기선 라벨만
    res.labels.append("long_only_primary")

    # T3.6 레짐 집중도 — 한 구간이 전체 알파의 대부분을 만들면 '팩터'가 아니라 '사건'이다.
    # 비중첩 부호 검사(T3.2)는 4/4 를 통과해도 크기가 한 구간에 쏠린 경우를 못 잡는다.
    seg_net = []
    for e in segs:
        sub = df[inv & df["ym"].isin(e)]
        b = backtest(sub, col, "fwd_mid", hold=factor.rebalance_months)
        if b:
            seg_net.append(max(b["net"], 0.0))
    conc = (max(seg_net) / sum(seg_net)) if seg_net and sum(seg_net) > 0 else 1.0
    add(Check("T3.6", "레짐 집중도", conc <= TH["regime_conc"], conc,
              f"최대구간/합 ≤{TH['regime_conc']}", f"{[round(x, 1) for x in seg_net]}"))

    # T3.5c 12월 배당 스트레스 (adj_close 가 배당 미반영이라 12월 최종거래일에 갭이 생긴다)
    nodec = df[inv & (df["ym"].dt.month != 12)]
    b2 = backtest(nodec, col, "fwd_mid", hold=factor.rebalance_months)
    if b2:
        delta = abs(b2["net"] - bt["net"]) / max(abs(bt["net"]), 1e-9)
        add(Check("T3.5", "12월 배당 스트레스", delta <= TH["december_delta"], delta,
                  f"|Δ|≤{TH['december_delta']:.0%}"))
        if delta > TH["december_delta"]:
            res.labels.append("dividend_tilt")

    # ============ T5 직교성 ============
    if existing:
        worst, worst_name = 0.0, ""
        for nm, s in existing.items():
            common = ic_mid.index.intersection(s.index)
            if len(common) < 24:
                continue
            r = abs(stats.spearmanr(ic_mid[common], s[common]).statistic)
            if r > worst:
                worst, worst_name = r, nm
        add(Check("T5.1", "직교성", worst <= TH["max_corr"], worst,
                  f"|ρ|≤{TH['max_corr']}", f"최대: {worst_name}"))

    # ============ 판정 ============
    hard = [c for c in res.failed if c.tier in ("T0", "T1", "T2.1", "T2.2", "T2.4", "T5.1")]
    soft = [c for c in res.failed if c.tier.startswith("T3")]
    if hard:
        res.verdict = Verdict.REJECT
    elif len(soft) == 0:
        res.verdict = Verdict.PROMOTE
    elif len(soft) == 1:
        res.verdict = Verdict.PROVISIONAL
        res.labels.append(f"soft_fail:{soft[0].name}")
    else:
        res.verdict = Verdict.REJECT
    return res
