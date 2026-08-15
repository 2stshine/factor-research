"""Pre-registered internal capital relative to current assets."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["current_assets"].where(frame["current_assets"] > 0)
    return frame["retained_earnings"] / base


FACTOR = Factor(
    name="retained_earnings_to_current_assets", family="internal_capital_current_asset_backing",
    category="quality", hypothesis="유동자산 대비 이익잉여금이 큰 기업은 단기 운영자산을 내부자본으로 뒷받침해 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("retained_earnings", "current_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "이익잉여금/유동자산이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "누적 내부이익이 단기 운영자산을 충분히 덮으면 외부 운전자금 의존도가 낮다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 내부자본 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: retained_earnings_to_assets — 차이: 총자산이 아니라 유동 운영자산의 내부자본 충당력을 측정한다.",
    "data_notes": "DART available_date PIT 이익잉여금과 양의 유동자산만 사용한다.",
}
