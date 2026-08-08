"""Pre-registered operating return-on-capital candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    capital_employed = frame["total_assets"] - frame["current_liabilities"]
    denominator = capital_employed.where(capital_employed > 0)
    return frame["operating_income_ttm"] / denominator


FACTOR = Factor(
    name="operating_return_on_capital_employed",
    family="capital_employment_efficiency",
    category="quality",
    hypothesis=(
        "장기 투입자본 한 단위당 영업이익이 높은 기업은 자본배분 우위가 지속되지만 시장이 "
        "이를 충분히 반영하지 않아 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("operating_income_ttm", "total_assets", "current_liabilities"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 operating_income_ttm/(total_assets-current_liabilities)가 높은 종목은 "
        "낮은 종목보다 다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "유동부채를 제외한 자본은 사업에 장기간 투입된 자금에 가깝다. 이 자본에서 높은 "
        "영업이익을 만드는 기업은 가격결정력, 자산 규율 또는 공급자 금융 활용에서 우위가 "
        "있고 그 지속성이 천천히 가격에 반영될 수 있다."
    ),
    "falsification": (
        "자동 gate의 예측 방향이 실패하거나 investable·중립화 검사를 통과하지 못하고, 또는 "
        "operating_roa·qual_roe·asset_turnover의 단순 재표현으로 판정되면 기각한다."
    ),
    "expected_relationship": (
        "operating_roa, qual_roe, asset_turnover와 양의 관계를 예상한다. 다만 유동부채 금융이 "
        "분모에서 제외되므로 총자산 수익성이나 자기자본 수익성과 기계적으로 같지는 않다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 operating_income_ttm, total_assets, "
        "current_liabilities를 사용한다. 투입자본이 양수일 때만 정의한다. 평균 투입자본이 아닌 "
        "최신 PIT 재무상태를 쓰며 유동부채에는 영업성·금융성 항목이 함께 포함된다."
    ),
}
