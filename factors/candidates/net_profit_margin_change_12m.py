"""Pre-registered 12-month change in net profit margin."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    revenue = ordered["revenue_ttm"].where(ordered["revenue_ttm"] > 0)
    current = ordered["net_income_ttm"] / revenue
    prior = current.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (current - prior).where(ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS))
    return value.reindex(frame.index)


FACTOR = Factor(
    name="net_profit_margin_change_12m",
    family="net_margin_expansion",
    category="earnings",
    hypothesis="최근 12개월 순이익률이 개선된 기업은 이익의 질과 비용 통제가 재평가되어 이후 상대수익이 높다.",
    predicted_sign=1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("net_income_ttm", "revenue_ttm"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT TTM 순이익률의 12개월 개선폭이 큰 종목은 다음 달 총수익률 순위가 높을 것이다.",
    "mechanism": "영업외손익과 세금까지 반영한 최종 마진 개선의 지속성이 후속 공시에 걸쳐 늦게 반영될 수 있다.",
    "falsification": "양의 방향과 자동 gate, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "net_profit_margin 및 operating_margin_change_12m와 관련되지만 최종 순이익률의 변화만 측정한다.",
    "data_notes": "DART available_date PIT net_income_ttm과 양의 revenue_ttm을 사용하고 정확한 12개월 간격만 허용한다.",
}
