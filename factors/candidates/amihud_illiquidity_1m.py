"""Monthly Amihud price-impact proxy from certified daily Silver data."""
from __future__ import annotations

from engine.factors import Factor


MIN_OBSERVATIONS = 10


def compute(frame):
    enough_history = frame["amihud_observations_1m"] >= MIN_OBSERVATIONS
    return frame["amihud_illiquidity_1m"].where(enough_history)


FACTOR = Factor(
    name="amihud_illiquidity_1m",
    family="liquidity",
    category="other",
    hypothesis=(
        "같은 거래대금으로 더 큰 가격변동이 발생하는 비유동 종목은 거래비용·가격충격 위험에 "
        "대한 보상으로 이후 기대수익이 높다."
    ),
    predicted_sign=1,
    params={"min_observations": MIN_OBSERVATIONS},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "최근 한 달의 일별 |분할조정 가격수익률|/거래대금 평균이 큰 종목은 작은 종목보다 이후 총수익률 "
        "순위가 높을 것이다."
    ),
    "mechanism": (
        "투자자는 현금화가 어렵고 주문의 가격충격이 큰 자산을 보유하기 위해 추가 보상을 "
        "요구할 수 있다."
    ),
    "falsification": (
        "투자가능 유니버스 IC와 기간 강건성이 유지되지 않거나 trading_turnover_20d·size와의 "
        "중복이 기준을 넘거나 정식 confirmation에 실패하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "낮은 거래활동을 나타내는 trading_turnover_20d의 최종 방향 및 소형주 방향과 관계가 "
        "예상되지만, 거래량 수준이 아니라 단위 거래대금당 가격충격을 측정한다."
    ),
    "data_notes": (
        "Silver 일별 분할조정 가격 adj_close 수익률과 양의 trading_value만 사용해 월별 평균을 "
        "만든다. 월중 최소 10개 유효 관측이 필요하며 호가스프레드의 직접 측정치는 아니다."
    ),
}
