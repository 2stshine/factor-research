# campaign-20260816-007 / epoch-0001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `adv_turnover_mean_36m` | `adv_turnover_mean_36m` | ROBUSTNESS_OR_DATA_GAP | DUPLICATE | `research/runs/cycle-0219-adv_turnover_mean_36m/report.md` |
| `price_reversal_6_3` | `price_reversal_6_3` | NO_PREDICTIVE_EVIDENCE | RELATED | `research/runs/cycle-0220-price_reversal_6_3/report.md` |
| `market_return_correlation_9m` | `market_return_correlation_9m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0221-market_return_correlation_9m/report.md` |
| `max_daily_return_instability_18m` | `max_daily_return_instability_18m` | DISCOVERY_FDR_PENDING | DUPLICATE | `research/runs/cycle-0222-max_daily_return_instability_18m/report.md` |
| `enterprise_earnings_yield_change_12m` | `enterprise_earnings_yield_change_12m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0223-enterprise_earnings_yield_change_12m/report.md` |
| `market_leverage_change_24m` | `market_leverage_change_24m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0224-market_leverage_change_24m/report.md` |
| `noncurrent_asset_growth_24m` | `noncurrent_asset_growth_24m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0225-noncurrent_asset_growth_24m/report.md` |
| `retained_earnings_to_assets_volatility_12m` | `retained_earnings_to_assets_volatility_12m` | DISCOVERY_FDR_PENDING | INDEPENDENT | `research/runs/cycle-0226-retained_earnings_to_assets_volatility_12m/report.md` |
| `trading_value_turnover_change_3m` | `trading_value_turnover_change_3m` | ROBUSTNESS_OR_DATA_GAP | INDEPENDENT | `research/runs/cycle-0227-trading_value_turnover_change_3m/report.md` |
| `market_relative_momentum_6_1` | `market_relative_momentum_6_1` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0228-market_relative_momentum_6_1/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
