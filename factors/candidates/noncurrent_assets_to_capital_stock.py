"""Pre-registered long-lived asset backing per legal capital."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    base = frame["capital_stock"].where(frame["capital_stock"] > 0)
    return frame["noncurrent_assets"] / base


FACTOR = Factor(
    name="noncurrent_assets_to_capital_stock", family="legal_capital_long_asset_backing",
    category="quality", hypothesis="납입 자본금 대비 장기 생산자산이 큰 기업은 자본기반의 실물 생산능력이 높아 이후 상대수익이 높다.",
    predicted_sign=1, params={}, rebalance_months=3,
    needs=("noncurrent_assets", "capital_stock"), compute=compute,
)
RESEARCH_SPEC = {
    "thesis": "비유동자산/자본금이 높은 종목의 이후 수익률 순위가 높을 것이다.",
    "mechanism": "법정자본 한 단위가 뒷받침하는 장기 생산설비가 크면 증자 없이 구축한 운영기반이 크다.",
    "falsification": "자동 gate, BY, 봉인 OOS, 귀무 또는 자산생산성 신호 직교성이 실패하면 기각한다.",
    "expected_relationship": "가장 가까운 기존 팩터: capital_stock_to_assets — 차이: 전체자산의 자본금 강도가 아니라 장기 생산자산의 법정자본 배수를 측정한다.",
    "data_notes": "DART available_date PIT 비유동자산과 양의 자본금만 사용한다.",
}
