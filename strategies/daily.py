"""Silver 일별 총수익률 적재 — 공분산 추정용.

월말 패널(엔진 캐시)만으로는 공분산 추정창이 60개월(T=60)뿐이라 후보 종목수 N(150~190)보다
작아 표본공분산이 특이해진다. 일별 수익률을 쓰면 같은 5년 창에서 T가 1,200일 이상이 되어
N/T가 2.8 → 0.13 수준으로 떨어진다.

엔진(`engine/`)은 인증 게이트 코드이므로 수정하지 않고, 연결 경로(`silver.connect`)만
재사용한다. 인증 필터는 엔진의 `PRICE_SNAPSHOT_SQL`과 동일하게 맞춘다
(`dq_run.status='CERTIFIED'`, KRX, KOSPI/KOSDAQ, stock).

    uv run python -m strategies.daily          # 캐시 생성 (RDS 필요)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine import silver

CACHE = REPO_ROOT / ".cache" / "daily_returns.parquet"
START_YEAR = 1997

# lag()로 직전 종가를 잡으므로 연도 경계에서 첫 거래일의 수익률이 끊기지 않도록
# 하한을 조금 앞당겨 조회한 뒤 잘라낸다.
DAILY_SQL = """
WITH certified AS (
    SELECT p.asset_id,
           p.trade_date,
           p.total_return_close,
           lag(p.total_return_close) OVER (
               PARTITION BY p.asset_id ORDER BY p.trade_date
           ) AS prior_close
    FROM public.price_daily p
    JOIN public.asset a ON a.asset_id = p.asset_id
    JOIN public.dq_run q
      ON q.run_id = p.quality_run_id AND q.status = 'CERTIFIED'
    WHERE p.source = 'KRX'
      AND a.exchange = 'KRX'
      AND a.asset_type = 'stock'
      AND p.market IN ('KOSPI', 'KOSDAQ')
      AND p.trade_date >= %(lo)s
      AND p.trade_date < %(hi)s
)
SELECT asset_id, trade_date,
       total_return_close / prior_close - 1.0 AS r
FROM certified
WHERE prior_close > 0
  AND total_return_close > 0
  AND trade_date >= %(keep)s
"""


def build_cache(start_year: int = START_YEAR, verbose: bool = True) -> Path:
    """연도별로 나눠 받아 (거래일 × 종목) 행렬로 캐시한다."""
    end_year = pd.Timestamp.today().year
    frames = []
    with silver.connect(read_only=True) as conn:
        for year in range(start_year, end_year + 1):
            keep = pd.Timestamp(year=year, month=1, day=1)
            params = {
                "lo": (keep - pd.Timedelta(days=30)).date(),   # lag 보존용 여유
                "hi": pd.Timestamp(year=year + 1, month=1, day=1).date(),
                "keep": keep.date(),
            }
            part = silver.read_frame(conn, DAILY_SQL, params)
            if part.empty:
                continue
            frames.append(part)
            if verbose:
                print(f"  {year}: {len(part):,}행", flush=True)
    if not frames:
        raise SystemExit("일별 수익률을 가져오지 못했습니다.")

    long = pd.concat(frames, ignore_index=True)
    long["trade_date"] = pd.to_datetime(long["trade_date"])
    wide = long.pivot_table(index="trade_date", columns="asset_id", values="r")
    wide = wide.sort_index().astype("float32")
    wide.columns = wide.columns.astype("int64")

    CACHE.parent.mkdir(exist_ok=True)
    wide.to_parquet(CACHE)
    if verbose:
        print(f"\n캐시 저장: {CACHE}")
        print(f"  {wide.shape[0]:,}거래일 × {wide.shape[1]:,}종목 "
              f"({wide.index.min().date()} ~ {wide.index.max().date()})")
    return CACHE


def load_daily() -> pd.DataFrame:
    """일별 수익률 행렬 (index=trade_date, columns=asset_id)."""
    if not CACHE.exists():
        raise SystemExit(
            f"일별 수익률 캐시가 없습니다: {CACHE}\n"
            "먼저 `uv run python -m strategies.daily`로 생성하세요 (RDS 필요)."
        )
    return pd.read_parquet(CACHE)


if __name__ == "__main__":
    build_cache()
