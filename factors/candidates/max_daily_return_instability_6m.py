"""Outcome-blind diversified candidate; immutable after registration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


WINDOW_MONTHS = 6
MIN_OBSERVATIONS = 4


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    source = ordered['max_daily_return_1m']
    value = source.groupby(ordered["asset_id"], sort=False).rolling(
        WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS
    ).std().reset_index(level=0, drop=True)
    return value.reindex(frame.index)


FACTOR = Factor(
    name='max_daily_return_instability_6m',
    family='max_daily_return_instability_6m',
    category='quality',
    exploration_domain='low_risk',
    hypothesis='최근 6개월 max_daily_return_1m의 std가 낮은 종목은 복권형 수요와 위험추종 수요의 과대가격을 피하여 이후 상대수익이 높다.',
    predicted_sign=-1,
    params={'window_months': WINDOW_MONTHS, 'min_observations': MIN_OBSERVATIONS, 'source_field': 'max_daily_return_1m', 'reducer': 'std'},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": '최근 6개월 max_daily_return_1m의 std가 낮은 종목은 복권형 수요와 위험추종 수요의 과대가격을 피하여 이후 상대수익이 높다.',
    "mechanism": '인증된 일별 수익 분포의 월별 요약을 고정 창에서 다시 집계해 가격 추세가 아닌 실현 위험의 수준 또는 불안정성을 측정한다.',
    "falsification": (
        "사전등록 방향이 무결성·입력 커버리지·Discovery IC·강건성·campaign-wide BY·"
        "Gold 상관·SQL parity·귀무 보정·봉인 OOS 중 하나라도 통과하지 못하면 기각한다."
    ),
    "expected_relationship": '기존 고유변동성·가격범위와 일부 관계가 예상되며 Gold 0.70 gate로 독립성을 확인한다.',
    "data_notes": 'Silver가 월말에 고정한 일별 위험 요약과 36개월 이하 달력창만 사용한다.',
}
