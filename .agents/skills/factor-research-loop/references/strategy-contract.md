# Candidate strategy contract

Create one file under `factors/candidates/`. Export exactly one `FACTOR` and one `RESEARCH_SPEC`.

```python
from __future__ import annotations

from engine.factors import Factor


def compute(frame):
    numerator = frame["operating_income_ttm"]
    denominator = frame["total_assets"].where(frame["total_assets"] > 0)
    return numerator / denominator


FACTOR = Factor(
    name="operating_roa",
    family="operating_roa",
    category="quality",
    hypothesis="영업 수익성이 높은 기업은 자산 효율성의 지속성이 과소평가된다.",
    predicted_sign=1,
    params={},
    rebalance_months=3,
    needs=("operating_income_ttm", "total_assets"),
    compute=compute,
)

RESEARCH_SPEC = {
    "thesis": "검증할 방향성 가설을 결과를 보기 전에 기술한다.",
    "mechanism": "위험보상 또는 행동·회계 메커니즘을 기술한다.",
    "falsification": "어떤 게이트 결과가 가설을 기각하는지 기술한다.",
    "expected_relationship": "어떤 기존 팩터와 관련되거나 직교할지 예상한다.",
    "data_notes": "PIT 가용일, 결측 시작일, 단위와 분모 제약을 기술한다.",
}
```

## Rules

- 후보 하나는 단일 경제 신호여야 한다. 둘 이상의 팩터 순위, z-score 또는 점수를 더하거나 가중합하지 않는다.
- 여러 원천 필드가 하나의 해석 가능한 비율을 만드는 것은 허용한다. 예: `operating_income_ttm / total_assets`.
- 다른 등록 팩터의 `f_<name>` 컬럼을 후보 산식에서 참조하지 않는다.
- Return a numeric `pandas.Series` on the input index.
- Make a larger final score mean higher expected return through `predicted_sign`.
- Put tunable numerical literals in `params`; reference those values from a named function rather than hiding them in the formula.
- Group time-series operations by `asset_id`, never ticker text.
- Use `return_close`, which is mapped only from a Silver `total_return_close` carrying the certified `krx_gross_dividend_reinvested_v1` contract.
- Commodity inputs require a separately certified point-in-time, roll-adjusted contract and a new preregistered single-exposure definition. Do not add the current historical-backfill continuous-futures series to an existing stock factor.
- Declare financial inputs in `needs`. They must already be PIT-materialized in the panel.
- Avoid masks that redefine the universe. Use denominator validity guards only to prevent undefined ratios.
- Do not winsorize, neutralize, or select a sample inside the factor; the shared gate owns those decisions.
- Use a new candidate file for any post-result revision. Preserve the original source and report.
