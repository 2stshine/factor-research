# campaign-20260815-015 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `net_income_to_capital_stock` | `legal_capital_net_return` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0149-net_income_to_capital_stock/report.md` |
| `retained_earnings_to_noncurrent_liabilities` | `internal_capital_long_debt_coverage` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0150-retained_earnings_to_noncurrent_liabilities/report.md` |
| `working_capital_growth_12m` | `working_capital_investment` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0151-working_capital_growth_12m/report.md` |
| `equity_debt_coverage_change_12m` | `book_solvency_improvement` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0152-equity_debt_coverage_change_12m/report.md` |
| `capital_stock_share_change_12m` | `contributed_capital_share_change` | NO_PREDICTIVE_EVIDENCE | RELATED | `research/runs/cycle-0153-capital_stock_share_change_12m/report.md` |
| `noncurrent_assets_to_capital_stock` | `legal_capital_long_asset_backing` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0154-noncurrent_assets_to_capital_stock/report.md` |
| `noncurrent_liabilities_yield` | `market_long_debt_burden` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0155-noncurrent_liabilities_yield/report.md` |
| `adv20_change_12m` | `trading_liquidity_growth` | ROBUSTNESS_OR_DATA_GAP | DUPLICATE | `research/runs/cycle-0156-adv20_change_12m/report.md` |
| `price_recovery_12m` | `price_recovery_from_low` | WRONG_SIGN_OR_NO_EDGE | RELATED | `research/runs/cycle-0157-price_recovery_12m/report.md` |
| `return_gain_loss_ratio_12m` | `return_magnitude_asymmetry` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0158-return_gain_loss_ratio_12m/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
