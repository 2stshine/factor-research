"""Pre-registered working-capital buffer candidate; immutable after evaluation."""
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    assets = frame["total_assets"].where(frame["total_assets"] > 0)
    return (frame["current_assets"] - frame["current_liabilities"]) / assets


FACTOR = Factor(
    name="net_working_capital_to_assets",
    family="working_capital_buffer",
    category="quality",
    hypothesis=(
        "총자산 대비 순운전자본 완충력이 큰 기업은 단기 자금압박과 불리한 외부조달 위험이 "
        "낮아 이후 상대적으로 높은 수익을 낸다."
    ),
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("current_assets", "current_liabilities", "total_assets"),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver PIT의 (current_assets-current_liabilities)/total_assets가 높은 종목은 낮은 "
        "종목보다 다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "순운전자본 완충력은 영업 충격을 흡수하고 강제 차입·증자·자산매각을 피할 여력을 "
        "나타낸다. 시장이 이 재무 유연성의 지속성과 하방 보호를 충분히 반영하지 못하면 "
        "이후 가격에 점진적으로 반영될 수 있다."
    ),
    "falsification": (
        "현재 ruleset의 무결성·커버리지, 전체·투자 가능 IC와 Rank ICIR, 기간·중립화 "
        "강건성, campaign BY, 봉인 OOS 또는 Gold 직교성 기준을 통과하지 못하면 기각한다."
    ),
    "expected_relationship": (
        "current_ratio와 양의 관계, current_liability_concentration 및 레버리지와 음의 관계를 "
        "예상한다. 유동비율이나 12개월 운전자본 변화가 아니라 총자산 대비 순유동 완충력의 "
        "수준이므로 정의는 구별된다."
    ),
    "data_notes": (
        "DART available_date 순으로 재생한 current_assets, current_liabilities, total_assets를 "
        "사용한다. 총자산이 양수일 때만 정의하고 음의 순운전자본은 보존한다. 금융업에서는 "
        "유동·비유동 분류의 의미가 다를 수 있으나 사후 표본 제외는 하지 않는다."
    ),
}
