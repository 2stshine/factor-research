"""2단계 — 제약부 mean-variance QP (long-only + 캡 + L1 턴오버).

    max_w  wᵀμ − c·wᵀΣw − γ‖w − w_prev‖₁
    s.t.   Σw = 1,  0 ≤ w ≤ u

턴오버 페널티를 목적함수에 넣어 cost-aware하게 만든다(README: 턴오버 A vs B). closed-form이
없으므로 cvxpy(+OSQP/CLARABEL)로 푼다.
"""
from __future__ import annotations

import warnings

import cvxpy as cp
import numpy as np


def solve_weights(
    mu: np.ndarray,
    Sigma: np.ndarray,
    w_prev: np.ndarray,
    c: float,
    gamma: float,
    u: float,
) -> np.ndarray | None:
    """비중 벡터 w를 반환. 실패 시 None."""
    n = len(mu)
    if n == 0:
        return None
    w = cp.Variable(n)
    objective = (
        mu @ w
        - c * cp.quad_form(w, cp.psd_wrap(Sigma))
        - gamma * cp.norm1(w - w_prev)
    )
    constraints = [cp.sum(w) == 1, w >= 0, w <= u]
    prob = cp.Problem(cp.Maximize(objective), constraints)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            prob.solve(solver=cp.OSQP, verbose=False)
        except (cp.error.SolverError, Exception):
            try:
                prob.solve(solver=cp.CLARABEL, verbose=False)
            except Exception:
                return None
    if w.value is None or prob.status not in ("optimal", "optimal_inaccurate"):
        return None
    weights = np.asarray(w.value).flatten()
    weights = np.clip(weights, 0.0, None)     # 수치 음수 정리
    s = weights.sum()
    return weights / s if s > 0 else None
