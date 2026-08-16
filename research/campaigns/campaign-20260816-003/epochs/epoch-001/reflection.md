# campaign-20260816-003 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `price_momentum_18_6` | `price_momentum_18_6` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0179-price_momentum_18_6/report.md` |
| `positive_return_share_24m` | `positive_return_share_24m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0180-positive_return_share_24m/report.md` |
| `amihud_mean_24m` | `amihud_mean_24m` | ROBUSTNESS_OR_DATA_GAP | DUPLICATE | `research/runs/cycle-0181-amihud_mean_24m/report.md` |
| `amihud_volatility_24m` | `amihud_volatility_24m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0182-amihud_volatility_24m/report.md` |
| `realized_daily_volatility_change_24m` | `realized_daily_volatility_change_24m` | DISCOVERY_FDR_PENDING | INDEPENDENT | `research/runs/cycle-0183-realized_daily_volatility_change_24m/report.md` |
| `market_beta_12m` | `market_beta_12m` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0184-market_beta_12m/report.md` |
| `total_asset_growth_24m` | `total_asset_growth_24m` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0185-total_asset_growth_24m/report.md` |
| `equity_growth_6m` | `equity_growth_6m` | WRONG_SIGN_OR_NO_EDGE | RELATED | `research/runs/cycle-0186-equity_growth_6m/report.md` |
| `pretax_yield_change_6m` | `pretax_yield_change_6m` | DISCOVERY_FDR_PENDING | RELATED | `research/runs/cycle-0187-pretax_yield_change_6m/report.md` |
| `retained_earnings_to_assets_change_6m` | `retained_earnings_to_assets_change_6m` | NO_PREDICTIVE_EVIDENCE | RELATED | `research/runs/cycle-0188-retained_earnings_to_assets_change_6m/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
