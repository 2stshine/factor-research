"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 24
SKIP_MONTHS = 6


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    recent = grouped["adj_close"].shift(SKIP_MONTHS)
    distant = grouped["adj_close"].shift(LOOKBACK_MONTHS)
    recent_month = grouped["ym"].shift(SKIP_MONTHS)
    distant_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    raw = recent / distant.where(distant > 0) - 1.0
    relative = raw - raw.groupby([ordered["ym"], ordered["market"]]).transform("mean")
    exact = ordered["ym"].eq(recent_month + SKIP_MONTHS) & ordered["ym"].eq(
        distant_month + LOOKBACK_MONTHS
    )
    return relative.where(exact).reindex(frame.index)


FACTOR = Factor(
    name='market_relative_momentum_24_6',
    family='market_relative_momentum_24_6',
    category='momentum',
    exploration_domain='momentum_trend_reversal',
    hypothesis='시장 공통 추세를 뺀 24-6개월 종목 고유 모멘텀이 높은 종목의 이후 상대수익이 높다.',
    predicted_sign=1,
    params={'lookback_months': LOOKBACK_MONTHS, 'skip_months': SKIP_MONTHS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '시장 공통 추세를 뺀 24-6개월 종목 고유 모멘텀이 높은 종목의 이후 상대수익이 높다.',
    "mechanism": '동일 월·동일 시장 평균을 제거해 거시 재평가가 아닌 기업고유 정보의 지연 반영을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '일반 가격 모멘텀과 관련되지만 시장 공통성분 제거로 완전 중복은 아닐 것으로 예상한다.',
    "data_notes": 'adj_close, 동시점 market, 정확한 달력 시차만 사용한다.',
}
