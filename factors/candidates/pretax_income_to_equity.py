"""Pre-registered pretax return on book equity candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_equity"].where(frame["total_equity"] > 0)
    return frame["pretax_income_ttm"] / base

FACTOR = Factor(name="pretax_income_to_equity", family="pretax_book_equity_return", category="quality",
    hypothesis="자기자본 대비 세전이익이 높은 기업은 세율 잡음 전 주주자본 수익성이 높아 이후 상대수익이 높다.", predicted_sign=1,
    params={}, rebalance_months=3, needs=("pretax_income_ttm", "total_equity"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT pretax_income_ttm/total_equity가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "영업·금융성과를 포함하되 세금 변동을 제거한 자기자본 수익성이 기대치에 늦게 반영될 수 있다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 인접 ROE 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: operating_income_to_equity — 차이: 영업이익 대신 금융손익까지 포함한 세전이익을 사용한다.",
    "data_notes": "DART available_date PIT 세전이익과 양의 자기자본만 사용한다.",
}
