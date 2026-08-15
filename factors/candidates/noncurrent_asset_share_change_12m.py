"""Pre-registered 12-month change in noncurrent-asset share."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    assets = ordered["total_assets"].where(ordered["total_assets"] > 0)
    current = ordered["noncurrent_assets"] / assets
    prior = current.groupby(asset).shift(LOOKBACK_MONTHS)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (current - prior).where(ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS))
    return value.reindex(frame.index)


FACTOR = Factor(
    name="noncurrent_asset_share_change_12m",
    family="asset_rigidity_change",
    category="other",
    hypothesis="총자산 중 비유동자산 비중이 빠르게 높아진 기업은 재무 유연성이 낮아져 이후 상대수익이 낮다.",
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("noncurrent_assets", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT noncurrent_assets/total_assets의 12개월 변화가 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "자산구성이 고정자산 중심으로 이동하면 충격 대응력과 자본 회수 유연성이 낮아져 위험이 뒤늦게 가격에 반영될 수 있다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: noncurrent_asset_share — 차이: 자산 경직성 수준이 아니라 최근 12개월 구성 변화만 측정한다.",
    "data_notes": "DART available_date PIT 비유동자산과 양의 총자산을 쓰며 정확히 12개월 전 비율이 있을 때만 정의한다.",
}
