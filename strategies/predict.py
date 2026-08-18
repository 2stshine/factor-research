"""1단계 — 일별 표본 롤링 ridge로 횡단면 수익률 예측.

**학습 표본은 매 거래일**이다. 각 (종목, 거래일) 쌍이 한 행이고, 타깃은 그날부터
`fwd_days` 거래일 뒤까지의 누적 수익률이다. 월말 하루만 쓰던 방식 대비 관측이 약 21배가
되고, "월말"이라는 임의 날짜에 의존하는 잡음이 평균화된다.

**예측·리밸런싱은 월 1회**다. 매월 말 그 시점 횡단면에 β̂를 곱해 `r̂`를 만든다.

PIT: 신호일 `t`의 학습에는 **타깃이 이미 실현된 날짜만** 쓴다. 날짜 `d`의 타깃은
`d + fwd_days`에 확정되므로 `d ≤ t − fwd_days` 인 행만 학습에 넣는다.

표준화: `X`는 날짜별 횡단면 z-score, `y`는 학습표본 전체 표준화 후 적합하고 계수를
`s_y` 배해 **수익률 단위로 환원**한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.config import StrategyConfig


def _standardize_cross_section(block: pd.DataFrame, fcols: list[str], q: float) -> np.ndarray:
    """한 날짜의 횡단면: winsorize → z-score → 결측 0(=중앙값) 대체."""
    x = block[fcols].astype(float)
    x = x.clip(lower=x.quantile(q), upper=x.quantile(1 - q), axis=1)
    sd = x.std(ddof=0).replace(0.0, np.nan)
    return ((x - x.mean()) / sd).fillna(0.0).to_numpy()


def _ridge_fit(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """표준화 ridge → 수익률 단위 환원.

    `y`를 표준화해 `β̃ = (XᵀX + λI)⁻¹Xᵀỹ` 를 구한 뒤 `β = s_y · β̃` 로 되돌린다.
    절편은 두지 않는다 — `X`가 날짜별 z-score라 각 날짜 `Xᵀ1 = 0`이고 절편과 직교하므로
    `β`가 불변이며, 상수항은 랭킹·`Σw=1` 제약 하 MVO 최적해를 바꾸지 않는다.
    """
    sy = y.std(ddof=0)
    ys = (y - y.mean()) / sy if sy > 0 else y - y.mean()
    A = X.T @ X + lam * np.eye(X.shape[1])
    try:
        beta = np.linalg.solve(A, X.T @ ys)
    except np.linalg.LinAlgError:
        beta = np.linalg.pinv(A) @ (X.T @ ys)
    return beta * sy


def _press(X: np.ndarray, y: np.ndarray, lams: np.ndarray) -> np.ndarray:
    """PRESS (leave-one-out CV 잔차제곱합)을 λ 격자에 대해 계산.

        PRESS(λ) = Σᵢ [ (yᵢ − ŷᵢ) / (1 − hᵢᵢ) ]²,  H = X(XᵀX + λI)⁻¹Xᵀ

    `XᵀX`의 고유분해를 재사용해 λ마다 O(nK)로 끝낸다. `y`를 상수배해도 PRESS는 같은
    상수의 제곱배가 되므로 argmin은 표준화 여부와 무관하다.
    """
    d, V = np.linalg.eigh(X.T @ X)
    Xt = X @ V
    z = Xt.T @ y
    out = np.empty(len(lams))
    for j, lam in enumerate(lams):
        w = 1.0 / (d + lam)
        resid = y - Xt @ (w * z)
        lev = (Xt ** 2) @ w
        r = resid / np.clip(1.0 - lev, 1e-9, None)
        out[j] = float(r @ r)
    return out


def predict_returns(frame: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    """일별 프레임으로 학습하고 **월말마다** 예측한다.

    `frame`: `data.daily_frame()` 출력 (trade_date, asset_id, ym, target, f_*).
    반환: [ym, asset_id, r_hat, lam] — 월말 시점 예측만.
    """
    fcols = [f"f_{name}" for name in cfg.factors]
    frame = frame.sort_values("trade_date")
    dates = np.array(sorted(frame["trade_date"].unique()))
    by_date = {d: g for d, g in frame.groupby("trade_date", sort=True)}

    # 날짜별 표준화 행렬과 타깃을 한 번만 만든다.
    Z, Y = {}, {}
    for d, g in by_date.items():
        z = _standardize_cross_section(g, fcols, cfg.winsor_q)
        if cfg.signal == "ew_composite":
            # 팩터 간 상대 가중치를 학습하지 않고 동일가중으로 고정한다. 남은
            # 자유도는 스칼라 스케일 하나뿐이고, 그것만 아래 롤링 릿지가 적합해
            # r̂를 수익률 단위로 되돌린다.
            z = z.mean(axis=1, keepdims=True)
        elif cfg.signal != "ridge":
            raise SystemExit(f"알 수 없는 signal: {cfg.signal}")
        Z[d] = z
        Y[d] = g["target"].to_numpy(dtype=float)

    # 각 월의 마지막 거래일 = 신호일
    sig = pd.Series(dates).groupby(pd.Series(dates).dt.to_period("M")).max()
    date_pos = {d: i for i, d in enumerate(dates)}

    rows = []
    for t in sig:
        i = date_pos[t]
        # 타깃이 실현된 날짜만 학습에 쓴다 (PIT)
        hi = i - cfg.fwd_days
        lo = max(0, hi - cfg.train_window_days)
        if hi <= 0:
            continue
        train = [d for d in dates[lo:hi] if d in Z]
        if len(train) < cfg.min_train_days:
            continue

        Xs, ys = [], []
        for d in train:
            ok = ~np.isnan(Y[d])
            if not ok.any():
                continue
            Xs.append(Z[d][ok])
            ys.append(Y[d][ok])
        if not Xs:
            continue
        X = np.vstack(Xs)
        y = np.concatenate(ys)
        if len(X) < cfg.min_train_rows:
            continue

        if cfg.lambda_selection == "fixed":
            lam = cfg.ridge_lambda
        else:
            grid = np.asarray(cfg.lambda_grid_kappa, dtype=float) * len(X)
            sy = y.std(ddof=0)
            ys_std = (y - y.mean()) / sy if sy > 0 else y - y.mean()
            lam = float(grid[int(np.argmin(_press(X, ys_std, grid)))])

        beta = _ridge_fit(X, y, lam)
        gt = by_date[t]
        rows.append(pd.DataFrame({
            "ym": gt["ym"].to_numpy(),
            "asset_id": gt["asset_id"].to_numpy(),
            "r_hat": Z[t] @ beta,
            "lam": lam,
        }))

    if not rows:
        raise SystemExit("예측 가능한 월이 없습니다. 학습 윈도우/데이터 기간을 확인하세요.")
    return pd.concat(rows, ignore_index=True)
