"""Pre-registered non-current asset-share candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    noncurrent_assets = frame["noncurrent_assets"].where(
        frame["noncurrent_assets"] >= 0
    )
    return noncurrent_assets / assets


FACTOR = Factor(
    name="noncurrent_asset_share",
    family="asset_rigidity",
    category="other",
    hypothesis=(
        "총자산 중 비유동자산 비중이 낮은 기업은 자산 재배치 유연성과 충격 흡수력이 높아 "
        "이후 상대수익이 높다."
    ),
    predicted_sign=-1,
    params={},
    rebalance_months=3,
    needs=("noncurrent_assets", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "신호시점에 알려진 Silver PIT noncurrent_assets/total_assets가 낮은 종목은 높은 종목보다 "
        "다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "높은 비유동자산 비중은 수요 충격 때 자산을 빠르게 재배치하기 어렵고 고정비·감손 위험을 "
        "키울 수 있다. 반대로 자산구조가 덜 경직된 기업의 적응력이 가격에 늦게 반영되면 낮은 "
        "비유동자산 비중이 양의 미래수익 신호가 될 수 있다."
    ),
    "falsification": (
        "사전등록한 음의 방향이 무결성, 커버리지, 전체·투자가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, 다중검정, Gold SQL parity 또는 일회성 OOS 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "asset_turnover와 음의 관계, noncurrent_asset_encumbrance와 일부 관계를 예상한다. 그러나 "
        "부채 청구나 매출 효율이 아니라 자산의 유동·비유동 구성 자체를 측정하며, 기존 팩터와 "
        "고상관이면 새 정보로 보지 않는다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 noncurrent_assets와 total_assets만 사용한다. 총자산이 "
        "양수이고 비유동자산이 음수가 아닌 관측에서 정의한다. 업종별 자산구조 차이가 크므로 "
        "사후 업종 제외 없이 시장·유동성·규모 중립화 강건성을 그대로 적용한다."
    ),
}
