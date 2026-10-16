"""Pre-registered acceleration in 12-month sales growth."""
from __future__ import annotations
from engine.factors import Factor
LOOKBACK_MONTHS = 12

def compute(frame):
    x = frame.sort_values(["asset_id", "ym"]); g = x.groupby("asset_id")
    p1, p2 = g["revenue_ttm"].shift(12), g["revenue_ttm"].shift(24)
    y1, y2 = g["ym"].shift(12), g["ym"].shift(24)
    value = x["revenue_ttm"] / p1.where(p1 > 0) - p1 / p2.where(p2 > 0)
    return value.where(x["ym"].eq(y1 + 12) & x["ym"].eq(y2 + 24)).reindex(frame.index)

FACTOR = Factor(name="sales_growth_acceleration_12m", family="sales_growth_acceleration", category="earnings",
    exploration_domain="profitability_quality",
    hypothesis="12개월 매출성장률이 이전 12개월보다 가속한 기업은 수요 개선이 늦게 반영되어 이후 상대수익이 높다.",
    predicted_sign=1, params={"lookback_months": 12, "comparison_months": 24}, rebalance_months=1,
    needs=("revenue_ttm",), compute=compute)
RESEARCH_SPEC = {
    "thesis": "최근 전년동기 매출성장률에서 직전 전년동기 성장률을 뺀 값이 큰 종목은 이후 수익률 순위가 높을 것이다.",
    "mechanism": "성장 수준보다 성장의 가속은 수요·점유율 변화의 방향을 포착하며 후속 공시까지 점진 반영될 수 있다는 가설이다. Jegadeesh–Livnat (2006), Revenue surprises and stock returns의 매출 정보와 후속 이익 지속성 논의가 배경이지만, 이 TTM 성장 가속도는 기대 매출 대비 surprise나 논문 수식을 재현하지 않는다.",
    "falsification": "규모·유동성과 당기 매출효율·영업마진 통제 후 관계가 약해지면 독립적인 성장 전환 설명이 약해진다. 후속 영업수익성 변화와의 관계가 불확실하면 실적 전환 경로는 미확인으로 남긴다. 낮은 과거 매출 분모, 인수합병, 업종 구성, 공시 지연도 경쟁 설명이며 자료 없이 원인을 확정하지 않는다. 승인 여부는 기존 gate·BY·일회성 OOS 규칙을 그대로 따른다.",
    "expected_relationship": "가장 가까운 기존 팩터: sales_growth_12m — 차이: 성장률 수준이 아니라 전년동기 매출성장률의 전년 대비 변화(성장 가속도)를 측정한다.",
    "data_notes": "DART available_date PIT 매출과 정확한 12·24개월 전 양의 매출을 요구한다. TTM 원천 12개월과 수식 시차 24개월은 별도다. 월 리밸런싱 계약과 진단계획은 최초 평가 전에 선언하며 수식·방향은 기존 미시행 정의와 같다. 과거 연구 노출을 지우지 않으며 같은 과거 기간을 독립 OOS라고 부르지 않는다. 참조: https://www.sciencedirect.com/science/article/pii/S0165410106000061 ; 배경 문헌이지 국내 재현 또는 입력 승인 근거가 아니다.",
    "diagnostic_plan": {
        "question_kind": "EXPLANATORY",
        "question": "매출 성장 가속도와 다음 달 수익의 관계가 작은 과거 매출 분모·규모·거래활동·당기 영업효율 노출로 설명되는지 검토하고, 후속 공개 영업수익성 변화와 양립하는지 확인하라. 기대 매출 대비 surprise, 다음 사업연도 확정 실적, 인과적 수요 개선을 측정했다고 주장하지 말라.",
        "execution_cost": True,
        "ratio_controls": [
            {"name": "asset_turnover", "numerator": "revenue_ttm", "denominator": "total_assets", "available_at": "available_date"},
            {"name": "operating_margin", "numerator": "operating_income_ttm", "denominator": "revenue_ttm", "available_at": "available_date"}
        ],
        "economic_outcome": {
            "numerator": "operating_income_ttm",
            "denominator": "total_assets",
            "available_at": "available_date",
            "measurement_kind": "CHANGE",
            "horizon_months": 12,
            "rationale": "매출 가속이 후속 영업수익성 개선과 양립하는지 관측한다. 미래 공개 PIT snapshot의 변화이며 다음 사업연도 이익 또는 매출 surprise를 직접 측정하지 않는다. 동시 연관성 두 개로 인과적 매개를 입증하지 않는다.",
            "dataset_id": "certified-silver-pit-operating-roa-snapshot-change-12m"
        },
        "input_history": {
            "revenue_ttm": {"source_history_months": 12, "source_ref": "Silver certified four-quarter TTM contract; additional formula lag 24 months"}
        },
        "macro_axes": ["KR_PRODUCTION_INFLATION_DIRECTION"],
        "macro_contrasts": {"KR_PRODUCTION_INFLATION_DIRECTION": ["PRODUCTION_UP_INFLATION_DOWN", "PRODUCTION_DOWN_INFLATION_UP"]}
    },
}
