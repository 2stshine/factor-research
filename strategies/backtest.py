"""월별 백테스트 루프. 경로 의존(w_prev)을 상태로 들고 간다.

각 신호월 t: 후보 = (예측수익 상위 top_n) ∪ (직전 보유) → Σ 추정 가능 자산으로 제한 →
QP로 비중 결정 → 다음 달 실현수익(target=fwd_mid)·거래비용 반영. 거래비용(A, 측정)은
목적함수 턴오버 페널티(B, γ)와 같은 편도 비용률로 정합.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.config import StrategyConfig
from strategies.cov import estimate_cov
from strategies.optimize import solve_weights


def run_backtest(frame: pd.DataFrame, preds: pd.DataFrame,
                 daily_returns: pd.DataFrame, cfg: StrategyConfig) -> dict:
    cost_rate = cfg.cost_bps_per_side / 1e4
    gamma = cfg.turnover_gamma

    # (ym, asset_id) → target(=fwd_mid 실현 forward return)
    tgt = frame.set_index(["ym", "asset_id"])["target"]
    preds_by_month = {m: g for m, g in preds.groupby("ym", sort=True)}
    invest_by_month = {m: set(g["asset_id"]) for m, g in frame.groupby("ym", sort=True)}
    months = sorted(preds_by_month)

    w_prev: dict[int, float] = {}
    log = []

    for t in months:
        target_t = tgt.loc[t] if t in tgt.index.get_level_values(0) else pd.Series(dtype=float)
        if target_t.notna().sum() == 0:
            continue  # 마지막 월 등 forward 없음 → 평가 불가

        p = preds_by_month[t].dropna(subset=["r_hat"])
        if p.empty:
            continue
        ranked = p.sort_values("r_hat", ascending=False)
        top_ids = (list(ranked["asset_id"]) if cfg.top_n is None
                   else list(ranked["asset_id"].head(cfg.top_n)))
        # 후보 = 상위 top_n ∪ 직전 보유, 단 이번 달 예측/투자가능 집합 안의 자산만
        pred_ids = set(p["asset_id"])
        cand = [a for a in dict.fromkeys(top_ids + list(w_prev)) if a in pred_ids]

        used_ids, Sigma = estimate_cov(
            daily_returns, t, cand, cfg.cov_window_days, cfg.cov_min_days,
            cfg.cov_min_obs_ratio, cfg.cov_shrinkage)
        if not used_ids:
            continue

        mu_map = dict(zip(p["asset_id"], p["r_hat"]))
        mu = np.array([mu_map[a] for a in used_ids], dtype=float)
        wprev_vec = np.array([w_prev.get(a, 0.0) for a in used_ids], dtype=float)

        w = solve_weights(mu, Sigma, wprev_vec, cfg.risk_aversion_c, gamma, cfg.weight_cap_u)
        if w is None:
            continue

        new_w = {a: float(wi) for a, wi in zip(used_ids, w) if wi > 1e-6}

        # 실현 gross: target 있는 종목만, 비중 재정규화
        num, wsum = 0.0, 0.0
        for a, wi in new_w.items():
            rv = target_t.get(a, np.nan)
            if pd.notna(rv):
                num += wi * rv
                wsum += wi
        if wsum == 0:
            continue
        gross = num / wsum

        # 턴오버 비용: 직전 대비 전체 union의 |Δw| (강제청산 종목 포함)
        union = set(new_w) | set(w_prev)
        dturn = sum(abs(new_w.get(a, 0.0) - w_prev.get(a, 0.0)) for a in union)
        cost = cost_rate * dturn
        net = gross - cost

        # --- 벤치마크: 동일가중 top_n(같은 후보), 유니버스 EW ---
        bench_n = cfg.top_n or 200          # 벤치마크는 비교 가능하도록 상위 200 고정
        ew_ids = [a for a in top_ids[:bench_n] if pd.notna(target_t.get(a, np.nan))]
        ew_ret = float(np.mean([target_t[a] for a in ew_ids])) if ew_ids else np.nan
        uni_ids = [a for a in invest_by_month.get(t, set()) if pd.notna(target_t.get(a, np.nan))]
        uni_ret = float(np.mean([target_t[a] for a in uni_ids])) if uni_ids else np.nan

        # 옵티마이저가 스스로 예측한 위험. 실현 변동성과 크게 벌어지면 Σ 추정이
        # 무위험 방향을 만들어 주고 있다는 뜻이라, 성과보다 먼저 봐야 하는 진단이다.
        pred_var = float(w @ Sigma @ w)
        log.append({
            "ym": t, "gross": gross, "net": net, "cost": cost,
            "turnover": dturn, "n_holdings": len(new_w),
            "ew_topn": ew_ret, "univ_ew": uni_ret,
            "n_candidates": len(used_ids),
            "pred_vol_ann": float(np.sqrt(max(pred_var, 0.0) * 12)),
        })
        w_prev = new_w

    if not log:
        raise SystemExit("백테스트 결과가 비었습니다. 데이터/파라미터를 확인하세요.")
    return {"log": pd.DataFrame(log).set_index("ym")}
