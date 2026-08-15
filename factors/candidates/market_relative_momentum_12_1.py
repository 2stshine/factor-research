"""Pre-registered market-relative twelve-to-one price momentum."""
from __future__ import annotations

from engine.factors import Factor

LOOKBACK_MONTHS = 12
SKIP_MONTHS = 1


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    grouped = ordered.groupby("asset_id", sort=False)
    recent = grouped["adj_close"].shift(SKIP_MONTHS)
    distant = grouped["adj_close"].shift(LOOKBACK_MONTHS)
    recent_month = grouped["ym"].shift(SKIP_MONTHS)
    distant_month = grouped["ym"].shift(LOOKBACK_MONTHS)
    raw = recent / distant.where(distant > 0) - 1.0
    relative = raw - raw.groupby([ordered["ym"], ordered["market"]]).transform("mean")
    exact = ordered["ym"].eq(recent_month + SKIP_MONTHS) & ordered["ym"].eq(distant_month + LOOKBACK_MONTHS)
    return relative.where(exact).reindex(frame.index)


FACTOR = Factor(
    name="market_relative_momentum_12_1", family="market_relative_momentum",
    category="momentum", hypothesis="시장 공통 추세를 제외한 12-1개월 종목 고유 모멘텀은 이후에도 지속된다.",
    predicted_sign=1, params={"lookback_months": LOOKBACK_MONTHS, "skip_months": SKIP_MONTHS},
    rebalance_months=1, needs=(), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "동일 시장 평균을 뺀 12-1개월 분할조정 모멘텀이 높은 종목의 이후 순위가 높을 것이다.",
    "mechanism": "시장 전체 재평가가 아닌 기업고유 정보의 점진적 확산만 분리한다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 모멘텀 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: mom_12_1 — 차이: KOSPI·KOSDAQ별 공통 가격추세를 동월 횡단면에서 제거한다.",
    "data_notes": "분할조정 adj_close, 동시점 market, 정확한 1·12개월 달력 시차만 사용한다.",
}
