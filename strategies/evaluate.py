"""예측 모델 진단 — 배분과 분리해 ridge 자체의 예측력을 본다.

    uv run python -m strategies.evaluate

예측은 롤링 OOS(각 월은 과거만으로 학습)이므로 아래 IC·R²는 표본외 값이다.
수익률 예측에서 R²는 원래 ~0이 정상이므로(월 OOS R² 0.3~1%면 우수) **R²로 판단하지 말고**
IC와 분위 스프레드로 본다. R²는 과적합 여부(IS vs OOS 비교)를 보는 용도.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategies.config import StrategyConfig
from strategies import data, predict


def _monthly_ic(df: pd.DataFrame, xcol: str, ycol: str = "target") -> pd.Series:
    return df.groupby("ym").apply(
        lambda g: g[[xcol, ycol]].dropna().corr(method="spearman").iloc[0, 1]
        if g[[xcol, ycol]].dropna().shape[0] >= 30 else np.nan
    ).dropna()


def _ic_stats(ic: pd.Series, ppy: int = 12) -> dict:
    mean, sd, n = ic.mean(), ic.std(ddof=1), len(ic)
    return {"n": n, "mean": mean, "std": sd,
            "icir": mean / sd * np.sqrt(ppy) if sd > 0 else np.nan,
            "t": mean / sd * np.sqrt(n) if sd > 0 else np.nan,
            "pos": float((ic > 0).mean())}


def main() -> None:
    cfg = StrategyConfig()
    print("[load] 패널...")
    panel = data.load_panel()
    frame = data.daily_frame(panel, cfg)
    print("[predict] ridge (일별 표본, 롤링 OOS)...")
    preds = predict.predict_returns(frame, cfg)

    fcols = [f"f_{f}" for f in cfg.factors]
    # 진단은 월말 시점 예측과 그 시점 타깃으로 맞춘다
    last_day = frame.groupby("ym")["trade_date"].transform("max")
    me = frame[frame["trade_date"].eq(last_day)]
    m = preds.merge(me[["ym", "asset_id", "target"] + fcols],
                    on=["ym", "asset_id"], how="left")
    m = m[m["target"].notna()]
    print(f"  평가 표본 {len(m):,}행 / {m['ym'].nunique()}개월 "
          f"({m['ym'].min()}~{m['ym'].max()})")

    s = _ic_stats(_monthly_ic(m, "r_hat"))
    print("\n=== 결합 예측 r_hat — Rank IC ===")
    print(f"IC={s['mean']:+.4f}  std={s['std']:.4f}  ICIR(ann)={s['icir']:+.2f}  "
          f"t={s['t']:+.1f}  양수월={s['pos']:.0%}  n={s['n']}")

    print("\n=== 단일 팩터 Rank IC (참고) ===")
    for f in cfg.factors:
        si = _ic_stats(_monthly_ic(m, f"f_{f}"))
        print(f"{f:44s} IC={si['mean']:+.4f}  ICIR={si['icir']:+.2f}  t={si['t']:+.1f}")

    # 10분위 스프레드·단조성
    def _dec(g):
        x = g.dropna(subset=["r_hat", "target"])
        if len(x) < 50:
            return None
        return x.groupby(pd.qcut(x["r_hat"].rank(method="first"), 10,
                                 labels=False))["target"].mean()
    dec = [d for d in (_dec(g) for _, g in m.groupby("ym")) if d is not None]
    if dec:
        D = pd.concat(dec, axis=1).mean(axis=1)
        mono = (D.diff().dropna() > 0).mean()
        print("\n=== r_hat 10분위 평균 월수익 (낮음→높음) ===")
        print("  " + "  ".join(f"D{i}:{v:+.3%}" for i, v in enumerate(D)))
        print(f"  D9−D0 = {D.iloc[-1] - D.iloc[0]:+.3%}/월  단조증가비율 {mono:.0%}")

    # R²: in-sample(전기간 pooled) vs out-of-sample(롤링, 횡단면 demeaned)
    Xs, ys = [], []
    for _, g in me.groupby("ym", sort=True):
        g = g[g["target"].notna()]
        if g.empty:
            continue
        Xs.append(predict._standardize_cross_section(g, fcols, cfg.winsor_q))
        ys.append(g["target"].to_numpy(float))
    X, y = np.vstack(Xs), np.concatenate(ys)
    beta = predict._ridge_fit(X, y, cfg.ridge_lambda)
    yc, yhat = y - y.mean(), X @ beta
    r2_is = 1 - float(((yc - yhat) ** 2).sum()) / float((yc ** 2).sum())

    d = m.dropna(subset=["r_hat", "target"]).copy()
    d["y_dm"] = d["target"] - d.groupby("ym")["target"].transform("mean")
    d["p_dm"] = d["r_hat"] - d.groupby("ym")["r_hat"].transform("mean")
    r2_oos = 1 - float(((d["y_dm"] - d["p_dm"]) ** 2).sum()) / float((d["y_dm"] ** 2).sum())

    print("\n=== R² (과적합 점검용) ===")
    print(f"in-sample(pooled) R² = {r2_is:.4%}   "
          f"out-of-sample(횡단면) R² = {r2_oos:.4%}")
    print("  OOS >= IS 이면 과적합 없음.")


if __name__ == "__main__":
    main()
