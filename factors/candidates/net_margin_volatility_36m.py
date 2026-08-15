"""Pre-registered net-margin volatility candidate."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 36
MIN_OBSERVATIONS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    revenue = ordered["revenue_ttm"].where(ordered["revenue_ttm"] > 0)
    signal = ordered["net_income_ttm"] / revenue
    value = signal.groupby(ordered["asset_id"]).transform(
        lambda x: x.rolling(WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS).std()
    )
    return value.reindex(frame.index)


FACTOR = Factor(
    name="net_margin_volatility_36m", family="net_margin_stability", category="quality",
    hypothesis="최근 36개월 순이익률 변동성이 낮은 기업은 최종 마진의 예측 가능성이 높아 이후 상대수익이 높다.",
    predicted_sign=-1, params={"window_months": WINDOW_MONTHS, "min_observations": MIN_OBSERVATIONS},
    rebalance_months=3, needs=("net_income_ttm", "revenue_ttm"), compute=compute,
)

RESEARCH_SPEC = {
    "thesis": "Silver PIT net_income_ttm/revenue_ttm의 36개월 표준편차가 낮은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "최종 마진 안정성은 가격결정력·비용·금융손익의 결합된 지속성을 나타내며 투기적 고변동 기업의 과대평가와 대비된다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 net_profit_margin·회계 변동성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "net_profit_margin 수준 및 net_roa_volatility_36m과 관련되지만 매출 대비 마진 변동만 측정한다.",
    "data_notes": "DART available_date PIT 순이익과 양의 매출을 쓰며 36개월 창에서 최소 24개 월 관측을 요구한다.",
}
