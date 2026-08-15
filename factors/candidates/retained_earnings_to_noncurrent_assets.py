"""Pre-registered internal-capital backing of long-lived assets."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["noncurrent_assets"].where(frame["noncurrent_assets"] > 0)
    return frame["retained_earnings"] / base


FACTOR = Factor(
    name="retained_earnings_to_noncurrent_assets",
    family="internal_capital_long_asset_backing", category="quality",
    hypothesis="장기자산을 누적 내부이익으로 더 많이 뒷받침한 기업은 외부자금 의존이 낮아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("retained_earnings", "noncurrent_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "PIT 이익잉여금/비유동자산이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "장기투자를 내부 축적이익으로 충당한 기업은 재무제약과 외부조달 위험이 낮다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 내부자본 계열 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: retained_earnings_to_assets — 차이: 전체 자산이 아니라 장기자산의 내부자본 충당 정도를 측정한다.",
    "data_notes": "DART available_date PIT retained_earnings와 양의 noncurrent_assets만 사용한다.",
}
