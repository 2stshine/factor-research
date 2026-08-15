"""Pre-registered pretax-income debt coverage candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    liabilities = frame["total_liabilities"].where(frame["total_liabilities"] > 0)
    return frame["pretax_income_ttm"] / liabilities


FACTOR = Factor(
    name="pretax_income_to_liabilities",
    family="pretax_debt_coverage",
    category="quality",
    hypothesis="부채 대비 세전이익 창출력이 큰 기업은 상환능력이 높아 이후 상대수익이 높다.",
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("pretax_income_ttm", "total_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "Silver PIT pretax_income_ttm/total_liabilities가 높은 종목이 낮은 종목보다 이후 수익률 순위가 높을 것이다.",
    "mechanism": "세금 전 이익이 부채 청구권에 비해 크면 금리·세율 변화 전의 기본 상환여력이 강하다.",
    "falsification": "무결성·커버리지·IC·강건성·BY·봉인 OOS·귀무·Gold 직교성 gate 중 하나라도 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: operating_income_to_liabilities — 차이: 영업이익이 아니라 금융·영업외손익까지 반영한 세전 커버리지다.",
    "data_notes": "DART available_date PIT TTM 세전이익과 양의 총부채를 사용한다.",
}
