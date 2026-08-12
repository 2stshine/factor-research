"""Σ 추정 — 일별 수익률 표본공분산.

월말 관측만 쓰면 5년 창에서 T=60이라 후보 종목수 N보다 작다. 일별로 바꾸면 같은 기간에
T가 500거래일이 되어 관측이 20배 이상 늘어난다. 추정은 일별 스케일로 하고 거래일 21일
기준으로 월 환산한다.

`N > T` 여도 표본공분산은 Gram 행렬이라 PSD이고, 제약(Σw=1, 0≤w≤u)이 실행가능 영역을
컴팩트하게 만들므로 QP는 그대로 풀린다. Σ의 역행렬은 쓰지 않는다.

시점 t의 신호에는 t 월말까지의 일별 관측만 사용한다(PIT).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_MONTH = 21


def estimate_cov(
    daily: pd.DataFrame,
    signal_month: pd.Period,
    candidates: list[int],
    window_days: int,
    min_days: int,
    min_obs_ratio: float = 0.8,
) -> tuple[list[int], np.ndarray]:
    """반환: (사용된 asset_id 순서, 월 스케일 Σ). 관측이 부족한 종목은 제외한다.

    `daily`: index=trade_date, columns=asset_id 인 일별 수익률 행렬.
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
    return list(block.columns), (Xc.T @ Xc / len(Xc)) * TRADING_DAYS_PER_MONTH
