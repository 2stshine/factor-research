"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


LOOKBACK_MONTHS = 36
SKIP_MONTHS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    recent = grouped["adj_close"].shift(SKIP_MONTHS)
    distant = grouped["adj_close"].shift(LOOKBACK_MONTHS)
    recent_month = grouped["ym"].shift(SKIP_MONTHS)
    distant_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    value = recent / distant.where(distant > 0) - 1.0
    exact = ordered["ym"].eq(recent_month + SKIP_MONTHS) & ordered["ym"].eq(
        distant_month + LOOKBACK_MONTHS
    )
    return value.where(exact).reindex(frame.index)


FACTOR = Factor(
    name='price_reversal_36_24',
    family='price_reversal_36_24',
    category='momentum',
    exploration_domain='momentum_trend_reversal',
    hypothesis='분할조정 가격의 36개월 전 대비 24개월 전 수익률이 낮은 종목은 정보의 지연반영 또는 장기 과잉반응 교정으로 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'lookback_months': LOOKBACK_MONTHS, 'skip_months': SKIP_MONTHS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '분할조정 가격의 36개월 전 대비 24개월 전 수익률이 낮은 종목은 정보의 지연반영 또는 장기 과잉반응 교정으로 이후 상대수익이 높다.',
    "mechanism": '서로 다른 시작·종료 시점의 가격 경로는 최근 한 달 잡음과 장기 추세를 분리하며, 사전 고정한 부호는 점진적 정보확산 또는 과잉반응 교정을 검증한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '기존 모멘텀·반전과 관련될 수 있으나 정확한 구간이 달라 Gold 0.70 gate로 독립성을 확인한다.',
    "data_notes": 'PIT feature로 허용된 adj_close와 정확한 달력 시차만 사용하며 total_return_close는 사용하지 않는다.',
}
