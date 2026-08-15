"""Pre-registered 12-month legal-capital growth candidate."""
from __future__ import annotations

from engine.factors import Factor


LOOKBACK_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"])
    asset = ordered["asset_id"]
    capital_stock = ordered["capital_stock"]
    prior = capital_stock.groupby(asset).shift(LOOKBACK_MONTHS)
    prior = prior.where(prior > 0)
    prior_ym = ordered["ym"].groupby(asset).shift(LOOKBACK_MONTHS)
    consecutive = ordered["ym"].eq(prior_ym + LOOKBACK_MONTHS)
    return (capital_stock / prior - 1).where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="capital_stock_growth_12m",
    family="legal_capital_issuance_growth",
    category="other",
    hypothesis=(
        "최근 12개월 법정 자본금이 증가한 기업은 신규 납입자본과 희석성 자금조달의 신호가 커 "
        "이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    params={"lookback_months": LOOKBACK_MONTHS},
    rebalance_months=3,
    needs=("capital_stock",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 12개월 capital_stock 성장률이 낮은 기업은 높은 기업보다 다음 달 총수익률 "
        "순위가 높을 것이다."
    ),
    "mechanism": (
        "자본금 증가는 유상증자·주식전환·합병 등 법정 납입자본 확대를 포착한다. 경영자가 높은 "
        "평가나 자금수요를 이용해 자본을 늘린 뒤 희석과 투자수익성 저하가 나타나면 낮은 자본금 "
        "성장 기업의 상대수익이 높을 수 있다."
    ),
    "falsification": (
        "음의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS, 귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: net_equity_issuance_price_adjusted_12m — 차이: 시장가격으로 역산한 "
        "주식수 변화가 아니라 DART PIT 장부의 법정 자본금 변동만 측정한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT capital_stock을 사용한다. 정확히 12개월 전 "
        "자본금이 양수인 관측에서 정의하며 액면분할 자체는 자본금을 바꾸지 않는다."
    ),
}
