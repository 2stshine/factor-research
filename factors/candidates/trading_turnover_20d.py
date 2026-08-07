"""Pre-registered 20-day trading-turnover candidate; do not edit after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    market_cap = frame["market_cap"].where(frame["market_cap"] > 0)
    return frame["adv20"] / market_cap


FACTOR = Factor(
    name="trading_turnover_20d",
    family="trading_activity",
    category="other",
    hypothesis=(
        "기업가치 대비 최근 거래가 과도한 종목은 투자자 관심·의견불일치·투기 수요가 가격을 "
        "일시적으로 끌어올렸을 가능성이 높아, 거래회전 강도가 낮은 종목보다 이후 상대수익이 낮다."
    ),
    predicted_sign=-1,
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 ADV20/시가총액이 낮은 종목은 높은 종목보다 다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "시가총액 대비 거래대금이 크다는 것은 기업 규모에 비해 투자자 관심과 의견 교환이 "
        "집중됐다는 뜻이다. 과도한 관심이나 투기적 수요가 현재 가격에 먼저 반영되고 천천히 "
        "되돌려진다면 낮은 거래회전 종목이 이후 상대적으로 높은 수익을 낼 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 전체·투자 가능 IC, Rank ICIR, 기간 강건성 및 시장구분·유동성·비의도 "
        "규모 노출 제거 후 IC를 통과하지 못하면 단순 유동성·규모를 넘어선 거래활동 가설을 "
        "기각한다. campaign BY 또는 봉인 OOS confirmation 실패도 최종 기각으로 본다."
    ),
    "expected_relationship": (
        "유동성·관심도와 연결되므로 size 및 lottery-demand 계열과 일부 관계가 있을 수 있다. "
        "그러나 가격경로나 회계값이 아니라 최근 거래대금/기업가치 비율만 사용하므로 가치·수익성 "
        "팩터와의 관계는 제한적일 것으로 예상한다."
    ),
    "data_notes": (
        "인증된 KRX Silver의 월말 시점 ADV20과 market_cap만 사용한다. ADV20은 직전 20거래일 "
        "일평균 거래대금이며 시가총액이 양수인 관측에서만 정의한다. free-float 회전율이 아니고 "
        "거래정지·기업행위·시장별 거래관행의 영향을 받을 수 있으며, 목표 AUM의 체결 가능성을 "
        "직접 보장하지 않는다."
    ),
}
