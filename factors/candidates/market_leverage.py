"""Pre-registered debt-to-market-equity candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


DEBT_DEFINITION = "pit_total_noncommon_equity_liabilities"
EQUITY_DEFINITION = "month_end_market_cap"


def compute(frame):
    debt = frame["total_liabilities"].where(frame["total_liabilities"] >= 0)
    market_equity = frame["market_cap"].where(frame["market_cap"] > 0)
    return debt / market_equity


FACTOR = Factor(
    name="market_leverage",
    family="market_leverage",
    category="other",
    hypothesis=(
        "시장가치 자기자본 대비 비보통주 지분성 부채가 큰 기업은 재무위험과 주주 잔여청구권의 "
        "민감도가 높아, 투자자가 부담하는 위험에 대한 보상으로 이후 기대수익이 높다."
    ),
    predicted_sign=1,
    params={
        "debt_definition": DEBT_DEFINITION,
        "equity_definition": EQUITY_DEFINITION,
    },
    rebalance_months=3,
    needs=("total_liabilities",),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "공시시점에 사용 가능했던 총부채를 월말 시가총액으로 나눈 값이 높은 종목은 낮은 "
        "종목보다 다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "부채가 고정적인 선순위 청구권을 만들기 때문에 기업가치 변화가 주주가치에 더 크게 "
        "전달될 수 있다. 투자자가 이 재무위험을 완전히 가격에 반영한다면 높은 시장 "
        "레버리지에 기대수익 보상이 나타날 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성·커버리지·투자가능 IC·Rank ICIR·기간 및 중립화 "
        "강건성·campaign BY를 통과하지 못하거나 book leverage·가치·규모 신호와 중복되면 "
        "독립적인 시장 레버리지 가설을 기각한다. 봉인 OOS는 이번 discovery에서 열지 않는다."
    ),
    "expected_relationship": (
        "분자에 총부채를 쓰므로 qual_lev와 양의 관계가 예상되고, 시가총액이 분모라 size 및 "
        "value 계열과도 관계가 예상된다. 다만 장부자본 대신 시장가치 자기자본을 쓰므로 "
        "정의상 동일하지 않으며 실측 중복도를 별도로 판정한다."
    ),
    "data_notes": (
        "Silver PIT의 total_liabilities를 Bhandari가 말한 noncommon-equity liabilities의 "
        "한국 재무제표 대응값으로 사용하고 같은 월말의 양의 market_cap으로 나눈다. 총부채가 "
        "음수인 관측과 시가총액이 0 이하인 관측은 결측 처리한다. 이자부채만을 뜻하는 "
        "net-debt/market-equity 팩터는 아니며, 그 정의에는 차입금·현금 세부 데이터가 더 필요하다."
    ),
}
