"""Pre-registered pretax return-on-assets candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    return frame["pretax_income_ttm"] / assets


FACTOR = Factor(
    name="pretax_roa",
    family="pretax_roa",
    category="quality",
    hypothesis=(
        "총자산 대비 세전이익이 높은 기업은 영업성과와 비영업성과를 세후 잡음 전에 함께 "
        "현금창출력으로 전환하는 능력이 높아 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("pretax_income_ttm", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 pretax_income_ttm/total_assets가 높은 기업은 낮은 기업보다 다음 달 "
        "총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "세전이익은 영업성과에 이자와 기타 비영업손익을 반영하되 세율과 일회성 세후 조정의 "
        "차이는 제거한다. 시장이 자산 기반 전체 수익창출력의 지속성을 충분히 가격에 반영하지 "
        "않으면 높은 세전 자산수익성이 이후 상대수익으로 이어질 수 있다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성, 커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS, 귀무 보정 또는 기존 Gold 직교성 hard gate를 통과하지 "
        "못하면 가설을 기각한다."
    ),
    "expected_relationship": (
        "가장 가까운 기존 팩터: operating_roa — 차이: 영업이익만이 아니라 이자·비영업손익까지 "
        "반영한 세전이익의 자산 효율성을 측정하며, 세후 순이익을 쓰는 net_roa와도 정의가 다르다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 Silver PIT pretax_income_ttm과 total_assets만 사용한다. "
        "총자산이 양수인 관측에서 정의하고 적자 세전이익도 그대로 유지한다. 금융업과 비금융업의 "
        "자산 구조 차이는 공통 시장·규모 중립화 gate에서 진단한다."
    ),
}
