"""Pre-registered flexible-to-fixed asset mix."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    fixed = frame["noncurrent_assets"].where(frame["noncurrent_assets"] > 0)
    return frame["current_assets"] / fixed


FACTOR = Factor(
    name="current_assets_to_noncurrent_assets", family="flexible_asset_mix",
    category="other", hypothesis="비유동자산 대비 유동자산이 큰 기업은 자산 재배치 유연성이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("current_assets", "noncurrent_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "유동자산/비유동자산이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "회수 가능한 자산 비중이 크면 수요 충격에 투자와 운전자본을 빠르게 조정할 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자산구성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: noncurrent_asset_share — 차이: 총자산 비중이 아니라 유동·비유동 자산의 직접 교환비를 측정한다.",
    "data_notes": "DART available_date PIT 유동자산과 양의 비유동자산만 사용한다.",
}
