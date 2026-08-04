"""PIT 재무 패널.

T0.3 flow/stock 타입 태깅이 이 모듈의 존재 이유다.
`Q4 = FY − (Q1+Q2+Q3)` 를 재무상태표 지표에 적용하면 삼성전자 2024 자산총계가
**−933조**(정답 514조)가 나오는데 에러 없이 통과한다. 그리고 이 버그는
`TTM = Q1+Q2+Q3+Q4 = FY` 항등식 검사를 **100% 통과한다** — 데이터에 Q4 행이 없어
Q4 를 뺄셈으로 정의하는 순간 항등식이 정의상 참이 되기 때문이다.
타입 태깅만이 실제로 잡는다.
"""
from __future__ import annotations

import glob
import json
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

# T0.3 타입 태깅 — 이 분리가 없으면 조용히 틀린다
FLOW = frozenset({"revenue", "operating_income", "pretax_income",
                  "net_income", "comprehensive_income"})
STOCK = frozenset({"total_assets", "current_assets", "noncurrent_assets",
                   "total_liabilities", "current_liabilities", "noncurrent_liabilities",
                   "total_equity", "capital_stock", "retained_earnings"})

METRIC_MAP = {
    "자산총계": "total_assets", "유동자산": "current_assets", "비유동자산": "noncurrent_assets",
    "부채총계": "total_liabilities", "유동부채": "current_liabilities",
    "비유동부채": "noncurrent_liabilities", "자본총계": "total_equity",
    "자본금": "capital_stock", "이익잉여금": "retained_earnings",
    "매출액": "revenue", "영업이익": "operating_income", "영업이익(손실)": "operating_income",
    "법인세차감전 순이익": "pretax_income",
    "당기순이익(손실)": "net_income", "당기순이익": "net_income",
    "총포괄손익": "comprehensive_income",
}
REPRT = {"11011": ("FY", 4), "11013": ("Q1", 1), "11012": ("Q2", 2), "11014": ("Q3", 3)}
_DT = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})")


