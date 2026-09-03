"""일별 팩터값 — ridge 학습 표본을 매 거래일로 확장하기 위한 입력.

## 새 팩터를 추가하려면

`DAILY_FACTOR_DEFS`에 한 줄 추가하면 된다. 함수는 `DailyInputs`를 받아
**(거래일 × 종목) wide DataFrame**을 반환한다.

```python
def _my_factor(ctx: DailyInputs) -> pd.DataFrame:
    return -ctx.returns.rolling(60).mean()      # 부호 적용 필수

DAILY_FACTOR_DEFS["my_factor"] = _my_factor
```

**부호 규약** — 반환값은 엔진의 `f_<name>` 컬럼과 같아야 한다. 엔진은
`compute() * predicted_sign`으로 저장하므로 **값이 클수록 예측 고수익**이어야 한다.
`predicted_sign = −1`인 팩터는 부호를 뒤집어 반환한다.

**정의가 없는 팩터**는 자동으로 월말 asof 경로를 탄다(`data.daily_frame`). 파이프라인이
깨지지는 않지만 그 팩터만 월 단위 계단식이 되므로, `build_cache()`가 어느 팩터가 어느
경로인지 출력한다.

**달력월 기준 정의 주의** — 엔진 정의가 `date_trunc('month')` 파티션이면 매일 쓸 때
월초엔 며칠치, 월말엔 한 달치가 되어 "오늘이 월 며칠째인가"를 학습하게 된다. 동등한
롤링 창으로 재정의해야 한다.

이 재정의는 전략 레이어에만 존재한다. `gold.factor`·`engine/`은 건드리지 않으며,
연결은 `silver.connect(read_only=True)`라 쓰기가 불가능하다.

    uv run python -m strategies.daily_factors price     # 시총·주가 적재 (RDS)
    uv run python -m strategies.daily_factors build     # 팩터 계산·캐시 (로컬)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine import silver
from strategies import daily as daily_returns
from strategies import gold

PRICE_CACHE = REPO_ROOT / ".cache" / "daily_price.parquet"
CACHE = REPO_ROOT / ".cache" / "daily_factors.parquet"

PRICE_SQL = """
SELECT p.asset_id,
       p.trade_date,
       p.market_cap::double precision AS market_cap,
       p.adj_close::double precision  AS adj_close
FROM public.price_daily p
JOIN public.asset a ON a.asset_id = p.asset_id
JOIN public.dq_run q
  ON q.run_id = p.quality_run_id AND q.status = 'CERTIFIED'
WHERE p.source = 'KRX'
  AND a.exchange = 'KRX'
  AND a.asset_type = 'stock'
  AND p.market IN ('KOSPI', 'KOSDAQ')
  AND p.market_cap > 0
  AND p.adj_close > 0
  AND p.trade_date >= %(lo)s
  AND p.trade_date < %(hi)s
