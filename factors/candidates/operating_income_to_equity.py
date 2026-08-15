"""Pre-registered operating return on book equity candidate."""
from __future__ import annotations
from engine.factors import Factor

def compute(frame):
    base = frame["total_equity"].where(frame["total_equity"] > 0)
    return frame["operating_income_ttm"] / base

FACTOR = Factor(name="operating_income_to_equity", family="operating_book_equity_return", category="quality",
    hypothesis="자기자본 대비 영업이익이 높은 기업은 본업의 주주자본 생산성이 높아 이후 상대수익이 높다.", predicted_sign=1,
    params={}, rebalance_months=3, needs=("operating_income_ttm", "total_equity"), compute=compute)
RESEARCH_SPEC = {
    "thesis": "Silver PIT operating_income_ttm/total_equity가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "세금·금융구조 전 본업 이익을 주주 장부자본과 비교하면 지속 가능한 자본생산성을 포착한다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 ROA·ROE 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "operating_roa와 관련되지만 자기자본 기준 본업 수익률이다.",
    "data_notes": "DART available_date PIT 영업이익과 양의 자기자본만 사용한다.",
}
