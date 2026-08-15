"""Pre-registered net-ROA volatility candidate."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 36
MIN_OBSERVATIONS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    signal = ordered["net_income_ttm"] / assets
    value = signal.groupby(ordered["asset_id"]).transform(
        lambda x: x.rolling(WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS).std()
    )
    return value.reindex(frame.index)


FACTOR = Factor(
    name="net_roa_volatility_36m", family="net_profitability_stability", category="quality",
    hypothesis="최근 36개월 순자산수익성 변동성이 낮은 기업은 이익 지속성이 높아 이후 상대수익이 높다.",
    predicted_sign=-1, params={"window_months": WINDOW_MONTHS, "min_observations": MIN_OBSERVATIONS},
    rebalance_months=3, needs=("net_income_ttm", "total_assets"), compute=compute,
)

RESEARCH_SPEC = {
    "thesis": "Silver PIT net_income_ttm/total_assets의 36개월 표준편차가 낮은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "최종 이익의 안정성은 사업·금융·세금 충격을 견디는 능력을 나타내며 불확실성 할인 축소로 이어질 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 기존 수익성·변동성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "operating_roa_volatility_36m과 관련되지만 영업외손익과 세후 효과까지 포함한다.",
    "data_notes": "DART available_date PIT 순이익과 양의 총자산을 사용하며 36개월 창에서 최소 24개 월 관측을 요구한다.",
}
