"""캐시된 엔진 패널을 읽어 전략 입력 프레임으로 변환한다.

엔진 `scripts/run.py build`가 만든 `.cache/panel.pkl`(Panel: monthly DataFrame + dead
+ meta)을 재사용한다. 여기서는 gold 팩터 컬럼(f_<name>)·forward return·유니버스·수익
레벨만 추린다. 값 계산·검증은 상위 엔진의 책임이다.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))  # Panel 언피클에 engine 임포트 필요

from strategies.config import StrategyConfig

PANEL_CACHE = REPO_ROOT / ".cache" / "panel.pkl"


def load_panel():
    """엔진이 만든 월말 PIT 패널 캐시를 로드한다."""
    if not PANEL_CACHE.exists():
        raise SystemExit(
            f"패널 캐시가 없습니다: {PANEL_CACHE}\n"
            "먼저 `uv run python scripts/run.py build`로 인증 캐시를 생성하세요."
        )
    import engine.panel  # noqa: F401  (pickle이 참조하는 클래스 등록)

    with PANEL_CACHE.open("rb") as fh:
        return pickle.load(fh)


def strategy_frame(panel, cfg: StrategyConfig) -> pd.DataFrame:
    """long 형식 전략 프레임. 컬럼: asset_id, Code, ym, ret_level, market_cap,
    adv20, target, f_<factor>... . in_universe(+투자가능) 필터 적용."""
    df = panel.monthly
    fcols = [f"f_{name}" for name in cfg.factors]
    missing = [c for c in fcols if c not in df.columns]
    if missing:
        raise SystemExit(
            f"패널에 팩터 컬럼이 없습니다: {missing}. "
            "build 시 해당 팩터가 등록됐는지 확인하세요."
        )
    if cfg.target_col not in df.columns:
        raise SystemExit(f"패널에 타깃 컬럼이 없습니다: {cfg.target_col}")

    keep = ["asset_id", "Code", "ym", cfg.return_level_col, "market_cap",
            "adv20", "in_universe", cfg.target_col] + fcols
    out = df[keep].copy()
    out = out.rename(columns={cfg.return_level_col: "ret_level",
                              cfg.target_col: "target"})
    out = out[out["in_universe"].fillna(False)]
    if cfg.require_investable:
        out = out[out["adv20"].fillna(0) > 0]
    out["ym"] = out["ym"].astype("period[M]")
    return out.sort_values(["ym", "asset_id"]).reset_index(drop=True)


def daily_frame(panel, cfg: StrategyConfig, verbose: bool = True) -> pd.DataFrame:
    """일별 학습·예측 프레임.

    컬럼: trade_date, asset_id, ym, f_<factor>..., target

    - 팩터: 일별 캐시(`daily_factors`)의 롤링 정의 값을 쓴다. 재무 팩터처럼 일별 값이
      없는 것은 **직전 월말 값**을 그 이후 날짜에 붙인다(PIT — 미래를 보지 않는다).
    - 유니버스: 직전 월말의 `in_universe`·`adv20` 판정을 그 이후 날짜에 적용한다.
    - target: `fwd_days` 거래일 뒤까지의 누적 총수익률.
    """
    from strategies import daily as daily_returns
    from strategies import daily_factors as df_mod

    fac = df_mod.load_daily_factors()
    # parquet 왕복에서 해상도가 달라질 수 있어 merge_asof 전에 통일한다.
    fac["trade_date"] = pd.to_datetime(fac["trade_date"]).astype("datetime64[ns]")
    fcols = [f"f_{name}" for name in cfg.factors]

    # --- 일별 캐시에 없는 팩터·유니버스는 직전 월말 값을 asof로 붙인다 ---
    monthly = panel.monthly.copy()
    monthly["ym"] = monthly["ym"].astype("period[M]")
    monthly["month_end"] = (monthly["ym"].dt.to_timestamp(how="end")
                            .dt.normalize().astype("datetime64[ns]"))
    # 일별 정의가 없는 팩터는 직전 월말 값을 쓴다(월 단위 계단식). 조용히 넘어가면
    # 알아채기 어려우므로 명시한다.
    from_month = [c for c in fcols if c not in fac.columns]
    absent = [c for c in from_month if c not in monthly.columns]
    if absent:
        raise SystemExit(
            f"팩터 컬럼이 일별 캐시에도 월말 패널에도 없습니다: {absent}\n"
            "gold에 새로 승격된 팩터라면 엔진 패널을 다시 만드세요:\n"
            "  uv run python scripts/run.py build\n"
            "일별 정의를 쓰려면 daily_factors.DAILY_FACTOR_DEFS에 등록 후\n"
            "  uv run python -m strategies.daily_factors build"
        )
    if from_month and verbose:
        print(f"  [daily_frame] 월말 asof 적용: {', '.join(c[2:] for c in from_month)}")
    mcols = ["asset_id", "month_end", "in_universe", "adv20"] + from_month
    m = (monthly[mcols].sort_values("month_end")
         .rename(columns={"month_end": "asof_date"}))

    fac = fac.sort_values("trade_date")
    out = pd.merge_asof(
        fac, m, left_on="trade_date", right_on="asof_date", by="asset_id",
        direction="backward", allow_exact_matches=True,
    )

    out = out[out["in_universe"].fillna(False)]
    if cfg.require_investable:
        out = out[out["adv20"].fillna(0) > 0]

    # --- target: fwd_days 거래일 뒤까지의 누적 수익률 (상폐는 terminal 부여) ---
    r = daily_returns.load_daily()
    level = (1.0 + r).cumprod()
    fwd = level.shift(-cfg.fwd_days) / level - 1.0

    # 상폐·비활성 종목이 forward 창 안에서 사라지면 수익률이 NaN이 되어 학습에서 빠진다.
    # 그대로 두면 모델이 "무엇이 상폐를 예측하는가"를 배울 기회가 없는데 백테스트는 그
    # 손실을 그대로 맞는다(엔진 `fwd_mid`가 terminal -0.50으로 막는 바로 그 함정).
    # 엔진과 같은 규칙으로 terminal을 부여한다.
    valid = r.notna().to_numpy()
    n_days = len(r)
    has_obs = valid.any(axis=0)
    last_pos = n_days - 1 - valid[::-1].argmax(axis=0)      # 종목별 마지막 관측 위치
    row = np.arange(n_days)[:, None]
    dies_in_window = (row <= last_pos[None, :]) & (last_pos[None, :] < row + cfg.fwd_days)
    dead_ids = set(getattr(panel, "dead", pd.Series(dtype=float)).index)
    is_dead = np.array([a in dead_ids for a in r.columns]) & has_obs
    terminal_mask = dies_in_window & is_dead[None, :]

    fwd_v = fwd.to_numpy()
    fwd_v = np.where(terminal_mask & np.isnan(fwd_v), cfg.terminal_return, fwd_v)
    fwd = pd.DataFrame(fwd_v, index=fwd.index, columns=fwd.columns)

    tgt = fwd.stack().rename("target").reset_index()
    tgt.columns = ["trade_date", "asset_id", "target"]
    out = out.merge(tgt, on=["trade_date", "asset_id"], how="left")

    out["ym"] = out["trade_date"].dt.to_period("M")
    keep = ["trade_date", "asset_id", "ym", "target"] + fcols
    out = out[[c for c in keep if c in out.columns]]
    return out.sort_values(["trade_date", "asset_id"]).reset_index(drop=True)


