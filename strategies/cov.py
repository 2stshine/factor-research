"""Σ 추정 — PIT-safe `adj_close` 일별 가격수익률 + Ledoit-Wolf 축소.

월말 관측만 쓰면 5년 창에서 T=60이라 후보 종목수 N보다 작다. 일별로 바꾸면 같은 기간에
T가 500거래일이 되어 관측이 20배 이상 늘어난다. 추정은 일별 스케일로 하고 거래일 21일
기준으로 월 환산한다.

**표본공분산만으로는 부족하다.** `N > T`여도 PSD라 QP는 풀리지만, 랭크가 T로 막혀 있어
`N − T`개 방향의 추정 위험이 **정확히 0**이 된다. 옵티마이저는 그 방향을 공짜 점심으로
쓴다. 후보 2,049종목 / 창 500일에서 실측한 결과 포트폴리오 예측 변동성 9.9%에 실현
36.4% — 3.7배 과소평가였다. 제약(0≤w≤u)이 방어선이긴 하지만(Jagannathan-Ma 2003) 이
정도 N/T에서는 부족하다.

Ledoit-Wolf 축소로 작은 고유값을 들어올려 공짜 방향을 없앤다. 축소 대상은 **상수상관
행렬**이다 — 축소강도 δ는 기대 Frobenius 손실을 최소화하는 값이 닫힌형으로 나오므로
사람이 고르는 숫자가 아니다.

    Σ* = δ·F + (1−δ)·S,   F_ij = r̄·σ_i·σ_j (i≠j), F_ii = s_ii

단위행렬 대신 상수상관을 쓰는 이유: 단위행렬로 축소하면 상관이 0으로 끌려가 롱온리
포트폴리오의 **체계적 위험을 오히려 더 과소평가**한다. 상수상관은 평균 상관을 보존한 채
행렬만 조건화한다.

시점 t의 신호에는 t 월말까지의 일별 관측만 사용한다(PIT).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_MONTH = 21


def ledoit_wolf_constant_correlation(X: np.ndarray) -> tuple[np.ndarray, float]:
    """Ledoit-Wolf(2003) 상수상관 축소. 반환: (축소된 공분산, 축소강도 δ).

    `X`: (T × N) 평균제거된 수익률 행렬.
    """
    T, N = X.shape
    S = (X.T @ X) / T
    var = np.clip(np.diag(S).copy(), 1e-18, None)
    sd = np.sqrt(var)

    # 상수상관 타깃 F: 대각은 표본분산 그대로, 비대각은 평균상관 × σ_i σ_j
    corr = S / np.outer(sd, sd)
    off_sum = corr.sum() - np.trace(corr)
    r_bar = off_sum / (N * (N - 1)) if N > 1 else 0.0
    F = r_bar * np.outer(sd, sd)
    np.fill_diagonal(F, var)

    # π̂ = Σ_ij Var[x_i x_j] 추정. (1/T)Σ_t x_ti²x_tj² 를 행렬곱으로 한 번에 얻는다.
    X2 = X ** 2
    pi_matrix = (X2.T @ X2) / T - S ** 2
    pi_hat = float(pi_matrix.sum())

    # ρ̂ — 타깃과 표본의 공분산항. ϑ̂_ii,ij = [(X³)ᵀX/T]_ij − s_ii·s_ij 로 정리된다.
    theta = ((X ** 3).T @ X) / T - var[:, None] * S
    ratio = sd[None, :] / sd[:, None]              # ratio_ij = σ_j/σ_i
    cross = ratio * theta
    np.fill_diagonal(cross, 0.0)
    rho_hat = float(np.trace(pi_matrix) + r_bar * cross.sum())

    gamma_hat = float(((F - S) ** 2).sum())
    if gamma_hat <= 0:
        return S, 0.0
    delta = float(np.clip((pi_hat - rho_hat) / gamma_hat / T, 0.0, 1.0))
    return delta * F + (1.0 - delta) * S, delta


def estimate_cov(
    daily: pd.DataFrame,
    signal_month: pd.Period,
    candidates: list[int],
    window_days: int,
    min_days: int,
    min_obs_ratio: float = 0.8,
    shrinkage: str = "ledoit_wolf",
) -> tuple[list[int], np.ndarray]:
    """반환: (사용된 asset_id 순서, 월 스케일 Σ). 관측이 부족한 종목은 제외한다.

    `daily`: index=trade_date, columns=asset_id 인 `adj_close` 일별 가격수익률 행렬.
    `signal_month` 월말까지의 마지막 `window_days` 거래일을 창으로 쓴다.
    """
    hist = daily.loc[daily.index <= signal_month.to_timestamp(how="end")]
    if len(hist) < min_days:
        return [], np.empty((0, 0))
    win = hist.iloc[-window_days:]

    cols = [a for a in candidates if a in win.columns]
    if len(cols) < 2:
        return [], np.empty((0, 0))
    block = win[cols]

    # 상장 전·거래정지 등으로 결측이 많은 종목은 제외한다. 완전 히스토리를 요구하면
    # 최근 상장 종목이 전부 빠지므로 관측 비율 기준으로 거른다.
    enough = (block.notna().mean() >= min_obs_ratio).to_numpy()
    block = block.loc[:, enough]
    if block.shape[1] < 2:
        return [], np.empty((0, 0))

    # 남은 결측은 0(=평균 수익률)으로 채운다. 거래정지 구간을 "움직임 없음"으로 보는
    # 셈이라 변동성을 다소 낮추지만, 해당 종목을 통째로 버리는 것보다 낫다.
    block = block.dropna(axis=0, how="all").fillna(0.0)
    if len(block) < min_days:
        return [], np.empty((0, 0))

    X = block.to_numpy(dtype=float)
    Xc = X - X.mean(axis=0)
    if shrinkage == "ledoit_wolf":
        cov, _delta = ledoit_wolf_constant_correlation(Xc)
    elif shrinkage == "none":
        cov = (Xc.T @ Xc) / len(Xc)
    else:
        raise SystemExit(f"알 수 없는 shrinkage: {shrinkage}")
    return list(block.columns), cov * TRADING_DAYS_PER_MONTH
