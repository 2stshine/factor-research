"""Pre-registered asset-turnover volatility candidate."""
from __future__ import annotations

from engine.factors import Factor

WINDOW_MONTHS = 36
MIN_OBSERVATIONS = 24


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    signal = ordered["revenue_ttm"] / assets
    value = signal.groupby(ordered["asset_id"]).transform(
        lambda x: x.rolling(WINDOW_MONTHS, min_periods=MIN_OBSERVATIONS).std()
    )
    return value.reindex(frame.index)


FACTOR = Factor(
    name="asset_turnover_volatility_36m", family="asset_efficiency_stability", category="quality",
    hypothesis="최근 36개월 자산회전율 변동성이 낮은 기업은 운영 효율이 안정적이라 이후 상대수익이 높다.",
    predicted_sign=-1, params={"window_months": WINDOW_MONTHS, "min_observations": MIN_OBSERVATIONS},
    rebalance_months=3, needs=("revenue_ttm", "total_assets"), compute=compute,
)

RESEARCH_SPEC = {
    "thesis": "Silver PIT revenue_ttm/total_assets의 36개월 표준편차가 낮은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "일관된 자산 활용은 수요와 생산능력의 매칭이 안정적임을 보여주며 운영 불확실성 할인 축소로 이어질 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자산회전율 수준·변화 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "current_asset_turnover와 asset_turnover_change_12m에 관련되지만 장기 시계열 안정성만 측정한다.",
    "data_notes": "DART available_date PIT 매출과 양의 총자산을 쓰며 36개월 창에서 최소 24개 월 관측을 요구한다.",
}
