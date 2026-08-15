# campaign-20260815-007 / epoch-001 성찰

- OOS 상태: **SEALED**

- Discovery 다중검정: **PENDING** (campaign finalize에서 전체 후보 일괄 판정)

## 구조적 교훈

| factor | family | outcome | novelty | evidence |
|---|---|---|---|---|
| `asset_growth_acceleration_12m` | `investment_acceleration` | WRONG_SIGN_OR_NO_EDGE | RELATED | `research/runs/cycle-0089-asset_growth_acceleration_12m/report.md` |
| `capital_stock_to_liabilities` | `nominal_capital_debt_coverage` | WRONG_SIGN_OR_NO_EDGE | DUPLICATE | `research/runs/cycle-0090-capital_stock_to_liabilities/report.md` |
| `current_assets_to_assets` | `asset_liquidity_share` | NO_PREDICTIVE_EVIDENCE | DUPLICATE | `research/runs/cycle-0091-current_assets_to_assets/report.md` |
| `book_to_market_change_12m` | `book_value_repricing` | DISCOVERY_FDR_PENDING | RELATED | `research/runs/cycle-0092-book_to_market_change_12m/report.md` |
| `capital_stock_to_assets` | `nominal_capital_intensity` | DISCOVERY_FDR_PENDING | DUPLICATE | `research/runs/cycle-0093-capital_stock_to_assets/report.md` |

## 다음 epoch에서 허용되는 학습

- 다른 경제적 family와 아직 쓰지 않은 PIT 입력을 다음 epoch 후보로 검토한다.
- 실패 원인을 데이터·무결성·예측력·강건성·중복으로 구분해 연구 우선순위를 바꾼다.
- 중복 family에서는 변형을 늘리지 말고 대표 정의 비교로 전환한다.

## 금지되는 사후 적응

- 결과를 본 후보의 부호·룩백·산식·표본을 수정하지 않는다.
- 게이트 임계값을 이번 결과에 맞춰 완화하지 않는다.
- 봉인 OOS를 열거나 OOS 결과를 다음 후보 생성에 사용하지 않는다.
