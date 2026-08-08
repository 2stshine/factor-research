"""Pre-registered long-term asset encumbrance candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    noncurrent_assets = frame["noncurrent_assets"].where(
        frame["noncurrent_assets"] > 0
    )
    return frame["noncurrent_liabilities"] / noncurrent_assets


FACTOR = Factor(
    name="noncurrent_asset_encumbrance",
    family="long_term_asset_encumbrance",
    category="quality",
    hypothesis=(
        "비유동자산 대비 비유동부채가 큰 기업은 장기 자산에 대한 채권자 청구와 재무 경직성이 "
        "커 충격 흡수력이 낮고 이후 상대수익도 낮다."
    ),
    predicted_sign=-1,
    params={},
    rebalance_months=3,
    needs=("noncurrent_liabilities", "noncurrent_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 noncurrent_liabilities/noncurrent_assets가 낮은 기업은 다음 달 총수익률 "
        "순위가 높을 것이다."
    ),
    "mechanism": (
        "장기자산에 대한 높은 장기 채권자 청구는 자금조달 경직성과 하방 위험을 높인다. 시장이 "
        "이 장기 구조의 취약성을 늦게 반영하면 낮은 부담 기업이 상대적으로 우수할 수 있다."
    ),
    "falsification": (
        "사전등록한 음의 방향이 데이터 무결성, 투자 가능 IC·ICIR, 기간·중립화 강건성, "
        "campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "qual_lev의 총부채/자본 및 current_liability_concentration의 유동부채/총부채와 일부 관계는 "
        "가능하지만, 장기자산 대비 장기청구만 측정하므로 산식은 비동치다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 noncurrent_liabilities와 noncurrent_assets를 사용한다. "
        "비유동자산이 양수일 때만 정의하며 담보권 자체를 직접 식별하는 지표는 아니다."
    ),
}
