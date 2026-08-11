"""Pre-registered intermediate-momentum candidate; immutable after evaluation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.factors import Factor


FARTHEST_RETURN_LAG = 12
NEAREST_RETURN_LAG = 7
WINDOW_MONTHS = 6
SIGNAL_TO_FORMATION_MONTHS = 1
GAP_POLICY = "calendar_months_no_fill"


def compute(frame):
    ordered = frame.sort_values(["asset_id", "ym"], kind="mergesort")
    output = pd.Series(index=ordered.index, dtype=float)
    for _, group in ordered.groupby("asset_id", sort=False):
        calendar = pd.period_range(group["ym"].min(), group["ym"].max(), freq="M")
        total_return_index = group.set_index("ym")["return_close"].reindex(calendar)
        monthly_return = total_return_index.pct_change(fill_method=None)
        # The row at month s predicts the return in formation/holding month
        # t=s+1.  Therefore literature months t-12 ... t-7 map to observed
        # return months s-11 ... s-6, not s-12 ... s-7.
        formation_returns = monthly_return.shift(
            NEAREST_RETURN_LAG - SIGNAL_TO_FORMATION_MONTHS
        )
        signal = formation_returns.rolling(
            WINDOW_MONTHS, min_periods=WINDOW_MONTHS
        ).apply(lambda values: np.prod(1.0 + values) - 1.0, raw=True)
        output.loc[group.index] = signal.reindex(group["ym"]).to_numpy()
    return output.reindex(frame.index)


FACTOR = Factor(
    name="intermediate_momentum_12_7",
    family="intermediate_momentum",
    category="momentum",
    hypothesis=(
        "최근 12개월 전부터 7개월 전까지 누적된 정보가 천천히 가격에 반영되면, 해당 중기 "
        "구간의 승자는 최근 수익률을 사용하지 않아도 이후 상대수익이 높다."
    ),
    predicted_sign=1,
    params={
        "farthest_return_lag": FARTHEST_RETURN_LAG,
        "nearest_return_lag": NEAREST_RETURN_LAG,
        "window_months": WINDOW_MONTHS,
        "signal_to_formation_months": SIGNAL_TO_FORMATION_MONTHS,
        "gap_policy": GAP_POLICY,
    },
    rebalance_months=3,
    needs=(),
    compute=compute,
)


RESEARCH_SPEC = {
    "thesis": (
        "Silver 총수익지수로 측정한 t-12부터 t-7까지 정확히 6개 월수익의 복리 누적값이 "
        "높은 종목은 다음 달 총수익률 순위가 높을 것이다."
    ),
    "mechanism": (
        "기업 정보에 대한 투자자의 과소반응과 점진적 확산이 수개월 동안 가격 추세를 만들 수 "
        "있다. 최근 6개월을 완전히 제외해 단기 반전과 최근 모멘텀의 영향을 줄인다."
    ),
    "falsification": (
        "사전등록한 양의 방향이 무결성·커버리지·투자가능 IC·Rank ICIR·기간 및 중립화 "
        "강건성·campaign BY를 통과하지 못하거나 기존 팩터와 중복되면 독립적인 중기 "
        "모멘텀 가설을 기각한다. 봉인 OOS는 이번 discovery에서 열지 않는다."
    ),
    "expected_relationship": (
        "mom_12_1과 일부 과거수익 구간을 공유하므로 양의 관계는 예상한다. 그러나 t-6부터 "
        "t-1까지를 쓰지 않으므로 최근 추세·52주 고점 및 단기 반전과는 구별될 것으로 예상한다."
    ),
    "data_notes": (
        "인증된 Silver total_return_close에 매핑된 return_close로 월수익을 먼저 계산하고, "
        "다음 달을 formation month t로 두어 t-12~t-7의 6개 수익을 복리 누적한다. 종목별 "
        "달력월을 재색인하며 중간 결측을 채우지 않는다. 따라서 정확한 6개 월수익이 없는 "
        "관측은 결측이다."
    ),
}
