"""Pre-registered 12-month noncurrent-liability growth candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    current = ordered["noncurrent_liabilities"]
    prior = current.groupby(asset).shift(LOOKBACK_MONTHS).where(lambda x: x > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    value = (current / prior - 1).where(ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS))
    return value.reindex(frame.index)


FACTOR = Factor(
    name="noncurrent_liabilities_growth_12m",
    family="long_term_debt_growth",
    category="other",
    hypothesis="장기부채를 빠르게 늘린 기업은 재무위험과 자본배분 압력이 커 이후 상대수익이 낮다.",
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("noncurrent_liabilities",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT 비유동부채의 정확한 12개월 성장률이 낮은 종목이 높은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "장기 차입 확대는 미래 현금흐름의 고정 청구권과 재융자 위험을 높여 시장이 뒤늦게 위험을 재평가하게 할 수 있다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: liability_growth_12m — 차이: 단기 운전자금 부채를 제외한 장기 조달 증가만 측정한다.",
    "data_notes": "DART available_date PIT noncurrent_liabilities를 쓰며 정확히 12개월 전 양수 관측이 있을 때만 정의한다.",
}
