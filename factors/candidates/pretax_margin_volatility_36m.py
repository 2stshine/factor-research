"""Pre-registered pretax-margin volatility candidate."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 36
MIN_OBSERVATIONS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    revenue = ordered["revenue_ttm"].where(ordered["revenue_ttm"] > 0)
    signal = ordered["pretax_income_ttm"] / revenue
    value = signal.groupby(ordered["asset_id"]).transform(
        lambda x: x.rolling(WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS).std()
    )
    return value.reindex(frame.index)


FACTOR = Factor(
    name="pretax_margin_volatility_36m", family="pretax_margin_stability", category="quality",
    hypothesis="최근 36개월 세전이익률 변동성이 낮은 기업은 세율 영향 전 마진이 안정적이라 이후 상대수익이 높다.",
    predicted_sign=-1, params={"window_months": WINDOW_MONTHS, "min_observations": MIN_OBSERVATIONS},
    rebalance_months=3, needs=("pretax_income_ttm", "revenue_ttm"), compute=compute,
)

RESEARCH_SPEC = {
    "thesis": "Silver PIT pretax_income_ttm/revenue_ttm의 36개월 표준편차가 낮은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "세전 마진 안정성은 영업과 금융비용을 함께 반영하되 세금의 일회성 변동을 제거한 이익 지속성을 포착한다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 인접 마진 안정성 신호와의 직교성이 실패하면 기각한다.",
    "expected_relationship": "net_margin_volatility_36m과 관련되지만 세전 이익 정의로 구별된다.",
    "data_notes": "DART available_date PIT 세전이익과 양의 매출을 쓰며 36개월 창에서 최소 24개 월 관측을 요구한다.",
}
