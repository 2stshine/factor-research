# campaign-20260816-002 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `price_momentum_15_3` | `price_momentum_15_3` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0169-price_momentum_15_3/report.md` |
| `price_recovery_24m` | `price_recovery_24m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0170-price_recovery_24m/report.md` |
| `amihud_mean_18m` | `amihud_mean_18m` | ROBUSTNESS_OR_DATA_GAP | DUPLICATE | `research/runs/cycle-0171-amihud_mean_18m/report.md` |
| `amihud_volatility_18m` | `amihud_volatility_18m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0172-amihud_volatility_18m/report.md` |
| `max_daily_return_change_6m` | `max_daily_return_change_6m` | ROBUSTNESS_OR_DATA_GAP | RELATED | `research/runs/cycle-0173-max_daily_return_change_6m/report.md` |
| `market_beta_9m` | `market_beta_9m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0174-market_beta_9m/report.md` |
| `total_asset_growth_18m` | `total_asset_growth_18m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0175-total_asset_growth_18m/report.md` |
| `capital_stock_growth_18m` | `capital_stock_growth_18m` | DISCOVERY_FDR_PENDING | DUPLICATE | `research/runs/cycle-0176-capital_stock_growth_18m/report.md` |
| `earnings_yield_change_12m` | `earnings_yield_change_12m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0177-earnings_yield_change_12m/report.md` |
| `net_margin_change_6m` | `net_margin_change_6m` | NO_PREDICTIVE_EVIDENCE | RELATED | `research/runs/cycle-0178-net_margin_change_6m/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
