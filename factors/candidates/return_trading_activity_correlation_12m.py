"""Single monthly price/activity co-movement hypothesis, frozen before Discovery."""
from __future__ import annotations

import numpy as np

from engine.factors import Factor


WINDOW_MONTHS = 12


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    asset = ordered["asset_id"]
    raw_close = ordered["adj_close"]
    raw_activity = ordered["adv20"]
    # x - x is zero only for finite numeric values; no unbounded API is needed.
    close = raw_close.where((raw_close > 0) & (raw_close - raw_close).eq(0))
    prior_close = close.groupby(asset).shift(1)
    prior_month = ordered["ym"].groupby(asset).shift(1)
    returns = (close / prior_close - 1.0).where(ordered["ym"].eq(prior_month + 1))
    activity = np.log(raw_activity.where(
        (raw_activity > 0) & (raw_activity - raw_activity).eq(0)
    ))
    valid = returns.notna() & activity.notna()
    paired_return = returns.where(valid)
    paired_activity = activity.where(valid)
    product = paired_return * paired_activity
    return_mean = paired_return.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).mean().reset_index(level=0, drop=True)
    activity_mean = paired_activity.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).mean().reset_index(level=0, drop=True)
    product_mean = product.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).mean().reset_index(level=0, drop=True)
    return_variance = paired_return.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).var(ddof=0).reset_index(level=0, drop=True)
    activity_variance = paired_activity.groupby(asset, sort=False).rolling(
        WINDOW_MONTHS, min_periods=WINDOW_MONTHS
    ).var(ddof=0).reset_index(level=0, drop=True)
    covariance = product_mean - return_mean * activity_mean
    correlation = covariance / np.sqrt(
        return_variance.where(return_variance > 0)
        * activity_variance.where(activity_variance > 0)
    )
    oldest_month = ordered["ym"].groupby(asset).shift(WINDOW_MONTHS)
    consecutive = ordered["ym"].eq(oldest_month + WINDOW_MONTHS)
    return correlation.where(consecutive).reindex(frame.index)


