"""Pre-registered operating-income coverage of long-term liabilities."""
from __future__ import annotations
from engine.factors import Factor


def compute(frame):
    base = frame["noncurrent_liabilities"].where(frame["noncurrent_liabilities"] > 0)
    return frame["operating_income_ttm"] / base


FACTOR = Factor(
    name="operating_income_to_noncurrent_liabilities", family="long_term_operating_coverage", category="quality",
    hypothesis="비유동부채 대비 영업이익이 높은 기업은 장기 채무상환 여력이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("operating_income_ttm", "noncurrent_liabilities"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "Silver PIT operating_income_ttm/noncurrent_liabilities가 높은 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "본업 이익이 장기 의무를 넉넉히 덮으면 차환 위험과 잔여주주 청구권의 하방이 줄어든다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 총부채·유동부채 coverage 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "operating_income_to_liabilities와 관련되지만 장기 만기 의무만 분모로 쓴다.",
    "data_notes": "DART available_date PIT 영업이익과 양의 비유동부채만 사용한다.",
}
