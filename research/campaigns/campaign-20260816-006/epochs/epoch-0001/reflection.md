# campaign-20260816-006 / epoch-0001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `adv_turnover_mean_24m` | `adv_turnover_mean_24m` | ROBUSTNESS_OR_DATA_GAP | DUPLICATE | `research/runs/cycle-0209-adv_turnover_mean_24m/report.md` |
| `price_reversal_3_1` | `price_reversal_3_1` | NO_PREDICTIVE_EVIDENCE | RELATED | `research/runs/cycle-0210-price_reversal_3_1/report.md` |
| `market_return_correlation_6m` | `market_return_correlation_6m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0211-market_return_correlation_6m/report.md` |
| `max_daily_return_change_18m` | `max_daily_return_change_18m` | ROBUSTNESS_OR_DATA_GAP | RELATED | `research/runs/cycle-0212-max_daily_return_change_18m/report.md` |
| `pretax_yield_change_12m` | `pretax_yield_change_12m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0213-pretax_yield_change_12m/report.md` |
| `market_leverage_change_18m` | `market_leverage_change_18m` | WRONG_SIGN_OR_NO_EDGE | RELATED | `research/runs/cycle-0214-market_leverage_change_18m/report.md` |
| `noncurrent_asset_growth_18m` | `noncurrent_asset_growth_18m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0215-noncurrent_asset_growth_18m/report.md` |
| `net_equity_issuance_price_adjusted_36m` | `net_equity_issuance_price_adjusted_36m` | DISCOVERY_FDR_PENDING | DUPLICATE | `research/runs/cycle-0216-net_equity_issuance_price_adjusted_36m/report.md` |
| `pretax_to_operating_income_conversion` | `pretax_to_operating_income_conversion` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0217-pretax_to_operating_income_conversion/report.md` |
| `working_capital_accruals_24m` | `working_capital_accruals_24m` | WRONG_SIGN_OR_NO_EDGE | RELATED | `research/runs/cycle-0218-working_capital_accruals_24m/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
