# campaign-20260816-004 / epoch-0001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `price_momentum_24_6` | `price_momentum_24_6` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0189-price_momentum_24_6/report.md` |
| `return_seasonality_12m` | `return_seasonality_12m` | NO_PREDICTIVE_EVIDENCE | INDEPENDENT | `research/runs/cycle-0190-return_seasonality_12m/report.md` |
| `amihud_mean_36m` | `amihud_mean_36m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0191-amihud_mean_36m/report.md` |
| `amihud_volatility_36m` | `amihud_volatility_36m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0192-amihud_volatility_36m/report.md` |
| `realized_daily_volatility_instability_6m` | `realized_daily_volatility_instability_6m` | DISCOVERY_FDR_PENDING | RELATED | `research/runs/cycle-0193-realized_daily_volatility_instability_6m/report.md` |
| `market_beta_18m` | `market_beta_18m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0194-market_beta_18m/report.md` |
| `total_asset_growth_30m` | `total_asset_growth_30m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0195-total_asset_growth_30m/report.md` |
| `equity_growth_24m` | `equity_growth_24m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0196-equity_growth_24m/report.md` |
| `enterprise_sales_yield_change_6m` | `enterprise_sales_yield_change_6m` | DISCOVERY_FDR_PENDING | RELATED | `research/runs/cycle-0197-enterprise_sales_yield_change_6m/report.md` |
| `net_to_operating_income_conversion` | `net_to_operating_income_conversion` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0198-net_to_operating_income_conversion/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