def _period_end(dt: str | None) -> date | None:
    """thstrm_dt 에서 회계기간 종료일. 비12월 결산법인이 있어 bsns_year 로 가정하면 안 된다.
    형식 2종: '2025.04.01 ~ 2026.03.31'(기간형), '2026.03.31 현재'(시점형) — 둘 다 마지막 날짜."""
    hits = _DT.findall(dt or "")
    if not hits:
        return None
    y, m, d = hits[-1]
    try:
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def _amount(s: str | None) -> float | None:
    s = (s or "").replace(",", "").strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def build(bronze_dir: str, *, verbose: bool = True) -> pd.DataFrame:
    """bronze DART JSON → PIT 재무 패널 (분기 flow 단독값 + TTM, stock 시점값)."""
    files = glob.glob(f"{bronze_dir}/financials/dart/year=*/corp=*/*.json")
    if verbose:
        print(f"[fund] DART {len(files):,}개 파싱...", flush=True)

    recs = []
    for f in files:
        reprt = f.rsplit("/", 1)[1][:5]
        if reprt not in REPRT:
            continue
        fp, qn = REPRT[reprt]
        ticker = f.split("corp=")[1].split("/")[0]
        try:
            rows = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for r in rows:
            met = METRIC_MAP.get(r.get("account_nm"))
            if not met:
                continue
            v = _amount(r.get("thstrm_amount"))
            pe = _period_end(r.get("thstrm_dt"))
            if v is None or pe is None:
                continue
            rc = (r.get("rcept_no") or "").strip()
            filed = None
            if len(rc) >= 8 and rc[:8].isdigit():
                try:
                    filed = date(int(rc[:4]), int(rc[4:6]), int(rc[6:8]))
                except ValueError:
                    pass
            # PIT: 접수일 +1일. 없으면 법정기한.
            avail = filed + timedelta(days=1) if filed else pe + timedelta(days=90 if fp == "FY" else 45)
            recs.append((ticker, r.get("fs_div"), pe, qn, met, v, avail, rc))

    df = pd.DataFrame(recs, columns=["ticker", "fs_type", "period_end", "qn",
                                     "metric", "value", "available_date", "revision_key"])
    # revision_key 최신 1건 (운영 스키마의 DISTINCT ON 규칙과 동일)
    df = df.sort_values(["ticker", "fs_type", "period_end", "metric", "available_date", "revision_key"])
    df = df.drop_duplicates(["ticker", "fs_type", "period_end", "metric"], keep="last")
    # CFS 우선, 없으면 OFS
    df["_pri"] = (df["fs_type"] == "CFS").astype(int)
    df = df.sort_values(["ticker", "period_end", "metric", "_pri"])
    df = df.drop_duplicates(["ticker", "period_end", "metric"], keep="last")

    df["fy"] = pd.to_datetime(df["period_end"]).dt.year
    w = df.pivot_table(index=["ticker", "fy", "qn", "period_end", "available_date"],
                       columns="metric", values="value", aggfunc="last").reset_index()

    flow_cols = [c for c in w.columns if c in FLOW]
    q = w.sort_values(["ticker", "fy", "qn"]).reset_index(drop=True)

    # ---- Q4 역산: FY 행의 flow 컬럼에서만 Q1+Q2+Q3 을 뺀다 ----
    # stock 컬럼(자산·부채·자본)은 시점값이므로 FY 값을 그대로 둔다.
    # 이 한 줄의 구분이 삼성 자산총계를 −933조에서 514조로 되돌린다.
    q123 = (q[q["qn"].isin([1, 2, 3])]
            .groupby(["ticker", "fy"])[flow_cols]
            .agg(["sum", "count"]))
    is_fy = q["qn"] == 4
    key = pd.MultiIndex.from_arrays([q["ticker"], q["fy"]])
    for c in flow_cols:
        s = q123[(c, "sum")].reindex(key).values
        n = q123[(c, "count")].reindex(key).values
        # 3개 분기가 모두 있을 때만 역산 (하나라도 없으면 FY 값 유지)
        derived = np.where(is_fy.values & (n == 3), q[c].values - s, q[c].values)
        q[c] = derived

    q = q.sort_values(["ticker", "period_end"]).reset_index(drop=True)
    for c in flow_cols:                               # TTM: flow 만 4분기 합
        q[c + "_ttm"] = q.groupby("ticker")[c].transform(lambda s: s.rolling(4, min_periods=4).sum())
    q["available_date"] = pd.to_datetime(q["available_date"])

    if verbose:
        neg = int((q.get("total_assets", pd.Series(dtype=float)) < 0).sum())
        print(f"[fund] {len(q):,}행 / {q['ticker'].nunique():,}종목 · "
              f"자산총계 음수 {neg}건 {'✅' if neg == 0 else '❌ T0.3 실패'}")
    return q


def attach(monthly: pd.DataFrame, fund: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """PIT 머지 — 월말 시점에 '실제로 알 수 있었던' 최신 재무만 붙인다.

    available_date 대신 period_end 로 조인하면 look-ahead 다. merge_asof backward 가 그걸 막는다.
    """
    have = [c for c in cols if c in fund.columns]
    # merge_asof 는 키 dtype 이 정확히 같아야 한다 (datetime64[ns] vs [s] 불일치 방지)
    left = (monthly.assign(me_date=pd.to_datetime(monthly["trade_date"]).astype("datetime64[ns]"))
            .sort_values("me_date"))
    right = fund[["ticker", "available_date"] + have].rename(columns={"ticker": "Code"}).copy()
    right["available_date"] = pd.to_datetime(right["available_date"]).astype("datetime64[ns]")
    right = right.sort_values("available_date")
    return pd.merge_asof(left, right, left_on="me_date", right_on="available_date",
                         by="Code", direction="backward")