"""


@dataclass
class DailyInputs:
    """일별 팩터 정의가 쓸 수 있는 입력.

    `returns`: (거래일 × 종목) `adj_close` 기반 PIT-safe 가격수익률
    `price`:   (거래일 × 종목) `market_cap / adj_close` = 분할조정 주식수 대용.
               `daily_price.parquet`이 없으면 None.
    """

    returns: pd.DataFrame
    share_base: pd.DataFrame | None


FactorDef = Callable[[DailyInputs], pd.DataFrame]


# --- 일별 정의 (부호 적용 완료: 값이 클수록 예측 고수익) -------------------------

def _realized_volatility_252d(ctx: DailyInputs) -> pd.DataFrame:
    return -ctx.returns.rolling(252, min_periods=126).std()


def _max_daily_return_1m(ctx: DailyInputs) -> pd.DataFrame:
    """엔진은 달력월 max. 매일 쓰려면 동등한 21행 롤링으로 재정의한다."""
    return -ctx.returns.rolling(21, min_periods=10).max()


def _net_equity_issuance_price_adjusted_12m(ctx: DailyInputs) -> pd.DataFrame:
    """엔진은 월 인덱스 shift(12). 매일 쓰려면 252거래일 롤링으로 재정의한다."""
    if ctx.share_base is None:
        raise SystemExit(
            "이 팩터는 daily_price 캐시가 필요합니다. "
            "`uv run python -m strategies.daily_factors price` 먼저 실행하세요."
        )
    base = ctx.share_base
    prior = base.shift(252)
    return -(base / prior.where(prior > 0) - 1.0)


DAILY_FACTOR_DEFS: dict[str, FactorDef] = {
    "realized_volatility_252d": _realized_volatility_252d,
    "max_daily_return_1m": _max_daily_return_1m,
    "net_equity_issuance_price_adjusted_12m": _net_equity_issuance_price_adjusted_12m,
}


# --- 적재·계산 ------------------------------------------------------------------

def fetch_price(start_year: int = 1997, verbose: bool = True) -> Path:
    """일별 시가총액·수정주가 적재 (주식수 기반 팩터용)."""
    end_year = pd.Timestamp.today().year
    frames = []
    with silver.connect(read_only=True) as conn:
        for year in range(start_year, end_year + 1):
            params = {"lo": pd.Timestamp(year=year, month=1, day=1).date(),
                      "hi": pd.Timestamp(year=year + 1, month=1, day=1).date()}
            part = silver.read_frame(conn, PRICE_SQL, params)
            if part.empty:
                continue
            frames.append(part)
            if verbose:
                print(f"  {year}: {len(part):,}행", flush=True)
    d = pd.concat(frames, ignore_index=True)
    d["trade_date"] = pd.to_datetime(d["trade_date"])
    d["asset_id"] = d["asset_id"].astype("int64")
    PRICE_CACHE.parent.mkdir(exist_ok=True)
    d.to_parquet(PRICE_CACHE, index=False)
    if verbose:
        print(f"\n저장: {PRICE_CACHE}  ({len(d):,}행)")
    return PRICE_CACHE


def _load_inputs(verbose: bool = True) -> DailyInputs:
    r = daily_returns.load_daily()
    share = None
    if PRICE_CACHE.exists():
        p = pd.read_parquet(PRICE_CACHE)
        p["share_base"] = p["market_cap"] / p["adj_close"]
        share = p.pivot_table(index="trade_date", columns="asset_id",
                              values="share_base").sort_index()
        share = share.reindex(index=r.index, columns=r.columns)
    if verbose:
        print(f"  일별 feature 수익률 {r.shape[0]:,}일 × {r.shape[1]:,}종목"
              f"{'  / 주식수 로드' if share is not None else '  / 주식수 없음'}")
    return DailyInputs(returns=r, share_base=share)


def build_cache(factors: tuple[str, ...] | None = None, verbose: bool = True) -> Path:
    """gold 팩터 중 일별 정의가 있는 것을 계산해 long 형식으로 캐시한다."""
    names = tuple(factors) if factors else gold.approved_factors()
    if not names:
        raise SystemExit(
            "팩터 목록이 비었습니다. `uv run python -m strategies.gold`로 갱신하세요."
        )
    if verbose:
        print(f"[1/3] 대상 팩터 {len(names)}개: {', '.join(names)}")

    ctx = _load_inputs(verbose)

    computed, fallback = {}, []
    for name in names:
        fn = DAILY_FACTOR_DEFS.get(name)
        if fn is None:
            fallback.append(name)
            continue
        computed[f"f_{name}"] = fn(ctx)
    if verbose:
        print(f"[2/3] 일별 계산 {len(computed)}개"
              f"{'  / 월말 asof 대체 ' + str(len(fallback)) + '개: ' + ', '.join(fallback) if fallback else ''}")

    if not computed:
        raise SystemExit(
            "일별 정의가 있는 팩터가 하나도 없습니다. DAILY_FACTOR_DEFS를 확인하세요."
        )

    out = pd.DataFrame({col: df.stack() for col, df in computed.items()})
    out.index.names = ["trade_date", "asset_id"]
    out = out.reset_index()
    out["asset_id"] = out["asset_id"].astype("int64")
    for c in out.columns:
        if out[c].dtype == "float64":
            out[c] = out[c].astype("float32")
    fcols = [c for c in out.columns if c.startswith("f_")]
    out = out.dropna(how="all", subset=fcols)

    CACHE.parent.mkdir(exist_ok=True)
    out.to_parquet(CACHE, index=False)
    if verbose:
        print(f"[3/3] 캐시 저장: {CACHE}")
        print(f"  {len(out):,}행 / {out['asset_id'].nunique():,}종목 / "
              f"{out['trade_date'].nunique():,}거래일")
        if fallback:
            print(f"\n  ⚠ 월말 asof로 처리되는 팩터: {', '.join(fallback)}")
            print("    일별 정의를 추가하려면 DAILY_FACTOR_DEFS에 등록하세요.")
    return CACHE


def load_daily_factors() -> pd.DataFrame:
    if not CACHE.exists():
        raise SystemExit(
            f"일별 팩터 캐시가 없습니다: {CACHE}\n"
            "먼저 `uv run python -m strategies.daily_factors build`로 생성하세요."
        )
    return pd.read_parquet(CACHE)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "price":
        fetch_price()
    else:
        build_cache()
