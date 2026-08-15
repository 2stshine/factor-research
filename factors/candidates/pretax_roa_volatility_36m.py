"""Pre-registered pretax-ROA volatility candidate."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 36
MIN_OBSERVATIONS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    signal = ordered["pretax_income_ttm"] / assets
    value = signal.groupby(ordered["asset_id"]).transform(
        lambda x: x.rolling(WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS).std()
    )
    return value.reindex(frame.index)


FACTOR = Factor(
    name="pretax_roa_volatility_36m", family="pretax_profitability_stability", category="quality",
    hypothesis="최근 36개월 세전 자산수익성 변동성이 낮은 기업은 세율 잡음 전 이익 기반이 안정적이라 이후 상대수익이 높다.",
    predicted_sign=-1, params={"window_months": WINDOW_MONTHS, "min_observations": MIN_OBSERVATIONS},
    rebalance_months=3, needs=("pretax_income_ttm", "total_assets"), compute=compute,
)

RESEARCH_SPEC = {
    "thesis": "Silver PIT pretax_income_ttm/total_assets의 36개월 표준편차가 낮은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "세전 수익성 안정성은 영업과 금융손익을 함께 반영하면서 세율 변동은 배제해 지속 가능한 이익 기반을 포착한다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 기존 수익성 안정성 신호와의 직교성이 실패하면 기각한다.",
    "expected_relationship": "net·operating ROA 변동성과 관련되지만 세전이익 정의로 구별된다.",
    "data_notes": "DART available_date PIT 세전이익과 양의 총자산을 쓰며 36개월 창에서 최소 24개 월 관측을 요구한다.",
}