FACTOR = Factor(
    name="return_trading_activity_correlation_12m",
    family="price_activity_comovement",
    category="other",
    exploration_domain="liquidity_trading",
    hypothesis=(
        "수익률과 명목 거래대금의 양의 동행성이 큰 주식에는 가격 상승기에 집중된 일시적 수요가 "
        "섞일 수 있어, 동행성이 낮은 주식보다 다음 달 상대수익이 낮다는 가설을 검증한다."
    ),
    predicted_sign=-1,
    params={"window_months": WINDOW_MONTHS, "lookback_months": WINDOW_MONTHS,
            "min_observations": WINDOW_MONTHS, "activity_measure": "log_adv20"},
    rebalance_months=1,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": "직전 12개 월수익률과 각 월말 log(ADV20)의 Pearson 상관이 낮을수록 다음 달 총수익률 순위가 높다.",
    "mechanism": (
        "가격 상승기에 상대적으로 큰 거래대금이 동반되는 특성에 비정보성 수요 압력이 섞이고 "
        "그 압력이 완화되면 이후 상대수익이 낮을 수 있다는 독립 월별 가설이다. "
        "campbell_grossman_wang_1993_volume의 거래량·가격압력 구별 논리를 참고했지만, "
        "일별 거래량과 수익률 자기상관 연구의 재현도, 해당 논문이 검증한 월별 부호도 아니다."
    ),
    "falsification": (
        "사전 고정한 음의 방향이 Discovery 및 campaign 검사를 통과하지 못하면 승격하지 않는다. "
        "크기·유동성·변동성 노출 통제 뒤 관계가 사라지거나 높은 동행성의 이후 수익이 높으면 "
        "단순 가격압력 해석은 약해진다. 일시적 수요의 직접 관측이 없으므로 원인 확정은 불가능하다."
    ),
    "expected_relationship": (
        "거래대금 수준·성장률, log(ADV20/시총)의 변동성과 달리 자기 수익률과 거래활동의 "
        "공동 변화를 측정한다. market_return_correlation_12m은 시장수익과의 동조성으로 상대 변수가 다르다. "
        "결과 없는 정의 색인의 가격×거래활동 교차 검색으로 비교했으며 엔진 중복·Gold 상관 검사를 유지한다."
    ),
    "data_notes": (
        "asset_id별 양의 adj_close 13개 연속 월말과 양의 ADV20 12개를 요구한다. "
        "ADV20은 최근 20거래일 평균 거래대금이지 주식 수 거래량·월 총량·매수주문 불균형이 아니다. "
        "명목 거래대금에는 가격의 기계적 영향이 있다. 결측·달력 공백·0분산은 NaN이며 보간하지 않는다. "
        "12개월은 검증 전 정한 설계이며 원논문 최적기간이 아니다. 현재 month 신호는 다음 달 수익과 연결한다. "
        "레짐 38축은 동결 보조진단으로만 사용한다. PIT_ASSUMED를 팩터 입력 인증으로 전용하지 않는다. "
        "공개 교훈 balance_sheet_growth_requires_construct_and_distribution_checks의 측정과 메커니즘 구별만 참고했으며 "
        "이 연구는 누적 탐색 뒤 과거 표본을 재사용한 연구이고 신규 독립 검증이 아니다."
    ),
    "mechanism_plan": {
        "version": "mechanism-scientist-v1",
        "links": [
            {"id": "measurement", "claim": "측정값은 자기 수익률과 명목 거래활동의 동행성이지 직접 수요 압력이 아니다.",
             "expected_observation": "13개월 가격과 12쌍의 거래활동이 확보되고 상관의 양·음 범위가 나타난다.",
             "would_weaken": "결측 선택 또는 크기·변동성·유동성 노출이 값의 차이를 대부분 설명한다.",
             "required_sections": ["input_quality", "selection_profile"]},
            {"id": "economic_change", "claim": "고동행성에 포함된 일시적 수요가 이후 완화될 수 있다.",
             "expected_observation": "수요·관심의 후속 변화가 동행성과 연결되어야 하며 일반 실적 변화만으로는 증명할 수 없다.",
             "would_weaken": "후속 정보·실적 개선과 지속 수요가 더 잘 설명하거나 수요 변화를 직접 관측하지 못한다.",
             "required_sections": ["economic_outcomes"]},
            {"id": "price_response", "claim": "높은 원시 상관의 가격압력이 완화되면 낮은 상관 그룹의 다음 달 상대수익이 높다.",
             "expected_observation": "부호를 적용한 점수와 다음 달 수익의 양의 관계가 한 국면에만 의존하지 않는다.",
             "would_weaken": "반대 방향이거나 통제 후 관계가 약해지고 레짐별 표본이 부족해 일반화할 수 없다.",
             "required_sections": ["monthly_performance", "controlled_comparison", "regime_comparison"]},
            {"id": "implementation", "claim": "통계적 관계가 있어도 월간 거래비용과 수용력을 감당해야 한다.",
             "expected_observation": "사전 고정 월 리밸런싱 비용 후에도 관계가 유지되고 특정 비유동 종목에 집중되지 않는다.",
             "would_weaken": "회전율·비용·낮은 수용력 때문에 순수익 구현이 어렵다.",
             "required_sections": ["execution_costs"]}
        ],
        "rivals": [
            {"id": "informative_activity", "claim": "동행성은 가격압력보다 정보 반영과 추세 지속을 반영한다.",
             "distinguishing_observation": "높은 동행성에서 후속 정보·실적과 수익이 함께 개선되는지 확인할 자료가 필요하다."},
            {"id": "nominal_exposure", "claim": "명목 거래대금의 가격 성분과 크기·유동성·변동성이 상관을 만든다.",
             "distinguishing_observation": "동일 표본 노출 통제 전후 관계와 주식 수 거래량 기반 별도 관측이 필요하다."}
        ],
        "negative_control": {"status": "NOT_PLANNED", "why_no_mechanism": "", "shared_bias_assumptions": ""}
    }
}
