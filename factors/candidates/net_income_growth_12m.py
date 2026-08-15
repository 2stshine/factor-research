"""Pre-registered 12-month trailing-net-income growth candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    current = ordered["net_income_ttm"]
    prior = current.groupby(asset).shift(LOOKBACK_MONTHS).where(lambda x: x > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (current / prior - 1).where(ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS))
    return value.reindex(frame.index)


FACTOR = Factor(
    name="net_income_growth_12m",
    family="trailing_net_income_growth",
    category="earnings",
    hypothesis="최근 12개월 누적 순이익이 성장한 기업은 이익 개선이 점진 반영돼 이후 상대수익이 높다.",
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("net_income_ttm",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT net_income_ttm의 정확한 12개월 성장률이 높은 종목이 낮은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "연간 누적 순이익 개선의 지속성을 투자자가 한 번에 반영하지 못하면 공시 뒤에도 가격 조정이 이어질 수 있다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: earnings_change_to_assets — 차이: 단일 분기 변화액이 아니라 양의 TTM 순이익의 연간 성장률이다.",
    "data_notes": "DART available_date PIT net_income_ttm을 쓰며 전기 TTM 순이익이 양수이고 월 간격이 정확할 때만 정의한다.",
}
