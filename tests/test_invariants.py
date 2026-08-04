"""엔진의 핵심 불변식. 이게 깨지면 모든 팩터 결과가 조용히 틀린다.

  uv run python -m pytest tests/ -q
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import fundamentals as FU
from engine.factors import Factor, Registry


# ---------------------------------------------------------------- T0.3
def test_stock_metric_never_negative_after_q4_derivation():
    """자산총계에 Q4 역산이 적용되면 −933조가 나온다. flow/stock 분리가 그걸 막는다."""
    rows = []
    for qn, pe, rev, ta in [(1, "2024-03-31", 71.9, 470.9),
                            (2, "2024-06-30", 74.1, 485.8),
                            (3, "2024-09-30", 79.1, 491.3),
                            (4, "2024-12-31", 300.9, 514.5)]:  # FY 는 매출 누적, 자산은 시점
        rows.append({"ticker": "005930", "fy": 2024, "qn": qn, "period_end": pe,
                     "available_date": pd.Timestamp(pe) + pd.Timedelta(days=45),
                     "revenue": rev, "total_assets": ta})
    w = pd.DataFrame(rows)

    flow_cols = [c for c in w.columns if c in FU.FLOW]
    q = w.sort_values(["ticker", "fy", "qn"]).reset_index(drop=True)
    q123 = q[q["qn"].isin([1, 2, 3])].groupby(["ticker", "fy"])[flow_cols].agg(["sum", "count"])
    is_fy = q["qn"] == 4
    key = pd.MultiIndex.from_arrays([q["ticker"], q["fy"]])
    for c in flow_cols:
        s = q123[(c, "sum")].reindex(key).values
        n = q123[(c, "count")].reindex(key).values
        q[c] = np.where(is_fy.values & (n == 3), q[c].values - s, q[c].values)

    fy = q[q["qn"] == 4].iloc[0]
    assert fy["total_assets"] == pytest.approx(514.5), "stock 지표는 FY 값 그대로여야 한다"
    assert fy["revenue"] == pytest.approx(300.9 - (71.9 + 74.1 + 79.1), abs=0.1), \
        "flow 지표만 Q4 역산"
    assert fy["total_assets"] > 0


def test_flow_stock_sets_are_disjoint_and_cover_all_metrics():
    assert not (FU.FLOW & FU.STOCK)
    mapped = set(FU.METRIC_MAP.values())
    assert mapped == FU.FLOW | FU.STOCK, f"태깅 누락: {mapped ^ (FU.FLOW | FU.STOCK)}"


# ---------------------------------------------------------------- PIT
def test_attach_never_uses_future_filings():
    """available_date 가 월말보다 미래인 재무는 절대 붙으면 안 된다(look-ahead)."""
    monthly = pd.DataFrame({
        "Code": ["A"] * 3,
        "trade_date": pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
        "ym": pd.PeriodIndex(["2024-01", "2024-02", "2024-03"], freq="M"),
    })
    fund = pd.DataFrame({
        "ticker": ["A", "A"],
        "available_date": pd.to_datetime(["2024-02-15", "2024-05-15"]),
        "total_equity": [100.0, 999.0],       # 999 는 5월에야 알 수 있다
    })
    out = FU.attach(monthly, fund, ["total_equity"])
    got = dict(zip(out["trade_date"].dt.strftime("%Y-%m"), out["total_equity"]))
    assert pd.isna(got["2024-01"]), "공시 전에는 값이 없어야 한다"
    assert got["2024-02"] == 100.0
    assert got["2024-03"] == 100.0, "5월 공시가 3월에 새면 look-ahead"


def test_period_end_parses_both_dart_formats():
    assert FU._period_end("2025.04.01 ~ 2026.03.31") == date(2026, 3, 31)   # 비12월 결산
    assert FU._period_end("2026.03.31 현재") == date(2026, 3, 31)
    assert FU._period_end("") is None
    assert FU._period_end(None) is None


# ---------------------------------------------------------------- T0.5
def test_factor_requires_hypothesis():
    with pytest.raises(ValueError, match="hypothesis"):
        Factor(name="x", category="value", hypothesis="  ", predicted_sign=1,
               compute=lambda d: d["a"])


def test_undeclared_constant_is_detected():
    """게이트가 소스에서 숨은 파라미터를 찾아낸다."""
    def hidden(d):
        return d["market_cap"] ** 0.37        # ← 선언 안 된 튜닝 파라미터

    f = Factor(name="sneaky", category="other", hypothesis="테스트", predicted_sign=1,
               compute=hidden)
    assert 0.37 in f.undeclared_constants()

    g = Factor(name="honest", category="other", hypothesis="테스트", predicted_sign=1,
               compute=hidden, params={"exponent": 0.37})
    assert g.undeclared_constants() == []


def test_registry_rejects_duplicates():
    r = Registry()
    f = Factor(name="a", category="value", hypothesis="테스트", predicted_sign=1,
               compute=lambda d: d["x"])
    r.add(f)
    with pytest.raises(ValueError, match="중복"):
        r.add(f)


def test_definition_hash_is_stable_and_param_sensitive():
    mk = lambda p: Factor(name="a", category="value", hypothesis="테스트",
                          predicted_sign=1, compute=lambda d: d["x"], params=p)
    assert mk({"k": 1}).definition_hash == mk({"k": 1}).definition_hash
    assert mk({"k": 1}).definition_hash != mk({"k": 2}).definition_hash
