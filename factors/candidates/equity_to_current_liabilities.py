"""Pre-registered equity coverage of short-term liabilities."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    debt = frame["current_liabilities"].where(frame["current_liabilities"] > 0)
    return frame["total_equity"] / debt


FACTOR = Factor(
    name="equity_to_current_liabilities", family="short_term_equity_solvency",
    category="quality", hypothesis="유동부채 대비 자기자본이 큰 기업은 단기 채무충격을 흡수해 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("total_equity", "current_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "자기자본/유동부채가 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "단기 상환의무에 비해 영구 손실흡수자본이 크면 유동성 위기에 강하다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 지급능력 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: current_ratio — 차이: 유동자산이 아니라 영구 자기자본으로 단기부채를 덮는 능력을 측정한다.",
    "data_notes": "DART available_date PIT 자기자본과 양의 유동부채만 사용한다.",
}
