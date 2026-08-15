# campaign-20260815-013 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `retained_earnings_to_noncurrent_assets` | `internal_capital_long_asset_backing` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0129-retained_earnings_to_noncurrent_assets/report.md` |
| `retained_earnings_to_current_assets` | `internal_capital_current_asset_backing` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0130-retained_earnings_to_current_assets/report.md` |
| `capital_stock_to_current_assets` | `legal_capital_current_asset_intensity` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0131-capital_stock_to_current_assets/report.md` |
| `equity_to_current_liabilities` | `short_term_equity_solvency` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0132-equity_to_current_liabilities/report.md` |
| `operating_income_to_capital_stock` | `legal_capital_operating_return` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0133-operating_income_to_capital_stock/report.md` |
| `current_assets_yield` | `liquid_asset_value` | GOLD_REDUNDANCY | DUPLICATE | `research/runs/cycle-0134-current_assets_yield/report.md` |
| `daily_volatility_change_12m` | `risk_deterioration` | ROBUSTNESS_OR_DATA_GAP | INDEPENDENT | `research/runs/cycle-0135-daily_volatility_change_12m/report.md` |
| `max_daily_return_change_12m` | `lottery_demand_acceleration` | ROBUSTNESS_OR_DATA_GAP | RELATED | `research/runs/cycle-0136-max_daily_return_change_12m/report.md` |
| `market_relative_momentum_12_1` | `market_relative_momentum` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0137-market_relative_momentum_12_1/report.md` |
| `turnover_change_6m` | `trading_attention_change` | ROBUSTNESS_OR_DATA_GAP | INDEPENDENT | `research/runs/cycle-0138-turnover_change_6m/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
