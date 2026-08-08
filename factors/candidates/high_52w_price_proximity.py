"""Split-adjusted price proximity to the trailing 52-week high."""
from __future__ import annotations

from engine.factors import Factor


WINDOW_DAYS = 252
MIN_OBSERVATIONS = 200


def compute(frame):
    price = frame["adj_close"].where(frame["adj_close"] > 0)
    high = frame["price_high_252d"].where(frame["price_high_252d"] > 0)
    enough_history = frame["price_high_observations_252d"] >= MIN_OBSERVATIONS
    return (price / high).where(enough_history)


FACTOR = Factor(
    name="high_52w_price_proximity",
    family="price_anchoring",
    category="momentum",
    hypothesis=(
        "현재 가격이 52주 고가에 가까울수록 투자자의 기준점 조정이 지연되어 긍정적 정보가 "
        "가격에 계속 반영되고 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={
        "window_days": WINDOW_DAYS,
        "min_observations": MIN_OBSERVATIONS,
    },
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "월말 분할조정 가격이 최근 252거래일 고가에 가까운 종목은 멀리 있는 종목보다 이후 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "투자자가 과거 고가를 기준점으로 삼고 새로운 정보를 점진적으로 반영하면 고가 근접 "
        "종목의 정보 확산이 이어질 수 있다."
    ),
    "falsification": (
        "현재 gate의 무결성·IC·Rank ICIR·강건성·다중검정 및 confirmation을 통과하지 못하거나 "
        "mom_12_1과 독립성을 충족하지 못하면 별도 고가 앵커 가설을 기각한다."
    ),
    "expected_relationship": (
        "mom_12_1과 양의 관계를 예상하지만 누적수익이 아니라 현재 가격과 고가의 거리만 "
        "사용하므로 완전한 중복은 아닐 것으로 예상한다."
    ),
    "data_notes": (
        "배당재투자 지수인 return_close가 아니라 가격 기준점에 맞는 Silver adj_close를 사용한다. "
        "최근 252거래일 중 최소 200개 가격관측이 있어야 정의한다."
    ),
}
