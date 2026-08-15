"""Pre-registered long-term-liabilities-to-equity candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_equity"].where(frame["total_equity"] > 0)
    return frame["noncurrent_liabilities"] / base

FACTOR = Factor(name="noncurrent_liabilities_to_equity", family="long_term_book_leverage", category="other",
    hypothesis="자기자본 대비 비유동부채가 낮은 기업은 장기 레버리지 위험이 낮아 이후 상대수익이 높다.", predicted_sign=-1,
    params={}, rebalance_months=3, needs=("noncurrent_liabilities", "total_equity"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT noncurrent_liabilities/total_equity가 낮은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "장기 선순위 청구권이 주주자본 대비 작으면 장기간의 이자·차환 위험과 잔여청구권 민감도가 낮다.",
    "falsification": "음의 방향과 자동 gate, BY, 봉인 OOS, 귀무 또는 book leverage 직교성이 실패하면 기각한다.",
    "expected_relationship": "market_leverage와 관련되지만 장부 자기자본 대비 장기부채만 측정한다.",
    "data_notes": "DART available_date PIT 비유동부채와 양의 자기자본만 사용한다.",
}
