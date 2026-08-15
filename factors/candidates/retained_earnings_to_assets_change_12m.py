"""Pre-registered 12-month change in retained-earnings-to-assets."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    current = ordered["retained_earnings"] / assets
    prior = current.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (current - prior).where(ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS))
    return value.reindex(frame.index)


FACTOR = Factor(
    name="retained_earnings_to_assets_change_12m",
    family="retained_earnings_accumulation",
    category="quality",
    hypothesis="총자산 대비 이익잉여금이 최근 12개월 증가한 기업은 내부자본 축적이 재평가되어 이후 상대수익이 높다.",
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("retained_earnings", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT retained_earnings/total_assets의 12개월 변화가 큰 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "배당·증자와 구별되는 누적 내부이익의 증가가 자금조달 의존도와 부도위험을 낮출 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 보정 또는 retained_earnings 수준·성장 신호와의 직교성이 실패하면 기각한다.",
    "expected_relationship": "retained_earnings_to_assets 및 retained_earnings_growth_12m와 관련되지만 자산 대비 축적 속도만 측정한다.",
    "data_notes": "DART available_date PIT 이익잉여금과 양의 총자산을 사용하며 정확한 12개월 간격만 허용한다.",
}
