"""Pre-registered 12-month noncurrent-asset growth candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    current = ordered["noncurrent_assets"]
    prior = current.groupby(asset).shift(LOOKBACK_MONTHS).where(lambda x: x > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (current / prior - 1).where(ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS))
    return value.reindex(frame.index)


FACTOR = Factor(
    name="noncurrent_assets_growth_12m",
    family="long_lived_asset_investment_growth",
    category="other",
    hypothesis="비유동자산을 빠르게 확대한 기업은 과잉투자와 낮은 한계수익성 때문에 이후 상대수익이 낮다.",
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("noncurrent_assets",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT 비유동자산의 정확한 12개월 성장률이 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "장기 설비·투자자산의 급증은 경영자의 과잉확장과 낮은 한계 투자수익을 뒤늦게 드러낼 수 있다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: asset_growth_12m — 차이: 유동자산을 제외하고 장기 자산 투자만 측정한다.",
    "data_notes": "DART available_date PIT noncurrent_assets를 쓰며 정확히 12개월 전 양수 관측이 있을 때만 정의한다.",
}
