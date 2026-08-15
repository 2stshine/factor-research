"""Pre-registered recovery from the trailing twelve-month low."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    low = grouped["adj_close"].rolling(WINDOW_MONTHS, min_periods=WINDOW_MONTHS).min().reset_index(level=0, drop=True)
    oldest_month = grouped["ym"].shift(WINDOW_MONTHS - 1)
    value = ordered["adj_close"] / low.where(low > 0) - 1.0
    return value.where(ordered["ym"].eq(oldest_month + WINDOW_MONTHS - 1)).reindex(frame.index)


FACTOR = Factor(
    name="price_recovery_12m", family="price_recovery_from_low", category="momentum",
    hypothesis="12개월 저점에서 강하게 회복한 종목은 악재 해소가 점진 반영되어 이후 상대수익이 높다.",
    predicted_sign=1, params={"window_months": WINDOW_MONTHS}, rebalance_months=1,
    needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "현재 분할조정가격/12개월 최저가격 비율이 높은 종목의 이후 순위가 높을 것이다.",
    "mechanism": "저점 이후 지속적 회복은 재무곤경 완화와 정보확산을 나타내며 가격 조정이 이어질 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 가격앵커 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: high_12m_proximity — 차이: 고점 근접도가 아니라 저점 이후 회복 배수를 측정한다.",
    "data_notes": "분할조정 adj_close의 정확한 12개 달력월만 사용한다.",
}
