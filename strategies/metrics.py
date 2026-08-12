"""월별 수익률 시계열 성과 지표."""
from __future__ import annotations

import numpy as np
import pandas as pd


def summarize(returns: pd.Series, periods_per_year: int = 12) -> dict:
    r = returns.dropna().astype(float)
    n = len(r)
    if n == 0:
        return {}
    equity = (1 + r).cumprod()
    total = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (periods_per_year / n) - 1
    vol = r.std(ddof=1) * np.sqrt(periods_per_year)
    sharpe = (r.mean() * periods_per_year) / vol if vol > 0 else np.nan
    peak = equity.cummax()
    mdd = (equity / peak - 1).min()
    return {
        "months": n,
        "total_return": total,
        "cagr": cagr,
        "ann_vol": vol,
        "sharpe": sharpe,
        "mdd": mdd,
        "hit_rate": float((r > 0).mean()),
    }
