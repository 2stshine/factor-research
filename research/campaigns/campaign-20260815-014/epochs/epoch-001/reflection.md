# campaign-20260815-014 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `operating_coverage_change_12m` | `short_term_operating_coverage_improvement` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0139-operating_coverage_change_12m/report.md` |
| `revenue_to_current_liabilities` | `short_term_revenue_coverage` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0140-revenue_to_current_liabilities/report.md` |
| `retained_earnings_to_current_liabilities` | `internal_capital_short_debt_coverage` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0141-retained_earnings_to_current_liabilities/report.md` |
| `capital_stock_to_current_liabilities` | `legal_capital_short_debt_coverage` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0142-capital_stock_to_current_liabilities/report.md` |
| `noncurrent_assets_yield` | `long_lived_asset_value` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0143-noncurrent_assets_yield/report.md` |
| `current_liabilities_yield` | `market_short_debt_burden` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0144-current_liabilities_yield/report.md` |
| `amihud_volatility_12m` | `liquidity_instability` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0145-amihud_volatility_12m/report.md` |
| `trading_value_volatility_12m` | `trading_attention_instability` | ROBUSTNESS_OR_DATA_GAP | RELATED | `research/runs/cycle-0146-trading_value_volatility_12m/report.md` |
| `return_persistence_12m` | `monthly_return_persistence` | WRONG_SIGN_OR_NO_EDGE | INDEPENDENT | `research/runs/cycle-0147-return_persistence_12m/report.md` |
| `nonoperating_burden_margin` | `nonoperating_sales_burden` | DISCOVERY_FDR_PENDING | DUPLICATE | `research/runs/cycle-0148-nonoperating_burden_margin/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
