"""Pre-registered net-income productivity of long-lived assets."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["noncurrent_assets"].where(frame["noncurrent_assets"] > 0)
    return frame["net_income_ttm"] / base


FACTOR = Factor(
    name="net_income_to_noncurrent_assets", family="long_asset_net_productivity",
    category="quality",
    hypothesis="장기자산 대비 순이익이 높은 기업은 고정자본을 효율적으로 사용해 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("net_income_ttm", "noncurrent_assets"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "PIT 순이익/비유동자산이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "장기 설비와 무형자산에서 더 많은 최종이익을 만드는 기업은 자본배분 효율이 높다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 수익성 계열 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: operating_income_to_noncurrent_assets — 차이: 영업이익이 아니라 금융손익과 세금을 반영한 순이익을 사용한다.",
    "data_notes": "DART available_date PIT net_income_ttm과 양의 noncurrent_assets만 사용한다.",
}
