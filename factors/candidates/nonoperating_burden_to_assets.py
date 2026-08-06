"""Pre-registered non-operating burden candidate."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    return (frame["operating_income_ttm"] - frame["net_income_ttm"]) / assets


FACTOR = Factor(
    name="nonoperating_burden_to_assets",
    family="nonoperating_burden",
    category="quality",
    hypothesis=(
        "영업이익 중 이자·세금·비영업 손익 등으로 순이익에 도달하기 전에 소진되는 비중이 큰 "
        "기업은 재무·비영업 부담이 커 이후 상대적으로 낮은 수익을 낸다."
    ),
    predicted_sign=-1,
    rebalance_months=3,
    needs=("operating_income_ttm", "net_income_ttm", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 (operating_income_ttm-net_income_ttm)/total_assets가 낮은 종목은 높은 "
        "종목보다 이후 수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "영업이익과 순이익의 차이는 이자비용, 세금, 관계기업·기타 비영업 손익을 함께 반영한다. "
        "같은 자산 기반의 영업성과가 있어도 이 차이가 크면 주주에게 남는 이익의 변환 효율이 낮고 "
        "재무구조나 일회성 손실에 취약할 수 있다. 시장이 그 부담의 지속성을 과소평가하면 이후 "
        "상대수익률이 낮아질 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 강건성, "
        "고정 OOS, 다중검정·귀무 보정 또는 Gold 직교성 hard gate를 통과하지 못하면 가설을 "
        "기각한다."
    ),
    "expected_relationship": (
        "순이익 수준을 포함하므로 net_roa·qual_roe와 양의 관계가 일부 예상되고, 이자 부담을 통해 "
        "qual_lev와도 관계가 있을 수 있다. 다만 영업이익과 순이익 사이의 차이만 사용하므로 현재 "
        "수익성 수준과 완전히 같지는 않을 것으로 예상한다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT operating_income_ttm, net_income_ttm, "
        "total_assets만 사용한다. 총자산이 양수인 관측에서 정의한다. 세금과 일회성 비영업손익을 "
        "분리할 세부 계정이 없어 경제적 원인이 혼합될 수 있다."
    ),
}
