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
    exploration_domain="profitability_quality",
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
- Candidate code receives only the authenticated `2015-01` onward research view. Common IC evaluation remains fixed at `2018-03` after warm-up.
- The maximum permitted lookback is 36 months. Declare every time-series horizon in `params` with an interpretable month/lag/window key; an undeclared horizon or a value above 36 months is fail-closed before registration or computation.
- Candidate modules are declarative files: only the approved numerical-library imports are allowed, import-time I/O is forbidden, and the full file SHA-256 is frozen in the epoch. Candidate functions never receive raw `close`, `total_return_close`, the removed legacy alias `return_close`, `fwd_*` labels, cached `f_*` signals, or universe/lineage metadata. Every authoritative signal month is computed separately from that month's cross-section and no more than the candidate's declared trailing lookback. Static validation rejects unbounded asset-history GroupBy reducers while allowing explicit rolling windows of at most 36 months and same-month cross-sectional operations.
- Historical price features (momentum, reversal, volatility, beta, MAX, Amihud, price anchors) use `adj_close` and therefore mean **split-adjusted price return**, not dividend total return. The latest-revision ex-post `krx_gross_dividend_reinvested_v3/CERTIFIED` `total_return_close` is evaluator-only data used to construct next-month forward-return and IC labels.
- Direct dividend features remain disabled until Silver certifies a separate historical-vintage/known-at action contract. The latest-corrected ex-post action ledger must never be upgraded into feature evidence by locally synthesized metadata.
- Commodity inputs require a separately certified point-in-time, roll-adjusted contract and a new preregistered single-exposure definition. Do not add the current historical-backfill continuous-futures series to an existing stock factor.
- Declare financial inputs in `needs`. They must already be PIT-materialized in the panel.
- Declare one `exploration_domain` for every new candidate. Allowed values are `value`, `profitability_quality`, `investment_capital_allocation`, `momentum_trend_reversal`, `low_risk`, `liquidity_trading`, `financing_issuance`, and `size`. This metadata describes the preregistered economic mechanism; it must not be selected or changed after seeing IC or OOS results.
- For batches of at least five candidates, cover at least three explicit exploration domains. A ten-candidate batch covers at least five domains and contains no more than two candidates from one domain. If an intended domain lacks certified PIT inputs, submit fewer candidates instead of using a proxy or relabeling another accounting ratio.
- Avoid masks that redefine the universe. Use denominator validity guards only to prevent undefined ratios.
- Do not winsorize, neutralize, or select a sample inside the factor; the shared gate owns those decisions.
- Use a new candidate file for any post-result revision. Preserve the original source and report.
